"""Load hallotheo_demo/ into the theo Postgres schema.

Reads source files from data/hallotheo_demo/ and inserts into theo.* tables.
Idempotent: TRUNCATEs theo.* tables first, then re-inserts.

Run with:
    cd theo-copilot && python -m data.seed

Source of truth: data/hallotheo_demo/00_SZENARIO_BIBEL.md (entities + IDs).

Owner: Lead 3. PRODUCT_SPEC §10 Friday evening.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from infra.db import connect, close_pool


DATA_DIR = Path(__file__).resolve().parent / "hallotheo_demo"


def _read(name: str) -> str:
    """Read a dataset file. Never modifies it (per CLAUDE.md hackathon rules)."""
    return (DATA_DIR / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Static entities (transcribed from 00_SZENARIO_BIBEL.md)
# ---------------------------------------------------------------------------

PROPERTIES = [
    {
        "id": "zossener_47",
        "name": "Zossener Straße 47",
        "address": "Zossener Straße 47, 10961 Berlin",
        "owner": "Familie Wegener",
        "metadata": {
            "type": "mixed-use Altbau",
            "built": 1908,
            "denkmalgeschuetzt": True,
            "units_residential": 14,
            "units_commercial": 2,
            "owner_contact": "Dr. Klaus Wegener (Hamburg)",
            "managed_since": "2024-04-01",
            "previous_admin": "Hausverwaltung Schubert & Co",
            "heating": "Gas-Brennwertkessel Bj. 2018",
            "known_issues": [
                "Heizungssteuerung Strang 3./4. OG",
                "Souterrain Wasserschaden 2023",
            ],
        },
    },
]

UNITS = [
    {"id": "common", "property_id": "zossener_47", "label": "Gemeinschaftsanlage",
     "qm": 0, "type": "common"},
    {"id": "we_4l", "property_id": "zossener_47", "label": "WE 4 links",
     "qm": 68.2, "type": "wohnung"},
    {"id": "we_3r", "property_id": "zossener_47", "label": "WE 3 rechts",
     "qm": 78.4, "type": "wohnung"},
    {"id": "we_2l", "property_id": "zossener_47", "label": "WE 2 links",
     "qm": 65.0, "type": "wohnung"},
    {"id": "we_1l", "property_id": "zossener_47", "label": "WE 1 links",
     "qm": 62.0, "type": "wohnung"},
    {"id": "dg", "property_id": "zossener_47", "label": "Dachgeschoss",
     "qm": 70.0, "type": "wohnung"},
    {"id": "gewerbe_eg_v", "property_id": "zossener_47", "label": "Gewerbe EG (Café Krume & Korn)",
     "qm": 85.0, "type": "gewerbe"},
    {"id": "gewerbe_eg_h", "property_id": "zossener_47", "label": "Gewerbe EG (Falk + Bauer)",
     "qm": 72.0, "type": "gewerbe"},
]

TENANTS = [
    {"id": "koehler", "name": "Margarethe Köhler",
     "email": "margarethe.koehler1957@web.de", "phone": "+4930615 23 81",
     "metadata": {
         "age": 68, "since": "1997-04-01", "vulnerability": "post-OP",
         "daughter_lawyer": "Anja Köhler (Charlottenburg)",
         "medical_attest": "Hüftgelenks-OP 02/2024, Anlage 3 Mietvertrag 18.05.2024",
     }},
    {"id": "demir", "name": "Yusuf und Aylin Demir",
     "email": "y.demir@gmx.de", "phone": "+4930558 17 92",
     "metadata": {"since": "2021-07-01", "household_size": 4}},
    {"id": "brandt", "name": "Tobias Brandt",
     "email": "tobias.brandt@protonmail.com", "phone": "+4915123 45 678",
     "metadata": {"since": "2024-05-01", "occupation": "tech"}},
    {"id": "vogt", "name": "Stefan Vogt",
     "email": "stefan.vogt@gmail.com", "phone": "+4930412 56 789",
     "metadata": {"modernization_application_pending": True}},
    {"id": "hartmann", "name": "Lisa Hartmann (Café Krume & Korn)",
     "email": "lisa@krume-und-korn.de", "phone": "+4930289 17 65",
     "metadata": {"gewerbe": True, "since": "2019-09-01"}},
    {"id": "falk_bauer", "name": "Architekturbüro Falk + Bauer",
     "email": "kontakt@falk-bauer.de", "phone": "+4930765 43 21",
     "metadata": {"gewerbe": True, "since": "2017-01-01"}},
]

# Normalize phone to E.164 (strip spaces) for lookup-by-phone.
for t in TENANTS:
    t["phone"] = t["phone"].replace(" ", "")

LEASES = [
    {"id": "lease_koehler_we4l", "unit_id": "we_4l", "tenant_id": "koehler",
     "start_date": date(1997, 4, 1), "end_date": None,
     "rent_cold": 612.00, "status": "active",
     "full_text": _read("mietvertrag_WE4l_koehler_auszug.txt")},
    {"id": "lease_demir_we3r", "unit_id": "we_3r", "tenant_id": "demir",
     "start_date": date(2021, 7, 1), "end_date": date(2027, 6, 30),
     "rent_cold": 1380.00, "status": "active",
     "full_text": _read("mietvertrag_WE3r_demir_auszug.txt")},
    {"id": "lease_brandt_we2l", "unit_id": "we_2l", "tenant_id": "brandt",
     "start_date": date(2024, 5, 1), "end_date": None,
     "rent_cold": 1180.00, "status": "active", "full_text": ""},
    {"id": "lease_hartmann", "unit_id": "gewerbe_eg_v", "tenant_id": "hartmann",
     "start_date": date(2019, 9, 1), "end_date": date(2029, 8, 31),
     "rent_cold": 2450.00, "status": "active", "full_text": ""},
    {"id": "lease_falk_bauer", "unit_id": "gewerbe_eg_h", "tenant_id": "falk_bauer",
     "start_date": date(2017, 1, 1), "end_date": None,
     "rent_cold": 1890.00, "status": "active", "full_text": ""},
]

VENDORS = [
    {"id": "bergmann", "name": "Bergmann Heizungstechnik GmbH",
     "trade": "Heizung/Sanitär", "status": "active",
     "contract_until": date(2026, 12, 31),
     "notes": "Wartungsvertrag bis 12/2026. Reaktion Ø 4h. Inhaber Kurt Bergmann. Fair, zuverlässig."},
    {"id": "klempner_ecke", "name": "KlempnerEcke Berlin",
     "trade": "Sanitär (Reserve)", "status": "approved",
     "contract_until": None,
     "notes": "Schnell, mittlere Qualität."},
    {"id": "elektro_kbg", "name": "ElektroService Kreuzberg",
     "trade": "Elektrik", "status": "approved",
     "contract_until": None, "notes": "Solide, langsam."},
    {"id": "hausmeister_flink", "name": "HausMeisterFlink",
     "trade": "Hausmeisterservice", "status": "active",
     "contract_until": None, "notes": "Wochentlicher Vertrag, 320 €/Monat pauschal."},
    {"id": "fixdirekt", "name": "FixDirekt Berlin GmbH",
     "trade": "Handwerker (allgemein)", "status": "anomaly",
     "contract_until": None,
     "notes": "ANOMALIE: 3× vage Rechnungen in 6 Wochen seit Oktober 2025. "
              "Von Voreigentümerin 'wegen Empfehlung' beauftragt. Keine Belege, identische Formulierung."},
    {"id": "stadtwerke", "name": "Berliner Stadtwerke",
     "trade": "Versorger (Gas/Strom)", "status": "active",
     "contract_until": None, "notes": "Jahresabschluss April."},
    {"id": "schornsteinfeger", "name": "Schornsteinfeger Innung Kreuzberg",
     "trade": "Pflichtwartung", "status": "active",
     "contract_until": None, "notes": "Jährliche Pflichtwartung. Termin offen seit 5 Tagen."},
]

# Historical Köhler tickets (closed). The OPEN demo ticket gets created by the
# intake webhook when Köhler's WhatsApp arrives — do NOT seed it here.
TICKETS = [
    {"id": "VG-2024-0188", "unit_id": "we_4l", "category": "Heizung",
     "priority": "Standard",
     "opened_at": datetime(2024, 10, 12, 9, 30, tzinfo=timezone.utc),
     "closed_at": datetime(2024, 10, 13, 16, 0, tzinfo=timezone.utc),
     "resolution": "Entlüftung des Heizkörpers, Druckkontrolle am Strang. "
                   "Anlagendruck war zu niedrig, Wasser nachgefüllt. "
                   "Bergmann-Empfehlung: Thermostatventil bei nächster Wartung prüfen.",
     "cost": 145.00, "vendor_id": "bergmann", "status": "closed",
     "classified_intent": "heating",
     "full_text": "Heizung Wohnzimmer wird nicht richtig warm."},

    {"id": "VG-2024-0233", "unit_id": "we_4l", "category": "Heizung",
     "priority": "Standard",
     "opened_at": datetime(2024, 12, 2, 8, 15, tzinfo=timezone.utc),
     "closed_at": datetime(2024, 12, 3, 14, 30, tzinfo=timezone.utc),
     "resolution": "Thermostatkopf demontiert, gereinigt, wieder montiert. "
                   "Temporär wiederhergestellt. Bergmann: Ventileinsatz-Austausch erforderlich "
                   "(ca. 280-340 €).",
     "cost": 165.00, "vendor_id": "bergmann", "status": "closed",
     "classified_intent": "heating",
     "full_text": "Heizung Wohnzimmer wieder kalt."},

    {"id": "VG-2025-0021", "unit_id": "we_4l", "category": "Heizung",
     "priority": "DRINGEND",
     "opened_at": datetime(2025, 1, 22, 7, 45, tzinfo=timezone.utc),
     "closed_at": datetime(2025, 1, 23, 11, 0, tzinfo=timezone.utc),
     "resolution": "Ventileinsatz komplett verklemmt, Notfall-Reinigung und temporäre Funktion. "
                   "Bergmann hat schriftlich vermerkt: dritter Eingriff in 4 Monaten, "
                   "kumulierte Kosten über Tausch-Preis.",
     "cost": 220.00, "vendor_id": "bergmann", "status": "closed",
     "classified_intent": "heating",
     "full_text": "Heizung komplett ausgefallen während Frostperiode."},

    {"id": "VG-2025-0058", "unit_id": "we_4l", "category": "Mietminderung",
     "priority": "Hoch",
     "opened_at": datetime(2025, 2, 9, 10, 0, tzinfo=timezone.utc),
     "closed_at": datetime(2025, 2, 12, 17, 0, tzinfo=timezone.utc),
     "resolution": "Mietminderung 15% für 3 Wochen (22.01.-12.02.2025) anerkannt. "
                   "Tochter Anja Köhler (Anwältin) hatte formell angemerkt. "
                   "Verrechnung mit Folgemiete.",
     "cost": 91.80, "vendor_id": None, "status": "closed",
     "classified_intent": "mietminderung",
     "full_text": "Mieterin macht 15% Mietminderung für 3 Wochen geltend wegen wiederholtem "
                  "Heizungsausfall während Frostperiode. Berufung auf BGB § 536, Heizperiode."},

    {"id": "VG-2025-0142", "unit_id": "we_4l", "category": "Heizung (Saisonende-Check)",
     "priority": "Standard",
     "opened_at": datetime(2025, 4, 18, 11, 0, tzinfo=timezone.utc),
     "closed_at": datetime(2025, 4, 19, 15, 30, tzinfo=timezone.utc),
     "resolution": "Saisonende-Check Bergmann. Keine akute Maßnahme. "
                   "Bergmann hat formell Angebot BH-2025-0044 eingereicht (Tausch Thermostatventil).",
     "cost": 0.00, "vendor_id": "bergmann", "status": "closed",
     "classified_intent": "heating",
     "full_text": "Vorbereitung Heizperiodenende. Bergmann hat Heizkörper bei Routinewartung "
                  "nochmal angesehen und Angebot 340 € formal schriftlich eingereicht."},
]

VENDOR_OFFERS = [
    {"id": "BH-2025-0044", "vendor_id": "bergmann", "unit_id": "we_4l",
     "scope": "Austausch Thermostatventil-Einsatz Heizkörper Wohnzimmer (Honeywell V2000) "
              "+ Funktionstest + Druckkontrolle Heizstrang 3./4. OG",
     "amount": 371.88, "status": "pending", "issued_at": date(2025, 4, 18)},
]

INVOICES = [
    # FixDirekt — the anomaly pattern
    {"id": "FD-1271", "vendor_id": "fixdirekt", "unit_id": "zossener_47",
     "amount_brutto": 425.00, "issued_at": date(2023, 9, 3),
     "line_items": "Material+Std (detailliert)", "has_itemization": True,
     "raw_text": "Detaillierte Rechnung mit Stundennachweis und Materialliste."},
    {"id": "FD-1389", "vendor_id": "fixdirekt", "unit_id": "zossener_47",
     "amount_brutto": 578.00, "issued_at": date(2023, 12, 12),
     "line_items": "Material+Std (detailliert)", "has_itemization": True,
     "raw_text": "Detaillierte Rechnung mit Stundennachweis und Materialliste."},
    {"id": "FD-1402", "vendor_id": "fixdirekt", "unit_id": "zossener_47",
     "amount_brutto": 312.00, "issued_at": date(2024, 1, 4),
     "line_items": "Material+Std (detailliert)", "has_itemization": True,
     "raw_text": "Detaillierte Rechnung mit Stundennachweis und Materialliste."},
    {"id": "FD-1418", "vendor_id": "fixdirekt", "unit_id": "zossener_47",
     "amount_brutto": 485.00, "issued_at": date(2024, 1, 17),
     "line_items": "Material+Std (detailliert)", "has_itemization": True,
     "raw_text": "Detaillierte Rechnung mit Stundennachweis und Materialliste."},
    # The anomaly cluster — vague invoices after hallo theo handover
    {"id": "FD-2014", "vendor_id": "fixdirekt", "unit_id": "zossener_47",
     "amount_brutto": 1620.00, "issued_at": date(2025, 9, 30),
     "line_items": "Arbeitsleistung und Material / kleinere Reparaturen / sonstige Aufwendungen",
     "has_itemization": False,
     "raw_text": "Vage Rechnung ohne Aufstellung — KG/Hof."},
    {"id": "FD-2027", "vendor_id": "fixdirekt", "unit_id": "zossener_47",
     "amount_brutto": 1480.00, "issued_at": date(2025, 10, 24),
     "line_items": "Arbeitsleistung und Material / kleinere Reparaturen / sonstige Aufwendungen",
     "has_itemization": False,
     "raw_text": "Vage Rechnung ohne Aufstellung — TH/Diele."},
    {"id": "FD-2041", "vendor_id": "fixdirekt", "unit_id": "zossener_47",
     "amount_brutto": 1840.00, "issued_at": date(2025, 11, 14),
     "line_items": "Arbeitsleistung und Material / kleinere Reparaturen / sonstige Aufwendungen",
     "has_itemization": False,
     "raw_text": _read("fixdirekt_2041_und_historie.txt")},
    # Bergmann — for cost reference
    {"id": "BG-2024-101", "vendor_id": "bergmann", "unit_id": "we_4l",
     "amount_brutto": 145.00, "issued_at": date(2024, 10, 13),
     "line_items": "VG-2024-0188 Entlüftung+Druckkontrolle", "has_itemization": True,
     "raw_text": ""},
]

NKA = [
    {"id": "nka_demir_we3r_2024", "unit_id": "we_3r", "year": 2024,
     "total": 4934.19,
     "breakdown": {
         "heizung_verbrauch": 1948.52,
         "heizung_grundkosten": 803.12,
         "warmwasser": 466.55,
         "muell": 198.40, "wasser": 412.30, "hausreinigung": 264.18,
         "garten": 82.15, "schornsteinfeger": 29.40,
         "versicherung": 198.72, "grundsteuer": 287.40,
         "allgemeinstrom": 89.15, "aufzug": 154.30,
         "vorauszahlungen_geleistet": -4320.00,
         "nachzahlung": 614.19,
     },
     "raw_text": _read("NKA_2024_demir_WE3r.txt")},
]

EMAILS = [
    {"id": "email_koehler_2025_11_17", "from_address": "margarethe.koehler1957@web.de",
     "to_address": "sarah.weber@hallotheo.de",
     "subject": "Heizung Wohnzimmer geht schon wieder nicht — WE 4 links, Zossener Str. 47",
     "body": _read("email_01_koehler_heizung.txt"),
     "received_at": datetime(2025, 11, 17, 19, 43, tzinfo=timezone.utc),
     "thread_id": "thread_koehler_heizung_nov25", "unit_id": "we_4l"},
    {"id": "email_demir_2025_10_02", "from_address": "y.demir@gmx.de",
     "to_address": "sarah.weber@hallotheo.de",
     "subject": "Förmliche Beanstandung Nebenkostenabrechnung 2024 — Zossener 47, WE 3 rechts",
     "body": _read("email_02_demir_NK_beanstandung.txt"),
     "received_at": datetime(2025, 10, 2, 14, 18, tzinfo=timezone.utc),
     "thread_id": "thread_demir_nka2024", "unit_id": "we_3r"},
]

# Internal chat — Sarah ↔ Jonas. The Friday 16:22 message is the hero pre-approval.
CHAT_MESSAGES = [
    {"id": "chat_sj_001", "thread_id": "thread_sarah_jonas",
     "sender": "Sarah Weber",
     "body": "Jonas, kurze Sache vor dem Wochenende — Heizperiode läuft jetzt seit 6 Wochen "
             "und ich habe ein paar Objekte mit erwartbaren Problemfällen. Bei Zossener 47 "
             "z.B. der Heizkörper bei Frau Köhler. Du erinnerst dich, das war im Januar mit "
             "der Mietminderung.",
     "sent_at": datetime(2025, 11, 14, 16, 22, tzinfo=timezone.utc)},
    {"id": "chat_sj_002", "thread_id": "thread_sarah_jonas",
     "sender": "Jonas Petersen",
     "body": "Ja klar.",
     "sent_at": datetime(2025, 11, 14, 16, 23, tzinfo=timezone.utc)},
    {"id": "chat_sj_003", "thread_id": "thread_sarah_jonas",
     "sender": "Sarah Weber",
     "body": "Eigentümer (Familie Wegener) hat das Bergmann-Angebot für den Tausch immer noch "
             "nicht freigegeben, obwohl ich zweimal nachgefasst habe. Ich sehe schon kommen, "
             "dass sie wieder ausfällt und wir am Wochenende rennen müssen.",
     "sent_at": datetime(2025, 11, 14, 16, 24, tzinfo=timezone.utc)},
    {"id": "chat_sj_004", "thread_id": "thread_sarah_jonas",
     "sender": "Jonas Petersen",
     "body": "Was kostet der Tausch?",
     "sent_at": datetime(2025, 11, 14, 16, 25, tzinfo=timezone.utc)},
    {"id": "chat_sj_005", "thread_id": "thread_sarah_jonas",
     "sender": "Sarah Weber", "body": "Ca. 370 € brutto.",
     "sent_at": datetime(2025, 11, 14, 16, 25, tzinfo=timezone.utc)},
    # THE HERO PRE-APPROVAL — this is the "internal pre-approval" enrichment card.
    {"id": "chat_sj_006", "thread_id": "thread_sarah_jonas",
     "sender": "Jonas Petersen",
     "body": "Sarah ehrlich — wenn das ausfällt und sie ist 68, alleine, post-OP und hat "
             "schon einmal gemindert, dann ist das ein Risiko. Lass uns nicht jeden Cent "
             "zweimal umdrehen wenn der Eigentümer schläft. Wenn sie sich nochmal meldet: "
             "für so etwas hast du bis 500 € Vorabgenehmigung von mir. Beauftrage und "
             "dokumentier es, ich klär das mit Wegener im Nachgang wenn nötig.",
     "sent_at": datetime(2025, 11, 14, 16, 28, tzinfo=timezone.utc)},
    {"id": "chat_sj_007", "thread_id": "thread_sarah_jonas",
     "sender": "Sarah Weber", "body": "Okay, danke. Notiere ich.",
     "sent_at": datetime(2025, 11, 14, 16, 30, tzinfo=timezone.utc)},
]

# Channel threads — used by intake to find existing conversations.
CHANNEL_THREADS = [
    {"id": "ct_koehler_whatsapp", "channel": "whatsapp",
     "external_id": "wa_4930615232381",
     "tenant_id": "koehler", "unit_id": "we_4l",
     "last_message_at": datetime(2025, 11, 17, 19, 43, tzinfo=timezone.utc)},
    {"id": "ct_demir_email", "channel": "email",
     "external_id": "thread_demir_nka2024",
     "tenant_id": "demir", "unit_id": "we_3r",
     "last_message_at": datetime(2025, 10, 2, 14, 18, tzinfo=timezone.utc)},
]


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

# Order matters: dependencies first.
TRUNCATE_ORDER = [
    "trace_events",
    "proposed_actions",
    "vendor_dispatches",
    "channel_messages",
    "channel_threads",
    "chat_messages",
    "emails",
    "tickets",
    "vendor_offers",
    "invoices",
    "nka",
    "leases",
    "units",
    "tenants",
    "vendors",
    "properties",
]


# ---------------------------------------------------------------------------
# Schornsteinfeger demo ticket — autonomous_done (Phase 3 of autonomy work)
#
# This bypasses the normal intake/enrichment flow: we INSERT the ticket
# already-enriched + already-executed at 03:14 Uhr so the demo starts with
# an autonomous-mode ticket at the top of Sarah's inbox.
# ---------------------------------------------------------------------------

SF_TICKET_ID = "SF-2026-01"
SF_THREAD_ID = "ct_schornsteinfeger_email"
SF_TENANT_ID = "schornsteinfeger_innung"

SF_TENANT = {
    "id": SF_TENANT_ID,
    "name": "Schornsteinfeger Innung Kreuzberg",
    "email": "kontakt@schornsteinfeger-kreuzberg.de",
    "phone": "+4930225 14 80",
    "metadata": {"vendor_side": True, "trade": "Schornsteinfeger"},
}
SF_TENANT["phone"] = SF_TENANT["phone"].replace(" ", "")

SF_HISTORICAL_TICKETS = [
    {
        "id": "SF-2024-01", "unit_id": "common", "category": "Pflichtwartung",
        "priority": "Standard",
        "opened_at": datetime(2024, 1, 8, 9, 0, tzinfo=timezone.utc),
        "closed_at": datetime(2024, 1, 18, 12, 0, tzinfo=timezone.utc),
        "resolution": "Jahres-Pflichtwartung 2024 durchgeführt am 18.01.2024. "
                      "Alle Feuerstätten + Schornsteine i.O. Bescheinigung erstellt.",
        "cost": 0.00, "vendor_id": "schornsteinfeger", "status": "closed",
        "classified_intent": "scheduling",
        "full_text": "Jahres-Pflichtwartung 2024 — Schornsteinfeger Innung Kreuzberg.",
    },
    {
        "id": "SF-2025-01", "unit_id": "common", "category": "Pflichtwartung",
        "priority": "Standard",
        "opened_at": datetime(2025, 1, 14, 9, 0, tzinfo=timezone.utc),
        "closed_at": datetime(2025, 1, 23, 12, 0, tzinfo=timezone.utc),
        "resolution": "Jahres-Pflichtwartung 2025 durchgeführt am 23.01.2025. "
                      "Alle Feuerstätten + Schornsteine i.O. Bescheinigung erstellt.",
        "cost": 0.00, "vendor_id": "schornsteinfeger", "status": "closed",
        "classified_intent": "scheduling",
        "full_text": "Jahres-Pflichtwartung 2025 — Schornsteinfeger Innung Kreuzberg.",
    },
]

SF_INBOUND_EMAIL_BODY = (
    "Sehr geehrte Frau Weber,\n\n"
    "für die jährliche Pflichtwartung 2026 der Feuerstätten und Schornsteine "
    "in der Zossener Straße 47 benötigen wir einen Termin im 1. Quartal.\n\n"
    "Verfügbare Slots:\n"
    "  - Donnerstag, 15.01.2026, 09:00–12:00\n"
    "  - Donnerstag, 22.01.2026, 09:00–12:00\n"
    "  - Donnerstag, 29.01.2026, 13:00–16:00\n"
    "  - Donnerstag, 05.02.2026, 09:00–12:00\n\n"
    "Bitte um Rückmeldung bis Ende der Woche.\n\n"
    "Mit freundlichen Grüßen\n"
    "Heinrich Mader\n"
    "Schornsteinfeger Innung Kreuzberg"
)

SF_AUTONOMOUS_REPLY_BODY = (
    "Sehr geehrter Herr Mader,\n\n"
    "vielen Dank für Ihre Nachricht. Wir bestätigen den Termin am "
    "Donnerstag, 22.01.2026, 09:00–12:00 Uhr für die Jahres-Pflichtwartung "
    "der Feuerstätten und Schornsteine in der Zossener Straße 47.\n\n"
    "Der Zugang zum Heizraum erfolgt über das Treppenhaus, Kellergeschoss. "
    "Den Termin habe ich für Sarah Weber im Kalender vermerkt.\n\n"
    "Sollten sich Änderungen ergeben, melden wir uns rechtzeitig.\n\n"
    "Mit freundlichen Grüßen\n"
    "hallo theo Berlin GmbH\n"
    "i.A. Theo Copilot (autonom bestätigt im Namen von S. Weber)"
)

SF_ENRICHMENT = {
    "tenant_card": {
        "tenant_id": SF_TENANT_ID,
        "name": "Schornsteinfeger Innung Kreuzberg",
        "warnings": [],
        "sources": [{"kind": "vendor", "id": "schornsteinfeger"}],
    },
    "unit_card": {
        "unit_id": "common",
        "label": "Zossener Str. 47 — Gemeinschaftsanlage",
        "sources": [],
    },
    "lease_facts": [],
    "prior_incidents": {
        "count": 2,
        "timespan_months": 24,
        "timeline": [
            {"date": "2024-01-18",
             "fact": "Jahres-Pflichtwartung 2024 durchgeführt — alles i.O.",
             "source": {"kind": "ticket", "id": "SF-2024-01"}},
            {"date": "2025-01-23",
             "fact": "Jahres-Pflichtwartung 2025 durchgeführt — alles i.O.",
             "source": {"kind": "ticket", "id": "SF-2025-01"}},
        ],
        "pattern_summary": (
            "Routine: jährliche Pflichtwartung im Januar — Termin bestätigt im "
            "gleichen Format wie 2024 und 2025."
        ),
        "source": "postgres-fallback",
    },
    "open_vendor_offers": [],
    "internal_pre_approvals": [],
    "weather": None,
    "legal_context": [{
        "citation": "Schornsteinfeger-Handwerksgesetz § 14",
        "short_text": (
            "Eigentümer ist zur jährlichen Schornsteinfeger-Pflichtwartung "
            "verpflichtet. Termin ist verbindlich abzustimmen."
        ),
        "relevance": "Routine-Pflicht ohne Ermessensspielraum.",
        "source": {"kind": "wiki", "id": "policies/heating-emergency-de.md"},
    }],
    "suggested_actions": [{
        "action_type": "send_email_reply",
        "payload": {
            "subject": "Re: Jahres-Pflichtwartung 2026 — Terminabstimmung",
            "body": SF_AUTONOMOUS_REPLY_BODY,
            "thread_id": SF_THREAD_ID,
        },
        "rationale": (
            "Terminbestätigung an die Schornsteinfeger-Innung für den 22.01.2026 "
            "(im Kalender frei, gleiche Logistik wie 2024 und 2025)."
        ),
        "source_citations": [
            {"kind": "ticket", "id": "SF-2025-01"},
            {"kind": "wiki", "id": "policies/heating-emergency-de.md"},
        ],
        "confidence": "high",
        "bundle_id": None,
        "bundle_order": 0,
        "executed_at": "2026-05-23T03:14:00Z",
    }],
    "autonomy_mode": "autonomous_done",
    "autonomy_rationale": (
        "Alle fünf Guardrails grün: Kosten 0 € (Pflichtwartung im Standardvertrag "
        "enthalten); kein Mieter betroffen, keine Vulnerabilität; keine "
        "rechtliche Exposition; klare Präzedenz aus 2024 + 2025 (gleicher Termin, "
        "gleiche Logistik); Routine-Terminbestätigung. Habe um 03:14 Uhr autonom "
        "geantwortet."
    ),
}

SF_TRACE = [
    (1, "intent_classification",
     {"intent": "scheduling", "urgency": "standard", "confidence": 0.97,
      "reasoning": "Routine annual Schornsteinfeger appointment request."}),
    (2, "llm_call_started", {"turn": 0, "model": "claude-opus-4-5"}),
    (3, "tool_use",
     {"name": "list_tickets", "args": {"unit_id": "common"}}),
    (4, "tool_result",
     {"name": "list_tickets",
      "preview": "[SF-2024-01 closed, SF-2025-01 closed — both Pflichtwartung]"}),
    (5, "tool_use",
     {"name": "search_wiki", "args": {"query": "Schornsteinfeger Pflichtwartung"}}),
    (6, "tool_result",
     {"name": "search_wiki",
      "preview": "policies/heating-emergency-de.md — Pflichtwartung jährlich."}),
    (7, "llm_call_completed",
     {"turn": 0, "stop_reason": "end_turn",
      "usage": {"in": 4220, "out": 612}}),
    (8, "enrichment_payload",
     {"autonomy_mode": "autonomous_done",
      "rationale": "All 5 guardrails passed."}),
    (9, "tool_use",
     {"name": "send_email_reply",
      "args": {"subject": "Re: Jahres-Pflichtwartung 2026 — Terminabstimmung"}}),
    (10, "tool_result",
     {"name": "send_email_reply", "preview": "{message_id: em_...}"}),
]


async def insert_schornsteinfeger(conn) -> None:
    """Insert the autonomous_done Schornsteinfeger ticket + thread + trace."""
    import json
    # Pseudo-tenant for the Innungsmeister so channel_threads.tenant_id is satisfied
    await conn.execute(
        "INSERT INTO theo.tenants (id, name, email, phone, metadata) "
        "VALUES ($1, $2, $3, $4, $5::jsonb)",
        SF_TENANT["id"], SF_TENANT["name"], SF_TENANT["email"],
        SF_TENANT["phone"], json.dumps(SF_TENANT["metadata"]),
    )

    # Historical Pflichtwartung tickets (precedent for the autonomy decision)
    for tk in SF_HISTORICAL_TICKETS:
        await conn.execute(
            "INSERT INTO theo.tickets (id, unit_id, category, priority, opened_at, "
            "closed_at, resolution, cost, vendor_id, full_text, classified_intent, "
            "status) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)",
            tk["id"], tk["unit_id"], tk["category"], tk["priority"],
            tk["opened_at"], tk["closed_at"], tk["resolution"], tk["cost"],
            tk["vendor_id"], tk["full_text"], tk["classified_intent"], tk["status"],
        )

    # Channel thread + inbound email + outbound autonomous reply
    inbound_at = datetime(2026, 5, 23, 2, 41, tzinfo=timezone.utc)
    reply_at = datetime(2026, 5, 23, 3, 14, tzinfo=timezone.utc)

    await conn.execute(
        "INSERT INTO theo.channel_threads (id, channel, external_id, tenant_id, "
        "unit_id, last_message_at) VALUES ($1, 'email', $2, $3, 'common', $4)",
        SF_THREAD_ID, "email-schornsteinfeger-2026", SF_TENANT_ID, reply_at,
    )
    await conn.execute(
        "INSERT INTO theo.channel_messages (id, thread_id, direction, sender, "
        "body, sent_at) VALUES ($1, $2, 'inbound', $3, $4, $5)",
        "cm_sf_in", SF_THREAD_ID, "Schornsteinfeger Innung Kreuzberg",
        SF_INBOUND_EMAIL_BODY, inbound_at,
    )
    await conn.execute(
        "INSERT INTO theo.channel_messages (id, thread_id, direction, sender, "
        "body, sent_at) VALUES ($1, $2, 'outbound', $3, $4, $5)",
        "cm_sf_out", SF_THREAD_ID, "Theo Copilot (autonom)",
        SF_AUTONOMOUS_REPLY_BODY, reply_at,
    )

    # The autonomous ticket itself
    enrichment_json = json.dumps(SF_ENRICHMENT, default=str, ensure_ascii=False)
    suggested = SF_ENRICHMENT["suggested_actions"]
    suggested_json = json.dumps(suggested, default=str, ensure_ascii=False)
    await conn.execute(
        "INSERT INTO theo.tickets (id, unit_id, category, priority, opened_at, "
        "closed_at, resolution, cost, vendor_id, full_text, source_thread_id, "
        "classified_intent, status, enrichment, suggested_actions) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, "
        "$14::jsonb, $15::jsonb)",
        SF_TICKET_ID, "common", "Pflichtwartung", "Standard",
        inbound_at, reply_at,
        "Termin für 22.01.2026 bestätigt (autonom).",
        0.00, "schornsteinfeger",
        SF_INBOUND_EMAIL_BODY, SF_THREAD_ID,
        "scheduling", "closed",
        enrichment_json, suggested_json,
    )

    # Trace events
    for step, kind, payload in SF_TRACE:
        await conn.execute(
            "INSERT INTO theo.trace_events (ticket_id, step, kind, payload) "
            "VALUES ($1, $2, $3, $4::jsonb)",
            SF_TICKET_ID, step, kind, json.dumps(payload, default=str),
        )


async def truncate(conn) -> None:
    """Wipe theo tables in dependency-safe order."""
    for table in TRUNCATE_ORDER:
        await conn.execute(f"TRUNCATE TABLE theo.{table} RESTART IDENTITY CASCADE")


async def insert_all(conn) -> dict[str, int]:
    """Insert all static entities. Returns counts."""
    import json
    counts: dict[str, int] = {}

    # properties
    for p in PROPERTIES:
        await conn.execute(
            "INSERT INTO theo.properties (id, name, address, owner, metadata) "
            "VALUES ($1, $2, $3, $4, $5::jsonb)",
            p["id"], p["name"], p["address"], p["owner"], json.dumps(p["metadata"]),
        )
    counts["properties"] = len(PROPERTIES)

    # units
    for u in UNITS:
        await conn.execute(
            "INSERT INTO theo.units (id, property_id, label, qm, type) "
            "VALUES ($1, $2, $3, $4, $5)",
            u["id"], u["property_id"], u["label"], u["qm"], u["type"],
        )
    counts["units"] = len(UNITS)

    # tenants
    for t in TENANTS:
        await conn.execute(
            "INSERT INTO theo.tenants (id, name, email, phone, metadata) "
            "VALUES ($1, $2, $3, $4, $5::jsonb)",
            t["id"], t["name"], t["email"], t["phone"], json.dumps(t["metadata"]),
        )
    counts["tenants"] = len(TENANTS)

    # vendors
    for v in VENDORS:
        await conn.execute(
            "INSERT INTO theo.vendors (id, name, trade, status, contract_until, notes) "
            "VALUES ($1, $2, $3, $4, $5, $6)",
            v["id"], v["name"], v["trade"], v["status"], v["contract_until"], v["notes"],
        )
    counts["vendors"] = len(VENDORS)

    # leases
    for le in LEASES:
        await conn.execute(
            "INSERT INTO theo.leases (id, unit_id, tenant_id, start_date, end_date, "
            "rent_cold, status, full_text) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            le["id"], le["unit_id"], le["tenant_id"], le["start_date"], le["end_date"],
            le["rent_cold"], le["status"], le["full_text"],
        )
    counts["leases"] = len(LEASES)

    # vendor_offers
    for vo in VENDOR_OFFERS:
        await conn.execute(
            "INSERT INTO theo.vendor_offers (id, vendor_id, unit_id, scope, amount, status, issued_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7)",
            vo["id"], vo["vendor_id"], vo["unit_id"], vo["scope"],
            vo["amount"], vo["status"], vo["issued_at"],
        )
    counts["vendor_offers"] = len(VENDOR_OFFERS)

    # invoices
    for i in INVOICES:
        # Invoices may reference property_id ("zossener_47") as unit_id placeholder for building-wide.
        # The schema requires unit_id REFERENCES units(id), so use the property's own id only if a unit exists with that id.
        unit_ref = i["unit_id"] if any(u["id"] == i["unit_id"] for u in UNITS) else None
        await conn.execute(
            "INSERT INTO theo.invoices (id, vendor_id, unit_id, amount_brutto, issued_at, "
            "line_items, raw_text, has_itemization) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            i["id"], i["vendor_id"], unit_ref, i["amount_brutto"], i["issued_at"],
            i["line_items"], i["raw_text"], i["has_itemization"],
        )
    counts["invoices"] = len(INVOICES)

    # nka
    for n in NKA:
        await conn.execute(
            "INSERT INTO theo.nka (id, unit_id, year, total, breakdown, raw_text) "
            "VALUES ($1, $2, $3, $4, $5::jsonb, $6)",
            n["id"], n["unit_id"], n["year"], n["total"],
            json.dumps(n["breakdown"]), n["raw_text"],
        )
    counts["nka"] = len(NKA)

    # tickets (historical)
    for tk in TICKETS:
        await conn.execute(
            "INSERT INTO theo.tickets (id, unit_id, category, priority, opened_at, closed_at, "
            "resolution, cost, vendor_id, full_text, classified_intent, status) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)",
            tk["id"], tk["unit_id"], tk["category"], tk["priority"],
            tk["opened_at"], tk["closed_at"], tk["resolution"], tk["cost"],
            tk["vendor_id"], tk["full_text"], tk["classified_intent"], tk["status"],
        )
    counts["tickets"] = len(TICKETS)

    # emails
    for e in EMAILS:
        await conn.execute(
            "INSERT INTO theo.emails (id, from_address, to_address, subject, body, "
            "received_at, thread_id, unit_id) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            e["id"], e["from_address"], e["to_address"], e["subject"], e["body"],
            e["received_at"], e["thread_id"], e["unit_id"],
        )
    counts["emails"] = len(EMAILS)

    # chat_messages
    for c in CHAT_MESSAGES:
        await conn.execute(
            "INSERT INTO theo.chat_messages (id, thread_id, sender, body, sent_at) "
            "VALUES ($1, $2, $3, $4, $5)",
            c["id"], c["thread_id"], c["sender"], c["body"], c["sent_at"],
        )
    counts["chat_messages"] = len(CHAT_MESSAGES)

    # channel_threads
    for ct in CHANNEL_THREADS:
        await conn.execute(
            "INSERT INTO theo.channel_threads (id, channel, external_id, tenant_id, "
            "unit_id, last_message_at) "
            "VALUES ($1, $2, $3, $4, $5, $6)",
            ct["id"], ct["channel"], ct["external_id"], ct["tenant_id"],
            ct["unit_id"], ct["last_message_at"],
        )
    counts["channel_threads"] = len(CHANNEL_THREADS)

    return counts


async def main() -> None:
    print(f"--- seeding from {DATA_DIR} ---")
    async with connect() as conn:
        async with conn.transaction():
            await truncate(conn)
            counts = await insert_all(conn)
            await insert_schornsteinfeger(conn)
    await close_pool()

    print("--- seed complete ---")
    for table, n in counts.items():
        print(f"  {table:18s}  {n}")
    print(f"  schornsteinfeger    1 autonomous ticket + 2 historical + thread + trace")


if __name__ == "__main__":
    asyncio.run(main())
