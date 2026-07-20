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
