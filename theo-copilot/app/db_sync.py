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
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn) -> None:
    """Idempotent schema upgrades — keeps the demo runnable without
    requiring anyone to apply migrations manually. Mirrors
    infra/migrations/002_archive.sql."""
    with conn.cursor() as cur:
        cur.execute(
            """
            ALTER TABLE theo.tickets
                ADD COLUMN IF NOT EXISTS done_at         TIMESTAMPTZ,
                ADD COLUMN IF NOT EXISTS done_by         TEXT,
                ADD COLUMN IF NOT EXISTS resolution_note TEXT;
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_tickets_done_at "
            "ON theo.tickets(done_at) WHERE done_at IS NOT NULL"
        )


# How long a ticket lingers in the inbox after being marked done.
DONE_GRACE_HOURS = 72


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


_TICKET_LIST_SELECT = """
    SELECT t.id, t.unit_id, t.category, t.priority, t.status, t.opened_at,
           t.classified_intent, t.full_text,
           t.done_at, t.done_by, t.resolution_note,
           t.enrichment->'prior_incidents'->>'count' AS pattern_count,
           t.enrichment->>'autonomy_mode' AS autonomy_mode,
           u.label AS unit_label,
           -- Prefer the sender (channel_thread.tenant_id) over the
           -- unit-resident (lease-tenant). For most tickets they're the
           -- same; for vendor-side mail (Schornsteinfeger, etc.) only
           -- the channel_thread has the right party.
           COALESCE(tn_ct.name, tn_lease.name, 'unknown') AS tenant_name,
           ct.channel,
           -- Derived state: open / done / archived.
           CASE
             WHEN t.done_at IS NULL AND COALESCE(t.status, '') != 'closed'
               THEN 'open'
             WHEN t.done_at IS NOT NULL
                  AND t.done_at >= now() - (INTERVAL '1 hour' * %(grace)s)
               THEN 'done'
             ELSE 'archived'
           END AS derived_state
    FROM theo.tickets t
    LEFT JOIN theo.units u ON u.id = t.unit_id
    LEFT JOIN theo.leases l ON l.unit_id = u.id AND l.status = 'active'
    LEFT JOIN theo.tenants tn_lease ON tn_lease.id = l.tenant_id
    LEFT JOIN theo.channel_threads ct ON ct.id = t.source_thread_id
    LEFT JOIN theo.tenants tn_ct ON tn_ct.id = ct.tenant_id
"""


def fetch_ticket_list(
    view: str = "inbox",
    limit: int = 50,
    search: str | None = None,
) -> list[dict]:
    """Return tickets for the given view.

    view='inbox'   → open + recently-done (within DONE_GRACE_HOURS).
    view='archive' → archived (older done_at) + legacy status='closed'.
    """
    if view == "archive":
        where = (
            "WHERE (t.done_at IS NOT NULL "
            "       AND t.done_at < now() - (INTERVAL '1 hour' * %(grace)s)) "
            "   OR COALESCE(t.status, '') = 'closed'"
        )
        order = (
            "ORDER BY COALESCE(t.done_at, t.opened_at) DESC NULLS LAST"
        )
    else:
        where = (
            "WHERE (t.done_at IS NULL AND COALESCE(t.status, '') != 'closed') "
            "   OR (t.done_at IS NOT NULL "
            "       AND t.done_at >= now() - (INTERVAL '1 hour' * %(grace)s))"
        )
        # State wins — Done tickets sort below the still-open ones. Within
        # each group: priority (DRINGEND first), then recency. Mirrors the
        # Next.js backend (intake/api_routes.py::list_tickets).
        order = (
            "ORDER BY "
            "  CASE WHEN t.done_at IS NULL THEN 0 ELSE 1 END, "
            "  CASE t.priority "
            "    WHEN 'DRINGEND' THEN 0 "
            "    WHEN 'Wichtig'  THEN 1 "
            "    WHEN 'Hoch'     THEN 1 "
            "    ELSE 2 END, "
            "  t.opened_at DESC NULLS LAST"
        )

    params: dict[str, Any] = {"grace": DONE_GRACE_HOURS, "limit": limit}
    if search:
        where += (
            " AND (LOWER(COALESCE(tn_ct.name, tn_lease.name, '')) LIKE %(q)s "
            "  OR  LOWER(COALESCE(u.label, ''))                LIKE %(q)s "
            "  OR  LOWER(COALESCE(t.classified_intent, ''))    LIKE %(q)s "
            "  OR  LOWER(COALESCE(t.full_text, ''))            LIKE %(q)s "
            "  OR  LOWER(COALESCE(t.resolution_note, ''))      LIKE %(q)s)"
        )
        params["q"] = f"%{search.lower()}%"

    return _query(
        f"{_TICKET_LIST_SELECT} {where} {order} LIMIT %(limit)s",
        params,
    )


def count_open_tickets() -> int:
    """For the 'Inbox · N' tab badge — counts only truly open tickets,
    not the Done-but-still-visible ones."""
    row = _query_one(
        "SELECT COUNT(*)::int AS n FROM theo.tickets "
        "WHERE done_at IS NULL AND COALESCE(status, '') != 'closed'"
    )
    return int(row["n"]) if row else 0


def mark_ticket_done(
    ticket_id: str,
    done_by: str,
    resolution_note: str | None = None,
) -> None:
    """Mark a ticket as done. Stays visible in the inbox until
    done_at < now() - DONE_GRACE_HOURS, after which it's archived."""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE theo.tickets "
            "SET done_at = now(), done_by = %s, resolution_note = %s "
            "WHERE id = %s",
            (done_by, resolution_note, ticket_id),
        )
        # Audit trail
        cur.execute(
            "INSERT INTO theo.trace_events (ticket_id, step, kind, payload, "
            "created_at) VALUES (%s, "
            "  (SELECT COALESCE(MAX(step), 0) + 1 "
            "   FROM theo.trace_events WHERE ticket_id = %s), "
            "  'marked_done', %s::jsonb, now())",
            (
                ticket_id,
                ticket_id,
                json.dumps(
                    {"by": done_by, "resolution_note": resolution_note or ""}
                ),
            ),
        )


