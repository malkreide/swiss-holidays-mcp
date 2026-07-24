"""DNS-pinning HTTP transport (audit SEC-005).

The egress guard resolves and validates the upstream host, but by default httpx
re-resolves at connect time — leaving a TOCTOU window in which a poisoned
resolver could rebind an allow-listed host to an internal address between the
check and the connection.

``PinnedResolverTransport`` closes that window for **direct** connections: it
resolves each request's host **once** to an SSRF-safe IP (``guard.resolve_pinned``)
and pins the TCP connection to exactly that IP, while the TLS SNI and the
certificate hostname check still use the original hostname. The resolved IP is
the one actually connected to — there is no second lookup.

It is deliberately **not** installed when a forward proxy is configured (see
``client.build_http_client``): the proxy owns DNS resolution then, and rewriting
the URL to an IP would break the proxy ``CONNECT``. In that case the guard's
IP check remains, and a network-layer egress policy is the recommended control
(``deploy/`` + docs/network-egress.md).
"""

from __future__ import annotations

import httpx

from . import guard


class PinnedResolverTransport(httpx.AsyncBaseTransport):
    """Wrap an inner transport, pinning each request to a pre-validated IP."""

    def __init__(self, inner: httpx.AsyncBaseTransport) -> None:
        self._inner = inner

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        # Resolve once + SSRF-validate; this exact IP is what we connect to.
        ip = guard.resolve_pinned(host)
        port = request.url.port
        # Keep the Host header and TLS SNI / cert validation on the real hostname.
        request.headers["Host"] = f"{host}:{port}" if port else host
        request.extensions = {**request.extensions, "sni_hostname": host}
        request.url = request.url.copy_with(host=ip)
        return await self._inner.handle_async_request(request)

    async def aclose(self) -> None:
        await self._inner.aclose()
