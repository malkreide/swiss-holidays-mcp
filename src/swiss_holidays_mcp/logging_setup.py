"""Structured logging to stderr (audit OBS-003, OBS-004).

Logs go to **stderr** only — stdout is reserved for the stdio JSON-RPC channel
and must never be polluted (OBS-004). The formatter emits a compact
key=value line with a syslog/RFC 5424 severity level, so retries and graceful
degradations are observable without leaking internals into tool results
(OBS-002).
"""

from __future__ import annotations

import contextvars
import logging
import sys
import uuid

_LOGGER_NAME = "swiss_holidays_mcp"

# Per-call bound context (audit OBS-003): a correlation id and the tool name are
# bound for the duration of one tool call via contextvars, so every log line
# emitted while it runs — client retries, graceful-degradation warnings — shares
# the same ``cid`` and ``tool`` without threading them through every function.
_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")
_tool_name: contextvars.ContextVar[str] = contextvars.ContextVar("tool_name", default="")


def bind_tool_context(tool: str) -> tuple[contextvars.Token, contextvars.Token]:
    """Bind a fresh correlation id + tool name for the current logical call.

    Returns the contextvar reset tokens; pass them to ``unbind_tool_context`` in
    a ``finally`` block so nested/concurrent calls do not leak context.
    """
    cid_token = _correlation_id.set(uuid.uuid4().hex[:12])
    tool_token = _tool_name.set(tool)
    return cid_token, tool_token


def unbind_tool_context(tokens: tuple[contextvars.Token, contextvars.Token]) -> None:
    cid_token, tool_token = tokens
    _correlation_id.reset(cid_token)
    _tool_name.reset(tool_token)


class _KeyValueFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = (
            f"ts={self.formatTime(record, '%Y-%m-%dT%H:%M:%S%z')} "
            f"level={record.levelname} logger={record.name}"
        )
        tool = _tool_name.get()
        if tool:
            base += f" tool={tool}"
        cid = _correlation_id.get()
        if cid:
            base += f" cid={cid}"
        base += f" event={record.getMessage()}"
        extra = getattr(record, "context", None)
        if extra:
            base += " " + " ".join(f"{k}={v}" for k, v in extra.items())
        return base


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure the package logger to write structured lines to stderr."""
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level.upper())
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler(stream=sys.stderr)
        handler.setFormatter(_KeyValueFormatter())
        logger.addHandler(handler)
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)
