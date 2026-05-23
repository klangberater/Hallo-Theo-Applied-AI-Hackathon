"""Inbox list — dense email-client style rows. Whole row is the click target.

Renders three derived states from the ticket's `derived_state` field:
  open      — full opacity, priority chip, unread dot
  done      — dimmed, "Erledigt" chip, no unread, archive countdown
  archived  — used in the Archive tab only; full opacity, "Archiviert" chip
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
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

DONE_GRACE_HOURS = 72  # mirror of db_sync constant; kept local to avoid cycle


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


def _archive_remaining(done_at) -> str:
    if done_at is None:
        return "in Kürze"
    if done_at.tzinfo is None:
        done_at = done_at.replace(tzinfo=timezone.utc)
    archive_at = done_at + timedelta(hours=DONE_GRACE_HOURS)
    delta = archive_at - datetime.now(timezone.utc)
    s = int(delta.total_seconds())
    if s <= 0:
        return "in Kürze"
    days, rem = divmod(s, 86400)
    hours = rem // 3600
    if days:
        return f"in {days}T {hours}h"
    return f"in {hours}h"


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
    view: str = "inbox",
) -> None:
    """Render ticket rows. Each row is an <a href="?t=<id>"> link;
    main.py reads the query param to set the active ticket."""
    if not tickets:
        empty_msg = (
            "Keine archivierten Tickets. Erledigte Tickets erscheinen hier "
            "3 Tage nach dem Abschluss."
            if view == "archive"
            else "Keine Tickets."
        )
        st.markdown(
            "<div class='empty-state' style='padding:var(--space-8)'>"
            f"{empty_msg}</div>",
            unsafe_allow_html=True,
        )
        return

    for t in tickets:
        ticket_id = t["id"]
        state = t.get("derived_state") or "open"
        is_selected = ticket_id == selected_id
        # "Unread" only meaningful for open tickets — done/archived rows
        # don't get the blue dot or the bold sender.
        is_unread = state == "open" and ticket_id not in opened_ids
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
        if state == "done":
            classes.append("done")
        if state == "archived":
            classes.append("archived")
        row_class = " ".join(classes)

        # State-dependent meta chips.
        if state == "done":
            # Replace priority + autonomy chips with a green "Erledigt" chip.
            priority_html = (
                "<span class='chip chip-success inbox-chip'>✓ Erledigt</span>"
            )
            mode_chip_render = ""
            incidents_render = ""  # de-emphasize urgency on closed work
        elif state == "archived":
            done_at = t.get("done_at")
            when = (
                done_at.strftime("%d.%m.")
                if done_at is not None
                else ""
            )
            priority_html = (
                f"<span class='chip chip-neutral inbox-chip'>"
                f"Archiviert {when}</span>"
            )
            mode_chip_render = ""
            incidents_render = ""
        else:
            priority_html = _priority_chip(priority)
            mode_chip_render = mode_chip
            incidents_render = (
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

        # For done tickets in the inbox, replace preview with a status line.
        if state == "done":
            done_at = t.get("done_at")
            done_when = _ago(done_at) if done_at is not None else ""
            remaining = _archive_remaining(done_at)
            preview_text = (
                f"Erledigt {done_when} · Archivierung {remaining}"
            )
        elif state == "archived":
            note = (t.get("resolution_note") or "").strip()
            preview_text = note or "Archiviert."
        else:
            preview_text = preview

        # Single-line HTML to avoid Streamlit markdown parsing artifacts.
        row_html = (
            f'<a class="inbox-row-link" href="?t={escape(ticket_id)}" '
            f'target="_self" '
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
            f'{"".join(subject_parts)}{incidents_render}{mode_chip_render}'
            '</div>'
            f'<div class="inbox-row-preview">{escape(preview_text)}</div>'
            '</div></div>'
            '</a>'
        )

        st.markdown(row_html, unsafe_allow_html=True)
