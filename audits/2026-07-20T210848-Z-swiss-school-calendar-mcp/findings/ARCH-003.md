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
