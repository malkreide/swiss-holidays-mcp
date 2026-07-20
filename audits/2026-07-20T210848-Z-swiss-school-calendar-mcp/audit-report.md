# MCP-Server Audit-Report — `swiss-school-calendar-mcp` (Re-Audit)

**Audit-Datum:** 2026-07-20 (Re-Audit nach Remediation, v0.2.0)
**Skill-Version:** 1.0.0
**Catalog-Version:** 091f446b2796

---

## 1. Executive Summary

Server `swiss-school-calendar-mcp` wurde gegen 35 anwendbare Best-Practice-Checks geprüft. 27 bestanden, 8 Findings dokumentiert (0 critical, 3 high, 5 medium, 0 low). Production-Readiness: erreicht.

**Production-Readiness:** YES

---

## 2. Profil-Snapshot

| Feld | Wert |
|---|---|
| Server-Name | `swiss-school-calendar-mcp` |
| Audit-Datum | 2026-07-20 (Re-Audit) |
| Skill-Version | 1.0.0 |
| Catalog-Version | 091f446b2796 |

---

## 3. Applicability

### Status pro Kategorie

| Kategorie | Pass | Fail | Partial | Todo | N/A |
|---|---|---|---|---|---|
| ARCH | 8 | 0 | 3 | 0 | 0 |
| CH | 2 | 0 | 0 | 0 | 0 |
| OBS | 3 | 0 | 1 | 0 | 0 |
| OPS | 3 | 0 | 0 | 0 | 0 |
| SCALE | 0 | 0 | 0 | 0 | 1 |
| SDK | 2 | 0 | 2 | 0 | 0 |
| SEC | 9 | 0 | 2 | 0 | 1 |
| **Total** | **27** | **0** | **8** | **0** | **2** |

---

## 4. Findings-Übersicht

_Policy: `fail-or-partial`_

| ID | Category | Severity | Status |
|---|---|---|---|
| SDK-004 | SDK | high | partial |
| SEC-005 | SEC | high | partial |
| SEC-021 | SEC | high | partial |
| ARCH-002 | ARCH | medium | partial |
| ARCH-003 | ARCH | medium | partial |
| ARCH-011 | ARCH | medium | partial |
| OBS-003 | OBS | medium | partial |
| SDK-003 | SDK | medium | partial |

**Gesamt:** 8 Findings

---

## 5. Detail-Findings

### ARCH-002

## Finding: ARCH-002 — Tool-Beschreibung mit Use-Case-Tags

**Severity:** medium
**Status:** partial (accepted-risk / defense-in-depth)
**Server:** swiss-school-calendar-mcp
**Check-Reference:** ARCH-002

### Observed Behavior
All 10 tools use plain prose docstrings. They carry use-case context and differentiation in natural language but contain no <use_case>/<important_notes>/<example> tags (or any structured equivalent).

### Expected Behavior
Descriptions should embed a use_case tag (or equivalent structured marker) in at least 80% of tools, plus important-notes where caveats exist, to maximise semantic separability at tool-selection time.

### Evidence
- Tool descriptions are rich prose docstrings well over the 100-char median, with use-case framing and explicit differentiation (server.py:537-543 list_school_types explains ZH codes; server.py:556-568 get_school_holidays documents Schulart collapse; server.py:610-615 compare_school_holidays justifies the VS default).
- No tool falls under the 50-char floor; the shortest (next_school_holidays, server.py:646) is still a full descriptive sentence.

### Gaps
- No structured <use_case> / <important_notes> / <example> tags in any description (grep for these tags in src/ returns nothing) — the check asks for a use_case tag or equivalent in >=80% of tools.
- Caveats live in docstring prose rather than a discrete tagged field, so a client that only surfaces the first line loses them.

### Risk Description
Lower — descriptions are already informative; missing tags marginally reduce embedding-based tool-selection sharpness between the several similar holiday-lookup tools.

### Remediation
Add a short <use_case> block (and <important_notes> where relevant, e.g. the Schulart de-dup caveat) to each tool description; the existing prose can be lifted almost verbatim.

### Effort Estimate
S


### ARCH-003

## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

**Severity:** medium
**Status:** partial (accepted-risk / defense-in-depth)
**Server:** swiss-school-calendar-mcp
**Check-Reference:** ARCH-003

