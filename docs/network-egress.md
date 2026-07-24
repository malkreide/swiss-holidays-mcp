# Network Egress Policy

Audit references: SEC-004 (SSRF), SEC-005 (DNS rebinding), SEC-021 (egress
allow-list).

Egress is controlled in **two layers** (SEC-021), so a gap in one is caught by
the other:

| Layer | Where | Artifact |
|---|---|---|
| **Code** | in-process, before every socket opens | `ALLOWED_HOSTS` frozenset + `guard.py` |
| **Network** | pod / host, independent of the app | [`deploy/cilium-egress-fqdn.yaml`](../deploy/cilium-egress-fqdn.yaml), [`deploy/networkpolicy.yaml`](../deploy/networkpolicy.yaml) |

The code layer is always active. The network layer is deployed for any
networked (non-stdio) hardened deployment.

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

Adding a host is a **code change + review** and must be applied to **both
layers**:

1. Edit `ALLOWED_HOSTS` in `constants.py` and add the host to the table above.
2. Add the host to the `toFQDNs` list in `deploy/cilium-egress-fqdn.yaml` (and
   to your egress gateway / security-group rules if you use the stock
   `networkpolicy.yaml`).
3. Note it in the CHANGELOG.

It is deliberately not configurable at runtime — a missed network-layer update
would otherwise silently break the new host while the code layer allows it.

## Inbound (HTTP transport)

When run with an HTTP transport, the MCP SDK's DNS-rebinding protection is
enabled with an explicit Host/Origin allow-list (see `__main__._http_security`),
so browsers on other origins cannot drive the server via a rebinding attack.

## DNS rebinding / TOCTOU (audit SEC-005)

Outbound DNS is now **pinned in the client** for direct connections. Each
request goes through
[`PinnedResolverTransport`](../src/swiss_holidays_mcp/pinning.py): the host is
resolved **once** to an SSRF-safe IP (`guard.resolve_pinned`) and the TCP
connection is pinned to exactly that IP, while the `Host` header, TLS SNI and
certificate hostname check still use the original hostname. Because the pinned
IP is the one actually connected to — there is no second lookup — the
rebinding TOCTOU window is closed. Verified by a loopback TLS test
(`tests/test_pinning.py`): a request pinned to `127.0.0.1` still validates the
certificate against the hostname, and an unpinned IP connection without SNI is
rejected.

Pinning is **skipped behind a forward proxy** (`HTTPS_PROXY`/`ALL_PROXY`): the
proxy owns DNS resolution there, and rewriting the URL to an IP would break the
proxy `CONNECT`. In that case — and as defense-in-depth generally — the
**network layer** is the robust control, and it is shipped:

- [`deploy/cilium-egress-fqdn.yaml`](../deploy/cilium-egress-fqdn.yaml) —
  Cilium `toFQDNs` policy. The DNS proxy that enforces it is the authority on
  which IPs the pod may reach, independent of what the app resolves, so a
  rebinding answer to a poisoned resolver cannot be connected to.
- [`deploy/networkpolicy.yaml`](../deploy/networkpolicy.yaml) — stock
  Kubernetes fallback (DNS + 443 only; pair with an egress gateway for host
  pinning).
- Outside Kubernetes: a security-group / Cloudflare-WARP egress rule limiting
  outbound to these two hosts on 443 achieves the same.

For the documented **local stdio** use-case the client-side pin already closes
the window; the network-layer policy is the recommended addition for any
networked/hardened deployment.
