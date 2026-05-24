"""Inbound message → ticket + (optional) Graphiti episode pipeline.

handle_inbound() is called by the FastAPI webhook with a normalized
IncomingMessage. It:
  1. Looks up the tenant by phone
  2. Resolves their unit (via active lease)
  3. Finds or creates the channel thread
  4. Stores the incoming channel message
  5. Runs intent classification (Sonnet) to set priority + intent
  5b. Sends an immediate 2-sentence acknowledgement (Sonnet) —
      DB-only for email, DB + Baileys bridge for whatsapp
  6. Creates the ticket row
  7. Schedules a Graphiti episode write as a detached background task
     (never blocks the webhook — Graphiti has been observed taking
     9+ minutes on Together-AI retry storms)

See: PRODUCT_SPEC §3.1 Phase A + §7
"""
from __future__ import annotations

import asyncio
import logging
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from infra.db import connect
from intake.acknowledgement import generate_acknowledgement
from intake.intent_classifier import classify_intent

log = logging.getLogger(__name__)

# How long to allow a single Graphiti episode write to take before we cancel
# it. Graphiti's add_episode runs Together-AI fact extraction + embeddings +
# neo4j writes; we've seen it block for 9+ minutes when Together returns
# malformed JSON and Graphiti retries. The webhook MUST NOT wait on it.
GRAPHITI_WRITE_TIMEOUT_S = 90.0

# Track in-flight tasks so they don't get garbage-collected. (asyncio holds
# only weak refs to tasks; without a strong ref the task can be cancelled
# mid-flight by the GC.)
_BACKGROUND_TASKS: set[asyncio.Task] = set()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


_URGENCY_TO_PRIORITY = {
    "emergency": "DRINGEND",
    "urgent": "Wichtig",
    "standard": "Standard",
}


WHATSAPP_BRIDGE_URL = os.environ.get(
    "WHATSAPP_BRIDGE_URL", "http://127.0.0.1:8003",
)
ACK_SENDER = "hallo theo"


async def _write_graphiti_episode_with_timeout(
    *, ticket_id: str, body: str, tenant_id: str, unit_id: str,
    sent_at: datetime,
) -> None:
    """Background task: write a Graphiti episode without blocking intake.

    Graphiti's add_message_episode runs LLM extraction + embeddings + neo4j
    writes and has been observed taking 9+ minutes when the Together AI
    response is malformed and the SDK retries. The webhook can't wait on
    that — we fire this as a detached task and time out hard at 90s. If
    Graphiti is genuinely down we lose this one episode, which is fine:
    the demo reads pre-ingested episodes anyway.
    """
    started = time.monotonic()
    try:
        from infra.graphiti_client import add_message_episode
        await asyncio.wait_for(
            add_message_episode(
                name=f"intake-{ticket_id}",
                body=body,
                tenant_id=tenant_id,
                unit_id=unit_id,
                sent_at=sent_at,
            ),
            timeout=GRAPHITI_WRITE_TIMEOUT_S,
        )
        elapsed = time.monotonic() - started
        log.info("graphiti episode written for %s in %.1fs", ticket_id, elapsed)
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - started
        log.warning(
            "graphiti episode write timed out for %s after %.1fs", ticket_id, elapsed,
        )
    except Exception as e:  # noqa: BLE001
        elapsed = time.monotonic() - started
        log.warning(
            "graphiti episode write failed for %s after %.1fs: %s",
            ticket_id, elapsed, e,
        )