### Observed Behavior
Empty results are wrapped in typed envelopes and the school-holidays path plus unknown-canton path give actionable guidance, but there is no match_type field and no fuzzy/suggestion fallback; several empty paths (public holidays, compare, window) carry no note.

### Expected Behavior
Non-sensitive search tools should expose a match_type field and, on empty exact results, offer heuristic/related results or actionable suggestions.

### Evidence
- No tool returns a bare [] or the string 'No results'. Every path returns a typed Envelope carrying source/provenance/retrieved_at (models.py:17-28).
- op_get_school_holidays sets an explanatory note on empty results (server.py:252-258) distinguishing 'canton does not differentiate this Schulart' from 'range holds no holidays'.
- Unknown canton codes now raise an actionable ValueError pointing at another tool: _require_known_canton server.py:119-126 ('Call list_cantons for the 26 valid CH-XX codes').
- Upstream failure returns a degraded envelope with a retry note rather than silence (_degraded server.py:156-168).

### Gaps
- Responses carry no match_type field (exact/fuzzy/none) as the check's pass criteria request.
- No fuzzy-match or suggestion mechanism on empty non-sensitive results; op_get_public_holidays (server.py:269-290) and the computed compare/window tools return empty collections with no note.
- check_date returns is_school_holiday/is_public_holiday=false with matches=[] and no note on an ordinary non-holiday date (definitive, so acceptable, but no match_type signal).

### Risk Description
Low — the holiday domain is exact-lookup (canton+date), so fuzzy matching is a weak fit; the main anti-pattern (silent []) is already avoided.

### Remediation
Add a match_type field to the list/date envelopes and extend the empty-result note to the public-holidays and compare/window paths for consistency.

### Effort Estimate
S


### ARCH-011

## Finding: ARCH-011 — Standardisierte Repo-Struktur (src-Layout, tests, README.de.md)

**Severity:** medium
**Status:** partial (accepted-risk / defense-in-depth)
**Server:** swiss-school-calendar-mcp
**Check-Reference:** ARCH-011

### Observed Behavior
Repo layout, mandatory files, src-layout, CI workflows and README.de.md parity all conform, but the 10 tools and their logic sit in one 670-line server.py with no tools/ package split, and the deviation is undocumented.

### Expected Behavior
With >5 tools, tools should be grouped under a tools/ directory (file per group) leaving server.py as a thin registry/lifecycle module (~200 lines), or the deviation should be justified in the README.

