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
