"""Vendor action tools — propose and execute.

Same pattern as messaging.py: agent proposes, UI approves, then execute.

See: PRODUCT_SPEC §5.4
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from infra.db import connect


# ---------------------------------------------------------------------------
# Agent-callable — propose only.
# ---------------------------------------------------------------------------


async def propose_dispatch_vendor(
    vendor_id: str, ticket_id: str, scope: str, urgency: str, rationale: str = "",
) -> dict:
    async with connect() as conn:
        row = await conn.fetchrow(
            "INSERT INTO theo.proposed_actions (proposed_at, action_type, payload, "
            "rationale, status) VALUES ($1, $2, $3::jsonb, $4, 'pending') "
            "RETURNING id, status",
            datetime.now(timezone.utc), "dispatch_vendor",
            json.dumps({
                "vendor_id": vendor_id, "ticket_id": ticket_id,
                "scope": scope, "urgency": urgency,
            }),
            rationale,
        )
    return {"proposal_id": row["id"], "status": row["status"]}


async def propose_approve_offer(offer_id: str, rationale: str = "") -> dict:
    async with connect() as conn:
        row = await conn.fetchrow(
            "INSERT INTO theo.proposed_actions (proposed_at, action_type, payload, "
            "rationale, status) VALUES ($1, $2, $3::jsonb, $4, 'pending') "
            "RETURNING id, status",
            datetime.now(timezone.utc), "approve_offer",
            json.dumps({"offer_id": offer_id}), rationale,
        )
    return {"proposal_id": row["id"], "status": row["status"]}


# ---------------------------------------------------------------------------
# UI-callable execution — after approval.
# ---------------------------------------------------------------------------


async def execute_dispatch_vendor(
    vendor_id: str, ticket_id: str, scope: str, urgency: str,
) -> dict:
    async with connect() as conn:
        row = await conn.fetchrow(
            "INSERT INTO theo.vendor_dispatches (ticket_id, vendor_id, scope, urgency, "
            "dispatched_at) VALUES ($1, $2, $3, $4, $5) RETURNING id",
            ticket_id, vendor_id, scope, urgency, datetime.now(timezone.utc),
        )
        # Mark ticket awaiting_vendor
        await conn.execute(
            "UPDATE theo.tickets SET status = 'awaiting_vendor', vendor_id = $1 "
            "WHERE id = $2",
            vendor_id, ticket_id,
        )
    return {"dispatch_id": row["id"], "vendor_id": vendor_id, "ticket_id": ticket_id}


async def execute_approve_offer(offer_id: str) -> dict:
    async with connect() as conn:
        row = await conn.fetchrow(
            "UPDATE theo.vendor_offers SET status = 'approved' WHERE id = $1 "
            "RETURNING id, vendor_id, amount",
            offer_id,
        )
    if row is None:
        return {"error": f"offer not found: {offer_id}"}
    return {"offer_id": row["id"], "vendor_id": row["vendor_id"], "amount": float(row["amount"])}
