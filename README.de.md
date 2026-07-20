> **Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide/swiss-public-data-mcp)** — einer Sammlung von Open-Source-MCP-Servern, die KI-Agenten mit Schweizer Behörden- und Open-Data-Quellen verbinden.
>
> Dies ist ein **privates Projekt**. Es ist unabhängig von jeder Arbeitgeberin und jeder institutionellen Zugehörigkeit und stellt keine offizielle Position einer Behörde dar.

# swiss-school-calendar-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-orange.svg)](https://modelcontextprotocol.io/)
[![English](https://img.shields.io/badge/Docs-English-blue.svg)](README.md)

MCP-Server für **Schulferien und Feiertage** aller 26 Kantone — differenziert nach Schulart, was mehr Gewicht hat, als es auf den ersten Blick scheint.

---

## 🎯 Anchor Demo Query

> *«In welchen Wochen 2026 haben die Volksschulen von Zürich, Zug und Aargau gleichzeitig Ferien — und wie viele Überschneidungstage teilen sich die einzelnen Kantonspaare?»*

Diese Frage nutzt `find_common_free_window`, `compare_school_holidays` und `list_school_types` in einer einzigen Konversation und beantwortet eine Frage, die sich in der interkantonalen Koordination jedes Planungsjahr wiederholt.

---

## Warum dieser Server

Schulferien werden kantonal festgelegt, teilweise auf Bezirksebene, und in sechs Kantonen **separat pro Schulart**. Einen nationalen Kalender gibt es nicht. Wer über Kantonsgrenzen hinweg plant, öffnet heute 26 PDF-Seiten.

Subtiler: Die zugrunde liegende API publiziert dieselbe Ferienperiode mehrfach, sobald ein Kanton nach Schulart differenziert. Das sieht nach doppelten Daten aus und lädt zu naiver Deduplizierung ein — womit man genau jene Unterscheidung zerstört, die eine Schulbehörde braucht.

> **Eselsbrücke:** *Ein Duplikat in Schweizer Schuldaten ist meistens eine verkleidete Schulart.*

---

## Architektur-Entscheid

Dieser Server nutzt **Architektur A (Live-API only, mit In-Memory-Cache)**.

Begründung (live verifiziert am 19.07.2026):

- Alle zehn dokumentierten OpenHolidays-Endpoints antworteten mit HTTP 200 und plausiblen Nutzdaten; `/Subdivisions?countryIsoCode=CH` liefert exakt 26 Kantone und deckt sich damit mit der amtlichen Zahl.
- Zum Bauzeitpunkt liess sich kein öffentlicher Bulk-Dump verifizieren (Raw-Zugriff auf `openpotato/openholidays.data` ergab 404), Architektur B stand also nicht zur Verfügung.
- Ferientabellen ändern sich wenige Male pro Jahr. Ein TTL von zwölf Stunden nimmt fast die gesamte Upstream-Last weg, ohne Aktualitätsrisiko.

Konsequenzen:

- Jede Antwort trägt `provenance` (`live_api` | `cached` | `degraded`).
- Ein Upstream-Ausfall liefert einen `degraded`-Envelope mit erklärender `note` — nie eine stillschweigend leere Liste.
- `source_status` gibt immer einen auswertbaren Statusbericht zurück.

---

## Live-Probe-Befunde (19.07.2026)

| Endpoint | HTTP | Status | Records | Bemerkung |
|---|---|---|---|---|
| `/Countries` | 200 | ✅ funktioniert | 36 | |
| `/Subdivisions?countryIsoCode=CH` | 200 | ✅ funktioniert | 26 | deckt sich mit amtlicher Kantonszahl |
| `/Groups?countryIsoCode=CH` | 200 | ✅ funktioniert | 11 | Schulart-Gruppen, nur 6 Kantone |
| `/PublicHolidays` (CH, 2026) | 200 | ✅ funktioniert | 39 | inkl. kantonaler Geltung |
| `/SchoolHolidays` (CH, 2026) | 200 | ✅ funktioniert | 193 | 183 distinkt nach Schulart-Split |
| `/SchoolHolidaysByDate` | 200 | ✅ funktioniert | – | |
| `/SchoolHolidays?countryIsoCode=XX` | 200 | ⚠️ stillschweigend leer | 0 | ungültiges Land ≠ Fehler |
| `/Subdivisions?languageIsoCode=ZZ` | 200 | ⚠️ stiller EN-Fallback | 26 | ungültige Sprache ≠ Fehler |
| `/SchoolHolidays` ohne Datumsbereich | 400 | ✅ korrekter Fehler | – | RFC 9110 problem+json |
| Nager `/PublicHolidays/2026/CH` | 200 | ✅ funktioniert | 33 | 29 Zeilen mit `counties` |
| Nager `/LongWeekend/2026/CH` | 200 | ✅ funktioniert | 3 | |
| Nager `/PublicHolidays/2026/XX` | 404 | ✅ korrekter Fehler | – | strenger als OpenHolidays |

### Known findings

1. **Scheinbare Duplikate sind Schularten.** Zürich liefert die *Frühlingsferien 2026* zweimal: einmal für `CH-ZH-VS` (Volksschulen, mit Tag `Recommended`) und einmal für `CH-ZH-BS` + `CH-ZH-MS` (Berufsfach- und Mittelschulen). Statt zu deduplizieren den Parameter `school_type` verwenden (`VS` / `MS` / `BS` / `EO`).
2. **Nur sechs Kantone differenzieren** nach Schulart (AI, AR, BE, GR, SO, ZH). Sonst fehlt `groups`, und eine Tabelle gilt für alles. Der Filter behandelt ein fehlendes `groups`-Feld deshalb als «gilt für alle».
3. **Subdivision-Codes mischen Ebenen.** Records können `CH-AI-AP` oder `CH-BE-TH-BL` tragen. Immer auf das Präfix `CH-XX` matchen, nie auf Stringgleichheit.
4. **Eine leere Liste ist keine Antwort.** Ein unbekannter Länder- oder Kantonscode ergibt HTTP 200 mit `[]`. Dieser Server setzt eine erklärende `note`, damit «keine Ferien» und «falscher Filter» unterscheidbar bleiben.

---

## Tools

| Tool | Zweck |
|---|---|
| `list_cantons` | Die 26 Kantone mit ISO-Codes und Amtssprachen |
| `list_school_types` | Schulart-Gruppen pro Kanton (`CH-ZH-VS` usw.) |
| `get_school_holidays` | Schulferien für einen Kanton und Zeitraum |
| `get_public_holidays` | Feiertage für einen Kanton und ein Jahr |
| `check_date` | Ist ein bestimmtes Datum Schulferien oder Feiertag? |
| `compare_school_holidays` | Paarweise Überschneidungsmatrix über Kantone |
| `find_common_free_window` | Fenster, in denen alle genannten Kantone Ferien haben |
| `next_school_holidays` | Die nächsten anstehenden Ferienperioden |
| `get_long_weekends` | Lange Wochenenden und nötige Brückentage |
| `source_status` | Erreichbarkeit und Latenz beider Quellen |

Alle Tools sind mit `readOnlyHint: true` annotiert. Kein Tool schreibt irgendwohin.

---

## Architektur

```
                    ┌──────────────────────────┐
   Claude / jeder ─▶│  swiss-school-calendar   │
   MCP-Host         │  (FastMCP, 10 Tools)     │
                    └────────┬─────────────────┘
                             │  Retry 2s/4s/8s · 12h Cache
                    ┌────────┴─────────┐
                    ▼                  ▼
          OpenHolidays API        Nager.Date
          (CC BY 4.0)             (MIT)
          Kantone · Schularten    Lange Wochenenden
          Schul- + Feiertage      Brückentage
```

---

## Installation

```bash
uvx swiss-school-calendar-mcp
```

### Claude Desktop

```json
{
  "mcpServers": {
    "swiss-school-calendar": {
      "command": "uvx",
      "args": ["swiss-school-calendar-mcp"]
    }
  }
}
```

### Cloud (Render / Railway)

```bash
MCP_TRANSPORT=sse PORT=8000 python -m swiss_school_calendar_mcp
```

FastMCP exponiert SSE unter `/sse`, nicht unter `/mcp`.

---

## Testing

```bash
PYTHONPATH=src pytest tests/ -m "not live"   # offline, respx-gemockt
PYTHONPATH=src pytest tests/ -m live         # gegen die echte API
```

---

## Bekannte Einschränkungen

- **Inoffizielle Quelle.** OpenHolidays aggregiert kantonale Publikationen. Rechtsverbindlich bleibt die kantonale Behörde. Jede Antwort weist darauf hin.
- **Keine kommunale Ebene.** Stadtzürcher Besonderheiten wie Sechseläuten und Knabenschiessen sind upstream weder Feiertag noch Schulferien und deshalb nicht enthalten. Kandidat für Phase 2 über `zurich-opendata-mcp`.
- **Nagers lange Wochenenden ignorieren kantonale Feiertage.** Sie werden nur aus schweizweiten Feiertagen berechnet.
- **Keine garantierte historische Tiefe.** Die Abdeckung vor rund 2020 ist ungleichmässig.

---

## Credits & verwandte Projekte

- Daten: [OpenHolidays API](https://www.openholidaysapi.org/) (CC BY 4.0), [Nager.Date](https://date.nager.at/) (MIT)
- Portfolio: [`zh-education-mcp`](https://github.com/malkreide/zh-education-mcp), [`swiss-statistics-mcp`](https://github.com/malkreide/swiss-statistics-mcp), [`swisstopo-mcp`](https://github.com/malkreide/swisstopo-mcp)
- Gebaut nach der Methodik `mcp-data-source-probe`: *Live-Probe vor Design, Dump-Fallback vor API-Abhängigkeit, Retry vor Defaitismus.*

MIT-lizenziert. Public money, public code.
