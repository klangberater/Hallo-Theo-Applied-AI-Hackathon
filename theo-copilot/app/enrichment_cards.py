"""Typed renderer for the EnrichmentPayload — right column of the inbox."""
from __future__ import annotations

import streamlit as st

from app import timeline_viz


def _card_open(title: str, source: str | None = None) -> None:
    pill = ""
    if source:
        pill = f"<span class='source-pill {source}'>{source}</span>"
    st.markdown(
        f"<div class='card'><h4>{title} {pill}</h4>",
        unsafe_allow_html=True,
    )


def _card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def _cite(sources: list[dict]) -> str:
    if not sources:
        return ""
    parts = []
    for s in sources:
        label = s.get("id") or s.get("kind") or "source"
        parts.append(label)
    return "<div class='source-cite'>📎 " + " · ".join(parts) + "</div>"


def render(ticket: dict) -> None:
    enrichment = ticket.get("enrichment")
    if not enrichment:
        if ticket.get("status") == "enriching":
            st.info("⏳ Theo Copilot ist gerade dabei, das Ticket anzureichern…")
        else:
            st.info("Keine Enrichment-Daten verfügbar.")
        return

    # Tenant card
    tc = enrichment.get("tenant_card", {})
    if tc:
        _card_open("📍 Mieter:in")
        st.markdown(f"**{tc.get('name', '')}**")
        if tc.get("since"):
            st.caption(f"Mietverhältnis seit {tc['since']}")
        for w in tc.get("warnings", []):
            st.markdown(f"<div class='warn'>⚠ {w}</div>", unsafe_allow_html=True)
        st.markdown(_cite(tc.get("sources", [])), unsafe_allow_html=True)
        _card_close()

    # Unit card
    uc = enrichment.get("unit_card", {})
    if uc:
        _card_open("🏠 Wohneinheit")
        st.markdown(f"**{uc.get('label', '')}**")
        details = []
        if uc.get("qm"):
            details.append(f"{uc['qm']} qm")
        if uc.get("rent_cold"):
            details.append(f"{uc['rent_cold']:.2f} € kalt")
        if uc.get("lease_status"):
            details.append(uc["lease_status"])
        if details:
            st.caption(" · ".join(details))
        st.markdown(_cite(uc.get("sources", [])), unsafe_allow_html=True)
        _card_close()

    # Lease facts
    lease_facts = enrichment.get("lease_facts", [])
    if lease_facts:
        _card_open("📜 Mietvertrag-Auszüge")
        for f in lease_facts:
            st.markdown(f"- {f}")
        _card_close()

    # Prior incidents — THE Pattern card
    pi = enrichment.get("prior_incidents", {})
    if pi:
        source = pi.get("source", "")
        _card_open(
            f"🔁 Pattern — {pi.get('count', 0)} Vorfälle in {pi.get('timespan_months', '?')} Monaten",
            source=source,
        )
        if pi.get("pattern_summary"):
            st.markdown(f"_{pi['pattern_summary']}_")
        timeline_viz.render(pi.get("timeline", []))
        _card_close()

    # Open vendor offers
    offers = enrichment.get("open_vendor_offers", [])
    if offers:
        _card_open("💰 Offene Angebote")
        for o in offers:
            st.markdown(
                f"**{o.get('vendor_name', o.get('vendor_id', '?'))}** — "
                f"{o.get('amount', 0):.2f} €"
            )
            st.caption(o.get("scope", ""))
            if o.get("age_days"):
                st.markdown(
                    f"<span class='warn'>⚠ Seit {o['age_days']} Tagen unbearbeitet</span>",
                    unsafe_allow_html=True,
                )
        _card_close()

    # Internal pre-approvals — THE Jonas card
    preapprovals = enrichment.get("internal_pre_approvals", [])
    if preapprovals:
        _card_open("💬 Interne Vorab-Genehmigung")
        for p in preapprovals:
            sent_at = p.get("sent_at", "")
            st.markdown(f"**{p.get('sender', '?')}** _· {sent_at}_")
            st.markdown(
                f"<div style='font-style:italic;color:#a1a1aa;border-left:2px solid "
                f"#fbbf24;padding-left:0.6rem;margin:0.4rem 0'>{p.get('body', '')}</div>",
                unsafe_allow_html=True,
            )
            if p.get("interpretation"):
                st.markdown(f"→ {p['interpretation']}")
        _card_close()

    # Weather
    w = enrichment.get("weather")
    if w:
        _card_open("🌡 Wetter", source="stub" if "_stubbed" in str(w) else None)
        st.markdown(f"**{w.get('location', '')}**")
        st.markdown(w.get("forecast", ""))
        if w.get("relevant_because"):
            st.caption(w["relevant_because"])
        _card_close()

    # Legal context
    legal = enrichment.get("legal_context", [])
    if legal:
        _card_open("⚖ Rechtskontext")
        for ref in legal:
            st.markdown(f"**{ref.get('citation', '')}**")
            st.markdown(ref.get("short_text", ""))
            if ref.get("relevance"):
                st.caption(ref["relevance"])
            st.markdown("---")
        _card_close()
