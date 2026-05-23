"""Ticket list — left column of the inbox."""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st


CHANNEL_ICON = {
    "whatsapp": "💬",
    "email": "✉️",
    "voicemail": "📞",
    "portal": "🖥️",
}


def _ago(opened_at) -> str:
    if opened_at is None:
        return ""
    if opened_at.tzinfo is None:
        opened_at = opened_at.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - opened_at
    s = delta.total_seconds()
    if s < 60:
        return "jetzt"
    if s < 3600:
        return f"vor {int(s // 60)} min"
    if s < 86400:
        return f"vor {int(s // 3600)} h"
    return f"vor {delta.days} d"


def render(tickets: list[dict], selected_id: str | None) -> str | None:
    """Render ticket rows. Returns the newly-selected id, if changed."""
    if not tickets:
        st.info("Keine Tickets.")
        return None

    new_selection: str | None = None
    for t in tickets:
        ticket_id = t["id"]
        icon = CHANNEL_ICON.get(t.get("channel") or "whatsapp", "📨")
        pattern = t.get("pattern_count")
        title = f"{t.get('tenant_name', 'unknown')} · {t.get('unit_label', '')}"
        meta = f"{icon} {(t.get('classified_intent') or '').title()} · {_ago(t['opened_at'])}"
        if pattern and int(pattern) >= 3:
            meta += f" · 🔁 {pattern} Vorfälle"
        priority = t.get("priority") or "Standard"
        is_selected = ticket_id == selected_id

        with st.container():
            # Use a button per row — simpler than custom click handling
            cols = st.columns([1, 0.001])
            with cols[0]:
                if st.button(
                    f"**{title}**\n\n{meta}",
                    key=f"sel_{ticket_id}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    new_selection = ticket_id
        # Priority pill below
        if priority != "Standard":
            color = "#ef4444" if priority == "DRINGEND" else "#f97316"
            st.markdown(
                f"<div style='margin-top:-0.6rem;margin-bottom:0.8rem;font-size:0.7rem;"
                f"color:{color};text-align:right;padding-right:0.4rem'>{priority}</div>",
                unsafe_allow_html=True,
            )

    return new_selection
