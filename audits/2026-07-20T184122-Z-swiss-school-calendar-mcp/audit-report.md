# MCP-Server Audit-Report — `swiss-school-calendar-mcp`

**Audit-Datum:** 2026-07-20
**Skill-Version:** 1.0.0
**Catalog-Version:** 091f446b2796 (SHA-256 der checks/)

---

## 1. Executive Summary

Server `swiss-school-calendar-mcp` wurde gegen 35 anwendbare Best-Practice-Checks geprüft. 14 bestanden, 21 Findings dokumentiert (2 critical, 11 high, 8 medium, 0 low). Production-Readiness: NICHT erreicht — blockierend: SDK-001, SEC-016.

**Production-Readiness:** NO

---

## 2. Profil-Snapshot

| Feld | Wert |
|---|---|
| Server-Name | `swiss-school-calendar-mcp` |
| Audit-Datum | 2026-07-20 |
| Skill-Version | 1.0.0 |
| Catalog-Version | 091f446b2796 |

---

## 3. Applicability

### Status pro Kategorie

| Kategorie | Pass | Fail | Partial | Todo | N/A |
|---|---|---|---|---|---|
| ARCH | 3 | 2 | 6 | 0 | 0 |
| CH | 1 | 0 | 1 | 0 | 0 |
| OBS | 2 | 1 | 1 | 0 | 0 |
| OPS | 2 | 0 | 1 | 0 | 0 |
| SCALE | 0 | 0 | 0 | 0 | 1 |
| SDK | 1 | 1 | 2 | 0 | 0 |
| SEC | 5 | 1 | 5 | 0 | 1 |
| **Total** | **14** | **5** | **16** | **0** | **2** |

---

## 4. Findings-Übersicht

_Policy: `fail-or-partial`_

| ID | Category | Severity | Status |
|---|---|---|---|
| SEC-004 | SEC | critical | partial |
| SEC-016 | SEC | critical | fail |
| ARCH-004 | ARCH | high | partial |
| ARCH-009 | ARCH | high | partial |
| CH-006 | CH | high | partial |
| OBS-002 | OBS | high | partial |
| OPS-003 | OPS | high | partial |
| SDK-001 | SDK | high | fail |
| SDK-004 | SDK | high | partial |
| SEC-005 | SEC | high | partial |
| SEC-007 | SEC | high | partial |
| SEC-018 | SEC | high | partial |
| SEC-021 | SEC | high | partial |
| ARCH-002 | ARCH | medium | partial |
| ARCH-003 | ARCH | medium | partial |
| ARCH-007 | ARCH | medium | partial |
| ARCH-008 | ARCH | medium | fail |
| ARCH-011 | ARCH | medium | partial |
| ARCH-012 | ARCH | medium | fail |
| OBS-003 | OBS | medium | fail |
| SDK-003 | SDK | medium | partial |

**Gesamt:** 21 Findings

---

## 5. Detail-Findings

### ARCH-002

## Finding: ARCH-002 — Tool-Beschreibung mit Use-Case-Tags

**Severity:** medium
**Status:** partial
**Server:** swiss-school-calendar-mcp
**Check-Reference:** ARCH-002
**Check-Status:** partial

### Observed Behavior
Tool descriptions are decent multi-sentence docstrings with prose context and explicit differentiation, but contain no structured <use_case>/<important_notes> tags, and at least one tool (next_school_holidays) is a single terse sentence.

### Expected Behavior
Use-case tag (or equivalent structured section) present in >=80% of tools; caveats/limitations surfaced in-description; every tool >= 100 chars with clear differentiation.

### Evidence
- Descriptions are multi-sentence docstrings well above the 100-char median threshold — e.g. server.py:181-193 (get_school_holidays) and server.py:174-193 with Args block
- Differentiation between similar tools is explicit: get_school_holidays vs get_public_holidays vs next_school_holidays each state their distinct purpose (server.py:174-193, :224-229, :421-424)
- No <use_case> / <important_notes> / <example> XML tags anywhere in src/ — use-case info is embedded as prose only, and some tools have minimal framing (next_school_holidays docstring is a single sentence, server.py:424)

### Gaps
- No structured use_case/important_notes tags in any of the 10 tools (0% vs required 80%)
- next_school_holidays has only a one-sentence description with no use-case or caveat framing

### Risk Description
Weaker semantic separation at tool-selection time; the LLM has less structured signal to disambiguate the several holiday-lookup tools, mildly raising wrong-tool-selection risk.

### Remediation
Add a short structured use-case/important-notes block (tags or a consistent 'Use when: ... Do not use for: ...' convention) to each docstring; expand next_school_holidays with use-case and the VS default caveat.

### Effort Estimate
S


### ARCH-003

## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

**Severity:** medium
**Status:** partial
**Server:** swiss-school-calendar-mcp
**Check-Reference:** ARCH-003
**Check-Status:** partial

### Observed Behavior
Empty results are wrapped in a structured envelope (no bare [] or 'No results' string), and get_school_holidays adds a helpful note; but there is no match_type field, no fuzzy/suggestion fallback, and only one tool carries an explanatory empty note.

### Expected Behavior
Non-sensitive search tools surface a match_type field (exact/fuzzy/none) and provide fuzzy matches or actionable suggestions on empty results; empty-result notes present consistently across search tools.

### Evidence
- The bare-[] / 'No results found' anti-pattern is avoided: empty results return a structured Pydantic envelope with count=0 and an explanatory note — server.py:207-220 (get_school_holidays sets note explaining an unknown canton code yields an empty list, not an error)
- No match_type field (exact/fuzzy/none) on any response model — models.py:67-69 (HolidayListResponse has only count + holidays)
- No fuzzy-match or suggestion mechanism anywhere; other tools return empty lists silently without the explanatory note (e.g. list_school_types canton filter server.py:162-170; compare_school_holidays server.py:339-359)

### Gaps
- No match_type/match-quality field on responses
- No fuzzy fallback or suggestion mechanism for empty results
- Explanatory note is only implemented in get_school_holidays, not in the other search-style tools

