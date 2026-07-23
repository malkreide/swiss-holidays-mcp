"""HTTP transport CORS wiring (audit SDK-004). No network — Starlette TestClient."""

from starlette.testclient import TestClient

from swiss_holidays_mcp.__main__ import _build_http_app
from swiss_holidays_mcp.settings import Settings


def test_streamable_http_cors_allows_and_exposes_session_id():
    settings = Settings(transport="streamable-http", host="127.0.0.1", port=8000)
    app = _build_http_app(settings)
    client = TestClient(app)
    resp = client.options(
        "/mcp",
        headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Mcp-Session-Id",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:8000"
    assert "mcp-session-id" in resp.headers.get("access-control-allow-headers", "").lower()


def test_cors_origin_list_is_never_wildcard_and_includes_extras():
    settings = Settings(transport="streamable-http", port=9000, cors_origins="https://ui.example.ch")
    origins = settings.cors_origin_list
    assert "*" not in origins
    assert "https://ui.example.ch" in origins
    assert "http://127.0.0.1:9000" in origins


def test_cross_origin_not_on_allowlist_is_refused():
    settings = Settings(transport="streamable-http", host="127.0.0.1", port=8000)
    app = _build_http_app(settings)
    client = TestClient(app)
    resp = client.options(
        "/mcp",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    # CORSMiddleware does not echo an allow-origin for a disallowed origin.
    assert resp.headers.get("access-control-allow-origin") != "https://evil.example.com"
