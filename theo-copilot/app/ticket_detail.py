"""Ticket detail — middle column: serif title + conversation bubbles.

Also hosts the Mark-as-done / Reopen affordances and the Done banner
(per spec: Fletcher — Mark as Done & Archive)."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from html import escape

import streamlit as st

from app.db_sync import (
    DONE_GRACE_HOURS,
    fetch_thread_messages,
    mark_ticket_done,
    reopen_ticket,
)


_PRIORITY_CHIP = {
    "DRINGEND": "<span class='chip chip-critical'>Dringend</span>",
    "Hoch":     "<span class='chip chip-warning'>Hoch</span>",
    "Standard": "<span class='chip chip-neutral'>Standard</span>",
}


def _ensure_utc(dt) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _relative_past(dt: datetime) -> str:
    delta = datetime.now(timezone.utc) - _ensure_utc(dt)
    s = int(delta.total_seconds())
    if s < 60:
        return "gerade eben"
    if s < 3600:
        return f"vor {s // 60} Min."
    if s < 86400:
        return f"vor {s // 3600} Std."
    return f"vor {delta.days} Tagen"


def _archive_remaining(done_at: datetime) -> str:
    archive_at = _ensure_utc(done_at) + timedelta(hours=DONE_GRACE_HOURS)
    delta = archive_at - datetime.now(timezone.utc)
    s = int(delta.total_seconds())
    if s <= 0:
        return "in Kürze"
    days, rem = divmod(s, 86400)
    hours = rem // 3600
    if days:
        return f"in {days}T {hours}h"
    minutes = (rem % 3600) // 60
    return f"in {hours}h {minutes}Min."


@st.dialog("Ticket als erledigt markieren?")
def _confirm_mark_done(ticket: dict) -> None:
    tenant = ticket.get("tenant_name", "diesem Mieter")
    st.write(
        f"Dies schließt die Konversation mit **{tenant}**. "
        f"Das Ticket bleibt {DONE_GRACE_HOURS // 24} Tage im Posteingang, "
        "dann wandert es ins Archiv. Sie können dies jederzeit rückgängig "
        "machen."
    )
    note = st.text_input(
        "Lösungsnotiz (optional)",
        max_chars=280,
        placeholder=(
            "z.B. Heizkörper von Bergmann zurückgesetzt, Mieterin bestätigt."
        ),
    )
    cols = st.columns(2)
    if cols[0].button("Abbrechen", use_container_width=True):
        st.rerun()
    if cols[1].button(
        "Erledigt", type="primary", use_container_width=True,
        key="confirm_mark_done_btn",
    ):
        mark_ticket_done(
            ticket["id"], "Sarah Weber", (note or None),
        )
        st.toast("Ticket als erledigt markiert", icon="✓")
        st.rerun()


def _render_done_banner(ticket: dict) -> None:
    state = ticket.get("derived_state")
    if state not in {"done", "archived"}:
        return
    done_at = ticket.get("done_at")
    done_by = ticket.get("done_by") or "—"
    resolution = (ticket.get("resolution_note") or "").strip()

    note_html = ""
    if resolution:
        note_html = (
            f"<div class='done-banner-note'>Notiz: "
            f"<em>{escape(resolution)}</em></div>"
        )

    if state == "done" and done_at:
        when = _relative_past(done_at)
        remaining = _archive_remaining(done_at)
        text = (
            f"Erledigt {when} von {escape(done_by)}. "
            f"Automatische Archivierung {remaining}."
        )
        cls = "done-banner done"
    else:  # archived
        when_done = (
            _ensure_utc(done_at).strftime("%d.%m.%Y") if done_at else "—"
        )
        text = (
            f"Archiviert. Erledigt am {when_done}"
            f"{' von ' + escape(done_by) if done_by != '—' else ''}."
        )
        cls = "done-banner archived"

    st.markdown(
        f"<div class='{cls}'><div class='done-banner-text'>{text}</div>"
        f"{note_html}</div>",
        unsafe_allow_html=True,
    )

    # Reopen button (one click, no confirm — reopening is reversible).
    if st.button("↺ Wiedereröffnen", key=f"reopen_{ticket['id']}"):
        reopen_ticket(ticket["id"])
        st.toast("Ticket wiedereröffnet", icon="↺")
        st.rerun()


def render(ticket: dict) -> None:
    tenant = ticket.get("tenant_name") or "unbekannt"
    unit = ticket.get("unit_label") or ""
    address = ticket.get("property_address") or "Zossener Str. 47, 10961 Berlin"
    priority = ticket.get("priority") or "Standard"
    status = ticket.get("status") or "unknown"
    state = ticket.get("derived_state") or "open"

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

    # Done banner appears above the Mark-as-done action.
    _render_done_banner(ticket)

    # Mark-as-done lives between the header and the conversation. Hidden
    # if the ticket is already done/archived — Reopen takes its place
    # inside the banner.
    if state == "open":
        if st.button(
            "✓ Als erledigt markieren",
            key=f"mark_done_{ticket['id']}",
            use_container_width=False,
        ):
            _confirm_mark_done(ticket)

    # ---- Conversation ----------------------------------------------------
    thread_id = ticket.get("source_thread_id")
    messages = fetch_thread_messages(thread_id) if thread_id else []

    st.markdown(
        "<p class='section-label'>Konversation</p>", unsafe_allow_html=True
    )

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
