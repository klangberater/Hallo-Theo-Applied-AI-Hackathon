"""HTTP API endpoints for the Next.js SPA.

Read endpoints: tickets list, ticket detail, trace events, channel thread.
Write endpoints: execute a single action, execute a bundle atomically,
demo controls (fire scenarios, reset).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from infra.db import connect

log = logging.getLogger("api")

router = APIRouter()  # nginx strips '/api/' before forwarding


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------


@router.get("/tickets")
async def list_tickets(limit: int = 50) -> list[dict]:
    """Inbox list. Joins through channel_thread + lease to resolve the sender."""
    async with connect() as conn:
        rows = await conn.fetch(
            """
            SELECT t.id, t.unit_id, t.category, t.priority, t.status, t.opened_at,
                   t.classified_intent, t.full_text,
                   t.enrichment->'prior_incidents'->>'count' AS pattern_count,
                   t.enrichment->>'autonomy_mode' AS autonomy_mode,
                   u.label AS unit_label,
                   COALESCE(tn_ct.name, tn_lease.name, 'unknown') AS tenant_name,
                   ct.channel
            FROM theo.tickets t
            LEFT JOIN theo.units u ON u.id = t.unit_id
            LEFT JOIN theo.leases l ON l.unit_id = u.id AND l.status = 'active'
            LEFT JOIN theo.tenants tn_lease ON tn_lease.id = l.tenant_id
            LEFT JOIN theo.channel_threads ct ON ct.id = t.source_thread_id
            LEFT JOIN theo.tenants tn_ct ON tn_ct.id = ct.tenant_id
            ORDER BY
                CASE WHEN t.enrichment->>'autonomy_mode' = 'autonomous_done'
                     THEN 0 ELSE 1 END,
                t.opened_at DESC NULLS LAST
            LIMIT $1
            """,
            limit,
        )
    return [dict(r) for r in rows]


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str) -> dict:
    async with connect() as conn:
        row = await conn.fetchrow(
            """
            SELECT t.*,
                   u.label AS unit_label, u.qm AS unit_qm,
                   p.id AS property_id, p.name AS property_name,
                   p.address AS property_address,
                   COALESCE(tn_ct.id, tn_lease.id) AS tenant_id,
                   COALESCE(tn_ct.name, tn_lease.name) AS tenant_name,
                   COALESCE(tn_ct.email, tn_lease.email) AS tenant_email,
                   COALESCE(tn_ct.phone, tn_lease.phone) AS tenant_phone,
                   COALESCE(tn_ct.metadata, tn_lease.metadata) AS tenant_metadata,
                   l.rent_cold AS lease_rent_cold, l.start_date AS lease_start
            FROM theo.tickets t
            LEFT JOIN theo.units u ON u.id = t.unit_id
            LEFT JOIN theo.properties p ON p.id = u.property_id
            LEFT JOIN theo.leases l ON l.unit_id = u.id AND l.status = 'active'
            LEFT JOIN theo.tenants tn_lease ON tn_lease.id = l.tenant_id
            LEFT JOIN theo.channel_threads ct ON ct.id = t.source_thread_id
            LEFT JOIN theo.tenants tn_ct ON tn_ct.id = ct.tenant_id
            WHERE t.id = $1
            """,
            ticket_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail="ticket not found")
    return dict(row)


@router.get("/tickets/{ticket_id}/trace")
async def get_trace(ticket_id: str) -> list[dict]:
    async with connect() as conn:
        rows = await conn.fetch(
            "SELECT step, kind, payload, created_at FROM theo.trace_events "
            "WHERE ticket_id = $1 ORDER BY step ASC, id ASC",
            ticket_id,
        )
    return [dict(r) for r in rows]


@router.get("/tickets/{ticket_id}/thread")
async def get_thread(ticket_id: str) -> list[dict]:
    async with connect() as conn:
        row = await conn.fetchrow(
            "SELECT source_thread_id FROM theo.tickets WHERE id = $1", ticket_id,
        )
        if row is None or row["source_thread_id"] is None:
            return []
        rows = await conn.fetch(
            "SELECT * FROM theo.channel_messages WHERE thread_id = $1 "
            "ORDER BY sent_at ASC",
            row["source_thread_id"],
        )
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Write — execute actions
# ---------------------------------------------------------------------------


class ExecuteRequest(BaseModel):
    body_override: str | None = None    # for editing the WhatsApp draft inline


@router.post("/tickets/{ticket_id}/actions/{action_idx}/execute")
async def execute_single_action(
    ticket_id: str, action_idx: int, req: ExecuteRequest | None = None,
) -> dict:
    """Execute a single suggested action (propose mode flow)."""
    async with connect() as conn:
        row = await conn.fetchrow(
            "SELECT suggested_actions, source_thread_id FROM theo.tickets WHERE id=$1",
            ticket_id,
        )
    if row is None:
        raise HTTPException(404, "ticket not found")
    actions = row["suggested_actions"] or []
    if isinstance(actions, str):
        actions = json.loads(actions)
    if action_idx >= len(actions):
        raise HTTPException(400, "action_idx out of range")

    action = dict(actions[action_idx])
    payload = dict(action.get("payload") or {})
    if req and req.body_override is not None:
        payload["body"] = req.body_override
    action["payload"] = payload

    result = await _execute_action(ticket_id, row["source_thread_id"], action)
    return result


@router.post("/tickets/{ticket_id}/bundle/execute")
async def execute_bundle(ticket_id: str, req: ExecuteRequest | None = None) -> dict:
    """Atomic bundle execution (bundle_approve mode flow).

    All DB writes in one transaction. WhatsApp send fires AFTER commit so a
    rollback can't strand an irreversible send.
    """
    async with connect() as conn:
        row = await conn.fetchrow(
            "SELECT suggested_actions, source_thread_id FROM theo.tickets WHERE id=$1",
            ticket_id,
        )
    if row is None:
        raise HTTPException(404, "ticket not found")
    actions_raw = row["suggested_actions"] or []
    if isinstance(actions_raw, str):
        actions_raw = json.loads(actions_raw)
    actions = sorted(actions_raw, key=lambda a: a.get("bundle_order") or 0)

    # Optionally override the body of the (last) send_whatsapp_reply action
    if req and req.body_override is not None:
        for a in actions:
            if a.get("action_type") == "send_whatsapp_reply":
                a.setdefault("payload", {})["body"] = req.body_override
                break

    warnings: list[str] = []
    executed = 0

    db_actions = [a for a in actions if a.get("action_type") != "send_whatsapp_reply"]
    wa_actions = [a for a in actions if a.get("action_type") == "send_whatsapp_reply"]

    # Phase 1: DB writes in one tx
    async with connect() as conn:
        try:
            async with conn.transaction():
                for action in db_actions:
                    await _execute_db_side(
                        conn, ticket_id, row["source_thread_id"], action,
                    )
                    executed += 1
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "executed": 0, "warnings": warnings,
                    "error": f"DB rollback: {e}"}

    # Phase 2: irreversible WhatsApp send
    for action in wa_actions:
        result = await _execute_whatsapp_send(
            row["source_thread_id"], action.get("payload") or {},
        )
        if result.get("warning"):
            warnings.append(result["warning"])
        executed += 1

    return {"ok": True, "executed": executed, "warnings": warnings}


async def _execute_action(ticket_id: str, thread_id: str | None, action: dict) -> dict:
    """Single-action execution (no transaction)."""
    atype = action.get("action_type")
    if atype == "send_whatsapp_reply":
        return await _execute_whatsapp_send(thread_id, action.get("payload") or {})
    async with connect() as conn:
        await _execute_db_side(conn, ticket_id, thread_id, action)
    return {"ok": True, "action_type": atype}


async def _execute_db_side(conn, ticket_id: str, thread_id: str | None, action: dict) -> None:
    atype = action.get("action_type")
    payload = action.get("payload") or {}
    if atype == "dispatch_vendor":
        await conn.execute(
            "INSERT INTO theo.vendor_dispatches (ticket_id, vendor_id, scope, "
            "urgency, dispatched_at) VALUES ($1, $2, $3, $4, now())",
            ticket_id, payload.get("vendor_id"), payload.get("scope", ""),
            payload.get("urgency", "Standard"),
        )
        await conn.execute(
            "UPDATE theo.tickets SET status='awaiting_vendor', vendor_id=$1 WHERE id=$2",
            payload.get("vendor_id"), ticket_id,
        )
    elif atype == "approve_offer":
        await conn.execute(
            "UPDATE theo.vendor_offers SET status='approved' WHERE id=$1",
            payload.get("offer_id"),
        )
    elif atype == "send_email_reply":
        await conn.execute(
            "INSERT INTO theo.emails (id, from_address, to_address, subject, body, "
            "received_at, thread_id, unit_id) "
            "VALUES (gen_random_uuid()::text, $1, $2, $3, $4, now(), $5, NULL)",
            "sarah.weber@hallotheo.de", "<recipient>",
            payload.get("subject", ""), payload.get("body", ""), thread_id,
        )
    else:
        await conn.execute(
            "INSERT INTO theo.proposed_actions (proposed_at, action_type, payload, "
            "rationale, status) VALUES (now(), $1, $2::jsonb, $3, 'approved')",
            atype, json.dumps(payload), action.get("rationale", ""),
        )


async def _execute_whatsapp_send(thread_id: str | None, payload: dict) -> dict:
    bridge_url = os.environ.get("WHATSAPP_BRIDGE_URL", "http://127.0.0.1:8003")
    body = payload.get("body", "")
    if not thread_id or not body:
        return {"ok": False, "warning": "WhatsApp ohne Inhalt — übersprungen."}

    async with connect() as conn:
        recipient_row = await conn.fetchrow(
            "SELECT tn.phone FROM theo.channel_threads ct "
            "JOIN theo.tenants tn ON tn.id = ct.tenant_id WHERE ct.id = $1",
            thread_id,
        )

    warning = None
    if recipient_row and recipient_row["phone"]:
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.post(
                    f"{bridge_url}/send",
                    json={"to": recipient_row["phone"], "body": body},
                )
            if not r.is_success:
                warning = (
                    f"WhatsApp-Bridge {r.status_code}: {r.text[:120]}. "
                    "Bitte manuell senden."
                )
        except Exception as e:  # noqa: BLE001
            warning = f"WhatsApp-Bridge unerreichbar: {e}. Bitte manuell senden."

    async with connect() as conn:
        await conn.execute(
            "INSERT INTO theo.channel_messages (id, thread_id, direction, sender, "
            "body, sent_at) VALUES (gen_random_uuid()::text, $1, 'outbound', "
            "'Sarah Weber', $2, now())",
            thread_id, body,
        )
        await conn.execute(
            "UPDATE theo.channel_threads SET last_message_at=now() WHERE id=$1",
            thread_id,
        )

    return {"ok": True, "warning": warning}


# ---------------------------------------------------------------------------
# Demo controls
# ---------------------------------------------------------------------------


KOEHLER_BODY = (
    "Sehr geehrte Frau Weber, die Heizung im Wohnzimmer geht schon wieder nicht. "
    "Das ist jetzt das sechste Mal in 18 Monaten mit demselben Heizkörper. "
    "Die Wettervorhersage für Donnerstag und Freitag soll Frost werden. "
    "Ich bin nach meiner Hüft-OP nicht so belastbar mit der Kälte. "
    "Bitte sagen Sie mir Bescheid, wann jemand kommen kann."
)

_DATASET = Path(__file__).resolve().parent.parent / "data" / "hallotheo_demo"


@router.post("/demo/fire/koehler")
async def demo_fire_koehler(background: BackgroundTasks) -> dict:
    from intake.intake_service import handle_inbound
    result = await handle_inbound(
        channel="whatsapp",
        from_phone="+491793960546",
        body=KOEHLER_BODY,
    )
    if result["status"] != "accepted":
        raise HTTPException(422, detail=result)
    background.add_task(_run_enrichment_async, result["ticket_id"])
    return result


@router.post("/demo/fire/demir")
async def demo_fire_demir(background: BackgroundTasks) -> dict:
    from intake.intake_service import handle_inbound
    try:
        body = (_DATASET / "email_02_demir_NK_beanstandung.txt").read_text("utf-8")
    except FileNotFoundError:
        body = "Förmliche Beanstandung Nebenkostenabrechnung 2024."

    result = await handle_inbound(
        channel="email",
        from_email="y.demir@gmx.de",
        body=body,
        external_thread_id="thread_demir_nka2024",
    )
    if result["status"] != "accepted":
        raise HTTPException(422, detail=result)
    background.add_task(_run_enrichment_async, result["ticket_id"])
    return result


@router.post("/demo/reset")
async def demo_reset() -> dict:
    """Run data.seed to wipe + reload static state + Schornsteinfeger."""
    repo_root = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [".venv/bin/python", "-m", "data.seed"],
        cwd=repo_root, capture_output=True, text=True, timeout=60,
    )
    return {
        "ok": proc.returncode == 0,
        "stdout": (proc.stdout or "").strip().splitlines()[-5:],
        "stderr": (proc.stderr or "").strip()[-300:],
    }


async def _run_enrichment_async(ticket_id: str) -> None:
    """Wrapper so we can use it as a BackgroundTask without re-importing."""
    from agent.enrichment_loop import enrich_ticket
    try:
        await enrich_ticket(ticket_id)
    except Exception as e:  # noqa: BLE001
        log.exception("enrichment failed for %s: %s", ticket_id, e)
