"""Structured logging to stderr (audit OBS-003, OBS-004).

Logs go to **stderr** only — stdout is reserved for the stdio JSON-RPC channel
and must never be polluted (OBS-004). The formatter emits a compact
key=value line with a syslog/RFC 5424 severity level, so retries and graceful
degradations are observable without leaking internals into tool results
(OBS-002).
"""

from __future__ import annotations

import logging
import sys

_LOGGER_NAME = "swiss_holidays_mcp"


class _KeyValueFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = (
            f"ts={self.formatTime(record, '%Y-%m-%dT%H:%M:%S%z')} "
            f"level={record.levelname} logger={record.name} "
            f"event={record.getMessage()}"
        )
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
