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
