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

You receive a tenant message (German) PLUS optional caller context block,
and return a structured classification.

Categories (intent):
- heating:       Heizung/Heizkörper/Heizungsausfall/kalt/Frost-related
- nka_dispute:   Nebenkostenabrechnung-Beanstandung, Heizkosten-Streit, Belegeinsicht
- noise:         Lärmbeschwerden gegen Nachbarn
- payment:       Mieterzahlungs-/Mahnungs-/Rückzahlungsthemen
- other:         everything else

Urgency — base on the message AND the caller context together. The same
words from different callers warrant different urgency:

- emergency:  ANY of:
    - Heizungsausfall during Heizperiode AND (frost forecast OR vulnerable
      tenant (post-OP, hohes Alter ≥65, Kleinkind, Pflegestufe) OR repeat
      incident pattern (≥3 prior same-intent cases))
    - Wasserschaden, Stromausfall, Gasleck, Aufzug stuck mit Person
- urgent:     formal Frist nähert sich, Mietminderung angedroht, single
              vulnerability marker without other escalation, or any
              heating issue from a tenant with a known vulnerability
- standard:   everything else

Be willing to escalate based on context even when the message itself is
terse. A short "Heizung kaputt" from a 68-year-old post-OP tenant with
5 prior heating cases in 18 months IS an emergency — the caller doesn't
have to repeat what we already know.

Return ONLY a JSON object with this exact shape:
{
  "intent": "heating",
  "urgency": "urgent",
  "confidence": 0.92,
  "reasoning": "one sentence in English"
}

No prose outside the JSON. No markdown fence.
"""


def _format_caller_context(ctx: dict | None) -> str:
    """Render a compact German context block to prepend to the user message."""
    if not ctx:
        return ""
    parts: list[str] = ["[Anrufer-Kontext]"]
    name = ctx.get("name")
    if name:
        parts.append(f"Name: {name}")
    age = ctx.get("age")
    if age:
        parts.append(f"Alter: {age}")
    since = ctx.get("since")
    if since:
        parts.append(f"Mietverhältnis seit: {since}")
    vuln = ctx.get("vulnerability")
    if vuln:
        parts.append(f"Verletzlichkeit / besondere Lage: {vuln}")
    prior = ctx.get("prior_incidents")
    if isinstance(prior, dict):
        cnt = prior.get("count")
        span = prior.get("timespan_months")
        intent = prior.get("intent")
        if cnt and intent:
            line = f"Frühere {intent}-Vorfälle: {cnt}"
            if span:
                line += f" in den letzten {span} Monaten"
            parts.append(line)
    unit = ctx.get("unit_label")
    if unit:
        parts.append(f"Wohneinheit: {unit}")
    if len(parts) == 1:
        return ""  # no meaningful context
    return "\n".join(parts)


def classify_intent(
    message_body: str, caller_context: dict | None = None,
) -> IntentResult:
    """Synchronous — it's a single short LLM call, no need to be async.

    `caller_context` is an optional dict of caller signals (name, age,
    vulnerability, prior_incidents.count/timespan_months/intent, unit_label).
    Anything provided is rendered into a "[Anrufer-Kontext]" block prepended
    to the message so the classifier can escalate terse messages from
    high-risk tenants appropriately.
    """
    client = _get_client()
    ctx_block = _format_caller_context(caller_context)
    user_content = (
        f"{ctx_block}\n\n[Nachricht des Mieters]\n{message_body}"
        if ctx_block else message_body
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
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
