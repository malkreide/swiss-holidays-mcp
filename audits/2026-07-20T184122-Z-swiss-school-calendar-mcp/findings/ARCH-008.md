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
