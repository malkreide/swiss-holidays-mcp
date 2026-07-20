# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- GitHub Actions CI (`.github/workflows/ci.yml`): test matrix on Python
  3.10 / 3.11 / 3.12 (ruff lint, `ruff format --check`, syntax + import checks,
  mocked unit tests) plus a `pip-audit` dependency-CVE scan.
- Nightly live-API workflow (`live-tests.yml`) and PyPI trusted-publisher
  workflow (`publish.yml`).
- Dependabot (`.github/dependabot.yml`): weekly pip + GitHub Actions updates.
- CI status badge in the READMEs.

### Changed

- Applied `ruff format` to `src/` and `tests/` so the source satisfies the new
  `ruff format --check` gate. Formatting only — no behaviour change.

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
