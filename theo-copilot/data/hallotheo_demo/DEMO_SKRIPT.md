# Demo-Skript — "Sarah Webers Dienstagmorgen"

> **Zielzeit:** 5 Min. Jeder Satz hat einen Job. Mit Stoppuhr proben.
> **Sprache:** Demo-UI auf Deutsch, Voiceover/Pitch frei wählbar (English funktioniert für ein Berlin-Hackathon-Publikum gut, falls Team gemischt; rein Deutsch ist aber stärker wenn Jury deutsche Sprecher hat).
> **Setting:** Dienstag, 18. November 2025, 08:00 Uhr. Berlin, Heizperiode aktiv, Frost ab Donnerstag vorhergesagt.

---

## Cold Open (0:00–0:25)

**[Slide: Ein Foto einer angespannten Person am Laptop. Posteingang mit vielen ungelesenen E-Mails sichtbar.]**

> "Sarah Weber verwaltet 75 Einheiten in Berlin als Senior-Verwalterin bei hallo theo. Sie bekommt täglich rund 120 Nachrichten. Eine echte Antwort am selben Tag ist hallo theos Markenversprechen — und Sarah liefert dieses Versprechen, jeden Tag, mit der Plattform und purer Anstrengung."

> "Aber wenn ein Vorgang Reasoning braucht — eine Nebenkostenabrechnung verteidigen, einen chronischen Mangel rechtlich einordnen, eine vage Handwerkerrechnung bewerten — landet diese Arbeit immer noch komplett in Sarahs Kopf."

> "Wir haben einen Reasoning-Layer für hallo theos Plattform gebaut, der genau diese Lücke schließt."

**[Wechsel zum Produkt]**

---

## Akt 1: Das Morgen-Briefing (0:25–1:25)

**[Produkt öffnet sich. Aufgeräumte Begrüßungsansicht.]**

> "Acht Uhr morgens. Sarah öffnet Theo Copilot. Statt einer Wand aus 47 ungelesenen E-Mails sieht sie das hier."

**[Im Produkt: Ein strukturiertes Briefing mit drei Sektionen]**

> "Drei Sachen brauchen heute eine Entscheidung. Zwei Sachen hat Theo Copilot über Nacht erledigt. Ein Muster, das Sarah kennen sollte."

> *Briefing langsam vorlesen:*
> - "Frau Köhler in WE 4 links meldet, dass ihre Heizung wieder ausgefallen ist. Das ist der sechste Vorgang in 18 Monaten. Ich habe etwas Wichtiges für dich gefunden."
> - "Familie Demir hat die Nebenkostenabrechnung 2024 beanstandet. Die Frist läuft am 2. Dezember. Ich habe die Verteidigung schon zusammengestellt."
> - "FixDirekt Berlin hat eine dritte vage Rechnung in sechs Wochen geschickt. Es gibt ein Muster, das du sehen solltest."

> *Pause.*

> "Und über Nacht hat Theo Copilot dem Schornsteinfeger mit Terminvorschlägen aus deinem Kalender geantwortet, und auf die zwei Besichtigungsanfragen für die DG-Wohnung."

> "Sarah hat ihren Posteingang noch nicht geöffnet — und weiß schon, wie ihr Tag aussieht."

---

## Akt 2: Der Heizungs-Moment (1:25–2:55) — DAS HERZSTÜCK

**[Klick auf die Köhler-Sache]**

> "Schauen wir uns die Heizungssache an. Ein klassisches RAG-System würde Frau Köhlers E-Mail ziehen und zusammenfassen. Theo Copilot geht weiter."

**[Das Produkt zeigt eine Reasoning-Trace — visuell, mit Quellen]**

> "Theo Copilot hat sieben verschiedene Quellen verbunden:"
> 1. "Frau Köhlers E-Mail — sechster Vorgang an demselben Heizkörper, sie verweist selbst auf ihre Liste."
> 2. "Die Vorgangshistorie — fünf vorherige Heizungs-Vorgänge, immer dasselbe Bauteil."
> 3. "Bergmanns formelles Angebot von April — Tausch des Thermostatventils, 340 €. Seit sieben Monaten ohne Freigabe vom Eigentümer."
> 4. "Frau Köhlers Mietvertrag — Anlage 3 von Mai 2024: ärztlich bestätigte Kältesensitivität nach Hüft-OP."
> 5. "Berliner Wetterdienst — ab Donnerstag bis Sonntag: Frost, -3°C nachts."
> 6. "Vorgang aus Januar 2025 — Frau Köhler hat damals eine Mietminderung in Höhe von 91,80 € erfolgreich durchgesetzt. Ihre Tochter ist Rechtsanwältin im Mietrecht."
> 7. "Und das hier." **[Slack-Thread markieren]** "Am Freitag um 16:22, dein Team Lead Jonas: 'Wenn sie sich nochmal meldet — für so etwas hast du bis 500 € Vorabgenehmigung von mir. Beauftrage und dokumentier es, ich klär das mit Wegener im Nachgang wenn nötig.'"

