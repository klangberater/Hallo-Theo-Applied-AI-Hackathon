"""The enrichment agent — Anthropic SDK tool-use loop.

Single Python function, no framework. Implements PRODUCT_SPEC §7.2.

`enrich_ticket(ticket_id)` runs the loop, captures trace events, persists
the final EnrichmentPayload to theo.tickets.enrichment + suggested_actions.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv

from agent.enrichment_schema import EnrichmentPayload
from agent.prompts import build_enrichment_system_prompt, render_enrichment_intent
from agent.trace import log_trace_step
from agent.tools import l1_wiki, l2_state, l3_memory
from agent.tools import messaging as msg_tools
from agent.tools import vendor as vendor_tools
from infra.db import connect

# Load .env (same chain as everywhere else).
for _candidate in [
    Path("/opt/fletcher/.env"),
    Path(__file__).resolve().parent.parent / ".env",
    Path.cwd() / ".env",
]:
    if _candidate.exists():
        load_dotenv(_candidate)
        break


MODEL = os.environ.get("ANTHROPIC_MODEL_REASONING", "claude-opus-4-5")
MAX_TURNS = 12

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic()
    return _client


# ---------------------------------------------------------------------------
# Tool registry — names must match the schema below.
# Each tool returns a JSON-serializable dict (or list of dicts).
# ---------------------------------------------------------------------------


async def _tool_get_tenant(tenant_id: str) -> dict | None:
    return await l2_state.get_tenant(tenant_id)


async def _tool_get_tenant_by_phone(phone: str) -> dict | None:
    return await l2_state.get_tenant_by_phone(phone)


async def _tool_get_unit(unit_id: str) -> dict | None:
    return await l2_state.get_unit(unit_id)


async def _tool_get_lease(unit_id: str) -> dict | None:
    return await l2_state.get_lease(unit_id)


async def _tool_list_tickets(unit_id: str, since: str | None = None) -> list[dict]:
    from datetime import date
    since_d = date.fromisoformat(since) if since else None
    return await l2_state.list_tickets(unit_id, since=since_d)


async def _tool_get_ticket(ticket_id: str) -> dict | None:
    return await l2_state.get_ticket(ticket_id)


async def _tool_list_invoices(
    vendor_id: str | None = None, unit_id: str | None = None,
) -> list[dict]:
    return await l2_state.list_invoices(vendor_id=vendor_id, unit_id=unit_id)


async def _tool_get_nka(unit_id: str, year: int) -> dict | None:
    return await l2_state.get_nka(unit_id, year)


async def _tool_get_vendor(vendor_id: str) -> dict | None:
    return await l2_state.get_vendor(vendor_id)


async def _tool_get_open_offers(
    unit_id: str | None = None, vendor_id: str | None = None,
) -> list[dict]:
    return await l2_state.get_open_offers(unit_id=unit_id, vendor_id=vendor_id)


async def _tool_list_internal_chat(
    thread_id: str | None = None, since: str | None = None,
) -> list[dict]:
    from datetime import datetime
    since_dt = datetime.fromisoformat(since) if since else None
    return await l2_state.list_internal_chat(thread_id=thread_id, since=since_dt)


async def _tool_query_temporal_memory(
    query: str, group_id: str, num_results: int = 10,
) -> list[dict]:
    return await l3_memory.query_temporal_memory(query, group_id, num_results)


async def _tool_get_entity_timeline(entity_name: str, group_id: str) -> list[dict]:
    return await l3_memory.get_entity_timeline(entity_name, group_id)


def _tool_search_wiki(query: str, k: int = 3) -> list[dict]:
    return l1_wiki.search_wiki(query, k=k)


def _tool_read_wiki_page(path: str) -> str:
    return l1_wiki.read_wiki_page(path)


async def _tool_get_weather_forecast(location: str, days_ahead: int = 4) -> dict:
    return await l2_state.get_weather_forecast(location, days_ahead)


TOOL_DISPATCH: dict[str, Any] = {
    "get_tenant": _tool_get_tenant,
    "get_tenant_by_phone": _tool_get_tenant_by_phone,
    "get_unit": _tool_get_unit,
    "get_lease": _tool_get_lease,
    "list_tickets": _tool_list_tickets,
    "get_ticket": _tool_get_ticket,
    "list_invoices": _tool_list_invoices,
    "get_nka": _tool_get_nka,
    "get_vendor": _tool_get_vendor,
    "get_open_offers": _tool_get_open_offers,
    "list_internal_chat": _tool_list_internal_chat,
    "query_temporal_memory": _tool_query_temporal_memory,
    "get_entity_timeline": _tool_get_entity_timeline,
    "search_wiki": _tool_search_wiki,
    "read_wiki_page": _tool_read_wiki_page,
    "get_weather_forecast": _tool_get_weather_forecast,
}


# Anthropic tool schemas
TOOL_SCHEMAS: list[dict] = [
    {
        "name": "query_temporal_memory",
        "description": "L3 — query Graphiti for temporal facts about a tenant, "
                       "property, or vendor. Use this FIRST for any tenant or "
                       "property situation; chronic patterns matter more than the "
                       "current incident in isolation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Free-text question, e.g. 'heating issues'"},
                "group_id": {"type": "string", "description": "e.g. 'tenant:koehler' or 'property:zossener_47'"},
                "num_results": {"type": "integer", "default": 10},
            },
            "required": ["query", "group_id"],
        },
    },
    {
        "name": "get_entity_timeline",
        "description": "L3 — get chronological episodes for an entity, scoped by group.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_name": {"type": "string"},
                "group_id": {"type": "string"},
            },
            "required": ["entity_name", "group_id"],
        },
    },
    {
        "name": "get_tenant",
        "description": "L2 — look up tenant by id.",
        "input_schema": {"type": "object", "properties": {"tenant_id": {"type": "string"}}, "required": ["tenant_id"]},
    },
    {
        "name": "get_tenant_by_phone",
        "description": "L2 — look up tenant by E.164 phone number.",
        "input_schema": {"type": "object", "properties": {"phone": {"type": "string"}}, "required": ["phone"]},
    },
    {
        "name": "get_unit",
        "description": "L2 — look up unit by id.",
        "input_schema": {"type": "object", "properties": {"unit_id": {"type": "string"}}, "required": ["unit_id"]},
    },
    {
        "name": "get_lease",
        "description": "L2 — get the active lease for a unit (includes full_text excerpt of contract).",
        "input_schema": {"type": "object", "properties": {"unit_id": {"type": "string"}}, "required": ["unit_id"]},
    },
    {
        "name": "list_tickets",
        "description": "L2 — list tickets for a unit, optionally since a date (YYYY-MM-DD).",
        "input_schema": {
            "type": "object",
            "properties": {
                "unit_id": {"type": "string"},
                "since": {"type": "string", "description": "ISO date YYYY-MM-DD"},
            },
            "required": ["unit_id"],
        },
    },
    {
        "name": "get_ticket",
        "description": "L2 — full detail of a single ticket.",
        "input_schema": {"type": "object", "properties": {"ticket_id": {"type": "string"}}, "required": ["ticket_id"]},
    },
    {
        "name": "list_invoices",
        "description": "L2 — list invoices, optionally filtered by vendor_id and/or unit_id.",
        "input_schema": {"type": "object", "properties": {
            "vendor_id": {"type": "string"}, "unit_id": {"type": "string"}}},
    },
    {
        "name": "get_nka",
        "description": "L2 — get the Nebenkostenabrechnung for a unit/year combination.",
        "input_schema": {
            "type": "object",
            "properties": {"unit_id": {"type": "string"}, "year": {"type": "integer"}},
            "required": ["unit_id", "year"],
        },
    },
    {
        "name": "get_vendor",
        "description": "L2 — look up vendor by id.",
        "input_schema": {"type": "object", "properties": {"vendor_id": {"type": "string"}}, "required": ["vendor_id"]},
    },
    {
        "name": "get_open_offers",
        "description": "L2 — list pending vendor offers, optionally by unit and/or vendor.",
        "input_schema": {"type": "object", "properties": {
            "unit_id": {"type": "string"}, "vendor_id": {"type": "string"}}},
    },
    {
        "name": "list_internal_chat",
        "description": "L2 — read internal team chat messages (Sarah ↔ Jonas). "
                       "ALWAYS check before recommending an action — a pre-approval "
                       "or veto may already exist.",
        "input_schema": {"type": "object", "properties": {
            "thread_id": {"type": "string"},
            "since": {"type": "string", "description": "ISO datetime"}}},
    },
    {
        "name": "search_wiki",
        "description": "L1 — semantic search over German policy + procedure markdown. "
                       "Use this to ground legal citations (BGB, BetrKV, HKV).",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "k": {"type": "integer", "default": 3},
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_wiki_page",
        "description": "L1 — read full text of a wiki page by relative path.",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    },
    {
        "name": "get_weather_forecast",
        "description": "External — Berlin weather forecast (stubbed in demo). Returns "
                       "frost prediction relevant to heating tickets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "days_ahead": {"type": "integer", "default": 4},
            },
            "required": ["location"],
        },
    },
]


# ---------------------------------------------------------------------------
# Loop
# ---------------------------------------------------------------------------


async def _dispatch_tool(name: str, args: dict) -> Any:
    fn = TOOL_DISPATCH.get(name)
    if fn is None:
        return {"error": f"unknown tool: {name}"}
    if asyncio.iscoroutinefunction(fn):
        return await fn(**args)
    return fn(**args)


async def enrich_ticket(ticket_id: str) -> EnrichmentPayload:
    """Run the enrichment agent. Persists result to theo.tickets.enrichment."""
    ticket = await l2_state.get_ticket(ticket_id)
    if ticket is None:
        raise ValueError(f"ticket not found: {ticket_id}")

    system = build_enrichment_system_prompt(ticket.get("classified_intent"))
    messages: list[dict] = [
        {"role": "user", "content": render_enrichment_intent(ticket)},
    ]

    client = _get_client()
    step = 0
    final_text = ""

    async with connect() as conn:
        await conn.execute(
            "UPDATE theo.tickets SET status = 'enriching' WHERE id = $1", ticket_id,
        )

    for turn in range(MAX_TURNS):
        step += 1
        await log_trace_step(ticket_id, step, "llm_call_started",
                              {"turn": turn, "model": MODEL})

        resp = client.messages.create(
            model=MODEL, max_tokens=8192,
            system=system, tools=TOOL_SCHEMAS, messages=messages,
        )

        await log_trace_step(ticket_id, step, "llm_call_completed",
                              {"turn": turn, "stop_reason": resp.stop_reason,
                               "usage": {"in": resp.usage.input_tokens,
                                         "out": resp.usage.output_tokens}})

        if resp.stop_reason == "end_turn":
            final_text = "".join(b.text for b in resp.content if b.type == "text")
            break

        if resp.stop_reason != "tool_use":
            # Unexpected — bail out, agent didn't end cleanly.
            await log_trace_step(ticket_id, step, "error",
                                  {"unexpected_stop_reason": resp.stop_reason})
            final_text = "".join(b.text for b in resp.content if b.type == "text")
            break

        # Run all tool_use blocks in this assistant turn, then continue.
        tool_results: list[dict] = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            step += 1
            await log_trace_step(ticket_id, step, "tool_use",
                                  {"name": block.name, "args": block.input})
            try:
                result = await _dispatch_tool(block.name, dict(block.input))
                # If l2_state stubbed (weather), surface that as a separate event.
                if isinstance(result, dict) and result.get("_stubbed"):
                    await log_trace_step(ticket_id, step, "stubbed_tool",
                                          {"name": block.name})
                step += 1
                await log_trace_step(ticket_id, step, "tool_result",
                                      {"name": block.name,
                                       "preview": str(result)[:500]})
                tool_results.append({
                    "type": "tool_result", "tool_use_id": block.id,
                    "content": json.dumps(result, default=str, ensure_ascii=False),
                })
            except Exception as e:  # noqa: BLE001
                await log_trace_step(ticket_id, step, "error",
                                      {"name": block.name, "error": str(e)})
                tool_results.append({
                    "type": "tool_result", "tool_use_id": block.id,
                    "content": json.dumps({"error": str(e)}),
                    "is_error": True,
                })

        messages.append({"role": "assistant", "content": resp.content})
        messages.append({"role": "user", "content": tool_results})
    else:
        await log_trace_step(ticket_id, step, "error",
                              {"reason": "MAX_TURNS reached without end_turn"})

    # Parse final text as EnrichmentPayload
    text = final_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        payload = EnrichmentPayload.model_validate_json(text)
    except Exception as e:  # noqa: BLE001
        await log_trace_step(ticket_id, step, "error",
                              {"parse_error": str(e), "raw": text[:1000]})
        raise

    # Persist
    payload_json = payload.model_dump(mode="json")
    suggested = payload_json.pop("suggested_actions", [])
    async with connect() as conn:
        await conn.execute(
            "UPDATE theo.tickets SET enrichment = $1::jsonb, "
            "suggested_actions = $2::jsonb, status = 'ready_for_review' WHERE id = $3",
            json.dumps(payload_json, ensure_ascii=False),
            json.dumps(suggested, ensure_ascii=False),
            ticket_id,
        )
    await log_trace_step(ticket_id, step + 1, "enrichment_payload",
                          {"cards": list(payload_json.keys()),
                           "suggested_actions_count": len(suggested)})
    return payload
