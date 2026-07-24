# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

Audit remediations from the `mcp-audit` run
(`audits/2026-07-23T140326-Z-swiss-holidays-mcp/`).

### Added

- **CORS layer exposing `Mcp-Session-Id` on HTTP transports (audit SDK-004).**
  The HTTP/SSE path now builds the Starlette app in `__main__` and attaches an
  explicit (never wildcard) CORS layer that exposes/allows `Mcp-Session-Id`, so
  a browser MCP client on another origin can read the session id and make
  follow-up requests. New `MCP_CORS_ORIGINS` setting for extra origins.
- **`match_type` on `HolidayListResponse` (audit ARCH-003).** Locality lookups
  now return a structured `exact` / `fuzzy` / `none` marker instead of only a
  free-text note, so a caller can branch on how the query resolved.
- **Structured `<use_case>` / `<important_notes>` tags on all 13 tools
  (audit ARCH-002).**
- **Per-call correlation id + bound tool context in logs (audit OBS-003).**
  Every log line emitted during a tool call now carries `tool=<name> cid=<id>`
  via contextvars (stderr-only preserved).
- **Progress reporting on the network-bound tools (audit SDK-003).**
  `check_date`, `is_holiday_today`, `source_status`, `export_holidays_ics` and
  the `holidays://` resource emit `ctx.report_progress` at their milestones.
- **Network-layer egress manifests (audit SEC-005, SEC-021).**
  `deploy/cilium-egress-fqdn.yaml` (Cilium `toFQDNs`) and
  `deploy/networkpolicy.yaml` complement the code-layer allow-list and close the
  DNS-rebinding TOCTOU residual at the network layer.

### Security

- **OBS-002 — mask unexpected error details.** This `mcp` SDK version (1.28.1)
  has no `mask_error_details` flag; FastMCP surfaces any exception raised in a
  tool to the client as `isError` text. A new `_safe_tool` decorator wraps all
  13 tools: deliberate, user-safe `ValueError` messages (input validation) pass
  through unchanged, while every other exception is logged to stderr only and
  replaced with a generic message — so tracebacks and internal detail (e.g. an
  upstream-schema `KeyError`) never reach the LLM. Covered by two regression
  tests.

### Documentation

- **Session affinity for scaled HTTP (audit SCALE-002).** `docs/scaling.md`
  documents the three deployment tiers and sticky-session examples
  (nginx/Traefik/Kubernetes) for multi-instance HTTP deployments.
- **Two-layer egress model (audit SEC-021).** `docs/network-egress.md` now
  describes the code + network layers and requires both to be updated when the
  allow-list changes.

### Fixed

- **Documentation drift (audit ARCH-011).** `docs/security.md` and
  `docs/roadmap.md` still referred to "10 tools" and roadmap status "v0.2.0";
  corrected to 13 tools / v0.5.0 to match the implementation.

## [0.5.0] — 2026-07-22

Local / municipal holidays. A live probe of OpenHolidays revealed that
sub-cantonal holidays — including the city of Zurich's Sechseläuten and
Knabenschiessen — are already published upstream at Bezirk (district) and
Gemeinde (municipality) level, and that the server was **flattening them onto
the canton**, presenting a city-only holiday as canton-wide.

### Added

- **`get_local_holidays` tool** — public holidays for a single municipality or
  district. Accepts a name (e.g. `"Zürich"`, `"Morschach"`) or a full
  subdivision code (e.g. `"CH-ZH-ZH-ZH"`), resolved against the OpenHolidays
  subdivision tree. Returns every holiday that applies in that locality and
  names the ones specific to it. The server now exposes **13 tools + 1
  resource**.
- **Sub-cantonal fidelity on `HolidayPeriod`** — new fields `scope`
  (`national` / `regional` / `local`, from upstream `regionalScope`), `half_day`
  (upstream `temporalScope`, e.g. Sechseläuten is a half day) and `subdivisions`
  (the precise district/municipality codes + names + level). Every tool that
  returns holidays now carries this, so a locality-specific holiday is no longer
  indistinguishable from a canton-wide one.

### Fixed

- Holidays observed only in one municipality (Sechseläuten, Knabenschiessen,
  Gallustag, …) are no longer reported as if they applied to the whole canton.

## [0.4.0] — 2026-07-21

### Added

- **`export_holidays_ics` tool** — exports a canton's public and/or school
  holidays for a year as an [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545)
  iCalendar (`.ics`) document, ready to import into any calendar app. All-day
  `VEVENT`s with exclusive `DTEND` and `TRANSP:TRANSPARENT`; filterable by
  `include` (`all` / `public` / `school`) and `school_type`. The writer
  (`ical.py`) is hand-rolled, adding no new dependency.
- **`holidays://{canton}/{year}` MCP resource** — a stable URI feed returning a
  Markdown summary of all public + school holidays for a canton and year, so
  clients can read a calendar as cacheable context without a tool call. The
  server now exposes **12 tools + 1 resource**.
- **`is_holiday_today` tool** — one-call convenience answering whether today is a
  school or public holiday in a given canton.

## [0.3.0] — 2026-07-21

