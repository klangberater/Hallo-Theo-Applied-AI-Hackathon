"""Async Postgres connection to the theo schema.

Builds an asyncpg pool from DATABASE_URL. Every connection runs SET search_path TO theo, public so the agent's L2 tools see theo tables first.

Owner: Lead 3 / shared. PRODUCT_SPEC §2.4.

See: docs/PRODUCT_SPEC.md
TODO: implementation goes here.
"""
