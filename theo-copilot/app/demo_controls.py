"""Demo-Steuerung — sidebar buttons to fire scenarios during the pitch.

Lives in the Streamlit sidebar (collapsed by default). Three controls:
  - Demo zurücksetzen     → re-runs data.seed (clean state for next rehearsal)
  - Köhler WhatsApp       → POSTs the Köhler body to /webhook/whatsapp
                             (use if your phone isn't to hand)
  - Demir NK-Beanstandung → POSTs the Demir body to /webhook/email

Each shows the resulting ticket id + asks the user to refresh the inbox.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import requests
import streamlit as st


# ---------------------------------------------------------------------------
# Scenario payloads
# ---------------------------------------------------------------------------

INTAKE_URL = os.environ.get("THEO_INTAKE_URL", "http://127.0.0.1:8002")

KOEHLER_PHONE = "+491793960546"   # the Baileys-paired test number
KOEHLER_BODY = (
    "Sehr geehrte Frau Weber, die Heizung im Wohnzimmer geht schon wieder nicht. "
    "Das ist jetzt das sechste Mal in 18 Monaten mit demselben Heizkörper. "
    "Die Wettervorhersage für Donnerstag und Freitag soll Frost werden. "
    "Ich bin nach meiner Hüft-OP nicht so belastbar mit der Kälte. "
    "Bitte sagen Sie mir Bescheid, wann jemand kommen kann."
)

DEMIR_EMAIL = "y.demir@gmx.de"
DEMIR_SUBJECT = "Förmliche Beanstandung Nebenkostenabrechnung 2024"
_DATASET = Path(__file__).resolve().parent.parent / "data" / "hallotheo_demo"
try:
    DEMIR_BODY = (_DATASET / "email_02_demir_NK_beanstandung.txt").read_text("utf-8")
except FileNotFoundError:
    DEMIR_BODY = (
        "Sehr geehrte Frau Weber, mit Schreiben vom 12.09.2025 haben wir die "
        "Nebenkostenabrechnung für 2024 erhalten. Hiermit erheben wir innerhalb "
        "der gesetzlichen Frist gemäß § 556 Abs. 3 BGB Einwendungen. ..."
    )


# ---------------------------------------------------------------------------
# Action helpers
# ---------------------------------------------------------------------------

def _fire_koehler() -> dict:
    r = requests.post(
        f"{INTAKE_URL}/webhook/whatsapp",
        json={"from": KOEHLER_PHONE, "body": KOEHLER_BODY},
        timeout=10,
    )
    return r.json() if r.ok else {"error": f"HTTP {r.status_code}: {r.text[:200]}"}


def _fire_demir() -> dict:
    r = requests.post(
        f"{INTAKE_URL}/webhook/email",
        json={
            "from_address": DEMIR_EMAIL,
            "subject": DEMIR_SUBJECT,
            "body": DEMIR_BODY,
            "external_thread_id": "thread_demir_nka2024",
        },
        timeout=10,
    )
    return r.json() if r.ok else {"error": f"HTTP {r.status_code}: {r.text[:200]}"}


def _reset_demo() -> dict:
    """Re-run data.seed in the same venv. Wipes + re-inserts statics +
    Schornsteinfeger autonomous ticket. Köhler/Demir tickets vanish — fire
    them again from the sidebar buttons."""
    repo_root = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [".venv/bin/python", "-m", "data.seed"],
        cwd=repo_root, capture_output=True, text=True, timeout=60,
    )
    return {
        "ok": proc.returncode == 0,
        "stdout": (proc.stdout or "").strip().splitlines()[-3:],
        "stderr": (proc.stderr or "").strip()[-200:],
    }


# ---------------------------------------------------------------------------
# Sidebar UI
# ---------------------------------------------------------------------------

def render() -> None:
    """Mount the demo controls as a collapsible expander at the top of the page."""
    with st.expander("🎭 Demo-Steuerung", expanded=False):
        st.caption(
            "Live-Trigger pro Szenario. Während der eigentlichen Vorführung "
            "zugeklappt lassen."
        )

        cols = st.columns(3)

        # --- Köhler ---
        with cols[0]:
            st.markdown("**📱 Köhler — Heizung**")
            st.caption("Fallback. Live-Demo: WhatsApp vom echten Telefon.")
            if st.button("Köhler simulieren", use_container_width=True,
                         key="demo_fire_koehler"):
                with st.spinner("Sende WhatsApp-Webhook…"):
                    result = _fire_koehler()
                if "ticket_id" in result:
                    st.success(f"Ticket {result['ticket_id']} erstellt.")
                    st.session_state["last_fired"] = result["ticket_id"]
                else:
                    st.error(result.get("error") or str(result))

        # --- Demir ---
        with cols[1]:
            st.markdown("**✉ Demir — NK-Beanstandung**")
            st.caption("Formelle E-Mail von y.demir@gmx.de.")
            if st.button("Demir abfeuern", use_container_width=True,
                         type="primary", key="demo_fire_demir"):
                with st.spinner("Sende E-Mail-Webhook…"):
                    result = _fire_demir()
                if "ticket_id" in result:
                    st.success(f"Ticket {result['ticket_id']} erstellt.")
                    st.session_state["last_fired"] = result["ticket_id"]
                else:
                    st.error(result.get("error") or str(result))

        # --- Reset ---
        with cols[2]:
            st.markdown("**↻ Zurücksetzen**")
            st.caption("Wipe + re-seed inkl. Schornsteinfeger.")
            if st.button("Demo zurücksetzen", use_container_width=True,
                         key="demo_reset"):
                with st.spinner("Setze zurück…"):
                    result = _reset_demo()
                if result["ok"]:
                    st.session_state.pop("selected_ticket_id", None)
                    st.session_state.opened_ticket_ids = set()
                    st.success("Demo zurückgesetzt.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Fehler: {result.get('stderr', 'unknown')}")

        if st.session_state.get("last_fired"):
            st.caption(
                f"Letzter Trigger: `{st.session_state['last_fired']}` — "
                "Enrichment dauert ~60 s."
            )
