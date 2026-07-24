"""Typed configuration (audit ARCH-004).

Configuration comes from a Pydantic-Settings object rather than scattered
``os.environ`` reads, so the transport, bind address and log level are
validated once at startup and are easy to test.

Security default (audit SEC-016): ``host`` defaults to ``127.0.0.1`` (loopback).
Binding to ``0.0.0.0`` is an explicit opt-in and emits a warning at startup —
the server has no built-in authentication.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MCP_", extra="ignore")

    transport: str = Field(default="stdio", description="stdio | sse | streamable-http (aka http)")
    host: str = Field(
        default="127.0.0.1",
        description="Bind address for HTTP transports. Loopback by default (SEC-016).",
    )
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = Field(default="INFO", description="DEBUG | INFO | WARNING | ERROR")
    cors_origins: str = Field(
        default="",
        description="Comma-separated extra CORS allow-origins for HTTP transports "
        "(audit SDK-004). The loopback origins are always included; add the public "
        "origin(s) your browser client is served from here. Never use '*'.",
    )

    @property
    def is_http(self) -> bool:
        return self.transport.lower() in {"sse", "streamable-http", "http"}

    @property
    def binds_all_interfaces(self) -> bool:
        return self.host in {"0.0.0.0", "::"}

    @property
    def cors_origin_list(self) -> list[str]:
        """Explicit CORS allow-list: loopback origins plus any configured extras.

        Deliberately never a wildcard — CORS with credentials requires explicit
        origins, and the server has no built-in auth (SEC-016, SDK-004).
        """
        origins = {
            f"http://127.0.0.1:{self.port}",
            f"http://localhost:{self.port}",
        }
        origins.update(o.strip() for o in self.cors_origins.split(",") if o.strip())
        return sorted(origins)
