"""Session-log writer for the reasoning trace UI.

log_trace_step(ticket_id: str, step: int, kind: str, payload: dict)

Writes to theo.trace_events. The Streamlit 'Why?' toggle reads from here to render the trace panel (PRODUCT_SPEC §8 View 3).

Owner: Lead 2.

See: docs/PRODUCT_SPEC.md
TODO: implementation goes here.
"""
