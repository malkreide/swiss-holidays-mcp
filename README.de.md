[🇬🇧 English Version](README.md)

> 🇨🇭 **Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide)**
>
> Dies ist ein **privates Projekt**. Es ist unabhängig von jeder Arbeitgeberin und jeder institutionellen Zugehörigkeit und stellt keine offizielle Position einer Behörde dar.

# 📅 swiss-school-calendar-mcp

[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![CI](https://github.com/malkreide/swiss-school-calendar-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/malkreide/swiss-school-calendar-mcp/actions)
[![Kein Auth erforderlich](https://img.shields.io/badge/Authentifizierung-nicht%20erforderlich-lightgrey)](https://github.com/malkreide/swiss-school-calendar-mcp)
[![Datenquelle](https://img.shields.io/badge/Daten-OpenHolidays%20%2F%20Nager.Date-green)](https://www.openholidaysapi.org/)

> MCP-Server für **Schulferien und Feiertage** aller 26 Kantone — differenziert nach *Schulart*, was mehr Gewicht hat, als es auf den ersten Blick scheint. Kein API-Key erforderlich.

---

## Übersicht

**swiss-school-calendar-mcp** verschafft KI-Assistenten wie Claude direkten Zugang zu Schweizer Schul- und Feiertagsdaten aller 26 Kantone — ohne API-Key. Schulferien werden kantonal festgelegt, teilweise auf Bezirksebene, und in sechs Kantonen **separat pro Schulart**. Einen nationalen Kalender gibt es nicht; wer über Kantonsgrenzen hinweg plant, öffnet sonst 26 PDF-Seiten.

Der Server deckt zwei thematische Cluster ab: **Schulferien** (mit *Schulart*-Differenzierung) und **Feiertage / lange Wochenenden**. Jedes Cluster bildet eine Gruppe zweckgebauter Tools, die Rohdaten in saubere, provenienz-getaggte JSON-Antworten übersetzen. Alle Daten stammen aus der [OpenHolidays API](https://www.openholidaysapi.org/) (CC BY 4.0) und von [Nager.Date](https://date.nager.at/) (MIT).

> **Eselsbrücke:** *Ein Duplikat in Schweizer Schuldaten ist meistens eine verkleidete Schulart.* Die zugrunde liegende API publiziert dieselbe Ferienperiode mehrfach, sobald ein Kanton nach Schulart differenziert. Das sieht nach doppelten Daten aus und lädt zu naiver Deduplizierung ein — womit man genau jene Unterscheidung zerstört, die eine Schulbehörde braucht.

**Anker-Demo-Abfrage:** *«In welchen Wochen 2026 haben die Volksschulen von Zürich, Zug und Aargau gleichzeitig Ferien — und wie viele Überschneidungstage teilen sich die einzelnen Kantonspaare?»*
→ Diese Frage nutzt `find_common_free_window`, `compare_school_holidays` und `list_school_types` in einer einzigen Konversation und beantwortet eine Frage, die sich in der interkantonalen Koordination jedes Planungsjahr wiederholt.
→ [Weitere Anwendungsbeispiele nach Zielgruppe](EXAMPLES.md) →

---

## Funktionen

- 🏫 **Schulferien** — Perioden pro Kanton und Zeitraum, differenziert nach *Schulart* (`VS` / `MS` / `BS` / `EO`)
- 🎌 **Feiertage** — kantonale Feiertagssätze, nicht nur das eidgenössische Minimum (Berchtoldstag & Co.)
- 🔍 **Datumsprüfung** — ist ein Datum in einem Kanton Schulferien oder Feiertag?
- 🔗 **Interkantonaler Vergleich** — paarweise Überschneidungsmatrix der Ferientage zwischen Kantonen
- 🪟 **Gemeinsame freie Fenster** — Zeiträume, in denen alle genannten Kantone gleichzeitig Ferien haben
- 🌉 **Lange Wochenenden & Brückentage** — berechnet aus eidgenössischen Feiertagen (Nager.Date)
- 🩺 **Quellen-Health** — Erreichbarkeit und Latenz beider Quellen, immer auswertbar
- 🔑 **Keine Authentifizierung nötig** — beide Datenquellen sind öffentlich zugänglich
- ☁️ **Dual Transport** — stdio für Claude Desktop, Streamable HTTP/SSE für Cloud-Deployment
- 🧾 **Provenienz auf jeder Antwort** — `live_api` | `cached` | `degraded`, nie eine stillschweigend leere Liste

---

## Datenquellen

| Quelle | Daten | Lizenz |
|---|---|---|
| [OpenHolidays API](https://www.openholidaysapi.org/) | Kantone, *Schularten*, Schulferien, Feiertage | CC BY 4.0 |
| [Nager.Date](https://date.nager.at/) | Lange Wochenenden und nötige Brückentage | MIT |

Beide Quellen sind öffentlich zugänglich, keine Authentifizierung nötig.
**Attribution erforderlich:** OpenHolidays (CC BY 4.0) und Nager.Date müssen bei Nutzung ihrer Daten als Quelle genannt werden.

---

## Tools

| Tool | Zweck | Datenquelle |
|---|---|---|
| `list_cantons` | Die 26 Kantone mit ISO-Codes und Amtssprachen | OpenHolidays |
| `list_school_types` | *Schulart*-Gruppen pro Kanton (`CH-ZH-VS` usw.) | OpenHolidays |
| `get_school_holidays` | Schulferien für einen Kanton und Zeitraum | OpenHolidays |
| `get_public_holidays` | Feiertage für einen Kanton und ein Jahr | OpenHolidays |
| `check_date` | Ist ein bestimmtes Datum Schulferien oder Feiertag? | OpenHolidays |
| `compare_school_holidays` | Paarweise Überschneidungsmatrix über Kantone | OpenHolidays |
| `find_common_free_window` | Fenster, in denen alle genannten Kantone Ferien haben | OpenHolidays |
| `next_school_holidays` | Die nächsten anstehenden Ferienperioden | OpenHolidays |
| `get_long_weekends` | Lange Wochenenden und nötige Brückentage | Nager.Date |
| `source_status` | Erreichbarkeit und Latenz beider Quellen | Eingebaut |

Alle Tools sind mit `readOnlyHint: true` annotiert. Kein Tool schreibt irgendwohin.

### Beispiel-Abfragen

| Abfrage | Tool |
|---|---|
| *«Welche Kantone gibt es, und wie lauten ihre Codes?»* | `list_cantons` |
| *«Zeige die Volksschulferien von Zürich für Frühling 2026»* | `get_school_holidays` |
| *«Ist der 3. April 2026 im Tessin ein Feiertag?»* | `check_date` |
| *«Überschneiden sich die Schulferien von Zürich und Zug dieses Jahr?»* | `compare_school_holidays` |
| *«Wann können ZH, ZG und AG eine gemeinsame schulfreie Woche planen?»* | `find_common_free_window` |
| *«Was sind die nächsten Ferien der Basler Schulen?»* | `next_school_holidays` |
| *«Welche langen Wochenenden hat 2026, und welche Brückentage brauchen sie?»* | `get_long_weekends` |

---

## 🛡️ Sicherheit & Grenzen

| Aspekt | Details |
|--------|---------|
| **Zugriff** | Nur lesend (`readOnlyHint: true`) — der Server kann keine Daten ändern oder löschen |
| **Personendaten** | Keine Personendaten — alle Quellen sind aggregierte, öffentliche Feiertagskalender |
| **Caching** | 12-Stunden-In-Memory-TTL (Ferientabellen ändern sich wenige Male pro Jahr) |
| **Retry** | Exponentielles Backoff 2s / 4s / 8s; 4xx ausser 429 werden nicht wiederholt |
| **Timeout** | 20 Sekunden pro API-Call (8 Sekunden für Health-Probes) |
| **Authentifizierung** | Kein API-Key nötig — beide Quellen sind öffentlich zugänglich |
| **Degradation** | Ein Upstream-Ausfall liefert einen `degraded`-Envelope mit erklärender `note`, nie eine stillschweigend leere Liste |
| **Nutzungsbedingungen** | Es gelten die ToS der jeweiligen Datenquellen: [OpenHolidays](https://www.openholidaysapi.org/), [Nager.Date](https://date.nager.at/) |

---

## Architektur

Dieser Server nutzt **Architektur A (Live-API only, mit In-Memory-Cache)**.

```
                    ┌──────────────────────────┐
   Claude / jeder ─▶│  swiss-school-calendar   │
   MCP-Host         │  (FastMCP · 10 Tools)    │
                    └────────┬─────────────────┘
                             │  Retry 2s/4s/8s · 12h Cache
                    ┌────────┴─────────┐
                    ▼                  ▼
          OpenHolidays API        Nager.Date
          (CC BY 4.0)             (MIT)
          Kantone · Schularten    Lange Wochenenden
          Schul- + Feiertage      Brückentage
```

**Begründung (live verifiziert am 19.07.2026):**

- Alle zehn dokumentierten OpenHolidays-Endpoints antworteten mit HTTP 200 und plausiblen Nutzdaten; `/Subdivisions?countryIsoCode=CH` liefert exakt 26 Kantone und deckt sich damit mit der amtlichen Zahl.
- Zum Bauzeitpunkt liess sich kein öffentlicher Bulk-Dump verifizieren (Raw-Zugriff auf `openpotato/openholidays.data` ergab 404), Architektur B stand also nicht zur Verfügung.
- Ferientabellen ändern sich wenige Male pro Jahr. Ein TTL von zwölf Stunden nimmt fast die gesamte Upstream-Last weg, ohne Aktualitätsrisiko.

**Konsequenzen:**

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

### Bekannte Befunde

1. **Scheinbare Duplikate sind Schularten.** Zürich liefert die *Frühlingsferien 2026* zweimal: einmal für `CH-ZH-VS` (Volksschulen, mit Tag `Recommended`) und einmal für `CH-ZH-BS` + `CH-ZH-MS` (Berufsfach- und Mittelschulen). Statt zu deduplizieren den Parameter `school_type` verwenden (`VS` / `MS` / `BS` / `EO`).
2. **Nur sechs Kantone differenzieren** nach Schulart (AI, AR, BE, GR, SO, ZH). Sonst fehlt `groups`, und eine Tabelle gilt für alles. Der Filter behandelt ein fehlendes `groups`-Feld deshalb als «gilt für alle».
3. **Subdivision-Codes mischen Ebenen.** Records können `CH-AI-AP` oder `CH-BE-TH-BL` tragen. Immer auf das Präfix `CH-XX` matchen, nie auf Stringgleichheit.
4. **Eine leere Liste ist keine Antwort.** Ein unbekannter Länder- oder Kantonscode ergibt HTTP 200 mit `[]`. Dieser Server setzt eine erklärende `note`, damit «keine Ferien» und «falscher Filter» unterscheidbar bleiben.

---

## Voraussetzungen

- Python 3.10 oder höher
- [uv](https://docs.astral.sh/uv/) / uvx (empfohlen) oder pip
- Internetzugang (beide APIs sind öffentlich)

---

## Installation

Via [`uv`](https://docs.astral.sh/uv/) `uvx` — kein Klonen oder manuelle Installation nötig:

```bash
uvx swiss-school-calendar-mcp
```

### Entwicklung

```bash
git clone https://github.com/malkreide/swiss-school-calendar-mcp
cd swiss-school-calendar-mcp
pip install -e ".[dev]"
```

---

## Konfiguration

### Claude Desktop

In `claude_desktop_config.json` einfügen:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

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

Claude Desktop neu starten — der Server startet beim ersten Aufruf automatisch.

### Cloud-Deployment (SSE / Streamable HTTP für Browser-Zugang)

Für die Nutzung via **claude.ai im Browser** (z.B. auf verwalteten Arbeitsplätzen ohne lokale Software):

```bash
MCP_TRANSPORT=sse PORT=8000 python -m swiss_school_calendar_mcp
```

FastMCP exponiert SSE unter `/sse`, nicht unter `/mcp`.

| Variable | Standard | Beschreibung |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | Transport: `stdio`, `sse`, `streamable-http` (bzw. `http`) |
| `PORT` / `MCP_PORT` | `8000` | Port für HTTP-Transporte |
| `MCP_HOST` | `0.0.0.0` | Bind-Adresse für HTTP-Transporte |

> 💡 *«stdio für den Entwickler-Laptop, SSE für den Browser.»*

---

## Projektstruktur

```
swiss-school-calendar-mcp/
├── src/
│   └── swiss_school_calendar_mcp/
│       ├── __init__.py       # Package-Init
│       ├── __main__.py       # Einstiegspunkt: stdio / SSE / Streamable HTTP
│       ├── server.py         # FastMCP-Server, 10 Tools
│       ├── client.py         # HTTP-Client: Retry, 12h-In-Memory-Cache, Normalisierung
│       ├── constants.py      # Kantonscodes, Schulart-Suffixe, API-Basen
│       └── models.py         # Pydantic-v2-Antwort-Envelopes
├── tests/
│   ├── conftest.py           # respx-Fixtures
│   ├── test_tools.py         # Tool-Unit-Tests (gemockt, kein Netzwerk)
│   ├── test_resilience.py    # Degradation / Retry / Cache-Verhalten
│   └── test_live.py          # Live-Smoke-Tests (Marker: live)
├── .github/
│   ├── dependabot.yml        # Wöchentliche Dependency-/Action-Update-PRs
│   └── workflows/            # ci.yml, live-tests.yml, publish.yml
├── pyproject.toml
├── CHANGELOG.md
├── CONTRIBUTING.md           # Beitragsleitfaden (Englisch)
├── CONTRIBUTING.de.md        # Beitragsleitfaden (Deutsch)
├── SECURITY.md               # Sicherheitsrichtlinie (Englisch)
├── SECURITY.de.md            # Sicherheitsrichtlinie (Deutsch)
├── EXAMPLES.md               # Anwendungsfälle nach Zielgruppe
├── server.json               # MCP-Registry-Manifest
├── LICENSE
├── README.md                 # Englische Version
└── README.de.md              # Diese Datei
```

---

## Lifecycle-Phase

Dieser Server ist in **Phase 1 (nur lesend)** — alle Tools nur lesend, keine
Authentifizierung, keine Seiteneffekte. Das 10-Tool-Budget (vom empfohlenen Maximum
von 15–20) lässt bewusst Spielraum für eine Phase-2-Erweiterung: Stadtzürcher
Besonderheiten wie Sechseläuten und Knabenschiessen, die upstream weder Feiertag
noch Schulferien sind und via [`zurich-opendata-mcp`](https://github.com/malkreide/zurich-opendata-mcp) kämen.

---

## Bekannte Einschränkungen

- **Inoffizielle Quelle.** OpenHolidays aggregiert kantonale Publikationen. Rechtsverbindlich bleibt die kantonale Behörde. Jede Antwort weist darauf hin.
- **Keine kommunale Ebene.** Stadtzürcher Besonderheiten wie Sechseläuten und Knabenschiessen sind upstream weder Feiertag noch Schulferien und deshalb nicht enthalten. Kandidat für Phase 2 über `zurich-opendata-mcp`.
- **Nagers lange Wochenenden ignorieren kantonale Feiertage.** Sie werden nur aus schweizweiten Feiertagen berechnet.
- **Keine garantierte historische Tiefe.** Die Abdeckung vor rund 2020 ist ungleichmässig.

---

## Tests

```bash
# Unit-Tests (kein Netzwerk erforderlich — respx-gemockt)
PYTHONPATH=src pytest tests/ -m "not live"

# Live-Smoke-Tests (gegen die echten Upstream-APIs)
PYTHONPATH=src pytest tests/ -m "live"

# Linting
ruff check src/ tests/
```

---

## Contributing

Beiträge sind willkommen! Lies bitte [CONTRIBUTING.de.md](CONTRIBUTING.de.md) (Deutsch) · [CONTRIBUTING.md](CONTRIBUTING.md) (Englisch) für Hinweise zu Fehlermeldungen, Einrichtung der Entwicklungsumgebung, Code-Stil und Test-Anforderungen.

Dieses Projekt folgt den Konventionen des [Swiss Public Data MCP Portfolios](https://github.com/malkreide).

---

## Sicherheit

Um eine Schwachstelle zu melden, folgen Sie bitte dem Responsible-Disclosure-Prozess in [SECURITY.de.md](SECURITY.de.md) (Deutsch) · [SECURITY.md](SECURITY.md) (Englisch). Der Server ist nur lesend und benötigt keinen API-Key; das Sicherheitsmodell ist im Abschnitt *Sicherheit & Grenzen* oben beschrieben.

---

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

---

## Deployment für Schweizer Behörden

Beim Self-Hosting für ein Schulamt oder eine kommunale Anwendung:

- **Datenresidenz:** Die Anfragen-Pattern selbst (welche Kantone ein:e Sachbearbeiter:in vergleicht) können Rückschlüsse auf laufende Planungen erlauben und gehören auf Schweizer oder vertrauenswürdige Infrastruktur.
- **Upstream-Calls** gehen an OpenHolidays (EU-gehostetes OGD-Projekt) und Nager.Date. Es verlassen keine Personendaten Ihre Umgebung; abgefragt werden nur Feiertagskalender.
- **Logging:** Logs werden auf stderr geschrieben; Aufbewahrungsdauer gemäss Behörden-IT-Richtlinie konfigurieren.
- **HTTP-Transport** sollte hinter einem Reverse Proxy mit Authentifizierung und per-IP-Rate-Limit laufen — der Server hat keine eingebaute Authentifizierung.

---

## Lizenz

MIT-Lizenz — siehe [LICENSE](LICENSE)

Quelldaten unterliegen den Bedingungen von OpenHolidays (CC BY 4.0) und Nager.Date (MIT); bei Nutzung ihrer Daten ist die Attribution dieser Quellen erforderlich.

---

## Autor

Hayal Oezkan · [github.com/malkreide](https://github.com/malkreide)

---

## Credits & Verwandte Projekte

- **Daten:** [OpenHolidays API](https://www.openholidaysapi.org/) (CC BY 4.0) · [Nager.Date](https://date.nager.at/) (MIT)
- **Protokoll:** [Model Context Protocol](https://modelcontextprotocol.io/) — Anthropic / Linux Foundation
- **Gebaut nach** der Methodik `mcp-data-source-probe`: *Live-Probe vor Design, Dump-Fallback vor API-Abhängigkeit, Retry vor Defaitismus.*
- **Portfolio:** [Swiss Public Data MCP Portfolio](https://github.com/malkreide)

| Server | Beschreibung |
|--------|--------------|
| [`zh-education-mcp`](https://github.com/malkreide/zh-education-mcp) | Bildungsdaten des Kantons Zürich |
| [`zurich-opendata-mcp`](https://github.com/malkreide/zurich-opendata-mcp) | Stadt Zürich Open Data |
| [`swiss-statistics-mcp`](https://github.com/malkreide/swiss-statistics-mcp) | BFS STAT-TAB — Schweizer Bundesstatistik |
| [`swisstopo-mcp`](https://github.com/malkreide/swisstopo-mcp) | Schweizer Bundes-Geodaten (swisstopo) |

MIT-lizenziert. Public money, public code.

<!-- mcp-name: io.github.malkreide/swiss-school-calendar-mcp -->
