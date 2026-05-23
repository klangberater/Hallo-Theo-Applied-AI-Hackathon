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

# Together AI / any OpenAI-compatible provider for Graphiti's LLM + embeddings.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")  # e.g. https://api.together.xyz/v1

# Sensible defaults for Together AI. Override via env if using a different provider.
GRAPHITI_LLM_MODEL = os.environ.get(
    "GRAPHITI_LLM_MODEL",
    "meta-llama/Llama-3.3-70B-Instruct-Turbo",
)
GRAPHITI_SMALL_MODEL = os.environ.get(
    "GRAPHITI_SMALL_MODEL",
    "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
)
GRAPHITI_EMBED_MODEL = os.environ.get(
    "GRAPHITI_EMBED_MODEL",
    "togethercomputer/m2-bert-80M-32k-retrieval",
)
GRAPHITI_EMBED_DIM = int(os.environ.get("GRAPHITI_EMBED_DIM", "768"))


_graphiti: Any | None = None


def _require_keys() -> None:
    if not NEO4J_PASSWORD:
        raise RuntimeError("NEO4J_PASSWORD not set in env")
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY not set — Graphiti needs an OpenAI-compatible key "
            "(Together AI in our setup). Add to /opt/fletcher/.env."
        )


async def get_graphiti() -> Any:
    """Lazy-initialize the singleton Graphiti client.

    Configured for Together AI by default (OPENAI_BASE_URL=https://api.together.xyz/v1).
    Falls back to OpenAI proper if OPENAI_BASE_URL is unset.
    """
    global _graphiti
    if _graphiti is not None:
        return _graphiti
    _require_keys()

    from graphiti_core import Graphiti
    from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
    from graphiti_core.llm_client.config import LLMConfig
    from graphiti_core.llm_client.openai_client import OpenAIClient

    llm_config = LLMConfig(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        model=GRAPHITI_LLM_MODEL,
        small_model=GRAPHITI_SMALL_MODEL,
    )
    llm_client = OpenAIClient(config=llm_config)

    embedder = OpenAIEmbedder(
        config=OpenAIEmbedderConfig(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            embedding_model=GRAPHITI_EMBED_MODEL,
            embedding_dim=GRAPHITI_EMBED_DIM,
        )
    )

    _graphiti = Graphiti(
        NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
        llm_client=llm_client, embedder=embedder,
    )
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
    group_id: str,
    source_description: str = "",
) -> None:
    """Pre-demo ingestion (scripts/ingest_graphiti.py).

    Note: graphiti-core 0.29.1 takes a single group_id on write but accepts
    multiple group_ids on search. Tenant-scope is what the demo queries
    against, so we group by tenant.
    """
    from graphiti_core.nodes import EpisodeType
    g = await get_graphiti()
    await g.add_episode(
        name=name,
        episode_body=body,
        source=EpisodeType.message,
        source_description=source_description,
        reference_time=reference_time,
        group_id=group_id,
    )


async def add_message_episode(
    *,
    name: str,
    body: str,
    tenant_id: str,
    unit_id: str | None,  # noqa: ARG001 — kept for caller compat
    sent_at: datetime,
) -> None:
    """Convenience wrapper for the intake pipeline. Groups by tenant."""
    await add_episode(
        name=name, body=body, reference_time=sent_at,
        group_id=tenant_group(tenant_id),
        source_description=f"intake from {tenant_id}",
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
