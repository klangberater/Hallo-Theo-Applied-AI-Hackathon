"""L3 temporal memory — Graphiti queries. THE MOAT.

query_temporal_memory(query: str, group_id: str, num_results: int = 10) -> list[TemporalFact]
get_entity_timeline(entity_name: str, group_id: str) -> list[Episode]

If USE_LIVE_GRAPHITI=false (kill-switch, §12.1), return from the JSON cache at KILL_SWITCH_CACHE_PATH instead of querying Graphiti.

Owner: Lead 1 → Lead 2 handoff. PRODUCT_SPEC §5.3 + §12.1.
CRITICAL: by Saturday noon this must return real temporal facts for the Köhler query. If not, that's a fire — see CLAUDE_MD_APPEND.

See: docs/PRODUCT_SPEC.md
TODO: implementation goes here.
"""
