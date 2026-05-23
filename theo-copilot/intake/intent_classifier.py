"""Fast intent classification with a Sonnet-class model.

Called once per inbound message, before the heavier enrichment loop fires.
Cheap, fast, deterministic enough for routing.

See: docs/PRODUCT_SPEC.md §7.1
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal, TypedDict

from anthropic import Anthropic
from dotenv import load_dotenv

# Best-effort .env load (matches infra/db.py chain).
for _candidate in [
    Path("/opt/fletcher/.env"),
    Path(__file__).resolve().parent.parent.parent / ".env",
    Path.cwd() / ".env",
]:
    if _candidate.exists():
        load_dotenv(_candidate)
        break


MODEL = os.environ.get("ANTHROPIC_MODEL_FAST", "claude-sonnet-4-5")

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic()  # reads ANTHROPIC_API_KEY from env
    return _client


Intent = Literal["heating", "nka_dispute", "noise", "payment", "other"]
Urgency = Literal["emergency", "urgent", "standard"]


class IntentResult(TypedDict):
    intent: Intent
    urgency: Urgency
    confidence: float
    reasoning: str


SYSTEM_PROMPT = """You are an intent classifier for a German property-management copilot.

You receive a tenant message (German) and return a structured classification.

Categories (intent):
- heating:       Heizung/Heizkörper/Heizungsausfall/kalt/Frost-related
- nka_dispute:   Nebenkostenabrechnung-Beanstandung, Heizkosten-Streit, Belegeinsicht
- noise:         Lärmbeschwerden gegen Nachbarn
- payment:       Mieterzahlungs-/Mahnungs-/Rückzahlungsthemen
- other:         everything else

Urgency:
- emergency:  Heizungsausfall in Heizperiode + (Frost vorhergesagt OR vulnerable tenant OR repeat incident)
- urgent:     formal Frist nähert sich, Mietminderung angedroht, Wasseraustritt
- standard:   everything else

Return ONLY a JSON object with this exact shape:
{
  "intent": "heating",
  "urgency": "urgent",
  "confidence": 0.92,
  "reasoning": "one sentence in English"
}

No prose outside the JSON. No markdown fence.
"""


def classify_intent(message_body: str) -> IntentResult:
    """Synchronous — it's a single short LLM call, no need to be async."""
    client = _get_client()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": message_body}],
    )
    text = "".join(block.text for block in resp.content if block.type == "text").strip()

    # Defensive: strip a markdown fence if the model wraps the JSON.
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"intent classifier returned non-JSON: {text!r}") from e

    # Validate fields
    if data.get("intent") not in {"heating", "nka_dispute", "noise", "payment", "other"}:
        raise ValueError(f"invalid intent: {data!r}")
    if data.get("urgency") not in {"emergency", "urgent", "standard"}:
        raise ValueError(f"invalid urgency: {data!r}")

    return IntentResult(
        intent=data["intent"],
        urgency=data["urgency"],
        confidence=float(data.get("confidence", 0.0)),
        reasoning=data.get("reasoning", ""),
    )


if __name__ == "__main__":
    # Smoke test against the Köhler email body.
    test_msg = (
        "Sehr geehrte Frau Weber, ich melde mich schon wieder und es tut mir leid. "
        "Die Heizung im Wohnzimmer bleibt seit heute Nachmittag kalt. Das ist jetzt "
        "das sechste Mal in den letzten anderthalb Jahren mit demselben Heizkörper. "
        "Die Wettervorhersage für Donnerstag und Freitag soll Frost werden."
    )
    result = classify_intent(test_msg)
    print(json.dumps(result, indent=2, ensure_ascii=False))
