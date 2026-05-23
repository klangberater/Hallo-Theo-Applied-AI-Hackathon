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
) -> None:
    """Render ticket rows. Each row is an <a href="?t=<id>"> link;
    main.py reads the query param to set the active ticket."""
    if not tickets:
        st.markdown(
            "<div class='empty-state' style='padding:var(--space-8)'>"
            "Keine Tickets.</div>",
            unsafe_allow_html=True,
        )
        return

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

        # Single-line HTML: Streamlit's markdown parser treats 4+ space
        # indents as code blocks and breaks HTML-block context on empty
        # interpolations (priority/mode_chip can be ""). Keep it on one line.
        # Whole row is wrapped in an <a> so the click target is browser-native
        # — main.py picks up ?t=<id> via st.query_params.
        row_html = (
            f'<a class="inbox-row-link" href="?t={escape(ticket_id)}" '
            f'aria-label="Ticket {escape(tenant_name)} öffnen">'
            f'<div class="{row_class}">'
            '<div class="inbox-row-dot"></div>'
            '<div class="inbox-row-body">'
            '<div class="inbox-row-top">'
            f'<span class="inbox-row-sender">{escape(tenant_name)}</span>'
            '<div class="inbox-row-meta">'
            f'<span class="inbox-row-channel" title="{channel}">'
            f'{channel_icon}</span>'
            f'{priority_html}'
            f'<span class="inbox-row-time">{escape(ago)}</span>'
            '</div></div>'
            '<div class="inbox-row-subject">'
            f'{"".join(subject_parts)}{incidents_html}{mode_chip}'
            '</div>'
            f'<div class="inbox-row-preview">{escape(preview)}</div>'
            '</div></div>'
            '</a>'
        )

        st.markdown(row_html, unsafe_allow_html=True)
