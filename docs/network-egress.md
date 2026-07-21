# Network Egress Policy

Audit references: SEC-004 (SSRF), SEC-005 (DNS rebinding), SEC-021 (egress
allow-list).

## Code-layer allow-list

The server only ever talks to two fixed, public HTTPS hosts. They are pinned in
an immutable `frozenset` in [`constants.py`](../src/swiss_holidays_mcp/constants.py):

| Host | Purpose | Licence |
|---|---|---|
| `openholidaysapi.org` | Cantons, Schularten, school + public holidays | CC BY 4.0 |
| `date.nager.at` | Long weekends / bridge days | MIT |

Every outbound request passes through
[`guard.py`](../src/swiss_holidays_mcp/guard.py) **before the socket is
opened**:

1. `assert_host_allowed(url)` — rejects any non-HTTPS scheme and any host not in
   the `frozenset` (SEC-021, SEC-004 scheme enforcement).
2. `assert_resolved_ip_safe(host)` — resolves the host once and rejects the
   request if any resolved address is loopback, link-local, private, multicast,
   reserved, unspecified, or a cloud-metadata IP (`169.254.169.254`,
   `fd00:ec2::254`) — the classic SSRF targets (SEC-004).

No tool constructs a URL from free-text user input; canton codes, dates and
language are the only parameters and they are validated (SEC-018).

## Extending the allow-list

Adding a host is a **code change + review**: edit `ALLOWED_HOSTS` in
`constants.py`, add the host to the table above, and note it in the CHANGELOG.
It is deliberately not configurable at runtime.

## Inbound (HTTP transport)

When run with an HTTP transport, the MCP SDK's DNS-rebinding protection is
enabled with an explicit Host/Origin allow-list (see `__main__._http_security`),
so browsers on other origins cannot drive the server via a rebinding attack.

## Residual risk (accepted)

Full outbound DNS **pinning** (reusing the guard's resolved IP for the actual
TCP connection, TOCTOU-free) is not implemented: httpx re-resolves at connect
time. Given the two-host frozen allow-list, TLS certificate validation against
the original hostname, and the IP blocklist above, the residual rebinding
window is accepted. A network-layer egress policy (NetworkPolicy / security
group restricting egress to these two hosts) is the recommended
defense-in-depth for a hardened deployment.