### Risk Description
On a mistyped canton code or an off-range date the model receives an empty list from most tools with no guidance, increasing the chance it hallucinates a holiday or dead-ends instead of correcting the query.

### Remediation
Add a match_type field to the response envelope and populate it; extend the explanatory-note pattern (already in get_school_holidays) to the other list/search tools; optionally suggest valid canton codes on empty results.

### Effort Estimate
M


### ARCH-004

## Finding: ARCH-004 — Inversion of Control: Transport-agnostische Server-Logik

**Severity:** high
**Status:** partial
**Server:** swiss-school-calendar-mcp
**Check-Reference:** ARCH-004
**Check-Status:** partial

### Observed Behavior
Handlers are cleanly transport-agnostic and dual transport works via MCP_TRANSPORT, but configuration uses ad-hoc os.environ.get in __main__.py rather than a typed Settings object, and there is no shared lifespan (the HTTP client is instantiated per tool call).

### Expected Behavior
Configuration centralised in a Pydantic-Settings object; shared setup (HTTP client) provided via lifespan/DI rather than per-call construction.

### Evidence
- Tool handlers are transport-agnostic: none access request/headers/websocket/stdin/stdout — all take plain typed args (server.py:104-503), so stdio and SSE produce identical results
- Dual transport selectable via ENV: __main__.py:11-20 reads MCP_TRANSPORT and dispatches to stdio / sse / streamable-http
- Config is read via raw os.environ.get, not a Pydantic BaseSettings object, and mcp is a module-global: __main__.py:16-17 (mcp.settings.host/port from os.environ) and server.py:43 (mcp = FastMCP(...) global); no BaseSettings/Settings class anywhere in src/

### Gaps
- No Pydantic-Settings (or equivalent) settings object; configuration is scattered os.environ.get calls
- No shared lifespan/setup; HolidayClient is created per-call via `async with HolidayClient()` (server.py:112 etc.) rather than injected

### Risk Description
Config drift and untyped env parsing (e.g. int(PORT)) can fail at runtime; per-call client construction forgoes connection reuse. Low correctness risk here (server is transport-agnostic) but weaker testability and config discipline.

### Remediation
Introduce a BaseSettings class for transport/host/port; move the HTTP client into a FastMCP lifespan and inject it, so tools do not construct a client per call.

### Effort Estimate
M


### ARCH-007

## Finding: ARCH-007 — Capability-Aggregation: Composability intern, Atomarität extern

**Severity:** medium
**Status:** partial
**Server:** swiss-school-calendar-mcp
**Check-Reference:** ARCH-007
**Check-Status:** partial

### Observed Behavior
Tools are well-aggregated and atomic from the LLM's perspective (no ID-chaining), but check_date fetches school and public holidays sequentially instead of with asyncio.gather.

### Expected Behavior
Where a tool issues multiple independent upstream calls, use asyncio.gather to parallelise them.

### Evidence
- Tools return self-contained, thought-complete results rather than IDs/pointers requiring follow-up calls — every tool returns a full Pydantic envelope (models.py:59-129); no getXId->getXDetails chaining exists
- Internal aggregation is present: check_date combines school + public holiday lookups (server.py:268-303); compare_school_holidays builds a pairwise overlap matrix internally (server.py:330-359)
- asyncio.gather / parallel fetch is never used; check_date issues its two upstream fetches sequentially (server.py:269-274: await school_holidays then await public_holidays)

### Gaps
- check_date performs two sequential awaits that could run in parallel via asyncio.gather

### Risk Description
Minor added latency on check_date (two round-trips serialised); no correctness impact.

### Remediation
Wrap the school_holidays and public_holidays fetches in check_date in a single asyncio.gather.

### Effort Estimate
S


### ARCH-008

## Finding: ARCH-008 — Drei Primitive nutzen: Tools, Resources und Prompts

**Severity:** medium
**Status:** open
**Server:** swiss-school-calendar-mcp
**Check-Reference:** ARCH-008
**Check-Status:** fail

### Observed Behavior
The server is Tools-only (10 tools) with no Resources or Prompts, and the READMEs contain no section justifying the tools-only choice.

### Expected Behavior
Use at least two of the three MCP primitives, or document in the README why tools-only is appropriate for this phase; evaluate static read-only tools (list_cantons, list_school_types) for Resource migration.

### Evidence
- Server exposes Tools only — no @mcp.resource or @mcp.prompt registrations anywhere in src/ (server.py defines 10 @mcp.tool and nothing else)
- No documented justification for tools-only: grep for resource/prompt/primitive across README.md and README.de.md returns zero matches
- Several tools are static, idempotent, side-effect-free read-only lookups that are strong Resource candidates — list_cantons (server.py:104-133) and list_school_types (server.py:136-170) return near-static reference data

### Gaps
- Neither of the two-primitives-minimum options is satisfied: no Resources/Prompts and no README rationale for tools-only

### Risk Description
Tool-manifest token cost for data that could be cacheable Resources; missed URI-navigability and client caching; audit cannot see a deliberate primitive-choice rationale.

### Remediation
Add a 'MCP Primitives' section to both READMEs justifying tools-only for Phase 1, and/or migrate list_cantons and list_school_types to Resources with a documented URI scheme.

### Effort Estimate
M


### ARCH-009

## Finding: ARCH-009 — Tool Annotations: readOnlyHint, destructiveHint, idempotentHint, openWorldHint

**Severity:** high
**Status:** partial
**Server:** swiss-school-calendar-mcp
**Check-Reference:** ARCH-009
**Check-Status:** partial

### Observed Behavior
Every tool sets readOnlyHint:True correctly, but no tool sets openWorldHint (all 10 make external HTTP calls) or idempotentHint, and there is no annotations policy/table in the docs.

### Expected Behavior
Explicit and complete annotations per MCP spec: readOnlyHint (present), openWorldHint:true for the outbound-HTTP tools, idempotentHint:true for idempotent reads, plus an annotations overview in the README.