> *Pause.*

> "Sarah hatte diese Nachricht gelesen, aber im Wochenende vergessen. Theo Copilot hat sie gefunden."

**[Das Produkt schlägt eine Aktion mit voller Begründung vor]**

> "Theo Copilot schlägt vor: Bergmann sofort für den Tausch beauftragen — der Auftrag ist bereits vorbereitet. Frau Köhler eine vorbereitete Antwort schicken mit konkretem Termin Mittwoch zwischen 09–11 Uhr. Familie Wegener eine kurze Mitteilung als CC, dass die Maßnahme im Rahmen der Vorab-Genehmigung erfolgt ist."

> "Sarah liest. Sarah ändert einen Satz in der Antwort an Frau Köhler — persönlicher Ton. Sarah klickt Bestätigen. Drei Aktionen, neunzig Sekunden. Vorher: 30 Minuten Recherche durch fünf Systeme, danach noch zehn Minuten Texte schreiben."

> **Verbindung zu hallo theo:** "Das adressiert direkt zwei der wiederkehrenden Branchen-Komplaints: 'Mängel werden ignoriert' und 'auf E-Mails wird nicht reagiert'. Hallo theos Plattform hat das Reaktionszeit-Problem schon gelöst. Wir lösen das Reasoning-Problem dahinter."

---

## Akt 3: Die Nebenkostenabrechnungs-Verteidigung (2:55–3:55)

**[Klick auf die Demir-Beanstandung]**

> "Die zweite Sache. Familie Demir hat formell die Nebenkostenabrechnung 2024 beanstandet — Heizkosten 39% höher als im Vorjahr. Ein typischer Vorgang, mit dem deutsche Verwalter:innen Stunden verbringen."

**[Produkt zeigt eine Antwort mit visualisierten Daten]**

> "Theo Copilot hat in acht Sekunden zusammengetragen: die Abrechnung, die Heizkostenverteiler-Werte aus 2023 und 2024, die Brennstoffrechnungen der Berliner Stadtwerke, den BetrKV-Verteilerschlüssel aus dem Mietvertrag."

> "Der Befund: Familie Demirs Verbrauch ist nahezu identisch zu 2023. Sogar minimal niedriger. Aber der Gaspreis war 2024 um 38% höher als 2023. Das ist die Quelle der Differenz."

> "Theo Copilot hat einen Entwurf einer Antwort vorbereitet — höflich, sachlich, mit einer einfachen Vergleichstabelle, die die Demirs sofort verstehen werden."

> "Das Wichtige hier: das ist keine Standardantwort. Das ist eine fundierte rechtssichere Verteidigung der Abrechnung, die sich an dieselben rechtlichen Grundlagen hält wie die Mieter — § 556 BGB, § 7 HKV, BetrKV."

> **Verbindung zu hallo theo:** "Eine Studie von Artz & Partner Rechtsanwälten hat 2022 dokumentiert, dass Nebenkostenabrechnungen im Schnitt um 317 € zu hoch waren. Diese Branche hat ein systematisches Vertrauensproblem. Wir geben Verwalter:innen das Werkzeug, ihre korrekten Abrechnungen schnell und transparent zu verteidigen — und ihre fehlerhaften zu erkennen, bevor sie rausgehen."

---

## Akt 4: Proaktive Finanzkontrolle (3:55–4:25)

**[Klick auf die FixDirekt-Anomalie]**

> "Zum Schluss noch das hier. FixDirekt Berlin hat eine dritte Rechnung über 1.840 € geschickt — 'Renovierung Dachgeschoss, kleinere Reparaturen, sonstige Aufwendungen nach Absprache.' Klingt normal, oder?"

**[Vergleichstabelle auf dem Bildschirm]**

> "Theo Copilot hat unaufgefordert verglichen. Drei FixDirekt-Rechnungen in sechs Wochen, alle über 1.500 €, alle ohne Aufstellung. Vor hallo theos Übernahme waren die Rechnungen desselben Anbieters bei der Voreigentümerin im Schnitt 450 € und detailliert aufgeschlüsselt. Anstieg seit September um 266%."

