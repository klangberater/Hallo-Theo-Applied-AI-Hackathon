"""Graphiti wrapper — the moat.

Single point of access to graphiti-core. Lazy-initializes a singleton
Graphiti client; callers don't need to manage lifecycle.

Requires:
  NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD — for the bolt connection
  OPENAI_API_KEY                          — Graphiti's default LLM for
                                            fact extraction. Without it,
                                            ingestion silently degrades to
                                            no fact extraction.

If OPENAI_API_KEY is missing OR Graphiti raises, every public function in
this module raises — agent/tools/l3_memory.py catches that and falls back
to the kill-switch cache or hand-curated stub.

See: PRODUCT_SPEC §6.2 + §6.3 + §12.1
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

for _candidate in [
    Path("/opt/fletcher/.env"),
    Path(__file__).resolve().parent.parent / ".env",
    Path.cwd() / ".env",
]:
    if _candidate.exists():
        load_dotenv(_candidate)
        break


NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")


_graphiti: Any | None = None


def _require_keys() -> None:
    if not NEO4J_PASSWORD:
        raise RuntimeError("NEO4J_PASSWORD not set in env")
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY not set — Graphiti needs it for fact extraction."
        )


async def get_graphiti() -> Any:
    """Lazy-initialize the singleton Graphiti client."""
    global _graphiti
    if _graphiti is not None:
        return _graphiti
    _require_keys()
    # Import lazily so the module imports even when graphiti-core can't fully
    # initialize (e.g. on a dev machine without OPENAI_API_KEY).
    from graphiti_core import Graphiti

    _graphiti = Graphiti(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    # build_indices_and_constraints() is idempotent and cheap.
    await _graphiti.build_indices_and_constraints()
    return _graphiti


# ---------------------------------------------------------------------------
# group_id helpers
# ---------------------------------------------------------------------------


def tenant_group(tenant_id: str) -> str:
    return f"tenant:{tenant_id}"


def property_group(property_id: str) -> str:
    return f"property:{property_id}"


def vendor_group(vendor_id: str) -> str:
    return f"vendor:{vendor_id}"


# ---------------------------------------------------------------------------
# Public API used by l3_memory + intake
# ---------------------------------------------------------------------------


async def add_episode(
    *,
    name: str,
    body: str,
    reference_time: datetime,
    group_ids: list[str],
    source_description: str = "",
) -> None:
    """Pre-demo ingestion (scripts/ingest_graphiti.py)."""
    from graphiti_core.nodes import EpisodeType
    g = await get_graphiti()
    await g.add_episode(
        name=name,
        episode_body=body,
        source=EpisodeType.message,
        source_description=source_description,
        reference_time=reference_time,
        group_ids=group_ids,
    )


async def add_message_episode(
    *,
    name: str,
    body: str,
    tenant_id: str,
    unit_id: str | None,
    sent_at: datetime,
) -> None:
    """Convenience wrapper for the intake pipeline."""
    group_ids = [tenant_group(tenant_id)]
    if unit_id:
        # Resolve unit's property and group by that too
        from infra.db import connect
        async with connect() as conn:
            row = await conn.fetchrow(
                "SELECT property_id FROM theo.units WHERE id = $1", unit_id,
            )
            if row and row["property_id"]:
                group_ids.append(property_group(row["property_id"]))
    await add_episode(
        name=name, body=body, reference_time=sent_at,
        group_ids=group_ids, source_description=f"intake from {tenant_id}",
    )


async def search_facts(
    *, query: str, group_id: str, limit: int = 10,
) -> list[dict]:
    """Hybrid search across Graphiti's temporal graph. Returns plain dicts."""
    g = await get_graphiti()
    # graphiti-core's search returns a list of facts/edges
    results = await g.search(query=query, group_ids=[group_id], num_results=limit)
    return [
        {
            "fact": getattr(r, "fact", str(r)),
            "valid_from": getattr(r, "valid_at", None),
            "valid_until": getattr(r, "invalid_at", None),
            "source_episodes": getattr(r, "episodes", []),
        }
        for r in results
    ]


async def get_timeline(*, entity_name: str, group_id: str) -> list[dict]:
    """Chronological episodes mentioning entity_name."""
    facts = await search_facts(
        query=entity_name, group_id=group_id, limit=20,
    )
    return facts