### Evidence
- All 10 tools carry an explicit annotation and readOnlyHint:True is consistent with their read-only behaviour — server.py:104,136,173,223,251,307,362,420,452,484 (annotations={"readOnlyHint": True})
- openWorldHint is omitted on every tool even though all 10 reach external HTTPS APIs (OpenHolidays / Nager.Date) via HolidayClient — e.g. server.py:112-114, and client.py:132-177 issue outbound HTTP
- idempotentHint is omitted on every tool despite all being idempotent reads; README mentions readOnlyHint (README.md:76, :96) but provides no full annotations table/policy

### Gaps
- openWorldHint:true missing on all tools although every tool performs external network egress
- idempotentHint:true missing on all (idempotent read-only) tools
- No annotations overview table / policy in README or docs/

### Risk Description
Hosts cannot show a network-egress hint for tools that call external APIs, and lose retry-safe signalling from idempotentHint; the host's UI security/UX signalling is under-specified.

### Remediation
Add openWorldHint:True and idempotentHint:True to all ten annotations (a shared read_only_tool helper avoids drift) and add an annotations table to the README.

### Effort Estimate
S


### ARCH-011

## Finding: ARCH-011 — Standardisierte Repo-Struktur (src-Layout, tests, README.de.md)

**Severity:** medium
**Status:** partial
**Server:** swiss-school-calendar-mcp
**Check-Reference:** ARCH-011
**Check-Status:** partial

### Observed Behavior
Repo structure is strong (all mandatory files, correct src-layout, parallel bilingual READMEs, CI+publish workflows), but the 10 tools all live in one 506-line server.py with no tools/ sub-package and no documented rationale for the deviation.

### Expected Behavior
Servers with >5 tools split tool bodies into a tools/ package (file per group), keeping server.py to registry/lifecycle (~<200 lines), or document the deviation.

### Evidence
- All mandatory top-level files present (README.md, README.de.md, CHANGELOG.md, LICENSE, pyproject.toml) and directories src/, tests/, .github/workflows/ exist; CI without live tests + publish workflow present (ci.yml, publish.yml, live-tests.yml)
- src-layout is correct and declared: pyproject.toml:44-45 (packages=["src/swiss_school_calendar_mcp"]); README.md and README.de.md have identical parallel top-level section inventory (both 20 '## ' headings, translated 1:1)
- With 10 tools there is no tools/ sub-package — all tools live in a single 506-line server.py (well over the ~200-line guidance), and the src package has no tools/ directory (only server.py, client.py, models.py, constants.py, __main__.py, __init__.py)

### Gaps
- Server has >5 tools but they are not split into a tools/ package; server.py is 506 lines vs the <200 guideline
- The single-file layout is not documented as a justified deviation in the README

### Risk Description
Harder code review and weaker test isolation as the tool set grows; minor and purely maintainability-related.

### Remediation
Extract tool groups (lists, holidays, comparison, health) into src/swiss_school_calendar_mcp/tools/*.py, or add a short note in README Project Structure justifying the single-file layout.

### Effort Estimate
S


### ARCH-012

## Finding: ARCH-012 — protocolVersion-Pinning + CHANGELOG + SDK-Update-Disziplin

**Severity:** medium
**Status:** open
**Server:** swiss-school-calendar-mcp
**Check-Reference:** ARCH-012
**Check-Status:** fail

### Observed Behavior
protocolVersion is left to the SDK default (never pinned), CHANGELOG and Dependabot exist but no CHANGELOG entry names a spec version and no README documents the supported protocol version or an update policy.

### Expected Behavior
Explicit protocolVersion pin in server.py, CHANGELOG entries that note spec-version bumps, and a README 'MCP Protocol Version' section with an update/breaking-change policy.

### Evidence
- protocolVersion is not pinned: server.py:43 (mcp = FastMCP("swiss-school-calendar-mcp")) passes no protocol_version, and grep for protocol_version across src/ returns nothing — the SDK default is taken
- mcp SDK is pinned as a range not an exact/known-spec version: pyproject.toml:24 (mcp>=1.2.0); CHANGELOG.md is present and Keep-a-Changelog formatted but its entries never reference an MCP spec version (CHANGELOG.md:1-52)
- No 'MCP Protocol Version' section and no update/breaking-change policy in either README (grep protocol/spec.version/breaking in README.md/README.de.md hits only a badge and a Credits line); Dependabot is present (.github/dependabot.yml, weekly pip + actions)

### Gaps
- protocolVersion not explicitly pinned in server code (SDK default in use)
- No spec-version references in CHANGELOG entries
- No README section documenting supported MCP protocol version or update/breaking-change policy

### Risk Description
A future mcp SDK upgrade (unbounded by mcp>=1.2.0) could silently change the negotiated protocol version and break clients, with no documented compatibility contract or audit trail.

### Remediation
Pin an explicit protocol version at FastMCP construction, add a 'MCP Protocol Version' + update-policy section to both READMEs, and reference the spec version in CHANGELOG entries; consider an upper bound on the mcp dependency.

### Effort Estimate
S


### CH-006

## Finding: CH-006 — Schulamt Klassifikationsschema: BUI/Vertraulich/Streng-Vertraulich

**Severity:** high
**Status:** partial
**Server:** swiss-school-calendar-mcp
**Check-Reference:** CH-006
**Check-Status:** partial

### Observed Behavior
The server processes only Public Open Data (holiday calendars, no PII) and states 'no personal data' in README/SECURITY, but there is no explicit Schulamt classification declaration (Öffentlich/BUI/VERT/SVERT), no highest-level statement, and no aggregation-risk note — despite schulamt_context=true making this check mandatory.

### Expected Behavior
An explicit classification artefact declaring the highest data class as 'Öffentlich', with a short aggregation-risk statement confirming that cross-cantonal aggregation of public holiday calendars cannot re-identify individuals.

### Evidence
- README.md:97 Safety & Limits declares 'Personal data | No personal data — all sources are aggregated, public holiday calendars'; README.de.md:97 mirrors ('Keine Personendaten').
- SECURITY.md:33-36 — 'All tools perform HTTP GET requests against the public OpenHolidays and ... APIs return aggregated, public holiday calendars only.' — implicit 'Öffentlich' classification.
- No formal classification document exists — find for *klassif*/*classif* returns nothing; no docs/ directory; no explicit BUI/VERT/SVERT statement in any file.
- src/swiss_school_calendar_mcp/server.py:307-359, 362-417 — aggregating tools operate only on cantonal-level public holiday calendars (no per-pupil/per-class data), so there is no re-identification surface; but no k-anonymity/min-group-size guard or aggregation-risk statement is present (grep for k_anonymity/min_class_size returns none).