> "Theo Copilot schlägt keine Anschuldigung vor. Es schlägt vor, höflich eine Belegaufstellung anzufordern, und parallel die Eigentümer-Familie zu informieren, dass eine Prüfung läuft. Saubere, sachliche Eskalation."

> **Verbindung zu hallo theo:** "Bei 9.000 verwalteten Einheiten und 30% Wachstum pro Monat ist das exakt die Art von schleichender finanzieller Leckage, die niemand mehr von Hand auffangen kann. Theo Copilot tut das im Hintergrund, jeden Tag, für jede Eigentümer-Familie."

---

## Schluss (4:25–4:55)

**[Folie zurück zum Anfang. Sarah verlässt das Büro pünktlich um 17:30.]**

> "Sarahs alter Dienstag endete um 19:30, mit zwei Sachen, die durchgerutscht sind. Ihr neuer Dienstag endet um 17:30 — und jede Entscheidung ist dokumentiert mit nachvollziehbarem Reasoning."

> "Wir nennen es Theo Copilot — als Modul für die hallo theo Plattform. Die Komplaints aus deinen eigenen Kundenbewertungen, die durch Prozessdesign allein nicht zu lösen sind, lösen wir durch Reasoning."

> "Danke."

---

## Vorbereitete Q&A

**F: hallo theo hat doch schon KI in der Plattform. Was ist anders?**
A: Wir haben das Marketing dazu gelesen — eure KI ist auf "Buchhaltung und Vorgangsverwaltung" fokussiert. Das ist Automatisierung von Routinen. Was wir bauen ist *Reasoning* über heterogene Daten in Situationen, die ein Verwalter heute noch im Kopf zusammenpuzzeln muss. Das ist eine andere Klasse von Werkzeug, und sie ergänzt sich perfekt mit eurer bestehenden Plattform.

**F: Wie geht ihr mit Halluzination um? Rechtliche Aussagen müssen verlässlich sein.**
A: Zwei Schichten. Erstens: jede Aktion ist von Sarah genehmigt, bevor sie ausgeführt wird — Theo schlägt vor, Sarah entscheidet. Zweitens: jede Empfehlung wird mit klickbarer Quellenangabe zurück auf das Originaldokument unterlegt. Wir optimieren auf *Vertrauen*, nicht auf *Autonomie*. Bei rechtlichen Themen verweisen wir auf den Paragraphen, nicht auf eine Behauptung.

**F: Datenschutz? Mieterdaten sind heikel.**
A: Theo Copilot läuft innerhalb der hallo theo Infrastruktur, nicht als externer Dienst. Es liest dieselben Quellen wie ein menschlicher Verwalter und mit denselben Berechtigungen. Keine Cross-Customer-Datenpoolung. DSGVO-konform by design.

**F: Was kostet das?**
A: Wir denken an ein Per-Einheit-Pricing, etwa im Bereich von 2–4 €/Einheit/Monat. Für hallo theo bei 9.000 Einheiten wären das 18.000–36.000 €/Monat — gegen die Einsparung von ungefähr 3–4 vollen Verwalter-FTEs durch reduzierte Reasoning-Zeit pro Vorgang. Die ROI-Rechnung ist eindeutig.

**F: Wieso sollte hallo theo das nicht selbst bauen?**
A: Sollten sie wahrscheinlich. Wir würden uns freuen, das als Teil von hallo theo zu bauen, statt daneben. Das Hackathon ist die richtige Form für das Gespräch.

**F: Was ist mit WEG vs. Mietverwaltung?**
A: Wir haben heute Mietverwaltung gezeigt — die Reasoning-Patterns für WEG (Eigentümerversammlungs-Vorbereitung, Beschlussvorlage-Generierung, Beirats-Briefings) folgen denselben Prinzipien und sind die nächste Iteration. Auf der Roadmap.

---

## Falls zu lang — was zuerst kürzen

In dieser Reihenfolge:
1. Q&A-Slide-Recap am Ende (einfach präsentieren, nicht zusammenfassen)
2. Den FixDirekt-Abschnitt auf 20 Sek. straffen
3. Die expliziten Quellverweise im NK-Abschnitt kürzen (nur eine nennen)

**NIE kürzen:**
- Den Slack-Moment im Heizungs-Akt (das ist das emotionale Hoch)
- Die Verbindung zu hallo theos eigenen Branchen-Komplaints (das ist das strategische Fundament)
- Das "alte vs. neue Dienstag"-Schluss-Bild (das ist die Kapitalisierung)
