"""Egress / SSRF guard for outbound HTTP.

Even though this server only ever talks to two fixed, well-known public hosts,
the guard is defence-in-depth (audit SEC-004, SEC-005, SEC-021):

* ``assert_host_allowed`` — pure check: HTTPS scheme + host on the frozen
  allow-list. No DNS, so it is cheap and test-safe.
* ``assert_resolved_ip_safe`` — resolves the host **once** and rejects the
  request if any resolved address is loopback, link-local, private, multicast,
  reserved, unspecified, or the cloud-metadata IP (``169.254.169.254`` / IPv6
  equivalents). This blocks the classic SSRF targets should DNS for an
  allow-listed host ever be poisoned.

Both are called before every outbound request in ``client.HolidayClient``.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from .constants import ALLOWED_HOSTS

# Explicit cloud-metadata endpoints, on top of the is_* range checks.
_METADATA_IPS = frozenset({"169.254.169.254", "fd00:ec2::254"})


class EgressError(RuntimeError):
    """An outbound request violated the egress policy."""


def assert_host_allowed(url: str) -> str:
    """Validate scheme + host against the allow-list. Returns the hostname.

    Pure (no network), so unit tests exercise the allow-list without DNS.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise EgressError(f"Refusing non-HTTPS egress to {url!r}.")
    host = parsed.hostname or ""
    if host not in ALLOWED_HOSTS:
        raise EgressError(
            f"Host {host!r} is not on the egress allow-list ({', '.join(sorted(ALLOWED_HOSTS))})."
        )
    return host


def _is_blocked_ip(ip: str) -> bool:
    if ip in _METADATA_IPS:
        return True
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def assert_resolved_ip_safe(host: str) -> None:
    """Resolve ``host`` once and reject SSRF-flavoured addresses.

    A single ``getaddrinfo`` call is used so there is one resolution to reason
    about (TOCTOU is not fully eliminated because httpx re-resolves for the
    actual connection — see docs/network-egress.md 'Residual risk').
    """
    infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    ips = {info[4][0] for info in infos}
    blocked = sorted(ip for ip in ips if _is_blocked_ip(ip))
    if blocked:
        raise EgressError(
            f"Host {host!r} resolved to blocked address(es) {blocked} — "
            "refusing egress (possible SSRF / DNS poisoning)."
        )
