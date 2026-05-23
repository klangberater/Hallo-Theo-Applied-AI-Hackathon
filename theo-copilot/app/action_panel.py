"""Suggested actions — three rendering branches by autonomy_mode.

- autonomous_done   → 'Erledigt' badges on every action + 'Was wurde getan?' expander
- bundle_approve    → one 'Umsetzen' button executes all actions atomically
- propose (default) → per-action approve buttons (current behaviour)
"""
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

    enrichment = ticket.get("enrichment") or {}
    autonomy = (enrichment.get("autonomy_mode") or "propose")
    rationale = enrichment.get("autonomy_rationale") or ""

    if autonomy == "autonomous_done":
        _render_autonomous_done(ticket, actions, rationale)
    elif autonomy == "bundle_approve":
        _render_bundle_approve(ticket, actions, rationale)
    else:
        _render_propose(ticket, actions)


# ---------------------------------------------------------------------------
# autonomous_done — already executed; just show what Theo did
# ---------------------------------------------------------------------------

def _render_autonomous_done(ticket: dict, actions: list[dict], rationale: str) -> None:
    st.markdown(
        f"""
        <div class='autonomy-banner autonomous'>
          <p class='autonomy-banner-title'>✓ Autonom erledigt</p>
          <p class='autonomy-banner-body'>{rationale or 'Theo hat dieses Ticket eigenständig bearbeitet — alle Aktionen sind unten dokumentiert.'}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<p class='section-label'>Durchgeführte Aktionen</p>", unsafe_allow_html=True)
    for action in actions:
        atype = action.get("action_type", "unknown")
        label, icon = ACTION_LABELS.get(atype, (atype, "·"))
        executed_at = action.get("executed_at") or ""
        when = executed_at[11:16] if len(executed_at) >= 16 else executed_at
        st.markdown(
            f"""
            <div class='action-card'>
              <div style='display:flex;align-items:center;gap:var(--space-3);
                          justify-content:space-between'>
                <p class='action-title' style='margin:0'>{icon} &nbsp; {label}</p>
                <span class='action-done'>✓ Erledigt {when}</span>
              </div>
              <p class='action-rationale'>{action.get('rationale', '')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Trace expander
    with st.expander("Was Theo gemacht hat (Trace)"):
        trace = db_sync.fetch_trace_events(ticket["id"])
        if not trace:
            st.caption("Keine Trace-Events vorhanden.")
        else:
            for e in trace:
                kind = e.get("kind", "")
                payload = e.get("payload", {})
                ts = e.get("created_at")
                ts_str = ts.strftime("%H:%M:%S") if hasattr(ts, "strftime") else str(ts)[:8]
                st.markdown(
                    f"<div style='font-family:var(--font-mono);font-size:13px;"
                    f"padding:6px 0;border-bottom:1px solid var(--paper-200)'>"
                    f"<span style='color:var(--text-tertiary)'>{ts_str}</span> &nbsp;"
                    f"<strong style='color:var(--teal-700)'>{kind}</strong> &nbsp;"
                    f"<span style='color:var(--text-secondary)'>"
                    f"{str(payload)[:160]}</span></div>",
                    unsafe_allow_html=True,
                )


# ---------------------------------------------------------------------------
# bundle_approve — one Umsetzen runs all atomically
# ---------------------------------------------------------------------------

def _render_bundle_approve(ticket: dict, actions: list[dict], rationale: str) -> None:
    st.markdown(
        f"""
        <div class='autonomy-banner bundle'>
          <p class='autonomy-banner-title'>Einmal bestätigen — {len(actions)} Aktionen</p>
          <p class='autonomy-banner-body'>{rationale or 'Mit einem Klick werden alle drei Aktionen atomar ausgeführt. Bei Fehler in einer Aktion wird das gesamte Bündel zurückgerollt.'}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<p class='section-label'>Aktionen im Bündel</p>", unsafe_allow_html=True)
    # Order by bundle_order so Sarah sees the sequence
    ordered = sorted(actions, key=lambda a: a.get("bundle_order") or 0)

    # Inline editable WhatsApp draft (the only thing Sarah might want to tweak)
    edited_bodies: dict[int, str] = {}
    for idx, action in enumerate(ordered):
        atype = action.get("action_type", "unknown")
        label, icon = ACTION_LABELS.get(atype, (atype, "·"))
        st.markdown(
            f"""
            <div class='action-card high'>
              <p class='action-title'>
                <span style='color:var(--text-tertiary);font-weight:500;
                             margin-right:var(--space-2)'>{idx + 1}.</span>
                {icon} &nbsp; {label}
              </p>
              <p class='action-rationale'>{action.get('rationale', '')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        payload = action.get("payload") or {}
        if atype == "send_whatsapp_reply" and payload.get("body"):
            edited = st.text_area(
                "Antwort (bearbeitbar)",
                value=payload["body"],
                height=160,
                key=f"draft_{ticket['id']}_{idx}",
                label_visibility="collapsed",
            )
            edited_bodies[idx] = edited

    cols = st.columns([2, 1, 3])
    with cols[0]:
        if st.button(
            "Bündel umsetzen",
            key=f"bundle_{ticket['id']}",
            type="primary",
            use_container_width=True,
        ):
            # Splice the edited bodies into the actions
            for idx, body in edited_bodies.items():
                ordered[idx].setdefault("payload", {})["body"] = body
            result = db_sync.execute_bundle(ticket, ordered)
            if result["ok"]:
                st.success(f"✓ {result['executed']} Aktionen ausgeführt.")
                if result.get("warnings"):
                    for w in result["warnings"]:
                        st.warning(w)
            else:
                st.error(f"Bündel fehlgeschlagen: {result.get('error', 'unknown')}")
            st.rerun()
    with cols[1]:
        if st.button("Ablehnen", key=f"bundle_reject_{ticket['id']}", use_container_width=True):
            st.toast("Bündel abgelehnt.")


# ---------------------------------------------------------------------------
# propose — current per-action behaviour
# ---------------------------------------------------------------------------

def _render_propose(ticket: dict, actions: list[dict]) -> None:
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
        if atype == "send_email_reply" and payload.get("body"):
            edited = st.text_area(
                "E-Mail (bearbeitbar)",
                value=payload["body"],
                height=200,
                key=f"emaildraft_{ticket['id']}_{idx}",
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
        st.toast(f"„{atype}" + "“ protokolliert.")
