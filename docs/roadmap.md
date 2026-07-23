# Roadmap & Phase Architecture

This server follows the portfolio's phased model (audit OPS-003). Phase
transitions require the documented prerequisites below and are recorded in
[`CHANGELOG.md`](../CHANGELOG.md).

## Phase 1 — Read-only (current)

- **Status:** active (v0.5.0).
- All 13 tools are annotated `readOnlyHint: true`, `destructiveHint: false`,
  `idempotentHint: true`, `openWorldHint: true`.
- No authentication, no write operations, no side effects.
- Data class: Public Open Data (holiday calendars, no personal data).

## Phase 2 — Municipal layer (planned)

Adds city-level Zurich specifics (Sechseläuten, Knabenschiessen) that are
neither cantonal public holidays nor school holidays upstream, via
[`zurich-opendata-mcp`](https://github.com/malkreide/zurich-opendata-mcp).

**Prerequisites for 1 → 2:**

- [x] Security audit run (mcp-audit-skill) — `audits/`
- [ ] Data-source probe for the municipal source (`mcp-data-source-probe`)
- [ ] Confirm no personal data enters scope (stays Public Open Data)

## Phase 3 — Write / multi-agent (not planned)

Out of scope for a holiday-calendar server. Would require, at minimum: an
auth model (Phase 1→2 keeps `auth_model: none`), a DSG processing record, and
GL / data-protection sign-off before any write capability is added.

## Non-goals

- No historical time-series guarantee before ~2020.
- No legally binding dates — the cantonal authority remains authoritative;
  every response says so.
