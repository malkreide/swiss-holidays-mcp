"""Inbound Host/Origin pinning on the HTTP transports (audit SEC-005, SDK-004).

The outbound half of SEC-005 (DNS pinning on egress) is covered by
``test_pinning.py``; this file covers the inbound half — the SDK's DNS-rebinding
protection, which ``_build_http_app`` configures from ``_http_security``.

These tests exist because of the mcp 1.x -> 2.x migration. Under 1.x the
allow-list was installed via ``mcp.settings.transport_security = ...``; under
2.x ``Settings`` has no such field and it is a per-app kwarg instead. Nothing in
the pre-existing suite asserted the allow-list was actually *active* — the CORS
tests pass either way — so a migration that dropped it would have gone
unnoticed here. These tests close that gap.
"""

import pytest
from starlette.testclient import TestClient

from swiss_holidays_mcp.__main__ import _build_http_app
from swiss_holidays_mcp.server import mcp
from swiss_holidays_mcp.settings import Settings

_INIT_BODY = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1"},
    },
}
_INIT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def _post_with_host(host: str):
    settings = Settings(transport="streamable-http", host="127.0.0.1", port=8000)
    # The session manager is started by the app's lifespan, so the client must
    # be used as a context manager or the request fails on an uninitialised
    # task group rather than on the Host check.
    with TestClient(_build_http_app(settings)) as client:
        return client.post("/mcp", headers={"Host": host, **_INIT_HEADERS}, json=_INIT_BODY)


def test_allowed_host_reaches_the_server():
    """A Host on the allow-list is served (control for the rejection tests)."""
    assert _post_with_host("127.0.0.1:8000").status_code == 200


def test_foreign_host_header_is_rejected():
    """A Host outside the allow-list is refused before reaching any tool."""
    assert _post_with_host("evil.example.com").status_code == 421


def test_allowed_hostname_on_wrong_port_is_rejected():
    """A right-hostname/wrong-port Host is refused — the load-bearing assertion.

    ``test_foreign_host_header_is_rejected`` alone would be false assurance: if
    ``transport_security`` were dropped, the SDK auto-enables its own localhost
    default on a localhost bind, which also rejects ``evil.example.com``. That
    default allows *any* port (``127.0.0.1:*``), whereas ``_http_security``
    pins the configured one. So this case — and only this case — actually
    distinguishes the explicit allow-list from the SDK fallback, and fails if
    the migration ever stops passing ``transport_security``.
    """
    assert _post_with_host("127.0.0.1:9999").status_code == 421


@pytest.mark.parametrize("field", ["host", "port", "transport_security"])
def test_server_settings_no_longer_accept_transport_fields(field):
    """Regression guard for the 1.x -> 2.x migration.

    ``MCPServer.settings`` dropped these fields; they are per-app/per-run kwargs
    now. Pydantic rejects assignment to an undefined field, so a reintroduced
    ``mcp.settings.<field> = ...`` raises at runtime the moment the HTTP path
    executes. That is loud rather than silent, but it is only reached when the
    HTTP path actually runs — this test makes the contract explicit instead of
    relying on an integration test happening to cover it.
    """
    assert not hasattr(mcp.settings, field)
    with pytest.raises(ValueError, match=f'has no field "{field}"'):
        setattr(mcp.settings, field, "sentinel")
