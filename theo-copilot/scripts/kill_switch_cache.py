"""Pre-compute the kill-switch fallback cache.

Runs the demo-critical Graphiti queries ONCE while Graphiti is healthy, dumps results to KILL_SWITCH_CACHE_PATH. When USE_LIVE_GRAPHITI=false, l3_memory reads from here instead.

CRITICAL: build this Friday night after first successful ingestion. Do not defer.

Owner: Lead 1. PRODUCT_SPEC §12.1.

See: docs/PRODUCT_SPEC.md
TODO: implementation goes here.
"""