### Gaps
- No explicit classification declaration using the Stadt Zürich scheme (highest level not stated as 'Öffentlich').
- No measures-mapping per level and no explicit aggregation-risk analysis, even to state that cross-cantonal aggregation of public calendars poses no re-identification risk.
- Classification is only implied via 'no personal data' prose in README/SECURITY, not a standalone documented artefact.

### Risk Description
Low in substance — the data is genuinely public with no PII, so the correct class is 'Öffentlich' and no re-identification is possible. The gap is formal: without an explicit declaration, an operations team cannot confirm the classification was assessed rather than assumed. Severity high per the mandatory-for-Schulamt frontmatter, but real-world risk is minimal.

### Remediation
Add a short classification statement (e.g. docs/klassifikation.md or a README subsection) declaring highest level 'Öffentlich', listing the data types, and explicitly noting the nil aggregation/re-identification risk since only cantonal-level public calendars are handled.

### Effort Estimate
S


### OBS-002

## Finding: OBS-002 — Mask Error Details: keine Stacktraces / SQL ans LLM

**Severity:** high
**Status:** partial
**Server:** swiss-school-calendar-mcp
**Check-Reference:** OBS-002
**Check-Status:** partial

### Observed Behavior
_degraded() interpolates the raw exception (`{exc}`) into the user-visible note, and client.py embeds a 300-char upstream response-body excerpt plus the full endpoint URL into UpstreamError. FastMCP is initialised without mask_error_details=True.

### Expected Behavior
Execution errors surface user-friendly, sanitised messages; raw exception text, upstream bodies and internal URLs stay out of the LLM context and go to a server-side log only. mask_error_details=True (or equivalent) guards unhandled errors.

### Evidence
- src/swiss_school_calendar_mcp/server.py:90-93 — _degraded() interpolates the raw exception into the user-facing note: f"Upstream is currently unavailable ({exc}). ..."; this string reaches the LLM context.
- src/swiss_school_calendar_mcp/client.py:109-111 — on 4xx the UpstreamError message embeds the upstream URL and a 300-char excerpt of the response body: f"HTTP {status} from {url}: {detail}" where detail = exc.response.text[:300].
- src/swiss_school_calendar_mcp/server.py:43 — FastMCP("swiss-school-calendar-mcp") is constructed without mask_error_details=True.
- No traceback.format_exc()/sys.exc_info() anywhere (grep of src/ returns none), and no SQL, credentials or secrets exist in this server (auth_model=none, no DB) — so the forwarded text is bounded to public-API URLs and public problem+json bodies.

### Gaps
- Raw exception string is forwarded to the LLM in every degraded note.
- Upstream response body excerpt (exc.response.text[:300]) and full upstream URL are forwarded on 4xx.
- mask_error_details=True is not set on the FastMCP instance.
- No server-side logging channel exists to which original errors could be redirected (see OBS-003).

### Risk Description
Low in this server's context — data class is Public Open Data with no PII, SQL, or secrets, so the leaked internals are limited to public API URLs and public problem+json bodies. Still a deviation from the masking best practice and a habit that becomes dangerous if the codebase later gains authenticated/private upstreams.

### Remediation
Replace `({exc})` in _degraded() with a fixed generic caveat; drop exc.response.text[:300] and the URL from the user-facing UpstreamError message (keep them only for an internal logger once OBS-003 is addressed); set FastMCP(..., mask_error_details=True).

### Effort Estimate
S


### OBS-003

## Finding: OBS-003 — Structured Logging mit RFC 5424 Severity-Stufen

**Severity:** medium
**Status:** open
**Server:** swiss-school-calendar-mcp
**Check-Reference:** OBS-003
**Check-Status:** fail

### Observed Behavior
The codebase contains no logging whatsoever: no structlog/loguru dependency, no logger instance, no severity levels, no correlation context. Retries and degradations happen silently.

### Expected Behavior
A structured logger (structlog) configured for JSON/logfmt output to stderr, using RFC 5424 severity levels, with per-tool-call bound context (tool name, correlation id) logging invocation, success and failure.

### Evidence
- No structlog/loguru/pino in dependencies — pyproject.toml:23-35 lists only mcp, httpx, pydantic (runtime) and pytest/respx/ruff (dev).
- grep of src/ for `import logging|structlog|loguru|getLogger` returns no matches — there is no logger, no severity levels, and no bound per-call context anywhere in the server or client.
- Error conditions in client.py (_fetch_with_retry retries, UpstreamError) and server.py (degraded branches) produce no log records at any level.

### Gaps
- No structured logger dependency.
- No JSON/logfmt log output.
- Zero severity levels in use (no debug/info/warning/error).
- No per-tool-call bound context (tool name, correlation/session id).
- Retries and upstream failures are silent — no operational observability.

### Risk Description
Operational blind spot — upstream outages, retry storms and schema drift leave no trace, making incident diagnosis and monitoring aggregation impossible. Medium severity; no direct security impact for a public-data read-only server.

### Remediation
Add structlog to dependencies, configure it with WriteLoggerFactory(file=sys.stderr) and a JSONRenderer, and emit bound log events (tool_invoked/tool_succeeded/tool_failed, retry attempts) across server.py tools and client.py _fetch_with_retry.

### Effort Estimate
S


### OPS-003

## Finding: OPS-003 — Phasenarchitektur: Read-only First, dann Write, dann Multi-Agent

**Severity:** high
**Status:** partial
**Server:** swiss-school-calendar-mcp
**Check-Reference:** OPS-003
**Check-Status:** partial

