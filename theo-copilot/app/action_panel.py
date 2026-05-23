"""Suggested actions + Approve & Send.

Renders the suggested_actions stack from the EnrichmentPayload. Each action
has its own Approve button which calls the appropriate execute_* helper.
"""
from __future__ import annotations

import streamlit as st

from app import db_sync


ACTION_LABELS = {
    "send_whatsapp_reply": "📱 WhatsApp-Antwort senden",
    "send_email_reply": "✉️ E-Mail-Antwort senden",
    "dispatch_vendor": "🔧 Handwerker beauftragen",
    "approve_offer": "✅ Angebot freigeben",
    "request_invoice_itemization": "📑 Belegaufstellung anfordern",
    "escalate_to_human": "⬆️ Eskalation an Team Lead",
}


def render(ticket: dict) -> None:
    actions = ticket.get("suggested_actions") or []
    if not actions:
        return

    st.markdown("---")
    st.markdown("**Vorgeschlagene Aktionen**")

    for idx, action in enumerate(actions):
        atype = action.get("action_type", "unknown")
        label = ACTION_LABELS.get(atype, atype)
        confidence = action.get("confidence", "medium")

        with st.container():
            cols = st.columns([3, 1])
            with cols[0]:
                st.markdown(f"**{idx + 1}. {label}**")
                if action.get("rationale"):
                    st.caption(action["rationale"])
            with cols[1]:
                approve_key = f"approve_{ticket['id']}_{idx}"
                if st.button(
                    f"Freigeben ({confidence})",
                    key=approve_key,
                    type="primary" if confidence == "high" else "secondary",
                    use_container_width=True,
                ):
                    _execute(ticket, action)
                    st.success("Ausgeführt.")
                    st.rerun()

            # Inline draft for messages — let Sarah edit before approving
            payload = action.get("payload") or {}
            if atype == "send_whatsapp_reply" and payload.get("body"):
                edited = st.text_area(
                    "Antwort (bearbeitbar)",
                    value=payload["body"],
                    height=180,
                    key=f"draft_{ticket['id']}_{idx}",
                    label_visibility="collapsed",
                )
                # Update payload in place so the approve button uses the edited body
                payload["body"] = edited


def _execute(ticket: dict, action: dict) -> None:
    """Call the right db_sync helper for the given action."""
    atype = action.get("action_type")
    payload = action.get("payload") or {}

    if atype == "send_whatsapp_reply":
        thread_id = payload.get("thread_id") or ticket.get("source_thread_id")
        if thread_id and payload.get("body"):
            db_sync.execute_send_whatsapp(thread_id, payload["body"])

    elif atype == "dispatch_vendor":
        db_sync.execute_dispatch_vendor(
            vendor_id=payload.get("vendor_id", ""),
            ticket_id=ticket["id"],
            scope=payload.get("scope", ""),
            urgency=payload.get("urgency", "Standard"),
        )

    elif atype == "approve_offer":
        offer_id = payload.get("offer_id")
        if offer_id:
            db_sync.execute_approve_offer(offer_id)

    elif atype in {"send_email_reply", "request_invoice_itemization", "escalate_to_human"}:
        # Best-effort logging only — these don't need to do real I/O for the demo.
        st.toast(f"Aktion '{atype}' protokolliert (kein externer Versand).")