### Changed (breaking)

- **Renamed the project `swiss-school-calendar-mcp` → `swiss-holidays-mcp`** and
  repositioned it as a general Swiss holiday calendar (public holidays, school
  holidays and long weekends) rather than a school-authority tool. School
  holidays with *Schulart* differentiation remain a first-class feature.
- The Python package/module is now `swiss_holidays_mcp`; the console script and
  PyPI/registry name are `swiss-holidays-mcp`. Update your client config:
  `uvx swiss-holidays-mcp` and the `mcpServers` key `swiss-holidays`.
- Tools, response models and behaviour are unchanged — this release is a
  rename + reframing only. (The v0.2.0 package was never published to PyPI, so
  no deprecation shim is provided.)

## [0.2.0] — 2026-07-20

Security & best-practice remediation following the 2026-07-20 mcp-audit
(`audits/2026-07-20T184122-Z-…`). Closes the two blocking findings plus the
open architecture/observability findings. MCP protocol version tested against
`2025-06-18`.

### Security

- **SEC-016 (critical):** the HTTP/SSE transport now binds **`127.0.0.1` by
  default**; `MCP_HOST=0.0.0.0` is an explicit opt-in that logs a warning.
- **SEC-004 / SEC-021:** added a code-layer egress guard (`guard.py`) — HTTPS
  enforcement, an immutable two-host `frozenset` allow-list, and an SSRF IP
  blocklist (loopback/private/link-local/cloud-metadata) checked before every
  request. Documented in `docs/network-egress.md`.
- **SEC-005 / SDK-004:** DNS-rebinding protection (Host/Origin allow-list)
  enabled for the HTTP transport.
- **SEC-018:** all tool inputs are schema-validated (canton against the 26 known
  codes, `YYYY-MM-DD` dates, bounded `year`/`count`/`min_days`, whitelisted
  `language`/`school_type`).
- **OBS-002:** raw exception text and upstream bodies are no longer surfaced in
  tool results — only in the stderr log.

### Changed

- **SDK-001 / ARCH-004:** a single `httpx.AsyncClient` and the 12h cache now
  live in the FastMCP **lifespan** and are injected via `Context`, instead of a
  new client per tool call. The cache is now effective across calls.
- Configuration moved to a Pydantic-Settings object (`settings.py`).

### Added

- **OBS-003:** structured logging to stderr (`logging_setup.py`).
- **SEC-007:** non-root multi-stage `Dockerfile`.
- **OPS-003 / ARCH-012 / ARCH-008 / CH-006:** `docs/roadmap.md`,
  `docs/security.md`, `docs/network-egress.md`; README sections on MCP
  primitives, protocol version and data classification.
- **ARCH-009:** full tool annotations (`destructiveHint`, `idempotentHint`,
  `openWorldHint`) on every tool.
- GitHub Actions CI (matrix 3.10/3.11/3.12, ruff, `ruff format --check`,
  `pip-audit`), nightly live-tests, PyPI trusted-publisher workflow, Dependabot,
  `.gitignore`, CI badge (from the prior CI PR).
- Dependency: `pydantic-settings>=2.2`; `mcp` pinned to `>=1.2.0,<2`.
- Packaging: the sdist excludes `audits/`, `docs/` and `.github/`
  (161 KB → 40 KB); the wheel is unchanged.

## [0.1.0] — 2026-07-19

### Added

- Ten read-only tools covering Swiss school and public holidays for all 26 cantons.
- Dual transport: stdio (Claude Desktop) and SSE / Streamable HTTP (cloud).
- Pydantic v2 response envelope carrying `source`, `provenance` and `retrieved_at`.
- Retry with exponential backoff (2s / 4s / 8s); 4xx except 429 are not retried.
- Graceful degradation: upstream failure returns a `degraded` envelope with an
  explanatory note instead of an empty list.
- `source_status` health tool for both upstream sources.

### Known findings (live probe, 2026-07-19)

- **Apparent duplicates are school types.** Six cantons (AI, AR, BE, GR, SO, ZH)
  publish the same holiday period once per *Schulart*. Zurich uses `CH-ZH-VS`
  (Volksschulen, tagged `Recommended`), `CH-ZH-MS` (Mittelschulen) and
  `CH-ZH-BS` (Berufsfachschulen). Naive de-duplication destroys exactly the
  distinction a school authority needs. Handled via the `school_type` filter.
  *Mnemonic: a duplicate in Swiss school data is usually a school type in disguise.*
- **An empty list is not an answer.** An unknown `countryIsoCode` or canton code
  returns HTTP 200 with `[]` rather than a 404. Responses now carry an
  explanatory `note` so that "no holidays" and "bad filter" stay distinguishable.
- **Silent language fallback.** An unsupported `languageIsoCode` silently falls
  back to EN. Languages are therefore validated locally before the request.
- **Mixed subdivision levels.** Records may carry sub-cantonal codes such as
  `CH-AI-AP` or `CH-BE-TH-BL`. Matching is done on the `CH-XX` prefix.
- **No verified public bulk dump** at build time, hence Architecture A rather
  than the portfolio's more common Architecture B.
