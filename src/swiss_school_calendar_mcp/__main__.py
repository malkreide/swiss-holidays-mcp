"""Entry point supporting both stdio (Claude Desktop) and HTTP/SSE (cloud).

Security defaults (audit SEC-016): the HTTP transport binds to ``127.0.0.1``
unless ``MCP_HOST`` is set explicitly. Binding to a public interface logs a
warning — the server has no built-in authentication and must sit behind an
authenticating reverse proxy in that case.
"""

from __future__ import annotations

from mcp.server.transport_security import TransportSecuritySettings

from .logging_setup import get_logger, setup_logging
from .server import mcp
from .settings import Settings


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
    origins = {f"http://127.0.0.1:{settings.port}", f"http://localhost:{settings.port}"}
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=sorted(hosts),
        allowed_origins=sorted(origins),
    )


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
        mcp.settings.host = settings.host
        mcp.settings.port = settings.port
        mcp.settings.transport_security = _http_security(settings)
        transport = "sse" if settings.transport.lower() == "sse" else "streamable-http"
        log.info("starting", extra={"context": {"transport": transport, "host": settings.host}})
        mcp.run(transport=transport)
    else:
        get_logger().info("starting", extra={"context": {"transport": "stdio"}})
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
