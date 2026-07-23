"""Structured logging: per-call correlation id + tool binding (audit OBS-003)."""

import logging

from swiss_holidays_mcp.logging_setup import (
    _KeyValueFormatter,
    bind_tool_context,
    unbind_tool_context,
)


def _line(event: str = "unit_event") -> str:
    record = logging.LogRecord("swiss_holidays_mcp", logging.INFO, __file__, 1, event, None, None)
    return _KeyValueFormatter().format(record)


def test_bound_context_adds_cid_and_tool():
    tokens = bind_tool_context("get_school_holidays")
    try:
        line = _line()
    finally:
        unbind_tool_context(tokens)
    assert "tool=get_school_holidays" in line
    assert "cid=" in line


def test_context_is_unbound_after_call():
    tokens = bind_tool_context("check_date")
    unbind_tool_context(tokens)
    line = _line()
    assert "tool=" not in line
    assert "cid=" not in line


def test_correlation_id_is_stable_within_a_binding():
    tokens = bind_tool_context("source_status")
    try:
        first = _line()
        second = _line()
    finally:
        unbind_tool_context(tokens)
    cid1 = first.split("cid=")[1].split()[0]
    cid2 = second.split("cid=")[1].split()[0]
    assert cid1 == cid2 and len(cid1) == 12
