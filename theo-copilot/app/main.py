"""Streamlit entry point — Theo Copilot operations inbox.

Layout per PRODUCT_SPEC §8 View 2 + Fletcher design system inbox pattern:
- Left:   ticket list (.inbox-list)
- Middle: detail header + conversation + suggested actions (.inbox-detail)
- Right:  enrichment context cards (.inbox-context)

Run:
    cd theo-copilot && streamlit run app/main.py \\
        --server.port 8501 --server.address 127.0.0.1
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

from app import action_panel, enrichment_cards, inbox, ticket_detail
from app.db_sync import fetch_ticket, fetch_ticket_list


st.set_page_config(
    page_title="Fletcher — Operations Inbox",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# Tokens lifted from docs/fletcher-design-system.html.
# CSS variables let every component reference them consistently.
CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
  :root {
    /* paper neutrals (warm, not gray) */
    --paper-50:#FBFAF7; --paper-100:#F5F3EE; --paper-200:#ECE9E2;
    --paper-300:#D9D5CB; --paper-400:#B5AFA1; --paper-500:#8A8475;
    --paper-600:#5F5A4E; --paper-700:#3F3B33; --paper-800:#26241F;
    --paper-900:#161513;
    /* teal (primary) */
    --teal-50:#ECFDF8; --teal-100:#D1FAEE; --teal-200:#A7F0DD;
    --teal-300:#6FE0C5; --teal-400:#36C9AA; --teal-500:#14B295;
    --teal-600:#0F8E78; --teal-700:#0E7060; --teal-800:#0D584E;
    --teal-900:#0A3F39;
    /* status */
    --red-50:#FEF2F2; --red-100:#FEE2E2; --red-200:#FECACA;
    --red-500:#DC2626; --red-600:#B91C1C; --red-700:#991B1B;
    --amber-50:#FFFBEB; --amber-100:#FEF3C7; --amber-200:#FDE68A;
    --amber-500:#D97706; --amber-600:#B45309; --amber-700:#92400E;
    --green-50:#F0FDF4; --green-100:#DCFCE7; --green-500:#16A34A;
    --green-600:#15803D; --green-700:#166534;
    --blue-50:#EFF6FF; --blue-100:#DBEAFE; --blue-500:#2563EB;
    --blue-600:#1D4ED8;
    /* semantic */
    --surface-canvas:var(--paper-50); --surface-raised:#FFFFFF;
    --surface-sunken:var(--paper-100);
    --text-primary:var(--paper-900); --text-secondary:var(--paper-700);
    --text-tertiary:var(--paper-500); --text-disabled:var(--paper-400);
    --border-subtle:var(--paper-200); --border-default:var(--paper-300);
    --border-strong:var(--paper-400); --border-focus:var(--teal-500);
    /* spacing (4px base) */
    --space-1:4px; --space-2:8px; --space-3:12px; --space-4:16px;
    --space-5:20px; --space-6:24px; --space-8:32px; --space-10:40px;
    --space-12:48px; --space-16:64px;
    /* radius */
    --radius-sm:6px; --radius-md:10px; --radius-lg:14px;
    --radius-xl:20px; --radius-full:9999px;
    /* shadow */
    --shadow-xs:0 1px 2px 0 rgba(22,21,19,.04);
    --shadow-sm:0 1px 3px 0 rgba(22,21,19,.06),0 1px 2px 0 rgba(22,21,19,.04);
    --shadow-md:0 4px 8px -2px rgba(22,21,19,.08),0 2px 4px -2px rgba(22,21,19,.04);
    /* fonts */
    --font-sans:'Geist',-apple-system,BlinkMacSystemFont,system-ui,sans-serif;
    --font-serif:'Fraunces',Georgia,serif;
    --font-mono:'JetBrains Mono','SF Mono',Menlo,monospace;
    /* type scale — 17px body floor */
    --text-xs:13px; --text-sm:15px; --text-base:17px; --text-md:19px;
    --text-lg:22px; --text-xl:28px; --text-2xl:36px;
    --leading-tight:1.2; --leading-snug:1.35; --leading-normal:1.55;
    --leading-relaxed:1.7;
  }

  /* App chrome — get rid of Streamlit's default padding + header */
  html, body, [data-testid="stAppViewContainer"] {
    background: var(--surface-canvas) !important;
    font-family: var(--font-sans) !important;
    font-size: var(--text-base);
    color: var(--text-primary);
    -webkit-font-smoothing: antialiased;
    font-feature-settings: 'ss01','cv11';
  }
  [data-testid="stHeader"] { display: none; }
  .block-container {
    padding-top: var(--space-5) !important;
    padding-bottom: var(--space-4) !important;
    max-width: 100% !important;
  }
  /* Streamlit native column gaps — tighten */
  [data-testid="stHorizontalBlock"] { gap: var(--space-4) !important; }

  /* Brand row */
  .brand {
    font-family: var(--font-serif);
    font-size: var(--text-xl);
    font-weight: 500;
    font-style: italic;
    color: var(--teal-700);
    letter-spacing: -0.01em;
    margin: 0;
  }
  .brand-sub {
    font-family: var(--font-sans);
    font-size: var(--text-sm);
    font-weight: 500;
    color: var(--text-tertiary);
    letter-spacing: 0.02em;
    margin-left: var(--space-3);
  }

  /* TICKET ROW (left column) — from design system pattern */
  .ticket {
    display: grid;
    grid-template-columns: 4px 1fr auto;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4) var(--space-3) 0;
    border-bottom: 1px solid var(--border-subtle);
    cursor: pointer;
    transition: background 120ms ease;
    align-items: start;
    text-decoration: none;
    color: inherit;
  }
  .ticket:hover { background: var(--paper-50); }
  .ticket.selected { background: var(--teal-50); }
  .ticket-bar {
    align-self: stretch;
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  }
  .ticket-bar-critical { background: var(--red-500); }
  .ticket-bar-warning  { background: var(--amber-500); }
  .ticket-bar-neutral  { background: transparent; }
  .ticket-name {
    font-size: var(--text-base); font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    margin: 0 0 2px;
  }
  .ticket-property {
    font-size: var(--text-sm); color: var(--text-secondary);
    margin: 0 0 var(--space-2);
  }
  .ticket-meta {
    display: flex; align-items: center; gap: var(--space-2);
    font-size: var(--text-xs); color: var(--text-tertiary);
  }
  .ticket-meta-sep {
    width: 3px; height: 3px; background: var(--paper-400); border-radius: 50%;
  }
  .ticket-vuln {
    color: var(--red-600); font-weight: 600;
  }
  .ticket-time {
    font-size: var(--text-xs); color: var(--text-tertiary);
    white-space: nowrap; padding-top: 2px;
  }

  /* Section labels (e.g. "INBOX", "CONVERSATION", "SUGGESTED ACTIONS") */
  .section-label {
    font-size: var(--text-xs); font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase; letter-spacing: 0.06em;
    margin: var(--space-6) 0 var(--space-3);
  }
  .section-label:first-child { margin-top: 0; }

  /* DETAIL HEADER (middle column) */
  .detail-title {
    font-family: var(--font-serif);
    font-size: var(--text-2xl); font-weight: 500;
    letter-spacing: -0.015em;
    margin: 0 0 var(--space-2);
    color: var(--text-primary);
  }
  .detail-subtitle {
    font-size: var(--text-sm); color: var(--text-tertiary);
    display: flex; gap: var(--space-2); flex-wrap: wrap;
    align-items: center;
  }
  .detail-subtitle-sep { color: var(--paper-400); }

  /* CONVERSATION BUBBLE — paper-100 for ALL bubbles per spec */
  .msg-bubble {
    background: var(--paper-100);
    border-radius: var(--radius-lg);
    padding: var(--space-4) var(--space-5);
    margin: var(--space-3) 0;
  }
  .msg-bubble.outbound {
    background: var(--teal-50);
    border-left: 3px solid var(--teal-600);
  }
  .msg-meta {
    font-size: var(--text-xs); color: var(--text-tertiary);
    display: flex; gap: var(--space-2); margin-bottom: var(--space-2);
  }
  .msg-meta strong { color: var(--text-primary); font-weight: 600; }
  .msg-body {
    font-size: var(--text-base); color: var(--text-primary);
    line-height: var(--leading-relaxed);
    margin: 0; white-space: pre-wrap;
  }

  /* CHIP */
  .chip {
    display: inline-flex; align-items: center; gap: var(--space-1);
    padding: 2px var(--space-2);
    font-size: var(--text-xs); font-weight: 600;
    letter-spacing: 0.04em; text-transform: uppercase;
    border-radius: var(--radius-full);
    border: 1px solid transparent;
  }
  .chip-critical { background: var(--red-50); color: var(--red-700); border-color: var(--red-200); }
  .chip-warning  { background: var(--amber-50); color: var(--amber-700); border-color: var(--amber-200); }
  .chip-success  { background: var(--green-50); color: var(--green-700); border-color: var(--green-100); }
  .chip-info     { background: var(--blue-50); color: var(--blue-600); border-color: var(--blue-100); }
  .chip-neutral  { background: var(--paper-100); color: var(--paper-700); border-color: var(--paper-200); }
  .chip-teal     { background: var(--teal-50); color: var(--teal-800); border-color: var(--teal-200); }

  /* CONTEXT CARD (right column) */
  .ctx-card {
    background: var(--surface-raised);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: var(--space-4) var(--space-5);
    margin-bottom: var(--space-4);
  }
  .ctx-card-elevated { box-shadow: var(--shadow-sm); }
  .ctx-card-header {
    font-size: var(--text-xs); font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase; letter-spacing: 0.06em;
    margin-bottom: var(--space-3);
    display: flex; align-items: center; gap: var(--space-2);
  }
  .ctx-name {
    font-size: var(--text-md); font-weight: 600;
    color: var(--text-primary); margin: 0 0 var(--space-1);
  }
  .ctx-detail {
    font-size: var(--text-sm); color: var(--text-secondary); margin: 0 0 var(--space-3);
  }
  .ctx-attrs { list-style: none; padding: 0; margin: 0;
               display: flex; flex-direction: column; gap: var(--space-2); }
  .ctx-attrs li {
    font-size: var(--text-sm); color: var(--text-secondary);
    line-height: var(--leading-snug);
    padding-left: var(--space-5); position: relative;
  }
  .ctx-attrs li::before {
    content: ''; position: absolute; left: 0; top: 8px;
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--paper-400);
  }
  .ctx-attrs li.alert::before { background: var(--red-500); }
  .ctx-attrs li.alert { color: var(--text-primary); font-weight: 500; }

  /* Pattern card timeline */
  .timeline-row {
    display: flex; gap: var(--space-3); margin-bottom: var(--space-3);
    align-items: flex-start;
  }
  .timeline-dot {
    flex-shrink: 0; width: 10px; height: 10px;
    border-radius: 50%; margin-top: 6px;
  }
  .timeline-date {
    flex-shrink: 0; min-width: 5.2rem;
    font-size: var(--text-xs); color: var(--text-tertiary);
    font-variant-numeric: tabular-nums; padding-top: 2px;
  }
  .timeline-fact {
    flex: 1; font-size: var(--text-sm); color: var(--text-primary);
    line-height: var(--leading-snug);
  }
  .timeline-source {
    color: var(--text-tertiary); font-size: var(--text-xs);
    font-family: var(--font-mono);
  }

  /* ACTION CARD (suggested actions) */
  .action-card {
    background: var(--surface-raised);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: var(--space-5);
    margin-bottom: var(--space-3);
    transition: border-color 120ms ease, box-shadow 120ms ease;
  }
  .action-card:hover {
    border-color: var(--border-default);
    box-shadow: var(--shadow-sm);
  }
  .action-card.high      { border-left: 3px solid var(--amber-500); }
  .action-card.critical  { border-left: 3px solid var(--red-500); }
  .action-card.irreversible { border-left: 3px solid var(--paper-700); }
  .action-title {
    font-size: var(--text-md); font-weight: 600;
    margin: 0 0 var(--space-2); color: var(--text-primary);
  }
  .action-rationale {
    font-size: var(--text-sm); color: var(--text-secondary);
    line-height: var(--leading-snug); margin: 0 0 var(--space-3);
  }

  /* Source pill on pattern card */
  .source-pill {
    display: inline-block; font-size: var(--text-xs); font-weight: 600;
    padding: 2px var(--space-2); border-radius: var(--radius-full);
    letter-spacing: 0.04em; text-transform: uppercase;
    margin-left: var(--space-2);
  }
  .source-pill.graphiti          { background: var(--teal-50); color: var(--teal-800); border:1px solid var(--teal-200); }
  .source-pill.postgres-fallback { background: var(--blue-50); color: var(--blue-600); border:1px solid var(--blue-100); }
  .source-pill.stub              { background: var(--amber-50); color: var(--amber-700); border:1px solid var(--amber-200); }
  .source-pill.cache             { background: var(--paper-100); color: var(--paper-700); border:1px solid var(--paper-200); }

  /* Streamlit overrides */
  /* Buttons */
  .stButton > button {
    min-height: 44px !important;
    font-family: var(--font-sans) !important;
    font-size: var(--text-base) !important;
    font-weight: 500 !important;
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--border-default) !important;
    background: var(--surface-raised) !important;
    color: var(--text-primary) !important;
    transition: background 120ms ease, box-shadow 120ms ease !important;
    padding: 0 var(--space-5) !important;
    text-align: left !important;
  }
  .stButton > button:hover {
    background: var(--paper-50) !important;
    border-color: var(--border-default) !important;
  }
  .stButton > button[kind="primary"] {
    background: var(--teal-600) !important;
    color: #fff !important;
    border-color: var(--teal-600) !important;
  }
  .stButton > button[kind="primary"]:hover {
    background: var(--teal-700) !important;
    border-color: var(--teal-700) !important;
  }
  /* Inbox rows: visual card + invisible button overlay (whole row clickable). */
  [class*="st-key-ticket-row-"] {
    position: relative;
  }
  [class*="st-key-ticket-row-"] [data-testid="stMarkdownContainer"] {
    pointer-events: none;
  }
  [class*="st-key-ticket-row-"] .ticket {
    pointer-events: none;
  }
  [class*="st-key-ticket-row-"] [data-testid="stVerticalBlock"] {
    gap: 0 !important;
  }
  [class*="st-key-ticket-row-"] .stButton {
    position: absolute;
    inset: 0;
    margin: 0 !important;
    z-index: 2;
  }
  [class*="st-key-ticket-row-"] .stButton > button {
    width: 100%;
    height: 100%;
    min-height: 0 !important;
    padding: 0 !important;
    border: none !important;
    background: transparent !important;
    color: transparent !important;
    box-shadow: none !important;
    cursor: pointer;
  }
  [class*="st-key-ticket-row-"] .stButton > button:hover {
    background: transparent !important;
  }
  [class*="st-key-ticket-row-"] .stButton > button:focus-visible {
    outline: 2px solid var(--border-focus);
    outline-offset: -2px;
  }
  /* Drive the card hover from the container, since the overlay button absorbs the pointer. */
  [class*="st-key-ticket-row-"]:hover .ticket:not(.selected) {
    background: var(--paper-50);
  }

  /* Text inputs */
  .stTextArea textarea, .stTextInput input {
    font-family: var(--font-sans) !important;
    font-size: var(--text-base) !important;
    color: var(--text-primary) !important;
    background: var(--surface-raised) !important;
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-md) !important;
    line-height: var(--leading-snug) !important;
    padding: var(--space-3) var(--space-4) !important;
  }
  .stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--teal-500) !important;
    box-shadow: 0 0 0 3px var(--teal-100) !important;
  }

  /* Captions */
  small, .stCaption { color: var(--text-tertiary); font-size: var(--text-sm); }

  /* Empty-state placeholder */
  .empty-state {
    color: var(--text-tertiary);
    font-family: var(--font-serif);
    font-style: italic;
    font-size: var(--text-md);
    text-align: center;
    padding: var(--space-16) var(--space-4);
  }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "selected_ticket_id" not in st.session_state:
    st.session_state.selected_ticket_id = None
if "show_trace" not in st.session_state:
    st.session_state.show_trace = False


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

header_l, header_r = st.columns([4, 1])
with header_l:
    st.markdown(
        "<p class='brand'>Fletcher<span class='brand-sub'>· Sarah Weber</span></p>",
        unsafe_allow_html=True,
    )
with header_r:
    if st.button("⟳ Aktualisieren", use_container_width=True):
        st.rerun()


# ---------------------------------------------------------------------------
# Layout — 3 columns
# ---------------------------------------------------------------------------

col_list, col_detail, col_enrich = st.columns([1, 1.5, 1.3], gap="medium")


# Left — ticket list
with col_list:
    st.markdown("<p class='section-label'>Inbox</p>", unsafe_allow_html=True)
    tickets = fetch_ticket_list()
    selected_id = inbox.render(tickets, st.session_state.selected_ticket_id)
    if selected_id and selected_id != st.session_state.selected_ticket_id:
        st.session_state.selected_ticket_id = selected_id
        st.rerun()


# Middle + right — detail + enrichment
if st.session_state.selected_ticket_id:
    ticket = fetch_ticket(st.session_state.selected_ticket_id)
    if ticket is None:
        with col_detail:
            st.warning("Ticket nicht gefunden.")
    else:
        with col_detail:
            ticket_detail.render(ticket)
            action_panel.render(ticket)
        with col_enrich:
            enrichment_cards.render(ticket)
else:
    with col_detail:
        st.markdown(
            "<div class='empty-state'>Wählen Sie ein Ticket aus der Liste.</div>",
            unsafe_allow_html=True,
        )
