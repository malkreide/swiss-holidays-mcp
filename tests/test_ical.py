"""Unit tests for the iCalendar writer (pure, no network)."""

from datetime import date, datetime, timezone

from swiss_holidays_mcp.ical import build_ics

_STAMP = datetime(2026, 7, 21, 16, 0, 0, tzinfo=timezone.utc)


def test_build_ics_structure():
    periods = [
        {
            "start_date": date(2026, 4, 20),
            "end_date": date(2026, 5, 2),
            "name": "Frühlingsferien",
            "kind": "School",
            "cantons": ["CH-ZH"],
        }
    ]
    ics = build_ics(
        periods, calendar_name="Swiss holidays CH-ZH 2026", source="OpenHolidays", dtstamp=_STAMP
    )

    assert ics.startswith("BEGIN:VCALENDAR\r\n")
    assert ics.rstrip().endswith("END:VCALENDAR")
    assert "\r\n" in ics  # CRLF line endings per RFC 5545
    assert "BEGIN:VEVENT" in ics
    assert "DTSTART;VALUE=DATE:20260420" in ics
    assert "DTEND;VALUE=DATE:20260503" in ics  # exclusive end (end + 1 day)
    assert "CATEGORIES:SCHOOL_HOLIDAY" in ics
    assert "TRANSP:TRANSPARENT" in ics
    assert "DTSTAMP:20260721T160000Z" in ics
    assert "SUMMARY:Frühlingsferien (CH-ZH)" in ics


def test_ics_escapes_special_chars_and_public_category():
    periods = [
        {
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 1, 1),
            "name": "New; Year, Day",
            "kind": "Public",
            "cantons": [],
        }
    ]
    ics = build_ics(periods, calendar_name="c", source="s", dtstamp=_STAMP)

    assert "SUMMARY:New\\; Year\\, Day" in ics
    assert "CATEGORIES:PUBLIC_HOLIDAY" in ics
    assert "DTEND;VALUE=DATE:20260102" in ics  # single day → exclusive next day


def test_empty_calendar_still_valid():
    ics = build_ics([], calendar_name="empty", source="s", dtstamp=_STAMP)
    assert "BEGIN:VCALENDAR" in ics and "END:VCALENDAR" in ics
    assert "BEGIN:VEVENT" not in ics