### Observed Behavior
The server correctly declares and implements Phase 1 (read-only, all tools readOnlyHint:true, no write/destructive tools), but there is no standalone roadmap.md and no documented phase-transition prerequisites/gates.

### Expected Behavior
Phase declared (met) plus a roadmap file enumerating phase-specific tasks and the documented preconditions for advancing Phase 1->2 (audit, ISDS/CH-005, DSG/CH-002).

### Evidence
- README.md:268-276 'Lifecycle Phase' — explicitly declares 'Phase 1 (read-only) — all tools read-only, no auth, no side effects' and names a Phase 2 candidate (Zurich municipal specifics); README.de.md:268 mirrors it.
- src/swiss_school_calendar_mcp/server.py:104,136,173,223,251,307,362,420,452,484 — every @mcp.tool declares annotations={"readOnlyHint": True}; no destructiveHint / write tool exists, matching the declared phase (write_capable=false).
- src/swiss_school_calendar_mcp/server.py:1-6 module docstring documents the 10/15-20 tool budget explicitly reserving headroom for a Phase 2 extension.
- CHANGELOG.md documents the read-only Architecture-A decision (grep hit line ~50).

### Gaps
- No dedicated docs/roadmap.md file with phase-specific task lists (find for *roadmap* returns nothing; no docs/ directory).
- Phase-1->2 transition prerequisites (audit run, ISDS classification, DSG processing record) are not documented as gates.
- Phase status is prose in the README rather than the status-table format the check illustrates.

### Risk Description
Low operationally for a read-only public-data server — the core discipline (read-only first) is honoured. The gap is documentation completeness: future maintainers lack an explicit gate before adding a semantic layer or write tools.

### Remediation
Add docs/roadmap.md with Phase 1/2/3 task checklists and the Phase-1->2 prerequisites; optionally reformat the README Lifecycle Phase section as a status table.

### Effort Estimate
S


### SDK-001

## Finding: SDK-001 — FastMCP Lifespan via @asynccontextmanager + AsyncExitStack

**Severity:** high
**Status:** open
**Server:** swiss-school-calendar-mcp
**Check-Reference:** SDK-001
**Check-Status:** fail

### Observed Behavior
There is no FastMCP lifespan. Each of the 10 tools opens `async with HolidayClient()` which builds a brand-new httpx.AsyncClient (fresh connection pool) per invocation and closes it on exit. The client's 12-hour in-memory cache is stored on that per-call instance and is discarded when the tool returns, so it never serves a subsequent call.

### Expected Behavior
An @asynccontextmanager lifespan initialises one shared httpx.AsyncClient (and the cache) before the first request and closes it after the last, passed via FastMCP(..., lifespan=lifespan) and reused by tools through the injected context.

### Evidence
- server.py:43 — `mcp = FastMCP("swiss-school-calendar-mcp")` constructed with NO `lifespan=` argument.
- client.py:80-85 — `HolidayClient.__aenter__` creates a fresh `httpx.AsyncClient(...)` every time the client is entered; `__owns_http` is True on the default path.
- server.py:112,148,195,231,267,320,378,427,459,491 — every tool opens its own `async with HolidayClient() as client:`, so a new httpx.AsyncClient (and TCP connection pool) is built and torn down per tool call.
- client.py:77,127 — the retry/response cache (`self._cache`) and `self._last_success` live on the per-call HolidayClient instance and are therefore discarded after each call; the 12h CACHE_TTL_SECONDS (client.py:34) can never produce a cross-call hit.
- grep across src/ — no `@asynccontextmanager`, no `lifespan=`, no `AsyncExitStack`, no shared `server.state` HTTP client.

### Gaps
- No lifespan function defined with @asynccontextmanager.
- FastMCP constructor receives no lifespan=.
- httpx.AsyncClient is instantiated per tool call rather than reused from a lifespan-managed pool.
- In-memory cache is instance-scoped and thus effectively dead across calls.

### Risk Description
No connection pooling or keep-alive reuse across calls (TCP+TLS handshake per tool call to OpenHolidays/Nager), and the caching layer provides no benefit because it is thrown away every call. Cleanup itself is handled by `async with`/__aexit__ so there is no hard resource leak, which bounds real-world impact for a low-traffic local-stdio deployment; the defect is performance and wasted-cache, not leakage.

### Remediation
Add `@asynccontextmanager async def lifespan(server): server.state.http = httpx.AsyncClient(...); try: yield; finally: await server.state.http.aclose()`, pass `lifespan=lifespan` to FastMCP, and have tools reuse `ctx.fastmcp.state.http` (HolidayClient already accepts an injected `http=` client, client.py:74, so it can wrap the shared client without owning it).

### Effort Estimate
S


### SDK-003

## Finding: SDK-003 — Context Injection für Progress Reports und Logging

**Severity:** medium
**Status:** partial
**Server:** swiss-school-calendar-mcp
**Check-Reference:** SDK-003
**Check-Status:** partial

### Observed Behavior
No tool takes a `ctx: Context` parameter; there is no progress reporting and no ctx-based logging anywhere. Most tools are single fast cached fetches, but the retry backoff (2+4+8s) and the double-fetch in check_date can push a call to ~14s with zero client-visible progress.

### Expected Behavior
Tools whose realistic worst-case runtime exceeds ~2s (those hitting the retry/backoff path) accept `ctx: Context` and emit `ctx.report_progress()` / `ctx.info()` / `ctx.warning()`, especially to signal upstream-degraded retries rather than blocking silently.

### Evidence
- server.py:105,137,173,224,252,308,363,421,453,485 — no tool signature includes `ctx: Context`; `Context` is never imported in server.py.
- grep across src/ — no `report_progress`, no `ctx.info`/`ctx.warning`/`ctx.error`, no sampling/elicitation.
- client.py:99-101 — retry loop sleeps `2**attempt` (2s, 4s, 8s) across up to MAX_ATTEMPTS=4 (client.py:33), so a degrading upstream can make a single tool call block ~14s with no progress or log signal to the client.
- server.py:267-274 — `check_date` performs two sequential upstream fetches (school + public holidays), each subject to the retry backoff, compounding worst-case latency without any progress notification.
- No use of `print()` or stdlib logging inside tools (good — avoids the stdio protocol-crash anti-pattern), but also no ctx-based logging substitute.

