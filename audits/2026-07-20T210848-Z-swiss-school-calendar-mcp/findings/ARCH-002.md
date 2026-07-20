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
