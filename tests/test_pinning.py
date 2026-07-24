"""DNS-pinning transport tests (audit SEC-005). Offline — no real egress.

Three layers of assurance:
  * the transport rewrites the URL to the pinned IP while keeping Host + SNI on
    the hostname (mechanism, mocked inner transport);
  * ``guard.resolve_pinned`` fails closed on SSRF addresses and picks a safe one;
  * a live loopback connection proves the socket actually goes to the pinned IP
    (plain HTTP), plus a real-TLS check that SNI/cert validation target the
    hostname (skipped where ``cryptography`` is unavailable, e.g. CI).
"""

import asyncio
import socket

import httpx
import pytest

from swiss_holidays_mcp import guard
from swiss_holidays_mcp.pinning import PinnedResolverTransport


class _Capture(httpx.AsyncBaseTransport):
    def __init__(self):
        self.seen = None

    async def handle_async_request(self, request):
        self.seen = request
        return httpx.Response(200, text="ok")


async def test_transport_pins_ip_and_keeps_host_and_sni(monkeypatch):
    monkeypatch.setattr(guard, "resolve_pinned", lambda host: "203.0.113.7")
    cap = _Capture()
    async with httpx.AsyncClient(transport=PinnedResolverTransport(cap)) as c:
        await c.get("https://openholidaysapi.org/Countries")

    assert cap.seen.url.host == "203.0.113.7"  # connection target is the pinned IP
    assert cap.seen.headers["Host"] == "openholidaysapi.org"  # Host stays the name
    assert cap.seen.extensions["sni_hostname"] == "openholidaysapi.org"  # TLS SNI too


def test_resolve_pinned_returns_first_safe_ip(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [
            (2, 1, 6, "", ("169.254.169.254", 443)),  # cloud metadata — blocked
            (2, 1, 6, "", ("8.8.8.8", 443)),  # safe, globally routable
        ],
    )
    assert guard.resolve_pinned("example.org") == "8.8.8.8"


def test_resolve_pinned_refuses_when_only_blocked(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("127.0.0.1", 443)), (2, 1, 6, "", ("10.0.0.1", 443))],
    )
    with pytest.raises(guard.EgressError):
        guard.resolve_pinned("rebind.example")


async def _serve_once(host="127.0.0.1", ssl_ctx=None):
    async def handle(reader, writer):
        await reader.read(1024)
        body = b"pinned-ok"
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n%s" % (len(body), body))
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(handle, host, 0, ssl=ssl_ctx)
    port = server.sockets[0].getsockname()[1]
    return server, port


async def test_live_pin_connects_to_pinned_ip(monkeypatch):
    """A bogus hostname resolves (via the pin) to loopback and the socket lands there."""
    server, port = await _serve_once()
    monkeypatch.setattr(guard, "resolve_pinned", lambda host: "127.0.0.1")
    async with server:
        await server.start_serving()
        transport = PinnedResolverTransport(httpx.AsyncHTTPTransport())
        async with httpx.AsyncClient(transport=transport) as c:
            resp = await c.get(f"http://does-not-resolve.invalid:{port}/")
        assert resp.text == "pinned-ok"


async def test_live_pin_tls_validates_against_hostname(monkeypatch):
    """Pinned to loopback, TLS SNI + cert validation still target the hostname."""
    pytest.importorskip("cryptography")  # skipped in CI (dep not installed)
    import datetime
    import ssl
    import tempfile
    from pathlib import Path

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "pinned.test")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime(2020, 1, 1))
        .not_valid_after(datetime.datetime(2035, 1, 1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("pinned.test")]), critical=False)
        .sign(key, hashes.SHA256())
    )
    tmp = Path(tempfile.mkdtemp())
    certf, keyf = tmp / "c.pem", tmp / "k.pem"
    certf.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    keyf.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    srv_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    srv_ctx.load_cert_chain(certf, keyf)

    server, port = await _serve_once(ssl_ctx=srv_ctx)
    monkeypatch.setattr(guard, "resolve_pinned", lambda host: "127.0.0.1")
    async with server:
        await server.start_serving()
        client_ctx = ssl.create_default_context(cafile=str(certf))
        transport = PinnedResolverTransport(httpx.AsyncHTTPTransport(verify=client_ctx))
        async with httpx.AsyncClient(transport=transport) as c:
            resp = await c.get(f"https://pinned.test:{port}/")
        assert resp.text == "pinned-ok"
