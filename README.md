> **Part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide/swiss-public-data-mcp)** — a collection of open-source MCP servers connecting AI agents to Swiss public and open data.
>
> This is a **private project**. It is independent of any employer or institutional affiliation and represents no official position of any authority.

# swiss-school-calendar-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-orange.svg)](https://modelcontextprotocol.io/)
[![Deutsch](https://img.shields.io/badge/Doku-Deutsch-red.svg)](README.de.md)

MCP server for Swiss **school holidays and public holidays** across all 26 cantons — differentiated by *Schulart* (school type), which matters more than it first appears.

---

## 🎯 Anchor demo query

> *«In which weeks of 2026 are the compulsory schools of Zurich, Zug and Aargau simultaneously on holiday — and how many overlapping days does each pair share?»*

This exercises `find_common_free_window`, `compare_school_holidays` and `list_school_types` in a single conversation, and answers a question that recurs every planning cycle in inter-cantonal coordination.

---

## Why this server exists

Swiss school holidays are set cantonally, sometimes at district level, and — in six cantons — **separately per school type**. A federal calendar does not exist. Anyone planning across cantonal borders is currently reduced to opening 26 PDF pages.

More subtly: the underlying API publishes the *same* holiday period several times when a canton differentiates by school type. That looks like duplicated data and invites naive de-duplication — which would destroy exactly the distinction a school authority needs.

> **Mnemonic:** *A duplicate in Swiss school data is usually a school type in disguise.*

---

## Architecture decision

This server uses **Architecture A (live API only, with in-memory cache)**.

Rationale (verified live on 2026-07-19):

- All ten documented OpenHolidays endpoints answered HTTP 200 with plausible payloads; `/Subdivisions?countryIsoCode=CH` returns exactly 26 cantons, matching the official count.
- No public bulk dump could be verified at build time (`openpotato/openholidays.data` raw access returned 404), so Architecture B was not available.
- Holiday tables change a handful of times per year, so a 12-hour in-memory TTL removes almost all upstream load without risking staleness.

Consequences:

- Every response carries `provenance` (`live_api` | `cached` | `degraded`).
- Upstream failure yields a `degraded` envelope with an explanatory `note`, never a silent empty list.
- `source_status` always returns an evaluable health report.

---

## Live-probe findings (2026-07-19)

| Endpoint | HTTP | Status | Records | Note |
|---|---|---|---|---|
| `/Countries` | 200 | ✅ works | 36 | |
| `/Subdivisions?countryIsoCode=CH` | 200 | ✅ works | 26 | matches official canton count |
| `/Groups?countryIsoCode=CH` | 200 | ✅ works | 11 | *Schulart* groups, only 6 cantons |
| `/PublicHolidays` (CH, 2026) | 200 | ✅ works | 39 | cantonal scope included |
| `/SchoolHolidays` (CH, 2026) | 200 | ✅ works | 193 | 183 distinct after school-type split |
| `/SchoolHolidaysByDate` | 200 | ✅ works | – | |
| `/SchoolHolidays?countryIsoCode=XX` | 200 | ⚠️ silently empty | 0 | invalid country ≠ error |
| `/Subdivisions?languageIsoCode=ZZ` | 200 | ⚠️ silent EN fallback | 26 | invalid language ≠ error |
| `/SchoolHolidays` without date range | 400 | ✅ correct error | – | RFC 9110 problem+json |
| Nager `/PublicHolidays/2026/CH` | 200 | ✅ works | 33 | 29 rows carry `counties` |
| Nager `/LongWeekend/2026/CH` | 200 | ✅ works | 3 | |
| Nager `/PublicHolidays/2026/XX` | 404 | ✅ correct error | – | stricter than OpenHolidays |

### Known findings

1. **Apparent duplicates are school types.** Zurich returns *Frühlingsferien 2026* twice: once for `CH-ZH-VS` (Volksschulen, tagged `Recommended`) and once for `CH-ZH-BS` + `CH-ZH-MS` (Berufsfach- and Mittelschulen). Use the `school_type` parameter (`VS` / `MS` / `BS` / `EO`) rather than de-duplicating.
2. **Only six cantons differentiate** by school type (AI, AR, BE, GR, SO, ZH). Elsewhere `groups` is absent and one table covers everything. The filter therefore treats an absent `groups` field as "applies to all".
3. **Subdivision codes mix levels.** Records may carry `CH-AI-AP` or `CH-BE-TH-BL`. Always match on the `CH-XX` prefix, never on string equality.
4. **An empty list is not an answer.** An unknown country or canton code yields HTTP 200 with `[]`. This server sets an explanatory `note` so that "no holidays" and "bad filter" stay distinguishable.

---

## Tools

| Tool | Purpose |
|---|---|
| `list_cantons` | The 26 cantons with ISO codes and official languages |
| `list_school_types` | *Schulart* groups per canton (`CH-ZH-VS` etc.) |
| `get_school_holidays` | School holidays for one canton and date range |
| `get_public_holidays` | Public holidays for one canton and year |
| `check_date` | Is a given date a school or public holiday? |
| `compare_school_holidays` | Pairwise overlap matrix across cantons |
| `find_common_free_window` | Windows where all listed cantons are on holiday |
| `next_school_holidays` | The next upcoming holiday periods |
| `get_long_weekends` | Long weekends and required bridge days |
| `source_status` | Reachability and latency of both upstreams |

All tools are annotated `readOnlyHint: true`. No tool writes anywhere.

---

## Architecture

```
                    ┌──────────────────────────┐
   Claude / any ───▶│  swiss-school-calendar   │
   MCP host         │  (FastMCP, 10 tools)     │
                    └────────┬─────────────────┘
                             │  retry 2s/4s/8s · 12h cache
                    ┌────────┴─────────┐
                    ▼                  ▼
          OpenHolidays API        Nager.Date
          (CC BY 4.0)             (MIT)
          cantons · Schularten    long weekends
          school + public         bridge days
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

FastMCP exposes SSE at `/sse`, not `/mcp`.

---

## Testing

```bash
PYTHONPATH=src pytest tests/ -m "not live"   # offline, respx-mocked
PYTHONPATH=src pytest tests/ -m live         # hits the real API
```

---

## Known limitations

- **Unofficial source.** OpenHolidays aggregates cantonal publications. For legally binding dates, the cantonal authority remains authoritative. Every response says so.
- **No municipal layer.** Zurich city specifics such as Sechseläuten and Knabenschiessen are neither public holidays nor school holidays upstream, and are therefore absent. Candidate for Phase 2 via `zurich-opendata-mcp`.
- **Nager long weekends ignore cantonal holidays.** They are computed from nationwide holidays only.
- **No historical depth guarantee.** Coverage of years before roughly 2020 is uneven.

---

## Credits & related projects

- Data: [OpenHolidays API](https://www.openholidaysapi.org/) (CC BY 4.0), [Nager.Date](https://date.nager.at/) (MIT)
- Portfolio: [`zh-education-mcp`](https://github.com/malkreide/zh-education-mcp), [`swiss-statistics-mcp`](https://github.com/malkreide/swiss-statistics-mcp), [`swisstopo-mcp`](https://github.com/malkreide/swisstopo-mcp)
- Built following the `mcp-data-source-probe` methodology: *live probe before design, dump fallback before API dependency, retry before defeatism.*

MIT licensed. Public money, public code.
