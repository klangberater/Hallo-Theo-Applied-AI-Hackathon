"""Ticket detail — middle column: serif title + conversation bubbles."""
from __future__ import annotations

from datetime import timezone

import streamlit as st

from app.db_sync import fetch_thread_messages


_PRIORITY_CHIP = {
    "DRINGEND": "<span class='chip chip-critical'>Dringend</span>",
    "Hoch":     "<span class='chip chip-warning'>Hoch</span>",
    "Standard": "<span class='chip chip-neutral'>Standard</span>",
}


def render(ticket: dict) -> None:
    tenant = ticket.get("tenant_name") or "unbekannt"
    unit = ticket.get("unit_label") or ""
    address = ticket.get("property_address") or "Zossener Str. 47, 10961 Berlin"
    priority = ticket.get("priority") or "Standard"
    status = ticket.get("status") or "unknown"

    chip_priority = _PRIORITY_CHIP.get(priority, _PRIORITY_CHIP["Standard"])
    status_chip = (
        f"<span class='chip chip-info'>{status.replace('_', ' ')}</span>"
        if status in {"open", "enriching"}
        else f"<span class='chip chip-success'>{status.replace('_', ' ')}</span>"
    )

    sep = "<span class='detail-subtitle-sep'>·</span>"

    st.markdown(
        f"""
        <h2 class='detail-title'>{tenant} — {unit}</h2>
        <div class='detail-subtitle'>
          <span>{address}</span> {sep}
          <span>Ticket <code style="font-family:var(--font-mono);font-size:12px">{ticket['id']}</code></span>
          {sep} {chip_priority} {status_chip}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Conversation ----------------------------------------------------
    thread_id = ticket.get("source_thread_id")
    messages = fetch_thread_messages(thread_id) if thread_id else []

    st.markdown("<p class='section-label'>Konversation</p>", unsafe_allow_html=True)

    if not messages:
        body = (ticket.get("full_text") or "").strip()
        st.markdown(
            f"""
            <div class='msg-bubble'>
              <div class='msg-meta'><strong>{tenant}</strong></div>
              <p class='msg-body'>{body}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for m in messages:
        sent_at = m["sent_at"]
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        when = sent_at.strftime("%d.%m. %H:%M")
        cls = "msg-bubble" if m["direction"] == "inbound" else "msg-bubble outbound"
        st.markdown(
            f"""
            <div class='{cls}'>
              <div class='msg-meta'><strong>{m['sender']}</strong>
                <span>·</span><span>{when}</span></div>
              <p class='msg-body'>{m['body']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