async def _send_whatsapp_via_bridge(to_phone: str, body: str) -> None:
    """Fire-and-forget POST to the Baileys bridge. Never raises.

    Bridge unreachable / not paired → log + move on. The DB row is the
    source of truth for the inbox UI; the WhatsApp send is best-effort.
    """
    url = f"{WHATSAPP_BRIDGE_URL.rstrip('/')}/send"
    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            r = await http.post(url, json={"to": to_phone, "body": body})
        if r.status_code >= 400:
            log.warning(
                "whatsapp bridge rejected ack: status=%s body=%s",
                r.status_code, r.text[:200],
            )
    except Exception as e:  # noqa: BLE001
        log.warning("whatsapp bridge unreachable for ack: %s", e)


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
    #         Build a compact caller-context block from tenant metadata + recent
    #         ticket history. Same "Heizung kaputt" warrants emergency from a
    #         68-year-old post-OP tenant with 5 prior heating cases, and Standard
    #         from a healthy first-time tenant. The caller doesn't have to
    #         repeat what we already know.
    import json as _json
    metadata = tenant.get("metadata") or {}
    if isinstance(metadata, str):
        try:
            metadata = _json.loads(metadata) or {}
        except Exception:  # noqa: BLE001
            metadata = {}
    caller_context: dict[str, Any] = {
        "name": tenant.get("name"),
        "age": metadata.get("age"),
        "since": metadata.get("since"),
        "vulnerability": metadata.get("vulnerability"),
    }
    # Prior incident count for this unit in the last 18 months — any intent,
    # any status. Lets the classifier weight "repeat pattern" without knowing
    # the current intent yet.
    try:
        async with connect() as conn:
            prior_count = await conn.fetchval(
                "SELECT COUNT(*)::int FROM theo.tickets "
                "WHERE unit_id = $1 "
                "AND opened_at > now() - interval '18 months'",
                unit_id,
            )
        if prior_count and prior_count > 0:
            caller_context["prior_incidents"] = {
                "count": prior_count,
                "timespan_months": 18,
                "intent": "Tickets insgesamt",
            }
    except Exception as e:  # noqa: BLE001
        log.warning("prior-incident lookup failed: %s", e)

    try:
        intent_result = classify_intent(body, caller_context=caller_context)
    except Exception as e:  # noqa: BLE001
        log.warning("intent classification failed: %s", e)
        intent_result = {"intent": "other", "urgency": "standard",
                         "confidence": 0.0, "reasoning": f"fallback (error: {e})"}

    priority = _URGENCY_TO_PRIORITY.get(intent_result["urgency"], "Standard")

    # --- 5b. Immediate acknowledgement reply.
    #         We always reply within ~1–2s so the tenant knows we heard them,
    #         long before the enrichment agent finishes. The outbound row goes
    #         into the same thread; for whatsapp we also POST to the Baileys
    #         bridge. Bridge failures are logged, not raised — the inbox UI
    #         stays consistent either way.
    try:
        ack_body = generate_acknowledgement(
            body,
            intent=intent_result.get("intent"),
            urgency=intent_result.get("urgency"),
            tenant_name=tenant["name"],
        )
        ack_sent_at = datetime.now(timezone.utc)
        ack_msg_id = _new_id("cm")
        async with connect() as conn:
            await conn.execute(
                "INSERT INTO theo.channel_messages (id, thread_id, direction, "
                "sender, body, sent_at) VALUES ($1, $2, 'outbound', $3, $4, $5)",
                ack_msg_id, thread_id, ACK_SENDER, ack_body, ack_sent_at,
            )
            await conn.execute(
                "UPDATE theo.channel_threads SET last_message_at = $1 WHERE id = $2",
                ack_sent_at, thread_id,
            )
        if channel == "whatsapp" and from_phone:
            await _send_whatsapp_via_bridge(from_phone, ack_body)
    except Exception as e:  # noqa: BLE001
        log.warning("acknowledgement send failed: %s", e)

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

    # --- 7. Graphiti episode write — fire-and-forget.
    #         Must NOT block the webhook response: Graphiti's add_episode
    #         has been observed taking 9+ minutes on retry storms. Detach
    #         it as a tracked background task with a hard timeout inside.
    task = asyncio.create_task(
        _write_graphiti_episode_with_timeout(
            ticket_id=ticket_id, body=body,
            tenant_id=tenant["id"], unit_id=unit_id, sent_at=sent_at,
        ),
        name=f"graphiti-episode-{ticket_id}",
    )
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)

    return {
        "status": "accepted",
        "ticket_id": ticket_id,
        "tenant_id": tenant["id"],
        "unit_id": unit_id,
        "thread_id": thread_id,
        "intent": intent_result,
        "priority": priority,
    }
