"""Streamlit entry point — Theo Copilot operations inbox.

Three-column layout per PRODUCT_SPEC §8 View 2:
- Left:   ticket list (inbox)
- Middle: conversation + suggested actions
- Right:  enrichment cards

Run:
    cd theo-copilot && streamlit run app/main.py \\
        --server.port 8501 --server.address 127.0.0.1
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

from app import action_panel, enrichment_cards, inbox, ticket_detail
from app.db_sync import fetch_ticket, fetch_ticket_list


st.set_page_config(
    page_title="Theo Copilot — Operations Inbox",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed",
)


CSS = """
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; max-width: 100% !important; }
    [data-testid="stHeader"] { display: none; }
    .ticket-row {
        padding: 0.6rem 0.8rem;
        border-radius: 8px;
        border: 1px solid #2a2a2a;
        margin-bottom: 0.4rem;
        background: #141414;
        color: #f5f5f5;
        cursor: pointer;
    }
    .ticket-row.selected { border-color: #fbbf24; background: #1a1a1a; }
    .ticket-row .meta { color: #71717a; font-size: 0.75rem; }
    .ticket-row .title { color: #f5f5f5; font-weight: 500; }
    .pattern-flag { color: #fbbf24; font-size: 0.8rem; }
    .priority-DRINGEND { color: #ef4444; font-weight: 600; }
    .priority-Hoch { color: #f97316; font-weight: 500; }
    .priority-Standard { color: #71717a; }
    .source-pill {
        display: inline-block; font-size: 0.7rem; padding: 0.1rem 0.5rem;
        border-radius: 999px; background: #27272a; color: #a1a1aa;
        margin-left: 0.4rem;
    }
    .source-pill.graphiti { background: #4c1d95; color: #ddd6fe; }
    .source-pill.stub { background: #422006; color: #fde68a; }
    .source-pill.postgres-fallback { background: #1e3a8a; color: #bfdbfe; }
    .card {
        background: #141414; border: 1px solid #2a2a2a; border-radius: 10px;
        padding: 0.9rem 1rem; margin-bottom: 0.7rem;
        color: #e4e4e7;
    }
    .card p, .card li, .card strong, .card em { color: #e4e4e7; }
    .card h4 { margin: 0 0 0.4rem; font-size: 0.85rem; color: #fbbf24;
               text-transform: uppercase; letter-spacing: 0.05em; }
    .card .warn { color: #fca5a5; }
    .source-cite { color: #71717a; font-size: 0.7rem; margin-top: 0.4rem; }
    .draft-reply textarea { font-family: inherit !important; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "selected_ticket_id" not in st.session_state:
    st.session_state.selected_ticket_id = None
if "show_trace" not in st.session_state:
    st.session_state.show_trace = False


# ---------------------------------------------------------------------------
# Layout — 3 columns + header
# ---------------------------------------------------------------------------

# Header
header_l, header_r = st.columns([4, 1])
with header_l:
    st.markdown(
        "### Theo Copilot &nbsp; <span style='color:#71717a;font-weight:400'>· Sarah Weber</span>",
        unsafe_allow_html=True,
    )
with header_r:
    if st.button("⟳ Refresh", use_container_width=True):
        st.rerun()

col_list, col_detail, col_enrich = st.columns([1, 1.4, 1.4], gap="medium")


# Left column — ticket list
with col_list:
    st.markdown("##### Inbox")
    tickets = fetch_ticket_list()
    selected_id = inbox.render(tickets, st.session_state.selected_ticket_id)
    if selected_id and selected_id != st.session_state.selected_ticket_id:
        st.session_state.selected_ticket_id = selected_id
        st.rerun()


# Middle + Right columns — detail + enrichment
if st.session_state.selected_ticket_id:
    ticket = fetch_ticket(st.session_state.selected_ticket_id)
    if ticket is None:
        with col_detail:
            st.warning("Ticket not found.")
    else:
        with col_detail:
            ticket_detail.render(ticket)
            action_panel.render(ticket)
        with col_enrich:
            enrichment_cards.render(ticket)
else:
    with col_detail:
        st.markdown(
            "<div style='color:#71717a;padding:3rem 1rem;text-align:center'>"
            "Wählen Sie ein Ticket aus der Liste aus."
            "</div>",
            unsafe_allow_html=True,
        )
