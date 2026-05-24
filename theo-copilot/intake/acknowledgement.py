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

WICHTIG: Diese Nachricht ist nur eine Bestätigung des Eingangs. Die eigentliche
Bearbeitung erfolgt durch einen Mitarbeiter und kann je nach Anliegen mehrere
Stunden oder Tage dauern. Mach KEINE konkreten Zeitversprechen.

Regeln:
- Genau 2 kurze Sätze, höflich, warm, in Sie-Form.
- Satz 1: Bedankt sich für die Nachricht (kurz, nicht floskelhaft).
- Satz 2: Bezieht sich konkret und empathisch auf das Thema und sagt, dass
  ein Mitarbeiter sich der Sache annimmt und sich zurückmeldet.
  Beispiel: "Es tut uns leid zu hören, dass Ihre Heizung wieder kalt ist —
  ein Kollege prüft das Anliegen und meldet sich bei Ihnen."
- VERBOTEN: konkrete Zeitangaben oder Eile-Versprechen wie "sofort",
  "umgehend", "in Kürze", "heute noch", "innerhalb von X Stunden",
  "morgen". Diese Worte dürfen NICHT vorkommen.
- ERLAUBT: nur bei urgency=emergency das Wort "schnellstmöglich".
- Keine Vermutungen über Schuld. Keine Versprechen zu Lösungen.
- Keine Signatur, keine Anrede mit Namen am Anfang — die Nachricht beginnt
  direkt mit dem ersten Satz.
- Nur den fertigen Antworttext zurückgeben, keine Erklärung, kein Markdown.
"""


# Fallback templates — used if the LLM call fails. Phrased to be honest
# about turnaround: no time promises, just "a colleague will get back to
# you". Only the emergency variant uses "schnellstmöglich".
_FALLBACK_STANDARD = {
    "heating": (
        "Vielen Dank für Ihre Nachricht. Es tut uns leid zu hören, dass Sie "
        "Probleme mit der Heizung haben — ein Kollege prüft das Anliegen "
        "und meldet sich bei Ihnen."
    ),
    "noise": (
        "Vielen Dank für Ihre Nachricht. Wir nehmen Lärmbeschwerden sehr "
        "ernst — ein Kollege sieht sich Ihr Anliegen an und meldet sich "
        "bei Ihnen zurück."
    ),
    "nka_dispute": (
        "Vielen Dank für Ihre Rückmeldung zur Nebenkostenabrechnung. "
        "Ein Kollege prüft Ihren Hinweis und meldet sich bei Ihnen."
    ),
    "payment": (
        "Vielen Dank für Ihre Nachricht. Ein Kollege prüft den Vorgang "
        "und meldet sich bei Ihnen zurück."
    ),
    "other": (
        "Vielen Dank für Ihre Nachricht. Ein Kollege sieht sich Ihr "
        "Anliegen an und meldet sich bei Ihnen."
    ),
}

_FALLBACK_EMERGENCY = (
    "Vielen Dank für Ihre Nachricht. Wir behandeln Ihr Anliegen mit "
    "höchster Priorität und melden uns schnellstmöglich bei Ihnen."
)


def generate_acknowledgement(
    body: str,
    intent: str | None = None,
    urgency: str | None = None,
    tenant_name: str | None = None,
) -> str:
    """Generate a warm 2-sentence acknowledgement.

    Synchronous on purpose — it's a single short LLM call and we want it
    to land before we return from the webhook.

    Critically: does NOT promise concrete timing. The real reply may take
    hours when a human is in the approval loop (propose / bundle_approve
    autonomy modes). The ack only confirms receipt + that a person will
    get back to them.
    """
    urgency_hint = (urgency or "standard").lower()
    user_msg = (
        f"urgency={urgency_hint}\n\n"
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

    if urgency_hint == "emergency":
        return _FALLBACK_EMERGENCY
    return _FALLBACK_STANDARD.get(intent or "other", _FALLBACK_STANDARD["other"])


if __name__ == "__main__":
    # Smoke
    print("--- standard heating ---")
    print(generate_acknowledgement(
        "Die Heizung im Wohnzimmer ist seit gestern Abend kalt.",
        intent="heating", urgency="standard",
    ))
    print("\n--- emergency heating ---")
    print(generate_acknowledgement(
        "Heizung komplett ausgefallen, Frost angekündigt, Kleinkind im Haus.",
        intent="heating", urgency="emergency",
    ))