### Gaps
- No tool declares ctx: Context, so no progress reporting is possible.
- Retry-backoff paths can exceed the 2s guidance silently with no ctx.report_progress or ctx.warning.
- Upstream-degraded conditions are returned in the payload note but never surfaced via ctx logging.

### Risk Description
During upstream slowdowns the client sees a multi-second stall with no feedback and may time out, and degraded/retry conditions are invisible except in the final payload. Impact is moderate: happy-path calls are fast and cached, so this only bites when upstream is slow.

### Remediation
Add `ctx: Context` to the network-bound tools (at minimum get_school_holidays, get_public_holidays, check_date, compare_school_holidays, find_common_free_window), and emit `ctx.info` before fetching plus `ctx.warning` on each retry attempt; thread ctx into the client retry loop or log around the `await client....` calls.

### Effort Estimate
S


### SDK-004

## Finding: SDK-004 — CORS Mcp-Session-Id Exposure bei HTTP/SSE

**Severity:** high
**Status:** partial
**Server:** swiss-school-calendar-mcp
**Check-Reference:** SDK-004
**Check-Status:** partial

### Observed Behavior
The server advertises HTTP/SSE transport via MCP_TRANSPORT but configures no CORS middleware; it uses the default FastMCP ASGI app, which does not expose the Mcp-Session-Id response header for cross-origin browser clients.

### Expected Behavior
When HTTP/SSE is enabled, a CORSMiddleware (or FastMCP cors settings) exposes `Mcp-Session-Id` via `expose_headers`, lists it in `allow_headers`, and restricts `allow_origins` to an explicit env-driven allow-list.

### Evidence
- __main__.py:13-18 — HTTP/SSE transport is a first-class supported mode: `MCP_TRANSPORT` in {sse, streamable-http, http} runs `mcp.run(transport="sse"|"streamable-http")` binding host 0.0.0.0 / PORT.
- server.py:43 — server relies on stock `FastMCP(...)`; no Starlette app, no Middleware list, no CORSMiddleware is constructed anywhere.
- grep across src/ — no `CORSMiddleware`, `expose_headers`, `allow_origins`, or `cors_*` configuration; the default FastMCP streamable_http/sse ASGI app is used unmodified.
- The stock MCP-SDK FastMCP HTTP app does not add `Access-Control-Expose-Headers: Mcp-Session-Id` by default, so a browser cross-origin client could not read the session id header when this server is run over HTTP.

### Gaps
- No CORS middleware configured despite dual (HTTP-capable) transport.
- `Mcp-Session-Id` is not exposed via Access-Control-Expose-Headers under the default app.
- No allow_origins allow-list wired to an env var for future HTTP deployment.

### Risk Description
Only materialises if the server is actually deployed over HTTP for browser-based cross-origin clients: those clients cannot read the session id, so follow-up requests lose session affinity and stateful conversation collapses — while stdio and server-side curl tests pass, making it hard to diagnose. Current deployment is local-stdio, so the risk is latent, not active; but the code path is shipped and unguarded.

### Remediation
Wrap the HTTP transport in a Starlette app with CORSMiddleware setting `expose_headers=["Mcp-Session-Id"]`, `allow_headers=[...,"Mcp-Session-Id"]`, and `allow_origins` from an ALLOWED_ORIGINS env var (no wildcard with credentials), or set the equivalent FastMCP cors settings before run().

### Effort Estimate
S


### SEC-004

## Finding: SEC-004 — SSRF-Prevention: HTTPS-Enforcement + IP-Blocklisting

**Severity:** critical
**Status:** partial
**Server:** swiss-school-calendar-mcp
**Check-Reference:** SEC-004
**Check-Status:** partial

### Observed Behavior
The server makes outbound GETs only to two hardcoded HTTPS hosts; no tool constructs a URL host from user/LLM free-text, and httpx follow_redirects defaults to False with TLS verification on. However none of the explicit SSRF controls from the spec exist (no scheme validation, no resolved-IP blocklist, no metadata-IP block, no egress proxy).

### Expected Behavior
Even with fixed hosts, defense-in-depth: an explicit https-only assertion and a resolved-IP blocklist (or egress proxy) applied before each outbound request, so a future refactor that introduces a user-influenced host, or a redirect/DNS-poisoning edge, cannot reach internal/metadata endpoints.

### Evidence
- src/swiss_school_calendar_mcp/constants.py:9-10 - upstream bases are hardcoded HTTPS constants OPENHOLIDAYS_BASE='https://openholidaysapi.org' and NAGER_BASE='https://date.nager.at/api/v3'; every request URL is built from these, never from user free-text
- src/swiss_school_calendar_mcp/client.py:132-177 - all request URLs are f-strings over the fixed bases; user-supplied values (canton, dates, language, year) only enter as query params / a numeric path segment, so the host is never attacker-controllable
- src/swiss_school_calendar_mcp/client.py:82-84 - httpx.AsyncClient created with default settings: follow_redirects defaults to False (an upstream 3xx to an internal IP is not followed) and TLS verification defaults on; no explicit scheme validation, no getaddrinfo/ipaddress blocklist, no metadata-IP (169.254.169.254) block, no egress proxy
- src/swiss_school_calendar_mcp/client.py:103,185 - self._http.get(url, ...) is called directly with no pre-request URL/scheme/IP check

### Gaps
- No explicit https-scheme assertion before outbound requests (relies on hardcoded constants)
- No resolved-IP blocklist for private/link-local/loopback ranges (169.254.169.254, 127.0.0.0/8, RFC1918, ::1, fe80::/10)
- No DNS-pinning / single-resolution; no egress proxy as defense-in-depth

### Risk Description
Low in current form because the host is never user-controlled and redirects are disabled; residual risk is a future code change adding a user-influenced URL, or DNS poisoning of the two fixed domains, with no blocklist backstop.

