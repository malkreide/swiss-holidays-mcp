# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Behoben

- **Die Pruefsummen im Fixture-Nachweis waren Zierde.** `PROVENANCE.md` fuehrt
  je Datei einen SHA-256 — um genau einen Fall zu fangen: eine Aufzeichnung,
  die nach dem Lauf von Hand nachgebessert wurde. Eine korrigierte Antwort ist
  wieder eine erfundene, und von aussen ist ihr das nicht anzusehen.
  Nachgerechnet hat sie kein Test. `test_die_pruefsumme_im_nachweis_stimmt`
  tut es jetzt, ueber die Bytes auf der Platte statt ueber den Loader — genau
  die hat der Recorder gehasht.

- **Das Zeitbudget des Retry hatte keinen einzigen Test.** `test_retry_policy.py`
  prüfte ausschliesslich `compute_delay` — eine reine Funktion, die *wie
  schnell* beantwortet und nie *wie lange*. Niemand fuhr die Schleife, also
  waren `RETRY_TOTAL_BUDGET`, der Abbruch vor einem unbezahlbaren Warten und
  die `asyncio.wait_for`-Frist, die das Budget durchsetzt, ungedeckt. Drei
  neue Tests decken sie, je in beide Richtungen:
  `test_das_budget_kuerzt_die_leiter` (mit der Gegenrichtung
  `test_ein_weites_budget_kuerzt_nichts`, sonst bestünde der erste auch auf
  einer kaputten Schleife) und
  `test_eine_langsame_antwort_wird_von_der_wanduhr_geschnitten` — bewusst ohne
  Fake-Uhr, weil die Zusicherung über echte Zeit geht.

  Die erste Fassung von `test_das_budget_kuerzt_die_leiter` zählte nur die
  Versuche und blieb grün, als der Abbruch *vor* dem Warten entfernt wurde —
  der zweite Abbruch fing es auf, und die Versuchszahl kann beide nicht
  unterscheiden. Sie prüft jetzt zusätzlich, dass die Summe der Wartezeiten das
  Budget nicht übersteigt; genau das verspricht der Kommentar in
  `_fetch_with_retry`.

- **Die autouse-Fixture der Resilienz-Tests ersetzte `asyncio.sleep` im ganzen
  Prozess.** `monkeypatch.setattr("swiss_holidays_mcp.client.asyncio.sleep", …)`
  liest sich lokal und ist es nicht: `client.asyncio` **ist** das
  stdlib-Modul. Weil die Fixture `autouse` ist, galt der Ersatz für jeden Test
  der Datei — httpx, respx und anyio eingeschlossen.

  Beide Nahtstellen tragen jetzt einen Namen dieses Moduls, `client._sleep` und
  `client._monotonic`; das ist die Portfolio-Konvention aus `CLAUDE.md` Teil 1.
  Ein Rundgang über die 23 Server im Zugriff fand dieses Repo und
  `swiss-efv-mcp` als die letzten beiden ohne sie.

  Für die Uhr ist das kein Stil, sondern Mechanik: `asyncio` liest
  `time.monotonic` aus demselben Modulobjekt, eine eingefrorene Uhr hält also
  `loop.time()` an — und `asyncio.wait_for`, die Frist des Budgets, wartet dann
  auf einen Moment, der nie kommt. Hier fiel das nicht auf, weil es die Uhr gar
  nicht traf; deshalb liest
  `test_die_beiden_nahtstellen_gehoeren_dem_modul` die Schleife im Quelltext,
  statt sich auf Verhalten zu verlassen. Ein Rückfall auf `asyncio.sleep` macht
  die Datei sonst nur 50× langsamer (0,3 s → 16 s) und meldet nichts.

