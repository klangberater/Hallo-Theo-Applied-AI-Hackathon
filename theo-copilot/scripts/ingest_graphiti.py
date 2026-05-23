"""Pre-demo Graphiti episode ingestion.

Loads the 8 hero episodes from PRODUCT_SPEC §6.2 into Neo4j via Graphiti.
After this completes, agent/tools/l3_memory.query_temporal_memory() will
return real temporal facts (source="graphiti") instead of the
hand-curated stub fallback.

Idempotent: Graphiti dedupes by episode name. Re-run safe.

Run with:
    cd theo-copilot && python -m scripts.ingest_graphiti

Then immediately:
    python -m scripts.kill_switch_cache    # snapshot working queries

Owner: Lead 1.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from infra.graphiti_client import add_episode, tenant_group  # noqa: E402


KOEHLER_GROUP = tenant_group("koehler")


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


EPISODES = [
    {
        "name": "medical-addendum-2024-05",
        "body": (
            "Anlage 3 zum Mietvertrag, 18.05.2024: Margarethe Köhler hat dem "
            "Vermieter durch ärztliches Attest (Dr. med. Henning, Charité "
            "Charlottenburg) angezeigt, dass sie nach Hüftgelenks-Operation "
            "(Februar 2024) eine erhöhte Empfindlichkeit gegenüber "
            "Raumtemperaturen unter 19°C aufweist. Der Vermieter nimmt dies "
            "zur Kenntnis und wird die Heizungsfunktionalität in der WE 4 "
            "links mit gebotener Sorgfalt sicherstellen."
        ),
        "reference_time": _utc(2024, 5, 18),
        "group_id": KOEHLER_GROUP,
        "source_description": "Mietvertrag-Anlage Köhler",
    },
    {
        "name": "heating-incident-2024-10",
        "body": (
            "VG-2024-0188 (12.10.2024, abgeschlossen 13.10.2024): Margarethe "
            "Köhler meldet, dass der Heizkörper im Wohnzimmer der WE 4 links "
            "nicht richtig warm wird. Bergmann Heizungstechnik wird beauftragt. "
            "Lösung: Entlüftung und Druckkontrolle am Strang, Anlagendruck zu "
            "niedrig, Wasser nachgefüllt. Technikernotiz Kurt Bergmann: "
            "'Heizkörper-Thermostat im Wohnzimmer reagiert träge. Empfehlung: "
            "bei nächster Wartung prüfen, ggf. tauschen.' Kosten 145,00 €."
        ),
        "reference_time": _utc(2024, 10, 12),
        "group_id": KOEHLER_GROUP,
        "source_description": "Vorgang VG-2024-0188",
    },
    {
        "name": "heating-incident-2024-12",
        "body": (
            "VG-2024-0233 (02.12.2024, abgeschlossen 03.12.2024): Heizung "
            "Wohnzimmer Köhler wieder kalt. Bergmann beauftragt. "
            "Thermostatkopf demontiert, gereinigt, wieder montiert. Funktion "
            "temporär wiederhergestellt. Technikernotiz: 'Thermostat klemmt "
            "mechanisch. Mein Vorschlag vom Oktober bleibt: Austausch des "
            "Ventileinsatzes erforderlich. Kosten ca. 280-340 €. Ich kann das "
            "nicht jedes Quartal aufs Neue mechanisch befreien.' Kosten "
            "165,00 €. Sarah Weber notiert: Angebot für Tausch bei Bergmann "
            "anfragen."
        ),
        "reference_time": _utc(2024, 12, 2),
        "group_id": KOEHLER_GROUP,
        "source_description": "Vorgang VG-2024-0233",
    },
    {
        "name": "heating-incident-2025-01",
        "body": (
            "VG-2025-0021 (22.01.2025, abgeschlossen 23.01.2025): DRINGEND. "
            "Heizung Wohnzimmer Köhler komplett ausgefallen während "
            "Frostperiode. Bergmann Notdienst. Ventileinsatz war komplett "
            "verklemmt, Notfall-Reinigung und temporäre Funktion. Kurt Bergmann "
            "vermerkt formal: 'Ich möchte hier formal anmerken, dass ich diesen "
            "Heizkörper in 4 Monaten zum dritten Mal repariere. Die "
            "kumulierten Kosten liegen bereits über dem Preis des Austauschs, "
            "den ich angeboten habe. Ich werde bei der nächsten Anforderung "
            "schriftlich eine Empfehlung zur Maßnahme aussprechen und um "
            "Freigabe oder dokumentierten Ablehnungsgrund bitten.' "
            "Kosten 220,00 € (Notdienst-Aufschlag)."
        ),
        "reference_time": _utc(2025, 1, 22),
        "group_id": KOEHLER_GROUP,
        "source_description": "Vorgang VG-2025-0021",
    },
    {
        "name": "mietminderung-2025-02",
        "body": (
            "VG-2025-0058 (09.02.2025, abgeschlossen 12.02.2025): Margarethe "
            "Köhler macht 15% Mietminderung für 3 Wochen (22.01.-12.02.2025) "
            "wegen wiederholtem Heizungsausfall während Frostperiode geltend. "
            "Berufung auf BGB § 536, Heizperiode. Tochter Anja Köhler "
            "(Anwältin mit Spezialgebiet Wohnungsrecht, Charlottenburg) hat "
            "formell schriftlich angemerkt. hallo theo erkennt Mietminderung "
            "an: 15% auf Bruttowarmmiete für 3 Wochen = 91,80 €, Verrechnung "
            "mit Folgemiete. Sarah Weber notiert: 'Anerkennen war richtig. "
            "Bei Widerspruch wäre Klage realistisches Risiko gewesen. Aber: "
            "das darf nicht nochmal passieren.'"
        ),
        "reference_time": _utc(2025, 2, 9),
        "group_id": KOEHLER_GROUP,
        "source_description": "Vorgang VG-2025-0058",
    },
    {
        "name": "bergmann-offer-2025-04",
        "body": (
            "Angebot Nr. BH-2025-0044 von Bergmann Heizungstechnik GmbH "
            "(18.04.2025): Austausch Thermostatventil-Einsatz Heizkörper "
            "Wohnzimmer WE 4 links — Honeywell V2000 Einsatz, Funktionstest "
            "mit Wärmebild-Kontrolle, Druckkontrolle Heizstrang 3./4. OG, "
            "12 Monate Gewährleistung. Material 100 €, Arbeitsleistung "
            "212,50 €, Anfahrt im Wartungsvertrag enthalten. Gesamt brutto "
            "371,88 €. Begründung Bergmann: 'In den letzten 13 Monaten habe "
            "ich diesen Heizkörper viermal notdürftig wieder in Funktion "
            "gebracht. Jeder Einsatz hat 145-220 € gekostet, in Summe bereits "
            "530 €. Wichtiger als die Kosten: bei dem aktuellen Zustand kann "
            "ich nicht zusagen, dass der Heizkörper über einen ganzen Winter "
            "durchhält.' Status: 22.04.2025 an Familie Wegener weitergeleitet, "
            "25.04.2025 Antwort 'Schauen wir uns nach Sommer an', "
            "15.10.2025 Sarah erinnert, 16.10.2025 'Mal sehen, müssen wir "
            "nicht sofort entscheiden'. Angebot seit 7 Monaten unbearbeitet."
        ),
        "reference_time": _utc(2025, 4, 18),
        "group_id": KOEHLER_GROUP,
        "source_description": "Angebot Bergmann BH-2025-0044",
    },
    {
        "name": "saisonende-check-2025-04",
        "body": (
            "VG-2025-0142 (18.04.2025): Saisonende-Check Heizung WE 4 links. "
            "Bergmann hat den Heizkörper Wohnzimmer bei seiner Routinewartung "
            "nochmal angesehen. Keine akute Maßnahme erforderlich (Heizung "
            "wird im Sommer nicht benötigt). Kurt Bergmann hat sein Angebot "
            "formell schriftlich eingereicht (BH-2025-0044). Kosten 0,00 € "
            "(im Wartungsvertrag enthalten)."
        ),
        "reference_time": _utc(2025, 4, 18),
        "group_id": KOEHLER_GROUP,
        "source_description": "Vorgang VG-2025-0142",
    },
    {
        "name": "internal-chat-2025-11-14-jonas-preapproval",
        "body": (
            "Interner Chat hallo theo, 14.11.2025 16:22-16:28. Sarah Weber an "
            "Jonas Petersen (Team Lead Berlin): Vor dem Wochenende, "
            "Heizperiode läuft seit 6 Wochen, Frau Köhler (WE 4l Zossener 47) "
            "ist erwartbarer Problemfall, das war im Januar die Mietminderung. "
            "Eigentümer (Familie Wegener) hat das Bergmann-Angebot für den "
            "Tausch trotz zweier Nachfragen nicht freigegeben. Sarah sieht "
            "kommen, dass die Heizung wieder ausfällt. Jonas Petersen antwortet "
            "16:28: 'Sarah ehrlich — wenn das ausfällt und sie ist 68, alleine, "
            "post-OP und hat schon einmal gemindert, dann ist das ein Risiko. "
            "Lass uns nicht jeden Cent zweimal umdrehen wenn der Eigentümer "
            "schläft. Wenn sie sich nochmal meldet: für so etwas hast du bis "
            "500 € Vorabgenehmigung von mir. Beauftrage und dokumentier es, "
            "ich klär das mit Wegener im Nachgang wenn nötig.' Sarah bestätigt: "
            "'Okay, danke. Notiere ich.'"
        ),
        "reference_time": _utc(2025, 11, 14, 16, 22),
        "group_id": KOEHLER_GROUP,
        "source_description": "Slack/Internal chat Sarah ↔ Jonas",
    },
]


async def main() -> None:
    print(f"--- ingesting {len(EPISODES)} episodes ---")
    for i, ep in enumerate(EPISODES, 1):
        print(f"[{i}/{len(EPISODES)}] {ep['name']} ({ep['reference_time'].date()})")
        try:
            await add_episode(
                name=ep["name"],
                body=ep["body"],
                reference_time=ep["reference_time"],
                group_id=ep["group_id"],
                source_description=ep["source_description"],
            )
        except Exception as e:  # noqa: BLE001
            print(f"  !! failed: {e}")
            raise
    print("--- ingest complete ---")
    print()
    print("Next: run `python -m scripts.kill_switch_cache` to snapshot working queries.")


if __name__ == "__main__":
    asyncio.run(main())
