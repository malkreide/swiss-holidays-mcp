# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] — 2026-07-20

Security & best-practice remediation following the 2026-07-20 mcp-audit
(`audits/2026-07-20T184122-Z-…`). Closes the two blocking findings plus the
open architecture/observability findings. MCP protocol version tested against
`2025-06-18`.

### Security

- **SEC-016 (critical):** the HTTP/SSE transport now binds **`127.0.0.1` by
  default**; `MCP_HOST=0.0.0.0` is an explicit opt-in that logs a warning.
- **SEC-004 / SEC-021:** added a code-layer egress guard (`guard.py`) — HTTPS
  enforcement, an immutable two-host `frozenset` allow-list, and an SSRF IP
  blocklist (loopback/private/link-local/cloud-metadata) checked before every
  request. Documented in `docs/network-egress.md`.
- **SEC-005 / SDK-004:** DNS-rebinding protection (Host/Origin allow-list)
  enabled for the HTTP transport.
- **SEC-018:** all tool inputs are schema-validated (canton against the 26 known
  codes, `YYYY-MM-DD` dates, bounded `year`/`count`/`min_days`, whitelisted
  `language`/`school_type`).
- **OBS-002:** raw exception text and upstream bodies are no longer surfaced in
  tool results — only in the stderr log.

### Changed

- **SDK-001 / ARCH-004:** a single `httpx.AsyncClient` and the 12h cache now
  live in the FastMCP **lifespan** and are injected via `Context`, instead of a
  new client per tool call. The cache is now effective across calls.
- Configuration moved to a Pydantic-Settings object (`settings.py`).

### Added

- **OBS-003:** structured logging to stderr (`logging_setup.py`).
- **SEC-007:** non-root multi-stage `Dockerfile`.
- **OPS-003 / ARCH-012 / ARCH-008 / CH-006:** `docs/roadmap.md`,
  `docs/security.md`, `docs/network-egress.md`; README sections on MCP
  primitives, protocol version and data classification.
- **ARCH-009:** full tool annotations (`destructiveHint`, `idempotentHint`,
  `openWorldHint`) on every tool.
- GitHub Actions CI (matrix 3.10/3.11/3.12, ruff, `ruff format --check`,
  `pip-audit`), nightly live-tests, PyPI trusted-publisher workflow, Dependabot,
  `.gitignore`, CI badge (from the prior CI PR).
- Dependency: `pydantic-settings>=2.2`; `mcp` pinned to `>=1.2.0,<2`.

## [0.1.0] — 2026-07-19

### Added

- Ten read-only tools covering Swiss school and public holidays for all 26 cantons.
- Dual transport: stdio (Claude Desktop) and SSE / Streamable HTTP (cloud).
- Pydantic v2 response envelope carrying `source`, `provenance` and `retrieved_at`.
- Retry with exponential backoff (2s / 4s / 8s); 4xx except 429 are not retried.
- Graceful degradation: upstream failure returns a `degraded` envelope with an
  explanatory note instead of an empty list.
- `source_status` health tool for both upstream sources.

### Known findings (live probe, 2026-07-19)

- **Apparent duplicates are school types.** Six cantons (AI, AR, BE, GR, SO, ZH)
  publish the same holiday period once per *Schulart*. Zurich uses `CH-ZH-VS`
  (Volksschulen, tagged `Recommended`), `CH-ZH-MS` (Mittelschulen) and
  `CH-ZH-BS` (Berufsfachschulen). Naive de-duplication destroys exactly the
  distinction a school authority needs. Handled via the `school_type` filter.
  *Mnemonic: a duplicate in Swiss school data is usually a school type in disguise.*
- **An empty list is not an answer.** An unknown `countryIsoCode` or canton code
  returns HTTP 200 with `[]` rather than a 404. Responses now carry an
  explanatory `note` so that "no holidays" and "bad filter" stay distinguishable.
- **Silent language fallback.** An unsupported `languageIsoCode` silently falls
  back to EN. Languages are therefore validated locally before the request.
- **Mixed subdivision levels.** Records may carry sub-cantonal codes such as
  `CH-AI-AP` or `CH-BE-TH-BL`. Matching is done on the `CH-XX` prefix.
- **No verified public bulk dump** at build time, hence Architecture A rather
  than the portfolio's more common Architecture B.
