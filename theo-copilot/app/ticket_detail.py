"""Ticket detail — middle column: conversation + (later) draft reply."""
from __future__ import annotations

from datetime import timezone

import streamlit as st

from app.db_sync import fetch_thread_messages


def render(ticket: dict) -> None:
    st.markdown(f"#### {ticket.get('tenant_name', 'unknown')} — {ticket.get('unit_label', '')}")
    st.caption(
        f"{ticket.get('property_address', '')}  ·  "
        f"Ticket {ticket['id']}  ·  "
        f"Status: **{ticket.get('status', 'unknown')}**  ·  "
        f"{ticket.get('priority', 'Standard')}"
    )

    # Conversation thread
    thread_id = ticket.get("source_thread_id")
    messages = fetch_thread_messages(thread_id) if thread_id else []
    if not messages:
        # Fall back to showing the inbound body from the ticket itself
        st.markdown("**Eingehende Nachricht:**")
        with st.container():
            st.markdown(
                f"<div style='background:#1a1a1a;border:1px solid #2a2a2a;"
                f"padding:0.8rem;border-radius:8px;white-space:pre-wrap'>"
                f"{(ticket.get('full_text') or '').strip()}"
                f"</div>",
                unsafe_allow_html=True,
            )
        return

    st.markdown("**Konversation**")
    for m in messages:
        sent_at = m["sent_at"]
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        when = sent_at.strftime("%d.%m. %H:%M")
        is_inbound = m["direction"] == "inbound"
        align = "flex-start" if is_inbound else "flex-end"
        bg = "#1a1a1a" if is_inbound else "#1e3a3a"
        st.markdown(
            f"<div style='display:flex;justify-content:{align};margin:0.4rem 0'>"
            f"<div style='background:{bg};border:1px solid #2a2a2a;padding:0.6rem 0.8rem;"
            f"border-radius:10px;max-width:80%;white-space:pre-wrap'>"
            f"<div style='font-size:0.7rem;color:#71717a;margin-bottom:0.2rem'>"
            f"{m['sender']} · {when}</div>"
            f"{m['body']}"
            f"</div></div>",
            unsafe_allow_html=True,
        )
