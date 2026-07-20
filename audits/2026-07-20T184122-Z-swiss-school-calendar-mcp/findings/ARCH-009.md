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