### Remediation
Add a small assert_https_and_public(url) helper (urlparse scheme check + getaddrinfo + ipaddress blocklist for RFC1918/loopback/link-local incl. 169.254.169.254 and ::1/fe80::) and call it in HolidayClient._fetch_with_retry/probe; keep follow_redirects=False explicit.

### Effort Estimate
M


### SEC-005

## Finding: SEC-005 — DNS-Rebinding-Prevention: DNS-Pinning gegen TOCTOU

**Severity:** high
**Status:** partial
**Server:** swiss-school-calendar-mcp
**Check-Reference:** SEC-005
**Check-Status:** partial

### Observed Behavior
No DNS-pinning implementation exists. The rebinding attack surface is nonetheless negligible because the two hostnames are hardcoded constants (not user-controllable) and default TLS certificate verification would reject a rebind to an unrelated internal IP.

### Expected Behavior
For servers matching the spec, DNS resolved once and the pinned IP reused for the TCP connection with original Host/SNI preserved. Here the equivalent protection is provided architecturally (fixed hosts + TLS verify), but no explicit pinning control is present.

### Evidence
- src/swiss_school_calendar_mcp/constants.py:9-10 - target hostnames (openholidaysapi.org, date.nager.at) are compile-time constants and cannot be supplied by a caller, so the classic rebinding precondition (attacker-controlled hostname) is absent
- src/swiss_school_calendar_mcp/client.py:82-84 - httpx.AsyncClient uses default per-request name resolution (no DNS pinning, no custom PinnedTransport); TLS verification is left at its secure default, so a MITM/rebind to an internal IP would fail certificate validation for the real domain
- src/swiss_school_calendar_mcp/client.py:103 - request issued via hostname each call; no single-resolution-then-pin pattern

### Gaps
- No DNS pinning / PinnedTransport; httpx resolves the hostname on every request
- No test asserting a single DNS lookup per request

### Risk Description
Very low: an attacker cannot influence the resolved hostname, and TLS verification defeats a rebind to an internal address for the fixed public domains.

### Remediation
Optional defense-in-depth: route outbound calls through a pinning transport or egress proxy shared with the SEC-004 fix; otherwise document that fixed hostnames + TLS verification are the accepted mitigation.

### Effort Estimate
M


### SEC-007

## Finding: SEC-007 — Container-Sandboxing: Docker / chroot mit minimalen Privilegien

**Severity:** high
**Status:** partial
**Server:** swiss-school-calendar-mcp
**Check-Reference:** SEC-007
**Check-Status:** partial

### Observed Behavior
No container image or sandbox configuration is committed. The server runs with full user privileges when launched locally, and no hardened Dockerfile exists for the documented cloud SSE path.

### Expected Behavior
A hardened Dockerfile (non-root UID, read-only rootfs, dropped capabilities, seccomp RuntimeDefault) for the network-deployment path, and/or documented sandboxing for local execution.

### Evidence
- Repository contains no Dockerfile, docker-compose, or k8s/helm manifests (glob for Dockerfile/docker-compose returned none); deployment is local stdio via uvx (README.md:175-211)
- src/swiss_school_calendar_mcp/server.py:104-503 - all 10 tools are readOnlyHint:true and touch only outbound HTTP; no filesystem writes, no subprocess, no secret access, limiting the blast radius of a compromised process
- pyproject.toml:37-38 - single console-script entry point; no build-time code execution hooks

### Gaps
- No hardened Dockerfile (non-root USER >=10000, readOnlyRootFilesystem, cap drop ALL, seccomp RuntimeDefault) is provided for the SSE/HTTP deployment path
- No process-level sandbox guidance for the local stdio install

### Risk Description
Limited in practice: the server is a read-only Public-Open-Data client with no secrets, no PII, no write/subprocess/filesystem tools, so a compromised process cannot exfiltrate stored data. Residual risk is a supply-chain compromise executing with user privileges (SSH keys, browser cookies) since no sandbox confines it.

### Remediation
Add a multi-stage Dockerfile with USER 10001, drop capabilities, read-only rootfs + tmpfs /tmp for the SSE deployment; note in SECURITY.md that local stdio runs with user privileges and recommend running under a restricted user.

### Effort Estimate
S


### SEC-016

## Finding: SEC-016 — 0.0.0.0-Binding-Prevention (NeighborJack)

**Severity:** critical
**Status:** open
**Server:** swiss-school-calendar-mcp
**Check-Reference:** SEC-016
**Check-Status:** fail

### Observed Behavior
When an HTTP/SSE transport is enabled, the listener binds 0.0.0.0 by default with no authentication. The spec's pass criteria require the code default to be 127.0.0.1 with 0.0.0.0 opt-in only inside a container; here the code default is 0.0.0.0, exactly the documented Fail-Pattern.

### Expected Behavior
Default MCP_HOST=127.0.0.1 in code; 0.0.0.0 set only via an explicit Dockerfile/deployment ENV; optional runtime warning when binding all interfaces outside a container.

### Evidence
- src/swiss_school_calendar_mcp/__main__.py:16 - mcp.settings.host = os.environ.get('MCP_HOST', '0.0.0.0') -> code default binds ALL interfaces, matching the spec's explicit Fail-Pattern; there is no local-vs-container differentiation and no built-in auth
- README.md:227 - env-var table documents MCP_HOST default as '0.0.0.0'
- SECURITY.md:45-51 - documents the exposure and recommends MCP_HOST=127.0.0.1 or a reverse proxy, but this is a documented opt-in mitigation, not a safe code default
- src/swiss_school_calendar_mcp/__main__.py:11,19-20 - mitigating factor: the 0.0.0.0 bind only occurs when MCP_TRANSPORT is explicitly set to an HTTP transport; the default transport is stdio and opens no port

### Gaps
- Code default host is 0.0.0.0 rather than 127.0.0.1 (spec requires default-loopback with container opt-in)
- No Dockerfile setting MCP_HOST=0.0.0.0 explicitly for the container-only case
- No warn-on-dangerous-binding log when binding 0.0.0.0 outside a container