- **Der Kantonsvergleich rechnete aus einer Antwort, die nur einen Kanton
  führte.** `op_compare_school_holidays` fragt `/SchoolHolidays` **ohne**
  `subdivisionCode` ab — schweizweit — und gruppiert dann *in* der Antwort nach
  Kanton. Aufgezeichnet war nur die kantonale Abfrage
  (`subdivisionCode=CH-ZH`), und der Fixture-Dispatcher ordnete nach URL zu.
  Beim Abspielen bekam der Vergleich damit zehn Zürcher Ferieneinträge und
  meldete für **jedes** Kantonspaar `overlapping_days = 0`:

  ```
  CH-ZH vs CH-BE: overlapping_days=0
  CH-ZH vs CH-VD: overlapping_days=0
  CH-BE vs CH-VD: overlapping_days=0
  ```

  «Keine gemeinsamen Ferientage in der ganzen Schweiz» ist kein Ergebnis,
  sondern eine Aufzeichnung, die zur Abfrage nicht passt — und sie sieht aus
  wie eine gültige Antwort. Es ist dieselbe Klasse Fehler wie ein
  Kürzungsschnitt in einer Liste, in der der Server filtert: der Negativbefund
  entsteht im Testaufbau und ist von einem echten nicht zu unterscheiden.

  Aufgezeichnet ist jetzt auch die schweizweite Abfrageform
  (`school_holidays_all.json`, ungekürzt), und der Dispatcher unterscheidet die
  beiden Formen am gesetzten `subdivisionCode`.
  `test_der_kantonsvergleich_findet_ueberhaupt_ueberschneidungen` fällt, sobald
  wieder aus einer Ein-Kanton-Antwort gerechnet wird;
  `test_die_schweizweite_aufzeichnung_fuehrt_mehr_als_einen_kanton` hält fest,
  dass die zweite Datei überhaupt etwas belegt.

  `ENDPOINTS` führt je Endpunkt jetzt eine **Menge** von Aufzeichnungen. Als
  einzelner Eintrag sah eine zweite Abfrageform aus wie gar keine — daran ist
  diese hier lange unbemerkt geblieben.

### Added

- **Aufgezeichnete Fixtures, eine je externem Endpunkt, mit Nachweis.**
  `tests/fixtures/` haelt jetzt echte Antworten fuer alle sieben Endpunkte der
  beiden Quellen — `/Subdivisions`, `/Groups`, `/PublicHolidays`,
  `/SchoolHolidays` und `/Countries` bei OpenHolidays, `/LongWeekend` und
  `/AvailableCountries` bei Nager.Date. Herkunft, Datum, Auswahlregel und
  SHA-256 stehen je Datei in `tests/fixtures/PROVENANCE.md`, wie im uebrigen
  Portfolio; geladen wird ueber `tests/fixture_data.py`.

  Festes Jahr (2026) und fester Kanton (CH-ZH) mit Absicht: eine Auswahl, die
  vom Zeitpunkt des Laufs abhinge, erzeugte bei jedem Aufzeichnen einen anderen
  Diff. `/Subdivisions` ist auf drei Kantone gekuerzt — ZH tief verschachtelt,
  BS flach, AR ganz ohne `children` —, weil der Vollabzug 399 kB waere; kein
  Feld innerhalb der Datensaetze wurde entfernt.

  Gegenprobe, jede Zusicherung einzeln neutralisiert: Aufnahmedatum entfernt ->
  Datums-Check faellt; Fixture ohne PROVENANCE-Eintrag -> Vollstaendigkeits-Check
  faellt; Aufzeichnung geloescht -> Abdeckungs-Waechter faellt; `name` als String
  statt Sprachliste -> zwei Tests fallen; nur den verschachtelten Kanton
  behalten -> der Subdivisions-Test faellt.

### Fixed

