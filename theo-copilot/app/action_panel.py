"""Suggested actions — design-system action cards + Approve button."""
from __future__ import annotations

import streamlit as st

from app import db_sync


ACTION_LABELS = {
    "send_whatsapp_reply":          ("WhatsApp-Antwort senden", "💬"),
    "send_email_reply":             ("E-Mail-Antwort senden", "✉"),
    "dispatch_vendor":              ("Handwerker beauftragen", "🔧"),
    "approve_offer":                ("Angebot freigeben", "✓"),
    "request_invoice_itemization":  ("Belegaufstellung anfordern", "📑"),
    "escalate_to_human":            ("An Team Lead eskalieren", "⬆"),
}


def _card_class(confidence: str, action_type: str) -> str:
    if confidence == "low":
        return "action-card critical"
    if action_type in {"dispatch_vendor", "approve_offer"}:
        return "action-card irreversible"
    if confidence == "medium":
        return "action-card high"
    return "action-card"


def render(ticket: dict) -> None:
    actions = ticket.get("suggested_actions") or []
    if not actions:
        return

    st.markdown(
        "<p class='section-label'>Vorgeschlagene Aktionen</p>",
        unsafe_allow_html=True,
    )

    for idx, action in enumerate(actions):
        atype = action.get("action_type", "unknown")
        label, icon = ACTION_LABELS.get(atype, (atype, "·"))
        confidence = action.get("confidence", "medium")
        card_cls = _card_class(confidence, atype)
        rationale = action.get("rationale", "")

        st.markdown(
            f"""
            <div class='{card_cls}'>
              <p class='action-title'>{icon} &nbsp; {label}</p>
              <p class='action-rationale'>{rationale}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Inline editable draft for messages
        payload = action.get("payload") or {}
        if atype == "send_whatsapp_reply" and payload.get("body"):
            edited = st.text_area(
                "Antwort (bearbeitbar)",
                value=payload["body"],
                height=170,
                key=f"draft_{ticket['id']}_{idx}",
                label_visibility="collapsed",
            )
            payload["body"] = edited

        cols = st.columns([1, 1, 4])
        with cols[0]:
            if st.button(
                "Freigeben",
                key=f"approve_{ticket['id']}_{idx}",
                type="primary",
                use_container_width=True,
            ):
                _execute(ticket, action)
                st.success(f"„{label}" + "“ ausgeführt.")
                st.rerun()
        with cols[1]:
            if st.button(
                "Ablehnen",
                key=f"reject_{ticket['id']}_{idx}",
                use_container_width=True,
            ):
                st.toast("Aktion abgelehnt.")


def _execute(ticket: dict, action: dict) -> None:
    atype = action.get("action_type")
    payload = action.get("payload") or {}

    if atype == "send_whatsapp_reply":
        thread_id = payload.get("thread_id") or ticket.get("source_thread_id")
        if thread_id and payload.get("body"):
            result = db_sync.execute_send_whatsapp(thread_id, payload["body"])
            if not result.get("sent_to_whatsapp"):
                st.warning(
                    "Antwort gespeichert, aber WhatsApp-Bridge nicht erreichbar: "
                    + (result.get("error") or "unknown")
                )

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
        st.toast(f"„{atype}" + "“ protokolliert (kein externer Versand).")
