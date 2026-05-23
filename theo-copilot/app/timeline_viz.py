"""Pattern timeline — vertical dot+date+fact rows using Fletcher tokens."""
from __future__ import annotations

from datetime import date

import streamlit as st


def render(timeline: list[dict]) -> None:
    if not timeline:
        st.markdown(
            "<p style='color:var(--text-tertiary);font-size:var(--text-sm);margin:0'>"
            "Keine historischen Vorfälle.</p>",
            unsafe_allow_html=True,
        )
        return

    def _parse_date(x):
        d = x.get("date")
        if isinstance(d, date):
            return d
        if isinstance(d, str):
            try:
                return date.fromisoformat(d[:10])
            except Exception:
                return date.min
        return date.min

    entries = sorted(timeline, key=_parse_date)
    today = date.today()

    rows: list[str] = []
    for entry in entries:
        d = _parse_date(entry)
        when = d.strftime("%d.%m.%Y") if d != date.min else "?"
        days_ago = (today - d).days if d != date.min else 0
        # Red = recent (<90d), amber = within last year, paper = older
        if days_ago < 90:
            color = "var(--red-500)"
        elif days_ago < 365:
            color = "var(--amber-500)"
        else:
            color = "var(--paper-400)"

        fact = entry.get("fact", "")
        src = entry.get("source", {})
        src_id = src.get("id", "") if isinstance(src, dict) else ""
        src_html = f"<div class='timeline-source'>📎 {src_id}</div>" if src_id else ""

        rows.append(
            f"""
            <div class='timeline-row'>
              <div class='timeline-dot' style='background:{color}'></div>
              <div class='timeline-date'>{when}</div>
              <div class='timeline-fact'>{fact}{src_html}</div>
            </div>
            """
        )

    st.markdown("".join(rows), unsafe_allow_html=True)
