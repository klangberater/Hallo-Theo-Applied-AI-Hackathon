"""Graphiti wrapper — the moat.

Single source for graphiti-core access. Reads NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, OPENAI_API_KEY from env. Exposes helpers for group_id construction ('tenant:<id>', 'property:<id>', 'vendor:<id>').

Owner: Lead 1 (Graphiti). PRODUCT_SPEC §6.2 + §6.3.
CRITICAL: if Graphiti isn't returning real temporal facts by Saturday noon, this file is where the fire is.

See: docs/PRODUCT_SPEC.md
TODO: implementation goes here.
"""
