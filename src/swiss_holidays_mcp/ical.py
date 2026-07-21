"""Minimal RFC 5545 (iCalendar) writer for holiday periods.

Hand-rolled on purpose — an ICS file for all-day holiday events is a small,
well-specified text format, and avoiding a third-party dependency keeps the
egress/supply-chain surface (audit ARCH-005, SEC-013) unchanged.

Each holiday period becomes an all-day ``VEVENT`` with a ``DATE``-valued
``DTSTART`` and an **exclusive** ``DTEND`` (end date + 1 day, per the spec),
marked ``TRANSP:TRANSPARENT`` so it does not block time in a calendar.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date, datetime, timedelta, timezone

PRODID = "-//malkreide//swiss-holidays-mcp//EN"

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _escape(text: str) -> str:
    """Escape TEXT values per RFC 5545 §3.3.11."""
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    """Fold a content line to <=75 octets with CRLF + single space (§3.1)."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    chunks: list[bytes] = []
    while len(raw) > 75:
        # Never split a multi-byte UTF-8 sequence: back off to a lead byte.
        cut = 75
        while cut > 0 and (raw[cut] & 0xC0) == 0x80:
            cut -= 1
        chunks.append(raw[:cut])
        raw = raw[cut:]
    chunks.append(raw)
    return "\r\n ".join(c.decode("utf-8") for c in chunks)


def _slug(text: str) -> str:
    return _SLUG_RE.sub("-", text.lower()).strip("-") or "holiday"


def _uid(period: dict) -> str:
    start = period["start_date"]
    end = period["end_date"]
    return (
        f"{start:%Y%m%d}-{end:%Y%m%d}-{period['kind'].lower()}-"
        f"{_slug(period['name'])}@swiss-holidays-mcp"
    )


def build_ics(
    periods: Iterable[dict],
    *,
    calendar_name: str,
    source: str,
    dtstamp: datetime | None = None,
) -> str:
    """Render ``periods`` as an iCalendar (``text/calendar``) document.

    Each period is a mapping with ``start_date`` / ``end_date`` (``date``),
    ``name`` (str), ``kind`` (``"School"`` | ``"Public"``) and optional
    ``cantons`` (list[str]).
    """
    stamp = (dtstamp or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        _fold(f"X-WR-CALNAME:{_escape(calendar_name)}"),
        _fold(f"X-WR-CALDESC:{_escape(source)}"),
    ]
    for period in periods:
        start: date = period["start_date"]
        end_exclusive: date = period["end_date"] + timedelta(days=1)
        cantons = ", ".join(period.get("cantons") or [])
        summary = period["name"] + (f" ({cantons})" if cantons else "")
        category = "PUBLIC_HOLIDAY" if period["kind"] == "Public" else "SCHOOL_HOLIDAY"
        lines += [
            "BEGIN:VEVENT",
            _fold(f"UID:{_uid(period)}"),
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{start:%Y%m%d}",
            f"DTEND;VALUE=DATE:{end_exclusive:%Y%m%d}",
            _fold(f"SUMMARY:{_escape(summary)}"),
            f"CATEGORIES:{category}",
            "TRANSP:TRANSPARENT",
            _fold(f"DESCRIPTION:{_escape(source)}"),
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
