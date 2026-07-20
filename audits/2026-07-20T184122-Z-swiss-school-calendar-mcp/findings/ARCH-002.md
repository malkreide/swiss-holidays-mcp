## Finding: ARCH-002 — Tool-Beschreibung mit Use-Case-Tags

**Severity:** medium
**Status:** partial
**Server:** swiss-school-calendar-mcp
**Check-Reference:** ARCH-002
**Check-Status:** partial

### Observed Behavior
Tool descriptions are decent multi-sentence docstrings with prose context and explicit differentiation, but contain no structured <use_case>/<important_notes> tags, and at least one tool (next_school_holidays) is a single terse sentence.

### Expected Behavior
Use-case tag (or equivalent structured section) present in >=80% of tools; caveats/limitations surfaced in-description; every tool >= 100 chars with clear differentiation.

### Evidence
- Descriptions are multi-sentence docstrings well above the 100-char median threshold — e.g. server.py:181-193 (get_school_holidays) and server.py:174-193 with Args block
- Differentiation between similar tools is explicit: get_school_holidays vs get_public_holidays vs next_school_holidays each state their distinct purpose (server.py:174-193, :224-229, :421-424)
- No <use_case> / <important_notes> / <example> XML tags anywhere in src/ — use-case info is embedded as prose only, and some tools have minimal framing (next_school_holidays docstring is a single sentence, server.py:424)

### Gaps
- No structured use_case/important_notes tags in any of the 10 tools (0% vs required 80%)
- next_school_holidays has only a one-sentence description with no use-case or caveat framing

### Risk Description
Weaker semantic separation at tool-selection time; the LLM has less structured signal to disambiguate the several holiday-lookup tools, mildly raising wrong-tool-selection risk.

### Remediation
Add a short structured use-case/important-notes block (tags or a consistent 'Use when: ... Do not use for: ...' convention) to each docstring; expand next_school_holidays with use-case and the VS default caveat.

### Effort Estimate
S
