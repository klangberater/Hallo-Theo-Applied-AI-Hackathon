"""The enrichment agent — Anthropic SDK tool-use loop.

enrich_ticket(ticket_id: str) -> EnrichmentPayload

Pseudocode is in PRODUCT_SPEC §7.2 — implement it verbatim. Single Python function, no framework. While stop_reason != end_turn, dispatch tool_use blocks against TOOL_DISPATCH, append tool_result, continue. Each tool call is logged via trace.log_trace_step.

Model: claude-opus-4-7 (override via ANTHROPIC_MODEL_REASONING env). No streaming.

Owner: Lead 2 (Agent). THIS IS THE HOT PATH FOR THE DEMO.

See: docs/PRODUCT_SPEC.md
TODO: implementation goes here.
"""
