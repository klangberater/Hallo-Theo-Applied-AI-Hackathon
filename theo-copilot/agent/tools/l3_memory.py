"""L3 temporal memory — Graphiti queries. THE MOAT.

Three-tiered resolution order (each tier auto-falls back to the next):
  1. live  — graphiti_client.search() against Neo4j (requires OPENAI_API_KEY
             for Graphiti's fact extraction LLM)
  2. cache — JSON file pre-computed during Friday-night ingestion
             (kill-switch per PRODUCT_SPEC §12.1)
  3. stub  — hand-curated facts for the Köhler hero query (so the demo
             works even when both Graphiti and the cache are unavailable)

The agent sees the same shape regardless of tier — only the `source`
field in each fact tells you which tier produced it.

See: PRODUCT_SPEC §5.3 + §12.1
"""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

for _candidate in [
    Path("/opt/fletcher/.env"),
    Path(__file__).resolve().parent.parent.parent.parent / ".env",
    Path.cwd() / ".env",
]:
    if _candidate.exists():
        load_dotenv(_candidate)
        break


USE_LIVE_GRAPHITI = os.environ.get("USE_LIVE_GRAPHITI", "true").lower() == "true"
CACHE_PATH = Path(
    os.environ.get("KILL_SWITCH_CACHE_PATH", "scripts/_kill_switch_cache.json")
)


# ---------------------------------------------------------------------------
# Hand-curated stub — Köhler temporal facts.
# Mirrors what Graphiti SHOULD extract from the 8 hero episodes in spec §6.2.
# When Graphiti is live we read from Neo4j instead; this stub is the demo
# safety-net.
# ---------------------------------------------------------------------------

_KOEHLER_FACTS = [
    {
        "fact": "Margarethe Köhler hat post-OP eine medizinische Empfindlichkeit "
                "gegen Raumtemperaturen unter 19°C (Anlage 3 zum Mietvertrag, 18.05.2024).",
        "valid_from": "2024-05-18",
        "valid_until": None,
        "source_episodes": ["medical-addendum-2024-05"],
        "category": "vulnerability",
    },
    {
        "fact": "Wohnzimmer-Heizkörper WE 4 links zeigt wiederkehrendes Versagen — "
                "5 Vorgänge in 13 Monaten (Okt 2024 - Apr 2025), gleiche Ursache "
                "(Thermostatventil-Einsatz).",
        "valid_from": "2024-10-12",
        "valid_until": None,
        "source_episodes": [
            "heating-incident-2024-10", "heating-incident-2024-12",
            "heating-incident-2025-01", "heating-incident-2025-04",
        ],
        "category": "chronic_pattern",
    },
    {
        "fact": "Bergmann Heizungstechnik hat 4 Notfall-Reparaturen am gleichen "
                "Heizkörper durchgeführt (kumulierte Kosten 530 €) und formell "
                "schriftliche Empfehlung für Ventileinsatz-Austausch eingereicht.",
        "valid_from": "2025-01-22",
        "valid_until": None,
        "source_episodes": ["heating-incident-2025-01", "heating-incident-2025-04"],
        "category": "vendor_recommendation",
    },
    {
        "fact": "Bergmann-Angebot BH-2025-0044 (Tausch Thermostatventil, 371,88 € brutto) "
                "wurde am 22.04.2025 an Familie Wegener weitergeleitet — seit 7 Monaten "
                "ohne Freigabe trotz zweier Nachfassen.",
        "valid_from": "2025-04-22",
        "valid_until": None,
        "source_episodes": ["bergmann-offer-2025-04"],
        "category": "open_decision",
    },
    {
        "fact": "Mieterin hat im Februar 2025 erfolgreich 15% Mietminderung für 3 Wochen "
                "durchgesetzt (91,80 €) — anerkannt durch Verwaltung wegen realistischem "
                "Klagerisiko. Tochter Anja Köhler ist Anwältin mit Spezialgebiet Mietrecht.",
        "valid_from": "2025-02-12",
        "valid_until": None,
        "source_episodes": ["mietminderung-2025-02"],
        "category": "legal_event",
    },
    {
        "fact": "Heizperiode aktiv seit 01.10.2025. Frostperiode -3°C ab Donnerstag "
                "(20.11.2025) vorhergesagt.",
        "valid_from": "2025-10-01",
        "valid_until": "2026-04-30",
        "source_episodes": [],
        "category": "environmental",
    },
]


def _annotate(facts: list[dict], source: str) -> list[dict]:
    return [{**f, "source": source} for f in facts]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def query_temporal_memory(
    query: str,
    group_id: str,
    num_results: int = 10,
) -> list[dict]:
    """Return temporal facts relevant to the query, scoped by group_id.

    group_id examples: 'tenant:koehler', 'property:zossener_47', 'vendor:bergmann'.
    """
    # Tier 1: live Graphiti
    if USE_LIVE_GRAPHITI:
        try:
            from infra.graphiti_client import search_facts
            facts = await search_facts(query=query, group_id=group_id, limit=num_results)
            if facts:
                return _annotate(facts, "graphiti")
        except Exception as e:  # noqa: BLE001
            # Don't let Graphiti errors break the demo — fall through.
            print(f"[l3_memory] graphiti unavailable, falling back: {e}")

    # Tier 2: kill-switch cache
    if CACHE_PATH.exists():
        try:
            cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            key = f"{group_id}|{query}"
            if key in cache:
                return _annotate(cache[key][:num_results], "cache")
        except Exception:  # noqa: BLE001
            pass

    # Tier 3: hand-curated stub (Köhler only)
    if group_id.startswith("tenant:koehler") or group_id == "tenant:koehler_we4l":
        return _annotate(_KOEHLER_FACTS[:num_results], "stub")
    return []


async def get_entity_timeline(entity_name: str, group_id: str) -> list[dict]:
    """Return episodes mentioning `entity_name`, scoped by group_id, chronologically."""
    if USE_LIVE_GRAPHITI:
        try:
            from infra.graphiti_client import get_timeline
            episodes = await get_timeline(entity_name=entity_name, group_id=group_id)
            if episodes:
                return _annotate(episodes, "graphiti")
        except Exception as e:  # noqa: BLE001
            print(f"[l3_memory] graphiti unavailable, falling back: {e}")

    # Stub timeline for Köhler heating
    if group_id.startswith("tenant:koehler") and "heizung" in entity_name.lower():
        return _annotate([
            {"date": str(date(2024, 10, 12)),
             "fact": "Wohnzimmer-Heizkörper nicht warm; Druck zu niedrig; Bergmann empfiehlt Thermostat-Prüfung."},
            {"date": str(date(2024, 12, 2)),
             "fact": "Wohnzimmer wieder kalt; Thermostat klemmt mechanisch."},
            {"date": str(date(2025, 1, 22)),
             "fact": "DRINGEND: Komplettausfall während Frost; Ventileinsatz verklemmt; Notdienst."},
            {"date": str(date(2025, 2, 12)),
             "fact": "Mietminderung 15% / 3 Wochen anerkannt (91,80 €)."},
            {"date": str(date(2025, 4, 18)),
             "fact": "Saisonende-Check; Bergmann-Angebot BH-2025-0044 formell eingereicht (371,88 €)."},
            {"date": str(date(2025, 11, 17)),
             "fact": "Mieterin meldet 6. Vorfall in 18 Monaten."},
        ], "stub")
    return []
