# Wo Fletcher sein Wissen aufbewahrt

> *Für nicht-technische Leser — Verwalter:innen, Eigentümer, Geschäftsführung.
> Für Engineering-Details siehe [docs/architecture.md](./architecture.md).*

Fletcher führt sein Wissen in **drei getrennten Speichern**. Jeder Speicher
beantwortet eine andere Frage. Wenn ein neues Ticket reinkommt, fragt Fletcher
alle drei nacheinander.

```
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│  L1 — Regelbuch     │  │  L2 — Aktenschrank  │  │  L3 — Gedächtnis    │
│  „Was gilt?"        │  │  „Was ist gerade?"  │  │  „Was wissen wir    │
│                     │  │                     │  │   über diese Person?"│
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

---

## L1 — Das Regelbuch

> *"Was sind die Regeln, Gesetze, internen Richtlinien?"*

Hier liegen die Dinge, die für alle Mieter und alle Häuser gleich gelten und
sich selten ändern.

**Beispiele:**

- **Mietrechtsgesetze:** BGB § 535 (Erhaltungspflicht), § 536 (Mietminderung),
  § 556 (Nebenkostenabrechnung), BetrKV (welche Betriebskosten umlegbar sind)
- **Interne Richtlinien:** Reaktionszeiten im Heizungsnotfall (4 h),
  Eskalations­schwellen, Belegprüfungs-Regeln
- **Antwortvorlagen:** Bestätigung Mängelmeldung, Anfrage nach Belegen,
  Terminbestätigungen

**Wie es genutzt wird:** Wenn Fletcher eine Antwort entwirft, schlägt er
diese Texte nach und zitiert die passenden Paragrafen wörtlich — er
*erfindet keine Rechtsverweise*, sondern verweist nur auf das, was hier
geschrieben steht.

**Technik (Stichworte für Q&A):** Markdown-Dateien im Repository,
durchsucht mit BM25 (Volltextsuche).

---

## L2 — Der Aktenschrank

> *"Welche Häuser, Mieter, Verträge, Tickets und Rechnungen gibt es —
> jetzt, in diesem Moment?"*

Hier liegen alle harten Fakten der laufenden Verwaltung — die Dinge, die
man auch ohne Fletcher in einer Excel-Tabelle führen könnte, nur eben in
einer richtigen Datenbank.

**Beispiele:**

- **Objekte und Wohneinheiten:** Zossener Str. 47, WE 4 links, 68 qm,
  Familie Wegener als Eigentümer
- **Mieter und Verträge:** Frau Köhler, seit 1997, Kaltmiete 612 €,
  medizinische Anlage zum Vertrag (Anlage 3)
- **Tickets:** alle früheren Vorgänge — z. B. die 5 Heizungs-Reparaturen
  bei Frau Köhler in 18 Monaten mit Datum, Kosten, Bergmann-Notizen
- **Rechnungen und Angebote:** Bergmann-Angebot für 372 € seit April
  unbearbeitet; FixDirekt-Rechnungen 1.840 €
- **Nachrichten:** WhatsApp- und E-Mail-Verläufe, interner Slack-Chat
  zwischen Sarah und Jonas

**Wie es genutzt wird:** Beim Öffnen eines Tickets zeigt Fletcher
*augenblicklich* die Mieter-Karte, den Vertragsstand, frühere Vorgänge.
Keine Suche, kein Wechsel ins andere System.

**Technik:** PostgreSQL-Datenbank mit ~15 Tabellen — strukturiert wie
ein klassisches CRM/PMS.

---

## L3 — Das Gedächtnis

> *"Was haben wir im Lauf der Zeit über diese Person, dieses Haus,
> diesen Handwerker gelernt?"*

Das ist der entscheidende Unterschied zu allem, was es bisher gibt. Hier
liegen keine Fakten, sondern **gelernte Muster**. Fletcher liest jede
neue Nachricht und jeden neuen Vorgang und extrahiert daraus
selbstständig dauerhafte Aussagen.

**Beispiele dessen, was hier — und nur hier — steht:**

> *„Frau Köhler hat nach ihrer Hüft-OP eine erhöhte Empfindlichkeit
> gegenüber Raumtemperaturen unter 19 °C — gültig seit 18.05.2024."*

> *„Der Wohnzimmer-Heizkörper in WE 4 links zeigt seit 18 Monaten ein
> wiederkehrendes Versagen — gleiche Ursache (Thermostatventil)."*

> *„Anja Köhler vertritt rechtlich ihre Mutter Margarethe Köhler."*

> *„Bergmann hat im April 2025 ein Angebot eingereicht — seit 7 Monaten
> ohne Freigabe."*

Diese Aussagen sind nirgendwo *direkt* gespeichert. Niemand hat sie
eingetippt. Fletcher hat sie aus den Texten der Vorgänge selbst
abgeleitet und im Gedächtnis abgelegt — mit Quellenangabe, sodass jede
Aussage später zurück auf den Ursprungstext zeigt.

**Wie es genutzt wird:** Wenn Fletcher Frau Köhlers heutige Heizungs­
meldung sieht, kennt er sofort *die ganze Geschichte* — nicht nur das
aktuelle Ticket. Das ist die „Mustererkennung", die die Verwalterin
sonst nur durch jahrelange Erfahrung mit dem Mieter aufbauen würde.

**Technik:** Wissensgraph in Neo4j, kontinuierlich gepflegt von einer
spezialisierten Memory-Komponente (Graphiti). Jede Aussage hat einen
Gültigkeits­zeitraum *(„gilt seit X"; „ungültig ab Y")* und Quellen.

---

## Wie die drei zusammenarbeiten

**Konkretes Beispiel:** Frau Köhler schickt heute Abend eine WhatsApp:
*"Die Heizung im Wohnzimmer geht schon wieder nicht."*

Innerhalb von Sekunden fragt Fletcher:

1. **L2 (Aktenschrank):** „Wer ist diese Telefonnummer?" → Margarethe Köhler,
   WE 4 links, Vertrag seit 1997, Bergmann-Angebot offen.
2. **L3 (Gedächtnis):** „Was wissen wir über diese Mieterin?" → 5 frühere
   Heizungs­vorgänge, eine erfolgreiche Mietminderung im Februar, post-OP-
   Empfindlichkeit, Tochter ist Anwältin.
3. **L1 (Regelbuch):** „Was schreibt das Gesetz hier vor?" → BGB § 535,
   Reaktionszeit 4 h in der Heizperiode.
4. **L2 erneut:** „Gibt es interne Vorab-Genehmigungen?" → Ja, Jonas
   Petersen hat letzten Freitag 500 € vorab freigegeben.

Erst aus der Kombination dieser drei Speicher entsteht der Vorschlag,
den die Verwalterin sieht — mit Quellenangabe zu jeder einzelnen
Behauptung.

---

## Warum drei statt einer Datenbank?

| Frage | Speicher | Warum getrennt? |
|---|---|---|
| Was sind die Regeln? | L1 | Selten geändert, oft gelesen — Versionierung wie ein Buch. |
| Was ist der aktuelle Stand? | L2 | Muss exakt, transaktional, prüfbar sein — klassische Datenbank. |
| Was haben wir gelernt? | L3 | Muss Muster über Zeit erkennen — dafür ist ein Graph gebaut. |

Jeder Speicher tut, wofür er konstruiert ist. Würde man alles in eine
Datenbank stopfen, würde Fletcher entweder bei den Regeln versagen,
beim Aktenschrank verstopfen, oder im Gedächtnis stumm bleiben.

---

## Datenschutz und Kontrolle

- **L1** enthält keine Mieterdaten. Es ist allgemein.
- **L2** enthält die Daten, die in jeder normalen Hausverwaltungs-Software
  liegen — geschützt nach gleicher Praxis.
- **L3** enthält *abgeleitete* Aussagen über Mieter und Häuser. Diese
  werden auf Wunsch genauso gelöscht wie die Originaldaten (Recht auf
  Vergessen-werden gemäß DSGVO).

Fletcher führt nichts im Verborgenen: jede Empfehlung kommt mit der
Quelle, jede Quelle ist auffindbar, jede Aussage ist nachvollziehbar.
