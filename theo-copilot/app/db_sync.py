"""Synchronous Postgres access for the Streamlit app.

Streamlit isn't async-friendly. asyncpg would need event-loop dancing.
psycopg2 is the path of least resistance here, and it's already in
pyproject.toml.

Cached via st.cache_resource for the connection pool itself.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras
import streamlit as st
from dotenv import load_dotenv

for _candidate in [
    Path("/opt/fletcher/.env"),
    Path(__file__).resolve().parent.parent.parent / ".env",
    Path.cwd() / ".env",
]:
    if _candidate.exists():
        load_dotenv(_candidate)
        break


@st.cache_resource
def get_conn():
    """Single per-session psycopg2 connection. Streamlit caches across reruns."""
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SET search_path TO theo, public")
    return conn


def _query(sql: str, args: tuple = ()) -> list[dict[str, Any]]:
    conn = get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, args)
        return [dict(r) for r in cur.fetchall()]


def _query_one(sql: str, args: tuple = ()) -> dict[str, Any] | None:
    rows = _query(sql, args)
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# Reads (used by Streamlit views)
# ---------------------------------------------------------------------------


def fetch_ticket_list(limit: int = 50) -> list[dict]:
    return _query(
        """
        SELECT t.id, t.unit_id, t.category, t.priority, t.status, t.opened_at,
               t.classified_intent,
               t.enrichment->'prior_incidents'->>'count' AS pattern_count,
               u.label AS unit_label,
               COALESCE(tn.name, 'unknown') AS tenant_name,
               ct.channel
        FROM theo.tickets t
        LEFT JOIN theo.units u ON u.id = t.unit_id
        LEFT JOIN theo.leases l ON l.unit_id = u.id AND l.status = 'active'
        LEFT JOIN theo.tenants tn ON tn.id = l.tenant_id
        LEFT JOIN theo.channel_threads ct ON ct.id = t.source_thread_id
        ORDER BY t.opened_at DESC NULLS LAST
        LIMIT %s
        """,
        (limit,),
    )


def fetch_ticket(ticket_id: str) -> dict | None:
    row = _query_one(
        """
        SELECT t.*,
               u.label AS unit_label, u.qm AS unit_qm,
               p.id AS property_id, p.name AS property_name, p.address AS property_address,
               tn.id AS tenant_id, tn.name AS tenant_name,
               tn.email AS tenant_email, tn.phone AS tenant_phone,
               tn.metadata AS tenant_metadata,
               l.rent_cold AS lease_rent_cold, l.start_date AS lease_start
        FROM theo.tickets t
        LEFT JOIN theo.units u ON u.id = t.unit_id
        LEFT JOIN theo.properties p ON p.id = u.property_id
        LEFT JOIN theo.leases l ON l.unit_id = u.id AND l.status = 'active'
        LEFT JOIN theo.tenants tn ON tn.id = l.tenant_id
        WHERE t.id = %s
        """,
        (ticket_id,),
    )
    if row is None:
        return None
    # tenant_metadata comes back as a dict already (psycopg2 JSONB)
    return row


def fetch_thread_messages(thread_id: str | None) -> list[dict]:
    if not thread_id:
        return []
    return _query(
        "SELECT * FROM theo.channel_messages WHERE thread_id = %s "
        "ORDER BY sent_at ASC",
        (thread_id,),
    )


def fetch_trace_events(ticket_id: str) -> list[dict]:
    return _query(
        "SELECT step, kind, payload, created_at FROM theo.trace_events "
        "WHERE ticket_id = %s ORDER BY step ASC, id ASC",
        (ticket_id,),
    )


# ---------------------------------------------------------------------------
# Writes (called from action_panel after Approve & Send)
# ---------------------------------------------------------------------------


def execute_send_whatsapp(thread_id: str, body: str) -> dict:
    """Send via Baileys bridge if reachable, else log-only (DB insert).

    Always inserts an outbound row so the Streamlit UI shows the reply
    immediately. If the Baileys bridge is up, also fires the real WhatsApp
    send. Returns {sent_to_whatsapp: bool, error?: str}.
    """
    import requests
    conn = get_conn()
    sent_to_whatsapp = False
    error = None

    # Find the recipient phone via the channel thread → tenant
    recipient_phone: str | None = None
    with conn.cursor() as cur:
        cur.execute(
            "SELECT tn.phone FROM theo.channel_threads ct "
            "JOIN theo.tenants tn ON tn.id = ct.tenant_id WHERE ct.id = %s",
            (thread_id,),
        )
        row = cur.fetchone()
        if row:
            recipient_phone = row[0]

    bridge_url = os.environ.get("WHATSAPP_BRIDGE_URL", "http://127.0.0.1:8003")
    if recipient_phone:
        try:
            r = requests.post(
                f"{bridge_url}/send",
                json={"to": recipient_phone, "body": body},
                timeout=8,
            )
            if r.ok:
                sent_to_whatsapp = True
            else:
                error = f"bridge {r.status_code}: {r.text[:200]}"
        except Exception as e:  # noqa: BLE001
            error = f"bridge unreachable: {e}"

    # Always record the outbound message in our channel log
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO theo.channel_messages (id, thread_id, direction, sender, "
            "body, sent_at) VALUES (gen_random_uuid()::text, %s, 'outbound', "
            "'Sarah Weber', %s, now())",
            (thread_id, body),
        )
        cur.execute(
            "UPDATE theo.channel_threads SET last_message_at = now() WHERE id = %s",
            (thread_id,),
        )

    return {"sent_to_whatsapp": sent_to_whatsapp, "error": error,
            "recipient": recipient_phone}


def execute_dispatch_vendor(vendor_id: str, ticket_id: str, scope: str, urgency: str) -> None:
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO theo.vendor_dispatches (ticket_id, vendor_id, scope, urgency, "
            "dispatched_at) VALUES (%s, %s, %s, %s, now())",
            (ticket_id, vendor_id, scope, urgency),
        )
        cur.execute(
            "UPDATE theo.tickets SET status = 'awaiting_vendor', vendor_id = %s "
            "WHERE id = %s",
            (vendor_id, ticket_id),
        )


def execute_approve_offer(offer_id: str) -> dict | None:
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE theo.vendor_offers SET status = 'approved' WHERE id = %s "
            "RETURNING id, vendor_id, amount",
            (offer_id,),
        )
        row = cur.fetchone()
    return {"id": row[0], "vendor_id": row[1], "amount": float(row[2])} if row else None


def update_proposed_action(proposal_id: int, status: str) -> None:
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE theo.proposed_actions SET status = %s WHERE id = %s",
            (status, proposal_id),
        )
