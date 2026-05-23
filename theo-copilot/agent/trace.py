"""Session-log writer for the reasoning trace UI.

Each tool call, tool result, LLM turn, and final enrichment is appended
as a row in theo.trace_events. The Streamlit "Why?" toggle reads from here.

See: docs/PRODUCT_SPEC.md §8 View 3
"""
from __future__ import annotations

import json
from typing import Any

from infra.db import connect


VALID_KINDS = {
    "llm_call_started",
    "llm_call_completed",
    "tool_use",
    "tool_result",
    "stubbed_tool",
    "enrichment_payload",
    "intent_classification",
    "error",
}


async def log_trace_step(
    ticket_id: str,
    step: int,
    kind: str,
    payload: dict[str, Any],
) -> None:
    """Append a trace event. Cheap — one INSERT, best-effort logging."""
    actual_kind = kind if kind in VALID_KINDS else "error"
    if actual_kind == "error" and kind not in VALID_KINDS:
        payload = {"_invalid_kind": kind, **payload}
    async with connect() as conn:
        await conn.execute(
            "INSERT INTO theo.trace_events (ticket_id, step, kind, payload) "
            "VALUES ($1, $2, $3, $4::jsonb)",
            ticket_id, step, actual_kind, json.dumps(payload, default=str),
        )


async def get_trace(ticket_id: str) -> list[dict]:
    """Fetch the trace timeline for a ticket — used by the UI."""
    async with connect() as conn:
        rows = await conn.fetch(
            "SELECT step, kind, payload, created_at FROM theo.trace_events "
            "WHERE ticket_id = $1 ORDER BY step ASC, id ASC",
            ticket_id,
        )
    return [dict(r) for r in rows]
