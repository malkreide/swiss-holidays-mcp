"""Entry point supporting both stdio (Claude Desktop) and HTTP/SSE (cloud).

Security defaults (audit SEC-016): the HTTP transport binds to ``127.0.0.1``
unless ``MCP_HOST`` is set explicitly. Binding to a public interface logs a
warning — the server has no built-in authentication and must sit behind an
authenticating reverse proxy in that case.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.transport_security import TransportSecuritySettings

from .logging_setup import get_logger, setup_logging
from .server import mcp
from .settings import Settings

if TYPE_CHECKING:
    from starlette.applications import Starlette

# Headers a browser MCP client must be allowed to send / read on HTTP transports
# (audit SDK-004). Mcp-Session-Id is the one that matters: without exposing it,
# a cross-origin client cannot read the session id and cannot make follow-ups.
_CORS_ALLOW_HEADERS = ["Content-Type", "Mcp-Session-Id", "Last-Event-ID", "MCP-Protocol-Version"]
_CORS_EXPOSE_HEADERS = ["Mcp-Session-Id"]
_CORS_ALLOW_METHODS = ["GET", "POST", "DELETE", "OPTIONS"]


def _http_security(settings: Settings) -> TransportSecuritySettings:
    """Host/Origin allow-list for the HTTP transport (audit SEC-005, SDK-004).

    Enables the SDK's DNS-rebinding protection and pins the Host/Origin headers
    the server will accept. Behind a reverse proxy, extend MCP_HOST accordingly.
    """
    hosts = {
        f"{settings.host}:{settings.port}",
        f"127.0.0.1:{settings.port}",
        f"localhost:{settings.port}",
    }
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=sorted(hosts),
        allowed_origins=settings.cors_origin_list,
    )


def _build_http_app(settings: Settings) -> Starlette:
    """Build the Starlette app for the selected HTTP transport, with CORS (SDK-004).

    ``mcp.run(transport=...)`` builds the app internally and gives no hook to add
    middleware, so the HTTP path constructs the app here, attaches an explicit
    (never wildcard) CORS layer that exposes ``Mcp-Session-Id``, and is served by
    ``main`` via uvicorn.
    """
    from starlette.middleware.cors import CORSMiddleware

    mcp.settings.host = settings.host
    mcp.settings.port = settings.port
    mcp.settings.transport_security = _http_security(settings)

    app = mcp.sse_app() if settings.transport.lower() == "sse" else mcp.streamable_http_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=_CORS_ALLOW_METHODS,
        allow_headers=_CORS_ALLOW_HEADERS,
        expose_headers=_CORS_EXPOSE_HEADERS,
    )
    return app


def main() -> None:
    settings = Settings()
    log = setup_logging(settings.log_level)

    if settings.is_http:
        if settings.binds_all_interfaces:
            log.warning(
                "binding_all_interfaces",
                extra={
                    "context": {
                        "host": settings.host,
                        "hint": "no built-in auth; use a reverse proxy or MCP_HOST=127.0.0.1",
                    }
                },
            )
        transport = "sse" if settings.transport.lower() == "sse" else "streamable-http"
        app = _build_http_app(settings)
        log.info("starting", extra={"context": {"transport": transport, "host": settings.host}})

        import uvicorn

        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
        )
    else:
        get_logger().info("starting", extra={"context": {"transport": "stdio"}})
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
