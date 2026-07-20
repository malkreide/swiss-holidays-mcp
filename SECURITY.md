# Security Policy

[🇩🇪 Deutsche Version](SECURITY.de.md)

## Supported Versions

Security fixes are provided for the latest released version on
[PyPI](https://pypi.org/project/swiss-school-calendar-mcp/). Please always
upgrade to the most recent version before reporting an issue.

## Reporting a Vulnerability

Please report security vulnerabilities **privately** — do not open a public
issue for security-sensitive reports.

- Use [GitHub Security Advisories](../../security/advisories/new) to report
  privately, **or**
- Contact the maintainer at [github.com/malkreide](https://github.com/malkreide).

Please include:

- A description of the vulnerability and its potential impact
- Steps to reproduce (proof of concept, affected tool/endpoint)
- The version affected and your environment (OS, Python version, transport)

You can expect an initial response within **7 days**. Once a fix is released,
we will credit you in the changelog unless you prefer to remain anonymous.

## Security Model

This server is **read-only** and requires **no API key**:

- All tools perform HTTP `GET` requests against the public OpenHolidays and
  Nager.Date APIs — no data is written, modified, or deleted upstream.
- No personally identifiable information (PII) is processed or stored. The
  APIs return aggregated, public holiday calendars only.
- The server enforces a 20 s timeout per request (8 s for health probes) and
  caches responses in memory for 12 hours.
- Retries use exponential backoff (2 s / 4 s / 8 s); `4xx` responses except
  `429` are not retried.
- Upstream failure returns a `degraded` response envelope with an explanatory
  note, never a silent empty list — so "no holidays" and "source down" stay
  distinguishable.

### Deployment Hardening

- The HTTP/SSE transport binds **`127.0.0.1` (loopback) by default** (`MCP_HOST`).
  Binding a public interface (`MCP_HOST=0.0.0.0`) is an explicit opt-in and logs
  a warning at startup — the server has **no built-in authentication**.
- For non-loopback use, run **behind a reverse proxy that provides
  authentication and per-IP rate limits** (e.g. nginx with `limit_req` +
  OAuth2-Proxy). DNS-rebinding protection (Host/Origin allow-list) is enabled
  for the HTTP transport.
- **Egress:** outbound requests are restricted to a two-host HTTPS allow-list
  with an SSRF IP-blocklist — see [`docs/network-egress.md`](docs/network-egress.md).
- Logs go to **stderr** and never contain request bodies or personal data.
  Review your retention policy before enabling verbose logging.
- Full security architecture: [`docs/security.md`](docs/security.md).

## Scope

In-scope: the code in this repository (the MCP server, HTTP client, and
transport layer). Out of scope: vulnerabilities in upstream services
([OpenHolidays](https://www.openholidaysapi.org/), [Nager.Date](https://date.nager.at/))
— please report those directly to the respective providers.

---

This project follows the conventions of the
[Swiss Public Data MCP Portfolio](https://github.com/malkreide).
