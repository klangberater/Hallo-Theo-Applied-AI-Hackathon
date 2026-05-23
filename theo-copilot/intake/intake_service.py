"""Inbound message → ticket + (optional) Graphiti episode pipeline.

handle_inbound() is called by the FastAPI webhook with a normalized
IncomingMessage. It:
  1. Looks up the tenant by phone
  2. Resolves their unit (via active lease)
  3. Creates a ticket row
  4. Stores the incoming channel message
  5. Runs intent classification (Sonnet) to set priority + intent
  6. Optionally writes a Graphiti episode (if Graphiti is healthy)
  7. Schedules the enrichment loop in the background

See: PRODUCT_SPEC §3.1 Phase A + §7
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Any

from infra.db import connect
from intake.intent_classifier import classify_intent

log = logging.getLogger(__name__)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


_URGENCY_TO_PRIORITY = {
    "emergency": "DRINGEND",
    "urgent": "Wichtig",
    "standard": "Standard",
}


async def handle_inbound(
    *,
    channel: str,
    from_phone: str | None = None,
    from_email: str | None = None,
    body: str,
    sent_at: datetime | None = None,
    external_thread_id: str | None = None,
) -> dict[str, Any]:
    """Run the full intake pipeline for a single inbound message.

    Returns a summary dict so the webhook caller can confirm success.
    """
    sent_at = sent_at or datetime.now(timezone.utc)

    # --- 1. Find tenant
    tenant = None
    async with connect() as conn:
        if from_phone:
            cleaned = "".join(c for c in from_phone if c.isdigit() or c == "+")
            tenant = await conn.fetchrow(
                "SELECT * FROM theo.tenants WHERE replace(phone, ' ', '') = $1", cleaned,
            )
        if tenant is None and from_email:
            tenant = await conn.fetchrow(
                "SELECT * FROM theo.tenants WHERE email = $1", from_email,
            )
        if tenant is None:
            return {"status": "rejected", "reason": "unknown_sender",
                    "from_phone": from_phone, "from_email": from_email}

        # --- 2. Resolve unit (most recent active lease)
        lease = await conn.fetchrow(
            "SELECT * FROM theo.leases WHERE tenant_id = $1 AND status = 'active' "
            "ORDER BY start_date DESC LIMIT 1",
            tenant["id"],
        )
        if lease is None:
            return {"status": "rejected", "reason": "no_active_lease",
                    "tenant_id": tenant["id"]}
        unit_id = lease["unit_id"]

        # --- 3. Find or create channel thread
        ext_id = external_thread_id or f"{channel}_{tenant['id']}_{sent_at.date()}"
        thread = await conn.fetchrow(
            "SELECT * FROM theo.channel_threads WHERE channel = $1 AND external_id = $2",
            channel, ext_id,
        )
        if thread is None:
            thread_id = _new_id("ct")
            await conn.execute(
                "INSERT INTO theo.channel_threads (id, channel, external_id, "
                "tenant_id, unit_id, last_message_at) VALUES ($1, $2, $3, $4, $5, $6)",
                thread_id, channel, ext_id, tenant["id"], unit_id, sent_at,
            )
        else:
            thread_id = thread["id"]
            await conn.execute(
                "UPDATE theo.channel_threads SET last_message_at = $1 WHERE id = $2",
                sent_at, thread_id,
            )

        # --- 4. Store inbound channel message
        msg_id = _new_id("cm")
        await conn.execute(
            "INSERT INTO theo.channel_messages (id, thread_id, direction, sender, "
            "body, sent_at) VALUES ($1, $2, 'inbound', $3, $4, $5)",
            msg_id, thread_id, tenant["name"], body, sent_at,
        )

    # --- 5. Intent classification (Sonnet) — outside the txn, it's a network call.
    try:
        intent_result = classify_intent(body)
    except Exception as e:  # noqa: BLE001
        log.warning("intent classification failed: %s", e)
        intent_result = {"intent": "other", "urgency": "standard",
                         "confidence": 0.0, "reasoning": f"fallback (error: {e})"}

    priority = _URGENCY_TO_PRIORITY.get(intent_result["urgency"], "Standard")

    # --- 6. Create the ticket
    ticket_id = _new_id("TK")
    async with connect() as conn:
        await conn.execute(
            "INSERT INTO theo.tickets (id, unit_id, category, priority, opened_at, "
            "full_text, source_thread_id, classified_intent, status) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'open')",
            ticket_id, unit_id,
            intent_result["intent"],
            priority, sent_at, body, thread_id, intent_result["intent"],
        )

    # --- 7. Optional Graphiti episode write (skip if Graphiti isn't reachable)
    try:
        from infra.graphiti_client import add_message_episode
        await add_message_episode(
            name=f"intake-{ticket_id}",
            body=body,
            tenant_id=tenant["id"],
            unit_id=unit_id,
            sent_at=sent_at,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("graphiti episode write skipped: %s", e)

    return {
        "status": "accepted",
        "ticket_id": ticket_id,
        "tenant_id": tenant["id"],
        "unit_id": unit_id,
        "thread_id": thread_id,
        "intent": intent_result,
        "priority": priority,
    }