- **The retry had six defects, all inherited from the shared template.** This
  server copied its retry from `reference/retry_backoff.py` in
  [mcp-data-source-probe-skill](https://github.com/malkreide/mcp-data-source-probe-skill),
  and the template shipped these until 2026-08-07. A sweep across eleven
  servers found that none read `Retry-After` and none jittered — one template,
  eleven copies, not eleven independent omissions.
  1. **No jitter.** The ladder was deterministic, so every client that hit the
     same outage retried in lockstep and the load returned as a wave exactly
     when the source recovered — the retry storm extending the outage it was
     meant to bridge. Now spread into `[0.5x, 1.5x]`.
  2. **`Retry-After` was never read.** A 429 or 503 answers the very question
     the backoff curve guesses at. Both RFC 9110 §10.2.3 forms are now read
     (delta-seconds and HTTP-date); an unparseable header yields `None` and
     falls back to the curve — it must never crash on the error path. The
     jitter on top is one-sided `[1.0x, 1.25x]`: the source said *when*, so
     later is polite and earlier ignores the value just read.
  3. **No cap on a single wait**, and the cap now binds *after* the jitter.
     `min(cap, base) * jitter` and `min(cap, base * jitter)` both contain a cap
     and a jitter; only the second is bounded — 20s times 1.5 is 30s.
  4. **The budget counted attempts, not seconds.** Four attempts against an
     upstream that takes 30s to time out is two minutes inside one tool call,
     and an attempt count never says so. Now 25s for the whole call, anchored
     on the MCP SDK's `MCP_DEFAULT_TIMEOUT = 30.0`.
  5. **Nothing held that budget.** It is now an `asyncio.timeout` wall-clock
     deadline rather than an httpx timeout: httpx bounds each *operation*, and
     its read timeout restarts with every chunk, so a slowly trickling response
     outlived the budget without any single read expiring.
  6. **Point six did not apply here, and that is worth saying.** The final
     message is deliberately generic (OBS-002) and the log line already carried
     `type(last_error).__name__` rather than `str(last_error)` — so this server
     never had the empty-`str()` problem that the sibling servers did. The log
     now also names the host and which of the two limits ran out; the message
     stays generic.

  `asyncio.wait_for` rather than `asyncio.timeout`, because this package
  supports Python 3.10 (`requires-python = ">=3.10"`) and `asyncio.timeout`
  needs 3.11. Verified against 3.10 locally.

  New `tests/test_retry_policy.py`: `Retry-After` in both forms plus the
  refusal cases, the jitter spread, that the cap binds after jittering, and the
  one-sided `Retry-After` jitter.

### Changed

- **Migrated to the `mcp` Python SDK 2.x** (`mcp>=2.0.0,<3`, was `>=1.28.1,<2`).
  The floor is hard: the server API moved from `mcp.server.fastmcp` to
  `mcp.server.mcpserver` (`FastMCP` is now `MCPServer`) with no compatibility
  shim, so the package cannot import under 1.x.
- **Transport configuration is per-app, not per-server (SEC-005, SDK-004).**
  `MCPServer.settings` no longer carries `host`, `port` or
  `transport_security`; `_build_http_app` passes the Host/Origin allow-list to
  `streamable_http_app()` / `sse_app()` directly. Pydantic rejects assignment to
  an undefined field, so the old `mcp.settings.transport_security = ...` form
  now raises `ValueError` rather than failing quietly — but only once the HTTP
  path actually runs, which nothing in the suite asserted.

### Added

- **`tests/test_transport_security.py` — inbound Host pinning is now asserted.**
  The pre-existing suite never checked that the SEC-005 allow-list was *active*:
  the CORS tests pass with or without it. The gap is subtle, because dropping
  `transport_security` makes the SDK auto-enable its own localhost default,
  which still rejects an obviously foreign Host. The load-bearing case is a
  right-hostname/wrong-port Host — allowed by the SDK fallback (`127.0.0.1:*`),
  refused by the configured allow-list. Verified by mutation: removing
  `transport_security` fails that test and only that test.

## [0.6.0] — 2026-07-24

Audit-hardening release. Closes all 10 findings from the `mcp-audit` run
(`audits/2026-07-23T140326-Z-swiss-holidays-mcp/`); the final re-audit
(`audits/2026-07-24T091128-Z-swiss-holidays-mcp/`) records **36 pass / 0
partial / 0 fail**, production-ready. No breaking changes.

### Added

- **Client-side DNS pinning (audit SEC-005).** Direct connections now go through
  `PinnedResolverTransport`: each host is resolved once to an SSRF-safe IP
  (`guard.resolve_pinned`) and the TCP connection is pinned to exactly that IP,
  while the `Host` header, TLS SNI and certificate hostname check stay on the
  name — closing the DNS-rebinding TOCTOU window. Skipped behind a forward proxy
  (the proxy owns resolution); the network-layer policy is the control there.
  Verified by a loopback TLS test.
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
- **Single-file `server.py` rationale (audit ARCH-011).** README (both
  languages) now documents why the 13 tools deliberately live in one module
  (thin uniform wrappers over shared `op_*` helpers + one client) — the
  catalogue-accepted justification for the layout, with a `tools/` split planned
  only if Phase 2 grows the tool count materially.

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
