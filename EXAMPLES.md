# Use Cases & Examples — swiss-holidays-mcp

Real-world queries by audience.

### 🏫 Bildung & Schule
Schulleitungen, Lehrpersonen, Schulverwaltungen, interkantonale Koordination

**Interkantonale Ferienüberschneidung planen**
«In welchen Wochen 2026 haben die Volksschulen von Zürich, Zug und Aargau gleichzeitig Ferien — und wie viele Überschneidungstage teilen sich die einzelnen Kantonspaare?»
→ `find_common_free_window(cantons=["CH-ZH", "CH-ZG", "CH-AG"], year=2026, school_type="VS")`
→ `compare_school_holidays(cantons=["CH-ZH", "CH-ZG", "CH-AG"], year=2026)`
Warum nützlich: Schulverwaltungen sehen auf einen Blick, wann gemeinsame Projektwochen, Lager oder Weiterbildungen über Kantonsgrenzen hinweg möglich sind, ohne 26 PDF-Ferienpläne abzugleichen. (Kein API-Key nötig)

**Die richtige Schulart erwischen**
«Zeige die Frühlingsferien 2026 der Zürcher Mittelschulen — nicht der Volksschulen.»
→ `list_school_types(canton="CH-ZH")`
→ `get_school_holidays(canton="CH-ZH", valid_from="2026-03-01", valid_to="2026-05-31", school_type="MS")`
Warum nützlich: Sechs Kantone publizieren separate Ferienpläne pro Schulart. Der `school_type`-Filter verhindert, dass scheinbare «Duplikate» (dieselbe Periode für eine andere Schulart) falsch interpretiert werden. (Kein API-Key nötig)

### 👨‍👩‍👧 Eltern & Schulgemeinde
Eltern, Elternräte, Erziehungsberechtigte

**Elternabend auf einen schulfreien Tag legen — oder gerade nicht**
«Ist der 3. April 2026 in Basel-Stadt ein Schul- oder Feiertag?»
→ `check_date(check_date_iso="2026-04-03", canton="CH-BS")`
Warum nützlich: Eltern und Schulen können Anlässe verlässlich planen, ohne im Kantonskalender zu blättern — die Antwort unterscheidet klar zwischen Schulferien und öffentlichem Feiertag. (Kein API-Key nötig)

**Nächste Ferien im Blick behalten**
«Wann sind die nächsten Schulferien für die Volksschulen im Kanton Bern?»
→ `next_school_holidays(canton="CH-BE", count=3, school_type="VS")`
Warum nützlich: Familien planen Reisen und Betreuung frühzeitig und sehen die drei kommenden Ferienperioden auf einen Blick. (Kein API-Key nötig)

### 🗳️ Bevölkerung & öffentliches Interesse
Allgemeine Öffentlichkeit, Vereine, Veranstalter

**Lange Wochenenden und Brückentage finden**
«Welche langen Wochenenden hat 2026 in der Schweiz, und welche Brückentage brauchen sie?»
→ `get_long_weekends(year=2026)`
Warum nützlich: Vereine, Veranstalter und Privatpersonen erkennen sofort, wann sich mit einem einzelnen Brückentag ein langes Wochenende ergibt. (Kein API-Key nötig)

**Kantonale Feiertage vergleichen**
«Welche Feiertage gelten 2026 im Kanton Tessin — und wie unterscheiden sie sich vom Kanton Zürich?»
→ `get_public_holidays(canton="CH-TI", year=2026)`
→ `get_public_holidays(canton="CH-ZH", year=2026)`
Warum nützlich: Feiertage wie Berchtoldstag oder Fronleichnam gelten nur in bestimmten Kantonen — der Vergleich macht diese Unterschiede transparent statt sie unter das eidgenössische Minimum zu subsumieren. (Kein API-Key nötig)

### 🤖 KI-Interessierte & Entwickler:innen
MCP-Enthusiast:innen, öffentliche Verwaltung, Prompt Engineers

**Verfügbarkeit und Provenienz prüfen (Robustheit)**
«Sind beide Datenquellen gerade erreichbar, und wie aktuell sind die Antworten?»
→ `source_status()`
Warum nützlich: Jede Antwort trägt `provenance` (`live_api` / `cached` / `degraded`); `source_status` liefert einen auswertbaren Health-Report, sodass Automationen «keine Daten» von «Quelle nicht erreichbar» unterscheiden können. (Kein API-Key nötig)

**Multi-Server-Planung**
«Finde die gemeinsamen schulfreien Wochen von ZH und ZG für 2026 und schlage über den `zurich-opendata-mcp` (https://github.com/malkreide/zurich-opendata-mcp) passende städtische Anlässe in dieser Zeit vor.»
→ `find_common_free_window(cantons=["CH-ZH", "CH-ZG"], year=2026, school_type="VS")`
Warum nützlich: Der Schulkalender liefert das Zeitfenster, ein zweiter Portfolio-Server die passenden lokalen Angebote — kombinierbar zu einem durchgängigen Planungsassistenten. (Kein API-Key nötig)

### 🔧 Technische Referenz: Tool-Auswahl nach Anwendungsfall

| Ich möchte… | Tool(s) | Auth nötig? |
|-------------|---------|-------------|
| die 26 Kantone samt ISO-Codes auflisten | `list_cantons` | Nein |
| wissen, welche Schularten ein Kanton separat führt | `list_school_types` | Nein |
| Schulferien für Kanton + Zeitraum abrufen | `get_school_holidays` | Nein |
| Feiertage für Kanton + Jahr abrufen | `get_public_holidays` | Nein |
| prüfen, ob ein Datum Schul-/Feiertag ist | `check_date` | Nein |
| die Ferienüberschneidung zwischen Kantonen messen | `compare_school_holidays` | Nein |
| gemeinsame schulfreie Fenster mehrerer Kantone finden | `find_common_free_window` | Nein |
| die nächsten Ferienperioden eines Kantons sehen | `next_school_holidays` | Nein |
| lange Wochenenden und Brückentage berechnen | `get_long_weekends` | Nein |
| die Erreichbarkeit der Datenquellen prüfen | `source_status` | Nein |
