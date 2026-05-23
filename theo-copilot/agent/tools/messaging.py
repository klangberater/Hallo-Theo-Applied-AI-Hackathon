"""Outbound messaging tools.

These write to the proposed_actions queue. They are NOT auto-executed —
the Streamlit UI's "Approve & Send" button is the gate, and on approval
it calls `execute_proposed_action()` below which writes to
theo.channel_messages.

See: PRODUCT_SPEC §5.4
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone

from infra.db import connect


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


# ---------------------------------------------------------------------------
# Agent-callable tools — propose only.
# ---------------------------------------------------------------------------


async def propose_whatsapp_reply(
    thread_id: str, body: str, rationale: str = "",
) -> dict:
    """Queue a WhatsApp reply for human approval."""
    async with connect() as conn:
        row = await conn.fetchrow(
            "INSERT INTO theo.proposed_actions (proposed_at, action_type, payload, "
            "rationale, status) VALUES ($1, $2, $3::jsonb, $4, 'pending') "
            "RETURNING id, status",
            datetime.now(timezone.utc), "send_whatsapp_reply",
            json.dumps({"thread_id": thread_id, "body": body}), rationale,
        )
    return {"proposal_id": row["id"], "status": row["status"]}


async def propose_email_reply(
    thread_id: str, subject: str, body: str, rationale: str = "",
) -> dict:
    async with connect() as conn:
        row = await conn.fetchrow(
            "INSERT INTO theo.proposed_actions (proposed_at, action_type, payload, "
            "rationale, status) VALUES ($1, $2, $3::jsonb, $4, 'pending') "
            "RETURNING id, status",
            datetime.now(timezone.utc), "send_email_reply",
            json.dumps({"thread_id": thread_id, "subject": subject, "body": body}),
            rationale,
        )
    return {"proposal_id": row["id"], "status": row["status"]}


# ---------------------------------------------------------------------------
# UI-callable execution — only after Sarah approves.
# ---------------------------------------------------------------------------


async def execute_whatsapp_reply(thread_id: str, body: str, sender: str = "Sarah Weber") -> dict:
    """Write the outbound message. The phone-mockup polls and renders it."""
    msg_id = _new_id("cm")
    async with connect() as conn:
        await conn.execute(
            "INSERT INTO theo.channel_messages (id, thread_id, direction, sender, "
            "body, sent_at) VALUES ($1, $2, 'outbound', $3, $4, $5)",
            msg_id, thread_id, sender, body, datetime.now(timezone.utc),
        )
        await conn.execute(
            "UPDATE theo.channel_threads SET last_message_at = $1 WHERE id = $2",
            datetime.now(timezone.utc), thread_id,
        )
    return {"message_id": msg_id, "thread_id": thread_id}


async def execute_email_reply(
    thread_id: str, subject: str, body: str, sender: str = "Sarah Weber",
) -> dict:
    msg_id = _new_id("em")
    async with connect() as conn:
        await conn.execute(
            "INSERT INTO theo.emails (id, from_address, to_address, subject, body, "
            "received_at, thread_id, unit_id) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, NULL)",
            msg_id, "sarah.weber@hallotheo.de", "<recipient_from_thread>",
            subject, body, datetime.now(timezone.utc), thread_id,
        )
    return {"message_id": msg_id, "thread_id": thread_id}
