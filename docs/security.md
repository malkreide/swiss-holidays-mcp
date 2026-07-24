# Security Architecture

Companion to [`SECURITY.md`](../SECURITY.md) (policy) — this file documents the
security model against the audit catalogue.

## Data classification (audit CH-006, CH-005)

| Data type | Classification | Personal data? |
|---|---|---|
| Cantons, Schularten, school holidays, public holidays | **Öffentlich (Public / BUI-none)** | No |
| Long weekends / bridge days | **Öffentlich** | No |
| Query patterns (which cantons an operator compares) | Öffentlich, but see note | No |

- **Highest classification handled: Öffentlich.** The server processes only
  aggregated public holiday calendars. No `Intern`, `Vertraulich` or
  `Streng vertraulich` data is in scope, so no ISDS classification (CH-005) or
  DSG processing record is required for Phase 1.
- **No personal data (DSG/DSGVO):** no PII is fetched, processed, logged or
  stored. Logs (stderr) contain only event names, upstream URLs and status
  codes — never request bodies or user identity.
- **Aggregation note:** query patterns could in principle hint at an operator's
  planning. When self-hosting for an authority, keep the deployment on trusted
  infrastructure; there is no granularity/k-anonymity concern because no
  personal micro-data is ever returned.

## Transport & binding (audit SEC-016, SEC-006)

- Default transport is **stdio** (no network surface).
- The HTTP/SSE transport binds **`127.0.0.1`** by default. Binding a public
  interface (`MCP_HOST=0.0.0.0`) is an explicit opt-in and logs a warning — the
  server has **no built-in authentication** and must run behind an
  authenticating reverse proxy with per-IP rate limits.
- DNS-rebinding protection (Host/Origin allow-list) is enabled for HTTP mode.

## Egress / SSRF (audit SEC-004, SEC-021, SEC-005)

See [`network-egress.md`](network-egress.md). Two-host frozen allow-list,
HTTPS-only, IP blocklist incl. cloud-metadata, `follow_redirects=False`.
Egress is enforced in two layers (SEC-021): the in-process guard plus a
network-layer policy for hardened deployments
([`deploy/cilium-egress-fqdn.yaml`](../deploy/cilium-egress-fqdn.yaml),
[`deploy/networkpolicy.yaml`](../deploy/networkpolicy.yaml)). DNS rebinding is
closed at the code layer by pinning the connection to the once-resolved,
SSRF-validated IP while TLS still validates the hostname
([`pinning.py`](../src/swiss_holidays_mcp/pinning.py), SEC-005); behind a
forward proxy the network-layer policy is the equivalent control.

## Lethal-trifecta assessment (audit SEC-019)

The server has the "access to private data" leg only in the weakest sense
(public data), and **neither** the "act/exfiltrate" leg (all 13 tools are
read-only, no write/send capability) **nor** untrusted-instruction ingestion
that could be acted upon. The trifecta is not present.

## Error handling (audit OBS-002, OBS-001)

Upstream failures are caught and returned as a `degraded` response envelope
with a generic, user-safe note. Raw exception text, upstream response bodies
and internal hostnames are logged to stderr only, never surfaced in a tool
result.

## Supply chain (audit SEC-013, ARCH-005)

No secrets: the server needs no API keys (both upstreams are keyless). CI runs
`pip-audit` (with a documented ignore for the disputed pyjwt CVE PYSEC-2025-183,
a transitive dependency of `mcp` that this server does not use) and Dependabot
opens weekly dependency PRs.
