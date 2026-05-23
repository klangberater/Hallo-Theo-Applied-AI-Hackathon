"""Pre-demo episode ingestion into Graphiti.

Reads the 8 hero episodes listed in PRODUCT_SPEC §6.2 from the dataset, builds episode bodies + reference_times + group_ids, calls graphiti.add_episode for each. Idempotent (Graphiti dedupes by name).

Run Friday night. After successful run, immediately run kill_switch_cache.py to snapshot the working query results (§12.1).

Owner: Lead 1.

See: docs/PRODUCT_SPEC.md
TODO: implementation goes here.
"""
