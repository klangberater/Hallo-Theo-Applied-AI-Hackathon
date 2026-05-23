"""Pre-compute the kill-switch fallback cache.

Runs the demo-critical Graphiti queries ONCE while Graphiti is healthy,
dumps results to KILL_SWITCH_CACHE_PATH. When USE_LIVE_GRAPHITI=false,
l3_memory reads from here instead — same payload shape, demo keeps
running if Together AI or Neo4j goes sideways.

Run AFTER scripts/ingest_graphiti.py succeeds. Re-run any time before
a dry run to refresh the cache.

PRODUCT_SPEC §12.1
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from infra.graphiti_client import search_facts  # noqa: E402


# Same (query, group_id) pairs the agent uses during the demo. Keep small —
# this cache exists to back up the moments that matter, not everything.
DEMO_QUERIES = [
    ("heating issues radiator problems", "tenant_koehler"),
    ("Heizung Wohnzimmer Köhler", "tenant_koehler"),
    ("Mietminderung Köhler", "tenant_koehler"),
    ("Bergmann offer thermostat replacement", "tenant_koehler"),
    ("internal chat Jonas pre-approval", "tenant_koehler"),
    ("medical condition vulnerability", "tenant_koehler"),
]


async def main() -> None:
    cache_path = Path(
        os.environ.get("KILL_SWITCH_CACHE_PATH", str(ROOT / "scripts" / "_kill_switch_cache.json"))
    )
    cache: dict[str, list[dict]] = {}

    for query, group_id in DEMO_QUERIES:
        print(f"caching: {query!r} / {group_id}")
        try:
            facts = await search_facts(query=query, group_id=group_id, limit=10)
            key = f"{group_id}|{query}"
            cache[key] = facts
            print(f"  → {len(facts)} facts")
        except Exception as e:  # noqa: BLE001
            print(f"  !! failed: {e}")
            continue

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, default=str, ensure_ascii=False, indent=2))
    print(f"--- wrote {cache_path} ({sum(len(v) for v in cache.values())} total facts) ---")


if __name__ == "__main__":
    asyncio.run(main())
