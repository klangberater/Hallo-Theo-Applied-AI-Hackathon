"""Enrichment cards — right column. Fletcher context-card pattern."""
from __future__ import annotations

import streamlit as st

from app import timeline_viz


def _open(title: str, source: str | None = None) -> None:
    pill = ""
    if source:
        pill = f"<span class='source-pill {source}'>{source.replace('-', ' ')}</span>"
    st.markdown(
        f"<div class='ctx-card'><div class='ctx-card-header'>{title}{pill}</div>",
        unsafe_allow_html=True,
    )


def _close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def _cite(sources: list[dict]) -> str:
    if not sources:
        return ""
    parts = [s.get("id") or s.get("kind") or "src" for s in sources]
    return (
        "<div style='color:var(--text-tertiary);font-size:var(--text-xs);"
        "font-family:var(--font-mono);margin-top:var(--space-3)'>📎 "
        + " · ".join(parts)
        + "</div>"
    )


def render(ticket: dict) -> None:
    enrichment = ticket.get("enrichment")
    if not enrichment:
        if ticket.get("status") == "enriching":
            st.markdown(
                "<div class='ctx-card'>"
                "<p style='margin:0;color:var(--text-secondary)'>"
                "⏳ Theo Copilot reichert das Ticket gerade an…</p>"
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='ctx-card'><p style='margin:0;color:var(--text-tertiary)'>"
                "Keine Anreicherungsdaten verfügbar.</p></div>",
                unsafe_allow_html=True,
            )
        return

    # ---- Mieterin ----------------------------------------------------------
    tc = enrichment.get("tenant_card", {})
    if tc:
        _open("Mieter:in")
        attrs = [f"<p class='ctx-name'>{tc.get('name','')}</p>"]
        if tc.get("since"):
            attrs.append(
                f"<p class='ctx-detail'>Mietverhältnis seit {tc['since']}</p>"
            )
        if tc.get("warnings"):
            items = "".join(f"<li class='alert'>{w}</li>" for w in tc["warnings"])
            attrs.append(f"<ul class='ctx-attrs'>{items}</ul>")
        st.markdown("".join(attrs), unsafe_allow_html=True)
        st.markdown(_cite(tc.get("sources", [])), unsafe_allow_html=True)
        _close()

    # ---- Wohneinheit ------------------------------------------------------
    uc = enrichment.get("unit_card", {})
    if uc:
        _open("Wohneinheit")
        details = []
        if uc.get("qm"):
            details.append(f"{uc['qm']} qm")
        if uc.get("rent_cold"):
            details.append(f"{uc['rent_cold']:.2f} € kalt")
        if uc.get("lease_status"):
            details.append(uc["lease_status"])
        st.markdown(
            f"<p class='ctx-name'>{uc.get('label','')}</p>"
            + (f"<p class='ctx-detail'>{' · '.join(details)}</p>" if details else ""),
            unsafe_allow_html=True,
        )
        st.markdown(_cite(uc.get("sources", [])), unsafe_allow_html=True)
        _close()

    # ---- Mietvertrag-Auszüge ----------------------------------------------
    lease_facts = enrichment.get("lease_facts", [])
    if lease_facts:
        _open("Mietvertrag-Auszüge")
        items = "".join(f"<li>{f}</li>" for f in lease_facts)
        st.markdown(f"<ul class='ctx-attrs'>{items}</ul>", unsafe_allow_html=True)
        _close()

    # ---- Pattern (the Graphiti moment) ------------------------------------
    pi = enrichment.get("prior_incidents", {})
    if pi:
        source = pi.get("source", "")
        count = pi.get("count", 0)
        span = pi.get("timespan_months", "?")
        _open(f"Pattern — {count} Vorfälle in {span} Monaten", source=source)
        if pi.get("pattern_summary"):
            st.markdown(
                f"<p style='font-size:var(--text-sm);color:var(--text-secondary);"
                f"line-height:var(--leading-snug);margin:0 0 var(--space-4);"
                f"font-style:italic'>{pi['pattern_summary']}</p>",
                unsafe_allow_html=True,
            )
        timeline_viz.render(pi.get("timeline", []))
        _close()

    # ---- Offene Angebote --------------------------------------------------
    offers = enrichment.get("open_vendor_offers", [])
    if offers:
        _open("Offene Angebote")
        for o in offers:
            name = o.get("vendor_name", o.get("vendor_id", "?"))
            amount = o.get("amount", 0)
            scope = o.get("scope", "")
            age = o.get("age_days")
            extra = (
                f"<p class='ctx-detail' style='color:var(--red-600)'>"
                f"⚠ Seit {age} Tagen unbearbeitet</p>"
                if age else ""
            )
            st.markdown(
                f"<p class='ctx-name'>{name} — {amount:.2f} €</p>"
                f"<p class='ctx-detail'>{scope}</p>{extra}",
                unsafe_allow_html=True,
            )
        _close()

    # ---- Interne Vorab-Genehmigung (Jonas) --------------------------------
    preapprovals = enrichment.get("internal_pre_approvals", [])
    if preapprovals:
        _open("Interne Vorab-Genehmigung", source="teal")
        for p in preapprovals:
            sent_at = p.get("sent_at", "")
            st.markdown(
                f"<p class='ctx-name' style='font-size:var(--text-sm)'>"
                f"{p.get('sender','?')} <span style='color:var(--text-tertiary);"
                f"font-weight:400'>· {sent_at}</span></p>"
                f"<blockquote style='font-style:italic;color:var(--text-secondary);"
                f"border-left:2px solid var(--teal-500);padding-left:var(--space-3);"
                f"margin:var(--space-2) 0;font-size:var(--text-sm);"
                f"line-height:var(--leading-snug)'>{p.get('body','')}</blockquote>"
                + (
                    f"<p class='ctx-detail' style='color:var(--text-primary)'>→ "
                    f"{p['interpretation']}</p>"
                    if p.get("interpretation") else ""
                ),
                unsafe_allow_html=True,
            )
        _close()

    # ---- Wetter -----------------------------------------------------------
    w = enrichment.get("weather")
    if w:
        is_stub = "_stubbed" in str(w) or w.get("source", {}).get("kind") == "stubbed"
        _open("Wetter", source="stub" if is_stub else None)
        st.markdown(
            f"<p class='ctx-name'>{w.get('location','Berlin')}</p>"
            f"<p class='ctx-detail'>{w.get('forecast','')}</p>"
            + (
                f"<p style='font-size:var(--text-xs);color:var(--text-tertiary);"
                f"margin:0'>{w['relevant_because']}</p>"
                if w.get("relevant_because") else ""
            ),
            unsafe_allow_html=True,
        )
        _close()

    # ---- Rechtskontext ----------------------------------------------------
    legal = enrichment.get("legal_context", [])
    if legal:
        _open("Rechtskontext")
        for ref in legal:
            st.markdown(
                f"<p class='ctx-name' style='font-size:var(--text-sm)'>"
                f"{ref.get('citation','')}</p>"
                f"<p class='ctx-detail'>{ref.get('short_text','')}</p>"
                + (
                    f"<p style='font-size:var(--text-xs);color:var(--text-tertiary);"
                    f"margin:0 0 var(--space-3)'>{ref['relevance']}</p>"
                    if ref.get("relevance") else ""
                ),
                unsafe_allow_html=True,
            )
        _close()
