"""The Pattern card timeline visualization — the Graphiti moment."""
from __future__ import annotations

from datetime import date

import streamlit as st


def render(timeline: list[dict]) -> None:
    """Render a vertical timeline of incidents — dot + date + 1-line fact."""
    if not timeline:
        st.caption("Keine historischen Vorfälle.")
        return

    # Sort by date for chronological display
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

    timeline = sorted(timeline, key=_parse_date)
    today = date.today()

    html_rows = []
    for entry in timeline:
        d = _parse_date(entry)
        when = d.strftime("%d.%m.%Y") if d != date.min else "?"
        # Compute days-ago for visual weight
        days_ago = (today - d).days if d != date.min else 0
        is_recent = days_ago < 90

        dot_color = "#fbbf24" if is_recent else "#ef4444" if days_ago < 365 else "#71717a"
        fact = entry.get("fact", "")
        src = entry.get("source", {})
        src_id = src.get("id", "") if isinstance(src, dict) else ""

        html_rows.append(
            f"""
            <div style="display:flex;gap:0.6rem;margin-bottom:0.5rem;align-items:flex-start">
              <div style="flex-shrink:0;padding-top:0.25rem;width:1rem;text-align:center">
                <span style="display:inline-block;width:0.7rem;height:0.7rem;border-radius:50%;
                             background:{dot_color}"></span>
              </div>
              <div style="flex-shrink:0;min-width:5rem;color:#a1a1aa;font-size:0.78rem;
                          padding-top:0.1rem;font-variant-numeric:tabular-nums">{when}</div>
              <div style="flex:1;font-size:0.85rem;color:#e4e4e7">{fact}
                {f'<div style="color:#71717a;font-size:0.7rem">📎 {src_id}</div>' if src_id else ''}
              </div>
            </div>
            """
        )

    st.markdown(
        "<div style='border-left:2px solid #27272a;padding-left:0.7rem;margin:0.4rem 0'>"
        + "".join(html_rows)
        + "</div>",
        unsafe_allow_html=True,
    )
