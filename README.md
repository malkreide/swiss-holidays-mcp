> 🇨🇭 **Part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide)**
>
> This is a **private project**. It is independent of any employer or institutional affiliation and represents no official position of any authority.

# 📅 swiss-holidays-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![CI](https://github.com/malkreide/swiss-holidays-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/malkreide/swiss-holidays-mcp/actions)
[![No Auth Required](https://img.shields.io/badge/auth-not%20required-lightgrey)](https://github.com/malkreide/swiss-holidays-mcp)
[![Data Source](https://img.shields.io/badge/Data-OpenHolidays%20%2F%20Nager.Date-green)](https://www.openholidaysapi.org/)

> A **Swiss holiday calendar** for AI agents — **public holidays, school holidays and long weekends** for all 26 cantons, with cross-cantonal comparison. School holidays are differentiated by *Schulart* (school type), which matters more than it first appears. No API key required.

[🇩🇪 Deutsche Version](README.de.md)

---

## Overview

**swiss-holidays-mcp** is a Swiss holiday calendar for AI assistants like Claude — **public holidays, school holidays and long weekends** for all 26 cantons, no API keys required. Public holidays are cantonal (Berchtoldstag, Fronleichnam & co. differ by canton, not just the federal minimum). School holidays are set cantonally, sometimes at district level, and — in six cantons — **separately per school type**. A single federal calendar does not exist; anyone planning across cantonal borders is otherwise reduced to opening 26 PDF pages.

The server covers two thematic clusters: **public holidays / long weekends** and **school holidays** (with *Schulart* differentiation). Each cluster maps to a group of purpose-built tools that translate raw agency data into clean, provenance-tagged JSON responses. All data comes from the [OpenHolidays API](https://www.openholidaysapi.org/) (CC BY 4.0) and [Nager.Date](https://date.nager.at/) (MIT).

> **Mnemonic:** *A duplicate in Swiss school data is usually a school type in disguise.* The underlying API publishes the *same* holiday period several times when a canton differentiates by school type. That looks like duplicated data and invites naive de-duplication — which would destroy exactly the distinction a school authority needs.

**Anchor demo query:** *"In which weeks of 2026 are the compulsory schools of Zurich, Zug and Aargau simultaneously on holiday — and how many overlapping days does each pair share?"*
→ This exercises `find_common_free_window`, `compare_school_holidays` and `list_school_types` in a single conversation, and answers a question that recurs every planning cycle in inter-cantonal coordination.
→ [More use cases by audience](EXAMPLES.md) →

---

## Features

- 🏫 **School holidays** — periods per canton and date range, differentiated by *Schulart* (`VS` / `MS` / `BS` / `EO`)
- 🎌 **Public holidays** — cantonal holiday sets, not just the federal minimum (Berchtoldstag & friends)
- 🔍 **Date check** — is a given date a school or public holiday in a canton?
- 🔗 **Cross-cantonal comparison** — pairwise overlap matrix of holiday days between cantons
- 🪟 **Common free windows** — date ranges where all listed cantons are simultaneously on holiday
- 🌉 **Long weekends & bridge days** — computed from federal public holidays (Nager.Date)
- 🏘️ **Local & municipal holidays** — district- and municipality-level specifics such as Zurich's Sechseläuten and Knabenschiessen, with a `scope` marker so they are never mistaken for canton-wide
- 📆 **iCal / ICS export** — a canton's holidays for a year as a ready-to-import `.ics` calendar
- 🔖 **Holiday feed resource** — `holidays://<canton>/<year>` MCP resource with a Markdown summary
- 📌 **"Is today a holiday?"** — one-call convenience for the everyday question
- 🩺 **Source health** — reachability and latency of both upstreams, always evaluable
- 🔑 **No authentication required** — both data sources are publicly accessible
- ☁️ **Dual transport** — stdio for Claude Desktop, Streamable HTTP/SSE for cloud deployment
- 🧾 **Provenance on every response** — `live_api` | `cached` | `degraded`, never a silent empty list

---

## Data Sources

| Source | Data | Licence |
|---|---|---|
| [OpenHolidays API](https://www.openholidaysapi.org/) | Cantons, *Schularten*, school holidays, public holidays | CC BY 4.0 |
| [Nager.Date](https://date.nager.at/) | Long weekends and required bridge days | MIT |

Both sources are publicly accessible, no authentication required.
**Attribution required:** OpenHolidays (CC BY 4.0) and Nager.Date must be cited as the source when using their data.

---

## Tools

| Tool | Purpose | Data Source |
|---|---|---|
| `list_cantons` | The 26 cantons with ISO codes and official languages | OpenHolidays |
| `list_school_types` | *Schulart* groups per canton (`CH-ZH-VS` etc.) | OpenHolidays |
| `get_school_holidays` | School holidays for one canton and date range | OpenHolidays |
| `get_public_holidays` | Public holidays for one canton and year | OpenHolidays |
| `get_local_holidays` | Public holidays for one municipality or district, incl. local specifics | OpenHolidays |
| `check_date` | Is a given date a school or public holiday? | OpenHolidays |
| `compare_school_holidays` | Pairwise overlap matrix across cantons | OpenHolidays |
| `find_common_free_window` | Windows where all listed cantons are on holiday | OpenHolidays |
| `next_school_holidays` | The next upcoming holiday periods | OpenHolidays |
| `get_long_weekends` | Long weekends and required bridge days | Nager.Date |
| `export_holidays_ics` | A canton's holidays for a year as an iCalendar (`.ics`) document | OpenHolidays |
| `is_holiday_today` | Is today a school or public holiday in a canton? | OpenHolidays |
| `source_status` | Reachability and latency of both upstreams | Built-in |

### Resources

| Resource URI | Content |
|---|---|
| `holidays://{canton}/{year}` | Markdown summary of all public + school holidays, e.g. `holidays://CH-ZH/2026` |

All tools carry the full annotation set — `readOnlyHint: true`, `destructiveHint: false`, `idempotentHint: true`, `openWorldHint: true` (they reach an external API). No tool writes anywhere. Inputs are schema-validated (canton codes against the 26 known cantons, dates as `YYYY-MM-DD`, `year` bounded, `language`/`school_type` whitelisted).

### Example Use Cases

| Query | Tool |
|---|---|
| *"Which cantons are there, and what are their codes?"* | `list_cantons` |
| *"Show Zurich's compulsory-school holidays for spring 2026"* | `get_school_holidays` |
| *"Is 3 April 2026 a public holiday in Ticino?"* | `check_date` |
| *"Do Zurich and Zug school holidays overlap this year?"* | `compare_school_holidays` |
| *"When can all of ZH, ZG, AG plan a joint week off school?"* | `find_common_free_window` |
| *"What are the next holidays for Basel-Stadt schools?"* | `next_school_holidays` |
| *"Which long weekends does 2026 have, and which bridge days do they need?"* | `get_long_weekends` |
| *"Which local holidays does the city of Zurich keep that the rest of the canton doesn't?"* | `get_local_holidays` |
| *"Export Zurich's 2026 holidays as an .ics calendar I can import"* | `export_holidays_ics` |
| *"Is today a holiday in Aargau?"* | `is_holiday_today` |

---

## 🛡️ Safety & Limits

| Aspect | Details |
|--------|---------|
| **Access** | Read-only (`readOnlyHint: true`) — the server cannot modify or delete any data |
| **Personal data** | No personal data — all sources are aggregated, public holiday calendars |
| **Caching** | 12-hour in-memory TTL (holiday tables change a handful of times per year) |
| **Retry** | Exponential backoff 2s / 4s / 8s; 4xx except 429 are not retried |
| **Timeout** | 20 seconds per API call (8 seconds for health probes) |
| **Authentication** | No API keys required — both upstreams are publicly accessible |
| **Degradation** | Upstream failure yields a `degraded` envelope with an explanatory `note`, never a silent empty list |
| **Terms of Service** | Subject to the ToS of the respective data sources: [OpenHolidays](https://www.openholidaysapi.org/), [Nager.Date](https://date.nager.at/) |

---

## Architecture

This server uses **Architecture A (live API only, with in-memory cache)**.

```
                    ┌──────────────────────────┐
   Claude / any ───▶│  swiss-holidays-mcp      │
   MCP host         │  (FastMCP · 13 tools)    │
                    └────────┬─────────────────┘
                             │  retry 2s/4s/8s · 12h cache
                    ┌────────┴─────────┐
                    ▼                  ▼
          OpenHolidays API        Nager.Date
          (CC BY 4.0)             (MIT)
          cantons · Schularten    long weekends
          school + public         bridge days
```

**Rationale (verified live on 2026-07-19):**

- All ten documented OpenHolidays endpoints answered HTTP 200 with plausible payloads; `/Subdivisions?countryIsoCode=CH` returns exactly 26 cantons, matching the official count.
- No public bulk dump could be verified at build time (`openpotato/openholidays.data` raw access returned 404), so Architecture B was not available.
- Holiday tables change a handful of times per year, so a 12-hour in-memory TTL removes almost all upstream load without risking staleness.

**Consequences:**

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

## Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) / uvx (recommended) or pip
- Internet access (both APIs are publicly available)

---

## Installation

Run via [`uv`](https://docs.astral.sh/uv/)'s `uvx` — no clone or manual install needed:

```bash
uvx swiss-holidays-mcp
```

### Development

```bash
git clone https://github.com/malkreide/swiss-holidays-mcp
cd swiss-holidays-mcp
pip install -e ".[dev]"
```

---

## Configuration

### Claude Desktop

Add to `claude_desktop_config.json`:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "swiss-holidays": {
      "command": "uvx",
      "args": ["swiss-holidays-mcp"]
    }
  }
}
```

Restart Claude Desktop — the server starts automatically on first use.

### Cloud Deployment (SSE / Streamable HTTP for browser access)

For use via **claude.ai in the browser** (e.g. on managed workstations without local software):

```bash
MCP_TRANSPORT=sse PORT=8000 python -m swiss_holidays_mcp
```

FastMCP exposes SSE at `/sse`, not `/mcp`.

| Variable | Default | Description |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | Transport: `stdio`, `sse`, `streamable-http` (aka `http`) |
| `PORT` / `MCP_PORT` | `8000` | Port for HTTP transports |
| `MCP_HOST` | `127.0.0.1` | Bind address for HTTP transports. Loopback by default; `0.0.0.0` is opt-in and logs a warning — run behind an authenticating reverse proxy. |
| `MCP_CORS_ORIGINS` | *(empty)* | Comma-separated extra CORS origins for browser clients (audit SDK-004). Loopback origins are always allowed; add the public origin your UI is served from, e.g. `https://ui.example.ch`. Never `*`. |

The HTTP transports attach an explicit CORS layer that exposes the
`Mcp-Session-Id` header, so a browser MCP client can read the session id and
make follow-up requests. The allow-list is never a wildcard.

Running **more than one HTTP instance** behind a load balancer requires sticky
sessions keyed on `Mcp-Session-Id` — see [`docs/scaling.md`](docs/scaling.md)
for nginx/Traefik/Kubernetes examples. A single instance (the common case) needs
no affinity configuration.

> 💡 *"stdio for the developer laptop, SSE for the browser."*

---

## Project Structure

```
swiss-holidays-mcp/
├── src/
│   └── swiss_holidays_mcp/
│       ├── __init__.py       # Package init
│       ├── __main__.py       # Entry point: stdio / SSE / Streamable HTTP
│       ├── server.py         # FastMCP server: lifespan, 13 tools, 1 resource, op_* logic
│       ├── client.py         # Shared HTTP client: retry, 12h cache, egress guard
│       ├── guard.py          # Egress / SSRF guard (HTTPS + allow-list + IP blocklist)
│       ├── ical.py           # RFC 5545 iCalendar (.ics) writer
│       ├── settings.py       # Pydantic-Settings config (loopback default)
│       ├── logging_setup.py  # Structured logging to stderr
│       ├── constants.py      # Canton codes, Schulart suffixes, API bases, allow-list
│       └── models.py         # Pydantic v2 response envelopes
├── tests/
│   ├── conftest.py           # respx fixtures
│   ├── test_tools.py         # Tool unit tests (mocked, no network)
│   ├── test_resilience.py    # Degradation / retry / cache behaviour
│   └── test_live.py          # Live smoke tests (marker: live)
├── docs/                     # roadmap.md, security.md, network-egress.md
├── deploy/                   # Network-layer egress manifests (Cilium / NetworkPolicy)
├── audits/                   # mcp-audit run artifacts
├── Dockerfile                # Non-root multi-stage container
├── .github/
│   ├── dependabot.yml        # Weekly dependency / action update PRs
│   └── workflows/            # ci.yml, live-tests.yml, publish.yml
├── pyproject.toml
├── CHANGELOG.md
├── CONTRIBUTING.md           # Contributing guide (English)
├── CONTRIBUTING.de.md        # Contributing guide (German)
├── SECURITY.md               # Security policy (English)
├── SECURITY.de.md            # Security policy (German)
├── EXAMPLES.md               # Use cases by audience
├── server.json               # MCP registry manifest
├── LICENSE
├── README.md                 # This file (English)
└── README.de.md              # German version
```

---

## Lifecycle Phase

This server is in **Phase 1 (read-only)** — all tools read-only, no auth, no side
effects. The 13-tool budget (of the 15–20 recommended maximum) still leaves
headroom. Local and municipal specifics — including Zurich's Sechseläuten and
Knabenschiessen — are covered directly from OpenHolidays via `get_local_holidays`
(a live probe showed they are published upstream at Gemeinde level), so no
separate city data source is required for them.

---

## MCP Primitives & Protocol Version

- **Primitives — Tools + Resources.** The 13 tools are idempotent,
  side-effect-free `GET`s. A **Resource** exposes a stable URI feed
  (`holidays://<canton>/<year>`) so clients can read a canton's calendar as
  cacheable context without a tool call. There are no recurring templated
  workflows, so **Prompts** are not used (revisited if that changes).
- **MCP protocol version.** Built and tested against protocol version
  `2025-06-18` (pinned as `MCP_PROTOCOL_VERSION` and surfaced by `source_status`).
  The wire version is negotiated by the pinned `mcp` SDK (`mcp>=1.2.0,<2`).
- **Update policy.** SDK and dependency bumps land via Dependabot (weekly);
  protocol-version or tool-definition changes are recorded in
  [`CHANGELOG.md`](CHANGELOG.md) with a version bump.

## Data classification

All data is **Öffentlich / Public Open Data** — aggregated holiday calendars,
no personal data (DSG/DSGVO). This is the highest classification the server
handles; the full model is in [`docs/security.md`](docs/security.md).

## Known Limitations

- **Unofficial source.** OpenHolidays aggregates cantonal publications. For legally binding dates, the cantonal authority remains authoritative. Every response says so.
- **Municipal coverage depends on the upstream.** OpenHolidays does carry district- and municipality-level public holidays (e.g. Sechseläuten, Knabenschiessen at `CH-ZH-ZH-ZH`), exposed through `get_local_holidays`. Completeness at Gemeinde level is only as good as the upstream data, which varies by canton. Municipal *school* holidays are not separately modelled.
- **Nager long weekends ignore cantonal holidays.** They are computed from nationwide holidays only.
- **No historical depth guarantee.** Coverage of years before roughly 2020 is uneven.

---

## Testing

```bash
# Unit tests (no network required — respx-mocked)
PYTHONPATH=src pytest tests/ -m "not live"

# Live smoke tests (hits the real upstream APIs)
PYTHONPATH=src pytest tests/ -m "live"

# Linting
ruff check src/ tests/
```

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) (English) · [CONTRIBUTING.de.md](CONTRIBUTING.de.md) (German) for guidelines on reporting bugs, setting up the development environment, code style and test requirements.

This project follows the conventions of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide).

---

## Security

To report a vulnerability, please follow the responsible disclosure process in [SECURITY.md](SECURITY.md) (English) · [SECURITY.de.md](SECURITY.de.md) (German). The server is read-only and requires no API key; see the *Safety & Limits* section above for the security model.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

---

## Deployment for Swiss Public Administration

If you self-host this server for a Swiss school authority or municipal use case:

- **Data residency:** the query patterns themselves (which cantons a civil servant compares) may reveal ongoing planning and are best kept on Swiss or trusted infrastructure.
- **Upstream calls** go to OpenHolidays (EU-hosted OGD project) and Nager.Date. No personal data leaves your environment; only holiday calendars are requested.
- **Logging:** logs are written to stderr; configure your IT retention policy accordingly.
- **HTTP transport** should run behind a reverse proxy with authentication and per-IP rate limits — the server has no built-in authentication.

---

## License

MIT License — see [LICENSE](LICENSE)

Source data is subject to the terms of OpenHolidays (CC BY 4.0) and Nager.Date (MIT); attribution to these sources is required when using their data.

---

## Author

Hayal Oezkan · [github.com/malkreide](https://github.com/malkreide)

---

## Credits & Related Projects

- **Data:** [OpenHolidays API](https://www.openholidaysapi.org/) (CC BY 4.0) · [Nager.Date](https://date.nager.at/) (MIT)
- **Protocol:** [Model Context Protocol](https://modelcontextprotocol.io/) — Anthropic / Linux Foundation
- **Built following** the `mcp-data-source-probe` methodology: *live probe before design, dump fallback before API dependency, retry before defeatism.*
- **Portfolio:** [Swiss Public Data MCP Portfolio](https://github.com/malkreide)

| Server | Description |
|--------|-------------|
| [`zh-education-mcp`](https://github.com/malkreide/zh-education-mcp) | Canton of Zurich education data |
| [`zurich-opendata-mcp`](https://github.com/malkreide/zurich-opendata-mcp) | City of Zurich Open Data |
| [`swiss-statistics-mcp`](https://github.com/malkreide/swiss-statistics-mcp) | BFS STAT-TAB — Swiss federal statistics |
| [`swisstopo-mcp`](https://github.com/malkreide/swisstopo-mcp) | Swiss federal geodata (swisstopo) |

MIT licensed. Public money, public code.

<!-- mcp-name: io.github.malkreide/swiss-holidays-mcp -->