### Risk Description
On a laptop in a shared/public network, enabling SSE exposes an unauthenticated MCP server to every host in the subnet (NeighborJack): tools/list + read-only tool calls, upstream data pull, and resource use. Partially mitigated because HTTP is opt-in (stdio is the default and opens no port).

### Remediation
Change default to MCP_HOST=127.0.0.1 in __main__.py; add ENV MCP_HOST=0.0.0.0 in a container image only; update README table; optionally log a warning when host in ('0.0.0.0','::') and no container is detected.

### Effort Estimate
S


### SEC-018

## Finding: SEC-018 — Input-Validation an Tool-Boundaries (Pydantic strict / Zod)

**Severity:** high
**Status:** partial
**Server:** swiss-school-calendar-mcp
**Check-Reference:** SEC-018
**Check-Status:** partial

### Observed Behavior
Only language (whitelist) and dates (fromisoformat) are validated. All other tool inputs are unconstrained plain str/int/list types: no numeric bounds, no string length/pattern, no strict mode, no extra='forbid'.

### Expected Behavior
Each tool argument validated against a strict schema at the boundary: numeric ge/le bounds, string min/max length and whitelist patterns, list size caps, canton codes checked against CANTON_CODES, and model_config {'strict': True, 'extra': 'forbid'}.

### Evidence
- src/swiss_school_calendar_mcp/client.py:49-58 - normalise_language() validates language against the SUPPORTED_LANGUAGES whitelist and raises ValueError (good, whitelist-based)
- src/swiss_school_calendar_mcp/server.py:261,467-471 - date inputs are parsed via date.fromisoformat, which raises on malformed values
- src/swiss_school_calendar_mcp/server.py:173-180,223-224,307-310,420-422 - tool arguments are plain str/int/list[str] with no Pydantic input model, no Field(ge/le) numeric bounds, no StringConstraints/pattern, no min/max length, and no model_config strict=True / extra='forbid'; matches the spec Fail-Pattern
- src/swiss_school_calendar_mcp/server.py:224 - year:int is unbounded and flows into f-string URLs (f'{year}-01-01') and into the Nager path /LongWeekend/{year}/CH (client.py:177); count/min_days ints are unbounded; cantons:list[str] has no length cap before an O(n^2) combinations pass (server.py:340)

### Gaps
- No numeric range constraints (ge/le) on year, count, min_days
- No length/pattern constraints on canton, school_type, cantons list; canton is not validated against CANTON_CODES before upstream use
- No Pydantic strict input models with extra='forbid' on any tool

### Risk Description
LLM hallucinations or malformed args can cause unbounded work (e.g. huge cantons lists -> O(n^2) overlap, absurd year/count values) or confusing empty results; low severity given read-only, in-memory, single upstream, but it is missing defense-in-depth.

### Remediation
Introduce Pydantic v2 input models per tool with Field(ge=..., le=...) for year/count/min_days, StringConstraints/length for canton & school_type (validate canton against CANTON_CODES), a max length on cantons, and strict/extra='forbid'.

### Effort Estimate
M


### SEC-021

## Finding: SEC-021 — Egress-Allow-List: Code-Layer und Network-Layer

**Severity:** high
**Status:** partial
**Server:** swiss-school-calendar-mcp
**Check-Reference:** SEC-021
**Check-Status:** partial

### Observed Behavior
Outbound requests are constrained to two hardcoded hosts by construction, but there is no explicit code-layer allow-list guard (frozenset + assert_host_allowed) and no network-layer egress control, and no egress policy documentation.

### Expected Behavior
A frozenset ALLOWED_HOSTS checked before each outbound request, plus a network-layer egress restriction for the deployed path, documented in docs/network-egress.md.

### Evidence
- src/swiss_school_calendar_mcp/constants.py:9-10 - egress is de facto restricted to two fixed hosts because every request URL is built from the hardcoded OPENHOLIDAYS_BASE and NAGER_BASE constants (client.py:132-177); no tool accepts a target host
- No frozenset ALLOWED_HOSTS + assert_host_allowed() pre-request guard exists (grep for allowed_hosts/frozenset in src/ returns none)
- No network-layer egress control committed: no Dockerfile, no k8s NetworkPolicy, no Terraform/security-group, no docs/network-egress.md (glob/grep found none)
- SECURITY.md:57-61 - names the two upstream services in scope but provides no formal egress policy table or update procedure

### Gaps
- No explicit code-layer frozenset allow-list with a pre-request host assertion
- No network-layer egress policy (NetworkPolicy / security group / WARP)
- No docs/network-egress.md documenting allowed hosts and an update procedure

### Risk Description
Low today because hosts are compile-time constants not derived from user input; residual exposure is a compromised image or future code change issuing requests to arbitrary domains with no allow-list or network backstop to catch exfiltration.

### Remediation
Add ALLOWED_HOSTS = frozenset({'openholidaysapi.org','date.nager.at'}) and assert_host_allowed(url) in HolidayClient before each GET; for cloud deployment add a NetworkPolicy/security-group egress rule and a docs/network-egress.md.

### Effort Estimate
M


---

## 6. Remediation-Plan

### Empfohlene Reihenfolge

1. **SEC-004** (critical, partial)
2. **SEC-016** (critical, fail)
3. **ARCH-004** (high, partial)
4. **ARCH-009** (high, partial)
5. **CH-006** (high, partial)
6. **OBS-002** (high, partial)
7. **OPS-003** (high, partial)
8. **SDK-001** (high, fail)
9. **SDK-004** (high, partial)
10. **SEC-005** (high, partial)
11. **SEC-007** (high, partial)
12. **SEC-018** (high, partial)
13. **SEC-021** (high, partial)
14. **ARCH-002** (medium, partial)
15. **ARCH-003** (medium, partial)
16. **ARCH-007** (medium, partial)
17. **ARCH-008** (medium, fail)
18. **ARCH-011** (medium, partial)
19. **ARCH-012** (medium, fail)
20. **OBS-003** (medium, fail)
21. **SDK-003** (medium, partial)

---

## 7. Audit-Metadata

| Feld | Wert |
|---|---|


_Generated by tools/build_report.py — do not edit by hand._
