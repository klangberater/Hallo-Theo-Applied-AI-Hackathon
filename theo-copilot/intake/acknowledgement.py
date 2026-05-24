"""Immediate acknowledgement reply.

Every inbound tenant message gets an automatic 2-sentence German
acknowledgement: thank-you + empathetic reference to the topic ("Es tut
uns leid zu hören, dass Ihre Heizung wieder kalt ist…"). This fires
within ~1–2s of receipt, long before the enrichment agent finishes.

Implementation: single Sonnet call. We pass the tenant name + intent +
the message body and ask for a short, warm German reply.

If the LLM call fails, we fall back to a static template keyed on intent
so the tenant still gets a reply.

See: PRODUCT_SPEC §7.1 (intake pipeline)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

for _candidate in [
    Path("/opt/fletcher/.env"),
    Path(__file__).resolve().parent.parent / ".env",
    Path.cwd() / ".env",
]:
    if _candidate.exists():
        load_dotenv(_candidate)
        break


log = logging.getLogger(__name__)

MODEL = os.environ.get("ANTHROPIC_MODEL_FAST", "claude-sonnet-4-5")

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic()
    return _client


SYSTEM_PROMPT = """Du schreibst die automatische Eingangsbestätigung einer deutschen Hausverwaltung (hallo theo) an einen Mieter, der gerade per WhatsApp/E-Mail eine Nachricht geschickt hat.

Regeln:
- Genau 2 kurze Sätze, höflich, warm, in Sie-Form.
- Satz 1: Bedankt sich für die Nachricht (kurz, nicht floskelhaft).
- Satz 2: Bezieht sich konkret und empathisch auf das Thema der Nachricht
  (z.B. "Es tut uns leid zu hören, dass Ihre Heizung wieder kalt ist —
  wir kümmern uns umgehend darum.").
- Keine Versprechen zu Fristen oder Lösungen. Keine Vermutungen über Schuld.
- Keine Signatur, keine Anrede mit Namen am Anfang — die Nachricht beginnt
  direkt mit dem ersten Satz.
- Nur den fertigen Antworttext zurückgeben, keine Erklärung, kein Markdown.
"""


_FALLBACK_BY_INTENT = {
    "heating": (
        "Vielen Dank für Ihre Nachricht. Es tut uns leid zu hören, dass Sie "
        "Probleme mit der Heizung haben — wir kümmern uns umgehend darum."
    ),
    "noise": (
        "Vielen Dank für Ihre Nachricht. Wir nehmen Lärmbeschwerden sehr "
        "ernst und melden uns schnellstmöglich bei Ihnen zurück."
    ),
    "nka_dispute": (
        "Vielen Dank für Ihre Rückmeldung zur Nebenkostenabrechnung. "
        "Wir prüfen Ihren Hinweis und melden uns zeitnah."
    ),
    "payment": (
        "Vielen Dank für Ihre Nachricht. Wir prüfen den Vorgang und "
        "melden uns in Kürze bei Ihnen."
    ),
    "other": (
        "Vielen Dank für Ihre Nachricht. Wir haben Ihr Anliegen erhalten "
        "und melden uns schnellstmöglich bei Ihnen."
    ),
}


def generate_acknowledgement(
    body: str, intent: str | None = None, tenant_name: str | None = None,
) -> str:
    """Generate a warm 2-sentence acknowledgement.

    Synchronous on purpose — it's a single short LLM call and we want it
    to land before we return from the webhook.
    """
    user_msg = (
        f"Eingehende Nachricht des Mieters:\n---\n{body.strip()}\n---\n\n"
        f"Schreibe jetzt die 2-Satz-Eingangsbestätigung."
    )
    try:
        resp = _get_client().messages.create(
            model=MODEL,
            max_tokens=200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        # Strip surrounding quotes / fences just in case.
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1].strip()
        if text:
            return text
        log.warning("acknowledgement LLM returned empty; using fallback")
    except Exception as e:  # noqa: BLE001
        log.warning("acknowledgement LLM failed: %s — using fallback", e)

    return _FALLBACK_BY_INTENT.get(intent or "other", _FALLBACK_BY_INTENT["other"])


if __name__ == "__main__":
    # Smoke
    print(generate_acknowledgement(
        "Die Heizung im Wohnzimmer ist seit gestern Abend wieder kalt. "
        "Wettervorhersage soll Frost werden.",
        intent="heating",
    ))
