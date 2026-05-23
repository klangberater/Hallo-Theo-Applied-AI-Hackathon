"""Reset between dry runs.

TRUNCATE theo.tickets, theo.channel_threads, theo.channel_messages, theo.proposed_actions, theo.trace_events. Re-run data/seed.py for the static rows. Optionally re-ingest Graphiti (skip if running multiple dry runs in a row — Graphiti is the slow part).

Owner: anyone.

See: docs/PRODUCT_SPEC.md
TODO: implementation goes here.
"""
