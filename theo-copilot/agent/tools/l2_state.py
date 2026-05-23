"""L2 state tools — Postgres queries against the theo schema.

Every function here is exposed to the agent as a tool (see
`agent/tools/__init__.py` registration). Each returns plain dicts so
the agent loop can JSON-serialize tool_result blocks directly.

Implements PRODUCT_SPEC §5.1.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from infra.db import connect


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rowdict(row) -> dict[str, Any] | None:
    """Convert an asyncpg Record (or None) to a plain dict."""
    if row is None:
        return None
    return dict(row)


def _normalize_phone(phone: str) -> str:
    """Strip whitespace and non-digit (except +) from a phone string."""
    return "".join(c for c in phone if c.isdigit() or c == "+")


# ---------------------------------------------------------------------------
# Core L2 tools
# ---------------------------------------------------------------------------


async def get_unit(unit_id: str) -> dict | None:
    async with connect() as conn:
        row = await conn.fetchrow("SELECT * FROM theo.units WHERE id = $1", unit_id)
        return _rowdict(row)


async def get_tenant(tenant_id: str) -> dict | None:
    async with connect() as conn:
        row = await conn.fetchrow("SELECT * FROM theo.tenants WHERE id = $1", tenant_id)
        return _rowdict(row)


async def get_tenant_by_phone(phone: str) -> dict | None:
    """Look up tenant by E.164 phone. Used by the WhatsApp intake."""
    normalized = _normalize_phone(phone)
    async with connect() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM theo.tenants WHERE replace(phone, ' ', '') = $1",
            normalized,
        )
        return _rowdict(row)


async def get_lease(unit_id: str) -> dict | None:
    async with connect() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM theo.leases WHERE unit_id = $1 ORDER BY start_date DESC LIMIT 1",
            unit_id,
        )
        return _rowdict(row)


async def list_tickets(unit_id: str, since: date | None = None) -> list[dict]:
    async with connect() as conn:
        if since is None:
            rows = await conn.fetch(
                "SELECT * FROM theo.tickets WHERE unit_id = $1 ORDER BY opened_at DESC",
                unit_id,
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM theo.tickets WHERE unit_id = $1 AND opened_at >= $2 "
                "ORDER BY opened_at DESC",
                unit_id, since,
            )
    return [dict(r) for r in rows]


async def get_ticket(ticket_id: str) -> dict | None:
    async with connect() as conn:
        row = await conn.fetchrow("SELECT * FROM theo.tickets WHERE id = $1", ticket_id)
        return _rowdict(row)


async def list_invoices(
    vendor_id: str | None = None,
    unit_id: str | None = None,
) -> list[dict]:
    clauses, args = [], []
    if vendor_id:
        args.append(vendor_id)
        clauses.append(f"vendor_id = ${len(args)}")
    if unit_id:
        args.append(unit_id)
        clauses.append(f"unit_id = ${len(args)}")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    async with connect() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM theo.invoices{where} ORDER BY issued_at DESC", *args,
        )
    return [dict(r) for r in rows]


async def get_invoice(invoice_id: str) -> dict | None:
    async with connect() as conn:
        row = await conn.fetchrow("SELECT * FROM theo.invoices WHERE id = $1", invoice_id)
        return _rowdict(row)


async def get_nka(unit_id: str, year: int) -> dict | None:
    async with connect() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM theo.nka WHERE unit_id = $1 AND year = $2",
            unit_id, year,
        )
        return _rowdict(row)


async def get_vendor(vendor_id: str) -> dict | None:
    async with connect() as conn:
        row = await conn.fetchrow("SELECT * FROM theo.vendors WHERE id = $1", vendor_id)
        return _rowdict(row)


async def get_open_offers(
    unit_id: str | None = None,
    vendor_id: str | None = None,
) -> list[dict]:
    clauses = ["status = 'pending'"]
    args: list = []
    if unit_id:
        args.append(unit_id)
        clauses.append(f"unit_id = ${len(args)}")
    if vendor_id:
        args.append(vendor_id)
        clauses.append(f"vendor_id = ${len(args)}")
    where = " WHERE " + " AND ".join(clauses)
    async with connect() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM theo.vendor_offers{where} ORDER BY issued_at DESC", *args,
        )
    return [dict(r) for r in rows]


async def get_thread(channel: str, external_thread_id: str) -> dict | None:
    async with connect() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM theo.channel_threads WHERE channel = $1 AND external_id = $2",
            channel, external_thread_id,
        )
        return _rowdict(row)


async def list_internal_chat(
    thread_id: str | None = None,
    since: datetime | None = None,
) -> list[dict]:
    """Reads theo.chat_messages — the Sarah↔Jonas-style threads."""
    clauses, args = [], []
    if thread_id:
        args.append(thread_id)
        clauses.append(f"thread_id = ${len(args)}")
    if since:
        args.append(since)
        clauses.append(f"sent_at >= ${len(args)}")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    async with connect() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM theo.chat_messages{where} ORDER BY sent_at ASC", *args,
        )
    return [dict(r) for r in rows]


async def list_tickets_for_operator(
    operator_id: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """The inbox feed. operator_id reserved for future per-user scoping."""
    clauses, args = [], []
    if status:
        args.append(status)
        clauses.append(f"status = ${len(args)}")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    async with connect() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM theo.tickets{where} ORDER BY opened_at DESC LIMIT 100", *args,
        )
    return [dict(r) for r in rows]


async def get_ticket_with_enrichment(ticket_id: str) -> dict | None:
    """Ticket + denormalized context the UI needs.

    Returns the ticket row plus joined unit/tenant/lease info so the
    detail view can render without a second round trip.
    """
    async with connect() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                t.*,
                u.label AS unit_label,
                u.qm   AS unit_qm,
                p.id   AS property_id,
                p.name AS property_name,
                p.address AS property_address,
                l.tenant_id,
                tn.name AS tenant_name,
                tn.email AS tenant_email,
                tn.phone AS tenant_phone,
                tn.metadata AS tenant_metadata
            FROM theo.tickets t
            LEFT JOIN theo.units u ON u.id = t.unit_id
            LEFT JOIN theo.properties p ON p.id = u.property_id
            LEFT JOIN theo.leases l ON l.unit_id = u.id AND l.status = 'active'
            LEFT JOIN theo.tenants tn ON tn.id = l.tenant_id
            WHERE t.id = $1
            """,
            ticket_id,
        )
        return _rowdict(row)


# ---------------------------------------------------------------------------
# Stubbed tools (the spec lets us stub these — log it in the trace)
# ---------------------------------------------------------------------------


async def get_weather_forecast(location: str, days_ahead: int = 4) -> dict:
    """STUBBED — hardcoded for the demo's Berlin scenario.

    The CLAUDE.md hackathon rules require flagging stubbed data in the
    trace. The caller (enrichment loop or l3_memory) is responsible for
    writing a trace event of kind 'stubbed_tool' alongside the result.
    """
    return {
        "location": location,
        "days_ahead": days_ahead,
        "summary": (
            "Berlin: Mi +1°C tags / -1°C nachts; Do bis So Frosteinbruch "
            "-3°C nachts, tags +2°C; ab Mo Wiederanstieg."
        ),
        "frost_expected": True,
        "_stubbed": True,
    }
