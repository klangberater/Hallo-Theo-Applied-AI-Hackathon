"""Inbox list — dense email-client style rows. Whole row is the click target."""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape

import streamlit as st


CHANNEL_ICON = {
    "whatsapp": "💬",
    "email": "✉",
    "voicemail": "📞",
    "portal": "🖥",
}

_MODE_CHIP = {
    "autonomous_done": (
        "<span class='mode-chip mode-chip-autonomous'>✓ Autonom erledigt</span>"
    ),
    "bundle_approve": (
        "<span class='mode-chip mode-chip-bundle'>Einmal bestätigen</span>"
    ),
    "propose": "",  # default — no chip; "Schritt für Schritt" is implicit
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


def _preview(text: str | None, limit: int = 110) -> str:
    if not text:
        return ""
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _priority_chip(priority: str) -> str:
    if priority == "DRINGEND":
        return "<span class='chip chip-critical inbox-chip'>Dringend</span>"
    if priority == "Hoch":
        return "<span class='chip chip-warning inbox-chip'>Hoch</span>"
    return ""


def render(
    tickets: list[dict],
    selected_id: str | None,
    opened_ids: set[str],
) -> str | None:
    """Render ticket rows. Returns newly-selected id if changed."""
    if not tickets:
        st.markdown(
            "<div class='empty-state' style='padding:var(--space-8)'>"
            "Keine Tickets.</div>",
            unsafe_allow_html=True,
        )
        return None

    new_selection: str | None = None
    for t in tickets:
        ticket_id = t["id"]
        is_selected = ticket_id == selected_id
        is_unread = ticket_id not in opened_ids
        priority = t.get("priority") or "Standard"
        channel = (t.get("channel") or "whatsapp").lower()
        channel_icon = CHANNEL_ICON.get(channel, "📨")
        pattern_raw = t.get("pattern_count")
        pattern_count = int(pattern_raw) if pattern_raw else 0
        intent = (
            t.get("classified_intent") or t.get("category") or "Allgemein"
        ).title()
        tenant_name = t.get("tenant_name", "unknown")
        unit_label = t.get("unit_label", "")
        ago = _ago(t["opened_at"])
        preview = _preview(t.get("full_text"))
        autonomy = t.get("autonomy_mode") or "propose"
        mode_chip = _MODE_CHIP.get(autonomy, "")

        classes = ["inbox-row"]
        if is_selected:
            classes.append("selected")
        if is_unread:
            classes.append("unread")
        row_class = " ".join(classes)

        priority_html = _priority_chip(priority)
        incidents_html = (
            f"<span class='inbox-pill-incidents'>🔁 {pattern_count}</span>"
            if pattern_count >= 3
            else ""
        )

        subject_parts = [
            f"<span class='inbox-row-category'>{escape(intent)}</span>"
        ]
        if unit_label:
            address_text = f"{escape(unit_label)} · Zossener Str. 47"
            subject_parts.append(
                "<span class='inbox-row-sep'>·</span>"
                f"<span class='inbox-row-address'>{address_text}</span>"
            )

        row_html = f"""
        <div class="{row_class}">
          <div class="inbox-row-dot"></div>
          <div class="inbox-row-body">
            <div class="inbox-row-top">
              <span class="inbox-row-sender">{escape(tenant_name)}</span>
              <div class="inbox-row-meta">
                <span class="inbox-row-channel" title="{channel}">{channel_icon}</span>
                {priority_html}
                <span class="inbox-row-time">{escape(ago)}</span>
              </div>
            </div>
            <div class="inbox-row-subject">
              {''.join(subject_parts)}
              {incidents_html}
              {mode_chip}
            </div>
            <div class="inbox-row-preview">{escape(preview)}</div>
          </div>
        </div>
        """

        with st.container(key=f"ticket-row-{ticket_id}"):
            st.markdown(row_html, unsafe_allow_html=True)
            if st.button(
                f"Ticket {tenant_name} öffnen",
                key=f"sel_{ticket_id}",
                use_container_width=True,
            ):
                new_selection = ticket_id

    return new_selection