### Evidence
- All mandatory top-level files present: README.md, README.de.md, CHANGELOG.md, LICENSE, pyproject.toml; mandatory dirs present: src/, tests/, .github/workflows/ (ci.yml, live-tests.yml, publish.yml).
- Correct src-layout: src/swiss_school_calendar_mcp/ with pyproject [tool.hatch.build.targets.wheel] packages = ['src/swiss_school_calendar_mcp'] (pyproject.toml:45-46).
- README.de.md is at full section parity with README.md (23 top-level ## sections map one-to-one, verified by diff of the heading inventories).
- Cross-cutting concerns are already split into modules: guard.py, settings.py, logging_setup.py, client.py, constants.py, models.py.

### Gaps
- All 10 tools plus their op_* logic live in a single server.py of 670 lines; the check asks for a tools/ subdirectory (file-per-group) once a server exposes >5 tools and for server.py to stay near ~200 lines (registry/lifecycle only).
- This deviation from the standard layout is not explicitly justified in the README.

### Risk Description
Low — organisational only; the module is well-structured (op_* logic separated from thin wrappers) but review/test isolation is harder in one large file.

### Remediation
Split tools into src/swiss_school_calendar_mcp/tools/ by cluster (school / public+longweekend / compare+window / status) or add a short README note justifying the single-file layout.

### Effort Estimate
S


### OBS-003

## Finding: OBS-003 — Structured Logging mit RFC 5424 Severity-Stufen

**Severity:** medium
**Status:** partial (accepted-risk / defense-in-depth)
**Server:** swiss-school-calendar-mcp
**Check-Reference:** OBS-003

### Observed Behavior


### Expected Behavior


### Evidence
- src/swiss_school_calendar_mcp/logging_setup.py:18-40 — a _KeyValueFormatter emits structured logfmt (key=value) lines with ts/level/logger/event plus an expanded 'context' dict; StreamHandler(sys.stderr) and propagate=False. Structured, not plaintext.
- src/swiss_school_calendar_mcp/client.py:134-165 uses _log.warning and _log.error with extra={'context': {...}}; server.py:156-159 _degraded uses _log.warning; __main__.py:43-59 uses log.warning/log.info. So info/warning/error are actively used.
- No print()/console.log/sys.stdout anywhere in src/ (grep clean).

### Gaps
- Pass-criterion 1 unmet: no structured-logging library (structlog/pino/loguru) in pyproject.toml dependencies — the implementation is hand-rolled on stdlib logging. The spec names structlog as the Python standard and lists it as a hard criterion (Modus 1 automated grep fails).
- Only 3 of the required >=4 severity levels are actively used (info, warning, error); debug is never emitted.
- No per-tool-call bound context: logs carry url/status/attempt but no tool name, session_id or correlation_id, so multi-step workflows are not correlatable (spec pass-criterion 4).

### Risk Description


### Remediation


### Effort Estimate
M


### SDK-003

## Finding: SDK-003 — Context Injection für Progress Reports und Logging

**Severity:** medium
**Status:** partial (accepted-risk / defense-in-depth)
**Server:** swiss-school-calendar-mcp
**Check-Reference:** SDK-003

### Observed Behavior


### Expected Behavior


### Evidence
- src/swiss_school_calendar_mcp/server.py:523-667 — every tool declares `ctx: Context` as its first parameter, so FastMCP dependency-injection is in place (context injection present).
- src/swiss_school_calendar_mcp/server.py:109-110 — `ctx` is genuinely used (not dead code): `_client(ctx)` reads the lifespan-scoped shared client from `ctx.request_context.lifespan_context`.
- src/swiss_school_calendar_mcp/logging_setup.py:31-40 — logging is routed to stderr via `StreamHandler(stream=sys.stderr)` with `propagate=False`, so stdout stays clean for the stdio JSON-RPC channel (OBS-004 satisfied; no `print()` in tool bodies).
- Tools are fast cached GETs (client.py:42 12h cache, 20s timeout) with no `asyncio.sleep`, no large loops and no `gather()` over many tasks, so the >2s progress-report criterion does not apply — `ctx.report_progress()` is legitimately absent.

### Gaps
- No tool uses `ctx.info()`/`ctx.warning()`/`ctx.error()`/`ctx.report_progress()` — `ctx` serves only as a service locator for the shared client.
- Graceful-degradation and retry events are logged only to the stdlib stderr logger (server.py:159 `_log.warning("degraded_response", ...)`, client.py:134-167). These never reach the MCP client as `notifications/message`; surfacing the degraded path via `ctx.warning()` would make the caveat visible client-side. Low practical impact given the returned envelope already carries `provenance="degraded"` + `note`.

### Risk Description


### Remediation


### Effort Estimate
M


### SDK-004

## Finding: SDK-004 — CORS Mcp-Session-Id Exposure bei HTTP/SSE

**Severity:** high
**Status:** partial (accepted-risk / defense-in-depth)
**Server:** swiss-school-calendar-mcp
**Check-Reference:** SDK-004

### Observed Behavior


### Expected Behavior


### Evidence
- src/swiss_school_calendar_mcp/__main__.py:18-34 — `_http_security()` builds `TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=..., allowed_origins=...)`; applied at __main__.py:54 `mcp.settings.transport_security = _http_security(settings)`. This pins Host/Origin (DNS-rebinding protection, SEC-005) but is NOT CORS response-header configuration.
- src/swiss_school_calendar_mcp/__main__.py:29 — `allowed_origins` is loopback-only (`http://127.0.0.1:<port>`, `http://localhost:<port>`); no wildcard.
- No `CORSMiddleware`, `expose_headers` or `Access-Control-Expose-Headers` anywhere in src/ — grep for `CORSMiddleware|expose_headers|allow_origins` returns only the TransportSecuritySettings usage. `Access-Control-Expose-Headers: Mcp-Session-Id` is therefore not set by application code.
- The server mounts the SDK streamable-http/sse app via `mcp.run(transport=...)` (__main__.py:57); the MCP Python SDK's streamable-http app does not add a CORSMiddleware exposing Mcp-Session-Id by default.

### Gaps
- The specific control this check targets — `Access-Control-Expose-Headers: Mcp-Session-Id` (and `allow_headers` including `Mcp-Session-Id`) — is absent. A browser-based cross-origin client could not read the session header.
- Mitigating context: deployment is local-stdio and, when HTTP is enabled, `allowed_origins` is loopback-only, so a cross-origin browser client is not a supported/target scenario and the practical risk is low. Not a full pass because the header exposure is simply not covered.

### Risk Description


### Remediation


### Effort Estimate
M


### SEC-005

## Finding: SEC-005 — DNS-Rebinding-Prevention: DNS-Pinning gegen TOCTOU

**Severity:** high
**Status:** partial (accepted-risk / defense-in-depth)
**Server:** swiss-school-calendar-mcp
**Check-Reference:** SEC-005

### Observed Behavior


### Expected Behavior


### Evidence
- __main__.py:18-34 _http_security builds TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=..., allowed_origins=...) and __main__.py:54 wires it into mcp.settings.transport_security — inbound (browser-driven) DNS-rebinding protection is enabled for the HTTP transport.
- guard.py:66-79 outbound path resolves the host a single time (one getaddrinfo) and range-checks the result before the request.
- docs/network-egress.md:42-50 documents the outbound residual risk as consciously accepted, with compensating controls (2-host allow-list, TLS cert validation, IP blocklist) and recommends a network-layer egress policy for hardened deployments.