def reopen_ticket(ticket_id: str, reopened_by: str = "Sarah Weber") -> None:
    """Return a Done or Archived ticket to the Open state.

    Also flips status='closed' (legacy seed tickets) → 'open' so the
    row leaves the archive's `OR status='closed'` match.
    """
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE theo.tickets "
            "SET done_at = NULL, "
            "    done_by = NULL, "
            "    resolution_note = NULL, "
            "    status = CASE WHEN status = 'closed' THEN 'open' "
            "                  ELSE status END "
            "WHERE id = %s",
            (ticket_id,),
        )
        cur.execute(
            "INSERT INTO theo.trace_events (ticket_id, step, kind, payload, "
            "created_at) VALUES (%s, "
            "  (SELECT COALESCE(MAX(step), 0) + 1 "
            "   FROM theo.trace_events WHERE ticket_id = %s), "
            "  'reopened', %s::jsonb, now())",
            (ticket_id, ticket_id, json.dumps({"by": reopened_by})),
        )


def fetch_ticket(ticket_id: str) -> dict | None:
    row = _query_one(
        """
        SELECT t.*,
               u.label AS unit_label, u.qm AS unit_qm,
               p.id AS property_id, p.name AS property_name,
               p.address AS property_address,
               -- Prefer the actual sender (channel_thread.tenant_id) so vendor-
               -- side tickets show the vendor, not the unit's resident.
               COALESCE(tn_ct.id, tn_lease.id) AS tenant_id,
               COALESCE(tn_ct.name, tn_lease.name) AS tenant_name,
               COALESCE(tn_ct.email, tn_lease.email) AS tenant_email,
               COALESCE(tn_ct.phone, tn_lease.phone) AS tenant_phone,
               COALESCE(tn_ct.metadata, tn_lease.metadata) AS tenant_metadata,
               l.rent_cold AS lease_rent_cold, l.start_date AS lease_start,
               CASE
                 WHEN t.done_at IS NULL AND COALESCE(t.status, '') != 'closed'
                   THEN 'open'
                 WHEN t.done_at IS NOT NULL
                      AND t.done_at >= now() - (INTERVAL '1 hour' * %s)
                   THEN 'done'
                 ELSE 'archived'
               END AS derived_state
        FROM theo.tickets t
        LEFT JOIN theo.units u ON u.id = t.unit_id
        LEFT JOIN theo.properties p ON p.id = u.property_id
        LEFT JOIN theo.leases l ON l.unit_id = u.id AND l.status = 'active'
        LEFT JOIN theo.tenants tn_lease ON tn_lease.id = l.tenant_id
        LEFT JOIN theo.channel_threads ct ON ct.id = t.source_thread_id
        LEFT JOIN theo.tenants tn_ct ON tn_ct.id = ct.tenant_id
        WHERE t.id = %s
        """,
        (DONE_GRACE_HOURS, ticket_id),
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

    # Always record the outbound message in our channel log + auto-reopen any
    # Done ticket on this thread (per spec §6.2: a reply implicitly reopens).
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
        cur.execute(
            "UPDATE theo.tickets "
            "SET done_at = NULL, done_by = NULL, resolution_note = NULL "
            "WHERE source_thread_id = %s AND done_at IS NOT NULL "
            "RETURNING id",
            (thread_id,),
        )
        reopened = [r[0] for r in cur.fetchall()]

    return {"sent_to_whatsapp": sent_to_whatsapp, "error": error,
            "recipient": recipient_phone, "reopened_tickets": reopened}


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


# ---------------------------------------------------------------------------
# Atomic bundle execution (bundle_approve mode)
# ---------------------------------------------------------------------------

def execute_bundle(ticket: dict, actions: list[dict]) -> dict:
    """Execute a sorted list of actions atomically.

    All Postgres writes happen in a single transaction. The irreversible
    WhatsApp /send call to the Baileys bridge runs LAST, AFTER the
    transaction commits — so a DB rollback never strands a real WhatsApp
    message in flight.

    Returns: {ok: bool, executed: int, warnings: list[str], error?: str}
    """
    import json
    import requests

    conn = get_conn()

    # Split: DB-side actions (rollbackable) vs. the WhatsApp send (irreversible)
    db_actions = [a for a in actions if a.get("action_type") != "send_whatsapp_reply"]
    whatsapp_actions = [a for a in actions if a.get("action_type") == "send_whatsapp_reply"]

    warnings: list[str] = []
    executed = 0

    # ---- Phase 1: all DB writes in one tx ---------------------------------
    try:
        prev_autocommit = conn.autocommit
        conn.autocommit = False
        with conn.cursor() as cur:
            for action in db_actions:
                atype = action.get("action_type")
                payload = action.get("payload") or {}
                if atype == "dispatch_vendor":
                    cur.execute(
                        "INSERT INTO theo.vendor_dispatches (ticket_id, vendor_id, "
                        "scope, urgency, dispatched_at) VALUES (%s, %s, %s, %s, now())",
                        (ticket["id"], payload.get("vendor_id"),
                         payload.get("scope", ""), payload.get("urgency", "Standard")),
                    )
                    cur.execute(
                        "UPDATE theo.tickets SET status='awaiting_vendor', "
                        "vendor_id=%s WHERE id=%s",
                        (payload.get("vendor_id"), ticket["id"]),
                    )
                elif atype == "approve_offer":
                    cur.execute(
                        "UPDATE theo.vendor_offers SET status='approved' WHERE id=%s",
                        (payload.get("offer_id"),),
                    )
                elif atype == "send_email_reply":
                    cur.execute(
                        "INSERT INTO theo.emails (id, from_address, to_address, "
                        "subject, body, received_at, thread_id, unit_id) "
                        "VALUES (gen_random_uuid()::text, %s, %s, %s, %s, now(), %s, NULL)",
                        ("sarah.weber@hallotheo.de", "<recipient>",
                         payload.get("subject", ""), payload.get("body", ""),
                         ticket.get("source_thread_id")),
                    )
                else:
                    # request_invoice_itemization / escalate_to_human — log to
                    # proposed_actions as 'approved'; no real I/O.
                    cur.execute(
                        "INSERT INTO theo.proposed_actions (proposed_at, action_type, "
                        "payload, rationale, status) "
                        "VALUES (now(), %s, %s::jsonb, %s, 'approved')",
                        (atype, json.dumps(payload), action.get("rationale", "")),
                    )
                executed += 1
            conn.commit()
    except Exception as e:  # noqa: BLE001
        try:
            conn.rollback()
        except Exception:
            pass
        return {"ok": False, "executed": 0, "warnings": [],
                "error": f"DB rollback: {e}"}
    finally:
        conn.autocommit = prev_autocommit

    # ---- Phase 2: irreversible WhatsApp send ------------------------------
    import os
    bridge_url = os.environ.get("WHATSAPP_BRIDGE_URL", "http://127.0.0.1:8003")
    for action in whatsapp_actions:
        payload = action.get("payload") or {}
        thread_id = payload.get("thread_id") or ticket.get("source_thread_id")
        body = payload.get("body", "")
        if not thread_id or not body:
            warnings.append("WhatsApp-Aktion ohne Inhalt übersprungen.")
            continue
        # Find recipient phone
        with conn.cursor() as cur:
            cur.execute(
                "SELECT tn.phone FROM theo.channel_threads ct "
                "JOIN theo.tenants tn ON tn.id = ct.tenant_id WHERE ct.id = %s",
                (thread_id,),
            )
            row = cur.fetchone()
        recipient = row[0] if row else None
        sent_ok = False
        if recipient:
            try:
                r = requests.post(
                    f"{bridge_url}/send",
                    json={"to": recipient, "body": body},
                    timeout=8,
                )
                sent_ok = r.ok
                if not r.ok:
                    warnings.append(
                        f"WhatsApp-Bridge {r.status_code}: {r.text[:120]}. "
                        "Bitte manuell senden."
                    )
            except Exception as e:  # noqa: BLE001
                warnings.append(f"WhatsApp-Bridge unerreichbar: {e}. Bitte manuell senden.")
        # Always log the outbound row so the UI shows the reply
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO theo.channel_messages (id, thread_id, direction, sender, "
                "body, sent_at) VALUES (gen_random_uuid()::text, %s, 'outbound', "
                "'Sarah Weber', %s, now())",
                (thread_id, body),
            )
            cur.execute(
                "UPDATE theo.channel_threads SET last_message_at=now() WHERE id=%s",
                (thread_id,),
            )
        executed += 1

    return {"ok": True, "executed": executed, "warnings": warnings}
