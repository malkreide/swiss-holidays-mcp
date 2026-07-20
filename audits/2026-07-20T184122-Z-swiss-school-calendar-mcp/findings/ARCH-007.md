## Finding: ARCH-007 — Capability-Aggregation: Composability intern, Atomarität extern

**Severity:** medium
**Status:** partial
**Server:** swiss-school-calendar-mcp
**Check-Reference:** ARCH-007
**Check-Status:** partial

### Observed Behavior
Tools are well-aggregated and atomic from the LLM's perspective (no ID-chaining), but check_date fetches school and public holidays sequentially instead of with asyncio.gather.

### Expected Behavior
Where a tool issues multiple independent upstream calls, use asyncio.gather to parallelise them.

### Evidence
- Tools return self-contained, thought-complete results rather than IDs/pointers requiring follow-up calls — every tool returns a full Pydantic envelope (models.py:59-129); no getXId->getXDetails chaining exists
- Internal aggregation is present: check_date combines school + public holiday lookups (server.py:268-303); compare_school_holidays builds a pairwise overlap matrix internally (server.py:330-359)
- asyncio.gather / parallel fetch is never used; check_date issues its two upstream fetches sequentially (server.py:269-274: await school_holidays then await public_holidays)

### Gaps
- check_date performs two sequential awaits that could run in parallel via asyncio.gather

### Risk Description
Minor added latency on check_date (two round-trips serialised); no correctness impact.

### Remediation
Wrap the school_holidays and public_holidays fetches in check_date in a single asyncio.gather.

### Effort Estimate
S
