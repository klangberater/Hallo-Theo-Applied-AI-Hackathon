"""Ticket list — left column. Fletcher design-system inbox row pattern."""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st


CHANNEL_ICON = {
    "whatsapp": "💬",
    "email": "✉",
    "voicemail": "📞",
    "portal": "🖥",
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


def _bar_class(priority: str) -> str:
    if priority == "DRINGEND":
        return "ticket-bar ticket-bar-critical"
    if priority == "Hoch":
        return "ticket-bar ticket-bar-warning"
    return "ticket-bar ticket-bar-neutral"


def render(tickets: list[dict], selected_id: str | None) -> str | None:
    """Render ticket rows. Returns newly-selected id if changed."""
    if not tickets:
        st.markdown(
            "<div class='empty-state' style='padding:var(--space-8)'>Keine Tickets.</div>",
            unsafe_allow_html=True,
        )
        return None

    new_selection: str | None = None
    for t in tickets:
        ticket_id = t["id"]
        is_selected = ticket_id == selected_id
        priority = t.get("priority") or "Standard"
        channel = (t.get("channel") or "whatsapp").lower()
        channel_icon = CHANNEL_ICON.get(channel, "📨")
        pattern = t.get("pattern_count")
        intent = (t.get("classified_intent") or "").title()
        tenant_name = t.get("tenant_name", "unknown")
        unit_label = t.get("unit_label", "")
        ago = _ago(t["opened_at"])

        meta_parts = [f"{channel_icon} {intent or 'Sonstiges'}"]
        if pattern and int(pattern) >= 3:
            meta_parts.append(f"<span class='ticket-vuln'>🔁 {pattern} Vorfälle</span>")
        meta_html = ' <span class="ticket-meta-sep"></span> '.join(meta_parts)

        selected_class = " selected" if is_selected else ""
        row_html = f"""
        <div class="ticket{selected_class}">
          <div class="{_bar_class(priority)}"></div>
          <div>
            <p class="ticket-name">{tenant_name}</p>
            <p class="ticket-property">{unit_label} · Zossener Str. 47</p>
            <div class="ticket-meta">{meta_html}</div>
          </div>
          <div class="ticket-time">{ago}</div>
        </div>
        """

        # Visual card + transparent overlay button (entire row is the click target).
        with st.container(key=f"ticket-row-{ticket_id}"):
            st.markdown(row_html, unsafe_allow_html=True)
            if st.button(
                f"Ticket {tenant_name} öffnen",
                key=f"sel_{ticket_id}",
                use_container_width=True,
            ):
                new_selection = ticket_id

    return new_selection
