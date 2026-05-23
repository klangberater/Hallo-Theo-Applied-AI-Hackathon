"""Streamlit entry point — the inbox.

Three-column layout per PRODUCT_SPEC §8 View 2:
- Left:   ticket list (inbox.py)
- Middle: ticket detail conversation + action panel (ticket_detail.py, action_panel.py)
- Right:  enrichment cards (enrichment_cards.py) + 'Why?' trace toggle

Trace state lives in st.session_state AND mirrors to theo.trace_events for re-run recovery (PRODUCT_SPEC §12.2).

Owner: Lead 4.

See: docs/PRODUCT_SPEC.md
TODO: implementation goes here.
"""
