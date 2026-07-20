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
