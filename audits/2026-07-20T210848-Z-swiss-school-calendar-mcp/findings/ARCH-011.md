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
