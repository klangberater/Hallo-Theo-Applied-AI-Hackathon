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

from app import action_panel, demo_controls, enrichment_cards, inbox, ticket_detail
from app.db_sync import fetch_ticket, fetch_ticket_list


st.set_page_config(
    page_title="Fletcher — Operations Inbox",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
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
  /* …but keep the sidebar collapse/expand chevron visible.
     Streamlit lives the toggle under a few different test-ids depending on
     version + collapsed state — re-show all of them. */
  [data-testid="stSidebarCollapsedControl"],
  [data-testid="stSidebarCollapseButton"],
  [data-testid="collapsedControl"],
  button[kind="header"],
  button[kind="headerNoPadding"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 999 !important;
    position: fixed !important;
    top: 8px !important; left: 8px !important;
    background: var(--surface-raised) !important;
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    width: 36px !important; height: 36px !important;
    align-items: center !important; justify-content: center !important;
    cursor: pointer !important;
  }
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

  /* INBOX ROW (left column) — dense email-client pattern */
  .inbox-row {
    display: grid;
    grid-template-columns: 14px 1fr;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--border-subtle);
    transition: background 120ms ease;
    align-items: start;
  }
  .inbox-row.selected { background: var(--teal-50); }
  .inbox-row-dot {
    width: 8px; height: 8px; border-radius: 50%;
    margin-top: 8px;
    background: transparent;
    transition: background 120ms ease;
  }
  .inbox-row.unread .inbox-row-dot { background: var(--teal-500); }
  .inbox-row-body {
    min-width: 0;  /* enables text-overflow on children */
  }
  .inbox-row-top {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: var(--space-2);
    margin-bottom: 2px;
  }
  .inbox-row-sender {
    font-size: var(--text-base);
    font-weight: 500;
    color: var(--text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .inbox-row.unread .inbox-row-sender {
    font-weight: 600;
    color: var(--text-primary);
  }
  .inbox-row-meta {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex-shrink: 0;
  }
  .inbox-row-channel {
    font-size: var(--text-xs);
    color: var(--text-tertiary);
  }
  .inbox-row-time {
    font-size: var(--text-xs);
    color: var(--text-tertiary);
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }
  .inbox-row-subject {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin-bottom: 3px;
    white-space: nowrap;
    overflow: hidden;
  }
  .inbox-row-category {
    font-weight: 600;
    color: var(--text-primary);
  }
  .inbox-row.unread .inbox-row-category {
    color: var(--text-primary);
  }
  .inbox-row-sep { color: var(--paper-400); }
  .inbox-row-address {
    color: var(--text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .inbox-row-preview {
    font-size: var(--text-sm);
    color: var(--text-tertiary);
    line-height: var(--leading-snug);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .inbox-pill-incidents {
    display: inline-flex;
    align-items: center;
    font-size: 11px;
    font-weight: 600;
    padding: 1px 7px;
    background: var(--red-50);
    color: var(--red-700);
    border: 1px solid var(--red-100);
    border-radius: var(--radius-full);
    white-space: nowrap;
  }
  .inbox-chip {
    font-size: 10px !important;
    padding: 1px 6px !important;
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

  /* CONTEXT CARD (right column) — borderless sections separated by a
     hairline divider; larger uppercase header so categories pop. */
  .ctx-card {
    background: transparent;
    border: none;
    border-radius: 0;
    padding: 0 0 var(--space-5);
    margin-bottom: var(--space-5);
    border-bottom: 1px solid var(--border-subtle);
  }
  .ctx-card:last-child {
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
  }
  .ctx-card-elevated { box-shadow: none; }
  .ctx-card-header {
    font-size: var(--text-sm); font-weight: 700;
    color: var(--teal-700);
    text-transform: uppercase; letter-spacing: 0.08em;
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

  /* Autonomy mode chip — on ticket rows and detail header */
  .mode-chip {
    display: inline-flex; align-items: center; gap: var(--space-1);
    font-size: var(--text-xs); font-weight: 600;
    padding: 2px var(--space-2); border-radius: var(--radius-full);
    letter-spacing: 0.04em;
    border: 1px solid transparent;
    white-space: nowrap;
  }
  .mode-chip-autonomous { background: var(--teal-50); color: var(--teal-800);
                          border-color: var(--teal-200); }
  .mode-chip-bundle     { background: var(--amber-50); color: var(--amber-700);
                          border-color: var(--amber-200); }
  .mode-chip-propose    { background: var(--paper-100); color: var(--paper-700);
                          border-color: var(--paper-200); }

  /* Autonomy banner — sits above suggested_actions */
  .autonomy-banner {
    border-radius: var(--radius-md);
    padding: var(--space-4) var(--space-5);
    margin: var(--space-3) 0 var(--space-4);
    border-left: 3px solid;
    font-size: var(--text-sm);
    line-height: var(--leading-snug);
  }
  .autonomy-banner-title {
    font-weight: 600; font-size: var(--text-sm);
    margin: 0 0 var(--space-2); display: flex; align-items: center; gap: var(--space-2);
  }
  .autonomy-banner-body { margin: 0; color: var(--text-secondary); }
  .autonomy-banner.autonomous { background: var(--teal-50); border-color: var(--teal-600); }
  .autonomy-banner.autonomous .autonomy-banner-title { color: var(--teal-800); }
  .autonomy-banner.bundle     { background: var(--amber-50); border-color: var(--amber-500); }
  .autonomy-banner.bundle .autonomy-banner-title { color: var(--amber-700); }

  /* Done badge for executed actions in autonomous_done */
  .action-done {
    display: inline-flex; align-items: center; gap: var(--space-1);
    font-size: var(--text-xs); font-weight: 600;
    color: var(--green-700); background: #F0FDF4;
    padding: 2px var(--space-2); border-radius: var(--radius-full);
    border: 1px solid var(--green-100);
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
  /* Inbox rows: each row is an <a> link to ?t=<id>. Whole row is the
     browser-native click target — but the text inside must NOT look like
     a link. Reset color/decoration aggressively so Streamlit's default
     <a> styling doesn't bleed through. */
  .inbox-row-link,
  .inbox-row-link:link,
  .inbox-row-link:visited,
  .inbox-row-link:hover,
  .inbox-row-link:active,
  .inbox-row-link *,
  .inbox-row-link *:hover {
    text-decoration: none !important;
    color: inherit !important;
  }
  .inbox-row-link {
    display: block;
    cursor: pointer;
  }
  /* Keep the colored chips/pills the way the row defines them. */
  .inbox-row-link .chip-critical,
  .inbox-row-link .chip-critical * { color: var(--red-700) !important; }
  .inbox-row-link .chip-warning,
  .inbox-row-link .chip-warning *  { color: var(--amber-700) !important; }
  .inbox-row-link .inbox-pill-incidents,
  .inbox-row-link .inbox-pill-incidents * { color: var(--red-700) !important; }
  .inbox-row-link .mode-chip-autonomous,
  .inbox-row-link .mode-chip-autonomous * { color: var(--teal-800) !important; }
  .inbox-row-link .mode-chip-bundle,
  .inbox-row-link .mode-chip-bundle *     { color: var(--amber-700) !important; }
  .inbox-row-link:focus-visible {
    outline: 2px solid var(--border-focus);
    outline-offset: -2px;
    border-radius: var(--radius-sm);
  }
  .inbox-row-link:hover .inbox-row:not(.selected) {
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
  .empty-state-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--space-4);
    padding: var(--space-16) var(--space-4);
    color: var(--text-tertiary);
    text-align: center;
  }
  .empty-state-icon {
    font-size: 64px;
    line-height: 1;
    opacity: 0.4;
    color: var(--paper-400);
  }
  .empty-state-text {
    font-family: var(--font-serif);
    font-style: italic;
    font-size: var(--text-md);
    color: var(--text-tertiary);
  }

  /* INDEPENDENT PANE SCROLLING ----------------------------------------
     Lock the whole app to viewport height so the page itself can't
     scroll; the inbox list, ticket detail, and context panes each
     handle their own scroll. */
  html, body {
    height: 100vh !important;
    max-height: 100vh !important;
    overflow: hidden !important;
  }
  [data-testid="stAppViewContainer"] {
    height: 100vh !important;
    max-height: 100vh !important;
    overflow: hidden !important;
  }
  [data-testid="stMain"] {
    height: 100vh !important;
    max-height: 100vh !important;
    overflow: hidden !important;
  }
  /* The block-container becomes a flex column: header on top,
     main-layout fills the rest. */
  .block-container,
  [data-testid="stMainBlockContainer"] {
    height: 100vh !important;
    max-height: 100vh !important;
    overflow: hidden !important;
    display: flex !important;
    flex-direction: column !important;
    padding-bottom: var(--space-3) !important;
  }
  /* main-layout takes remaining space below the header. */
  .st-key-main-layout {
    flex: 1 1 0% !important;
    min-height: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    overflow: hidden !important;
  }
  /* Outer horizontal block (col_list + col_detail) — explicit path so
     we don't accidentally match action_panel's button columns deeper. */
  .st-key-main-layout > [data-testid="stHorizontalBlock"] {
    flex: 1 1 0% !important;
    min-height: 0 !important;
    align-items: stretch !important;
    height: 100% !important;
  }
  /* Outer columns: col_list (scrolls) and col_detail (hidden — its
     subpanes scroll instead). */
  .st-key-main-layout
      > [data-testid="stHorizontalBlock"]
      > [data-testid="stColumn"] {
    height: 100% !important;
    max-height: 100% !important;
    min-height: 0 !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
  }
  /* col_detail wraps a nested horizontal block — hide its own overflow
     so the inner sub_detail / sub_context handle scroll, not col_detail. */
  .st-key-main-layout
      > [data-testid="stHorizontalBlock"]
      > [data-testid="stColumn"]:has(
        > [data-testid="stVerticalBlock"]
        > [data-testid="stHorizontalBlock"]
      ) {
    overflow: hidden !important;
  }
  /* col_detail's vertical-block wrapper: stretch so the inner
     horizontal block can take 100% height. */
  .st-key-main-layout
      > [data-testid="stHorizontalBlock"]
      > [data-testid="stColumn"]
      > [data-testid="stVerticalBlock"] {
    height: 100% !important;
    min-height: 0 !important;
    display: flex !important;
    flex-direction: column !important;
  }
  /* Nested horizontal block: sub_detail + sub_context. */
  .st-key-main-layout
      > [data-testid="stHorizontalBlock"]
      > [data-testid="stColumn"]
      > [data-testid="stVerticalBlock"]
      > [data-testid="stHorizontalBlock"] {
    flex: 1 1 0% !important;
    min-height: 0 !important;
    align-items: stretch !important;
    height: 100% !important;
  }
  /* Subpane columns: sub_detail (conversation + actions) and
     sub_context (enrichment cards) each scroll on their own. */
  .st-key-main-layout
      > [data-testid="stHorizontalBlock"]
      > [data-testid="stColumn"]
      > [data-testid="stVerticalBlock"]
      > [data-testid="stHorizontalBlock"]
      > [data-testid="stColumn"] {
    height: 100% !important;
    max-height: 100% !important;
    min-height: 0 !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
  }
  /* Thin paper-toned scrollbars. */
  .st-key-main-layout [data-testid="stColumn"] {
    scrollbar-width: thin;
    scrollbar-color: var(--paper-300) transparent;
  }
  .st-key-main-layout [data-testid="stColumn"]::-webkit-scrollbar {
    width: 6px;
  }
  .st-key-main-layout [data-testid="stColumn"]::-webkit-scrollbar-thumb {
    background: var(--paper-300);
    border-radius: 3px;
  }
  .st-key-main-layout [data-testid="stColumn"]::-webkit-scrollbar-track {
    background: transparent;
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
if "opened_ticket_ids" not in st.session_state:
    st.session_state.opened_ticket_ids = set()

# Click target for inbox rows is an <a href="?t=<id>"> link.
# Pick up the new selection from the URL before rendering anything.
_qp_ticket = st.query_params.get("t")
if _qp_ticket and _qp_ticket != st.session_state.selected_ticket_id:
    st.session_state.selected_ticket_id = _qp_ticket
    st.session_state.opened_ticket_ids.add(_qp_ticket)


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

# Demo-Steuerung — sidebar with one-click scenario triggers (Köhler, Demir, reset).
demo_controls.render()


# ---------------------------------------------------------------------------
# Layout — 2 columns (list + detail, with context as nested subpane).
# Wrapped in st.container(key="main-layout") so CSS can give each pane
# its own scroll without affecting the header row above.
# ---------------------------------------------------------------------------

with st.container(key="main-layout"):
    col_list, col_detail = st.columns([1, 3], gap="medium")

    with col_list:
        st.markdown(
            "<p class='section-label'>Inbox</p>", unsafe_allow_html=True
        )
        tickets = fetch_ticket_list()
        inbox.render(
            tickets,
            st.session_state.selected_ticket_id,
            st.session_state.opened_ticket_ids,
        )

    if st.session_state.selected_ticket_id:
        ticket = fetch_ticket(st.session_state.selected_ticket_id)
        if ticket is None:
            with col_detail:
                st.warning("Ticket nicht gefunden.")
        else:
            with col_detail:
                sub_detail, sub_context = st.columns([1.8, 1], gap="medium")
                with sub_detail:
                    ticket_detail.render(ticket)
                    action_panel.render(ticket)
                with sub_context:
                    st.markdown(
                        "<p class='section-label'>Kontext</p>",
                        unsafe_allow_html=True,
                    )
                    enrichment_cards.render(ticket)
    else:
        with col_detail:
            st.markdown(
                """
                <div class='empty-state-wrap'>
                  <div class='empty-state-icon'>✉</div>
                  <div class='empty-state-text'>Wählen Sie eine Nachricht aus der Liste.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