### Gaps
- The core control SEC-005 requires — outbound DNS pinning (reusing the resolved IP for the actual TCP connection with Host-header/SNI preservation) — is NOT implemented; httpx re-resolves at connect time, leaving a TOCTOU window.
- None of the SEC-005 outbound pass-criteria (pinned IP for connection, Host-header/SNI on original hostname, test asserting exactly 1 DNS call) are met.
- Inbound TransportSecuritySettings mitigates a different (inbound) rebinding vector, not the outbound one this check scores.

### Risk Description


### Remediation
Pin the resolved IP into the connection (custom httpx transport/resolver reusing the vetted address with SNI+Host preserved) or place a network-layer egress policy restricting egress to the two hosts. Currently accepted as documented residual risk.

### Effort Estimate
M


### SEC-021

## Finding: SEC-021 — Egress-Allow-List: Code-Layer und Network-Layer

**Severity:** high
**Status:** partial (accepted-risk / defense-in-depth)
**Server:** swiss-school-calendar-mcp
**Check-Reference:** SEC-021

### Observed Behavior


### Expected Behavior


### Evidence
- constants.py:12-16 ALLOWED_HOSTS = frozenset({'openholidaysapi.org','date.nager.at'}) — immutable code-layer allow-list, not env/config-mutable.
- client.py:117-119 guard.assert_host_allowed(url) is called before every outbound GET in _fetch_with_retry, and client.py:237 in probe(); guard.py:33-46 enforces HTTPS + membership.
- docs/network-egress.md:6-34 documents the allow-list, the two hosts and their purpose, and a code-change+review+CHANGELOG update procedure for extending it.

### Gaps
- The check explicitly requires BOTH layers ('Code-only ist unzureichend'). The network-layer egress control (Kubernetes NetworkPolicy / AWS Security Group / Cloudflare WARP) is NOT implemented — no k8s/Terraform manifest exists in the repo; docs/network-egress.md:44-50 only recommends it as defense-in-depth for a hardened deployment.
- Consistent with the local-stdio + optional-Docker deployment profile there is no orchestration layer in-repo to host a NetworkPolicy, so the network layer is left to the operator at deploy time.

### Risk Description


### Remediation
Ship a network-layer egress policy for containerised/cloud deployments (NetworkPolicy or security-group egress restricted to the two hosts on 443 plus DNS). Acceptable to remain code-layer-only for the default local-stdio deployment; document that the network layer is an operator responsibility.

### Effort Estimate
M


---

## 6. Remediation-Plan

### Empfohlene Reihenfolge

1. **SDK-004** (high, partial)
2. **SEC-005** (high, partial)
3. **SEC-021** (high, partial)
4. **ARCH-002** (medium, partial)
5. **ARCH-003** (medium, partial)
6. **ARCH-011** (medium, partial)
7. **OBS-003** (medium, partial)
8. **SDK-003** (medium, partial)

---

## 7. Audit-Metadata

| Feld | Wert |
|---|---|


_Generated by tools/build_report.py — do not edit by hand._
