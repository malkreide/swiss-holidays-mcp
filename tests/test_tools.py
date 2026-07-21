"""Happy-path, filter-logic and input-validation tests (no network)."""

import httpx
import pytest
import respx

from swiss_holidays_mcp.client import normalise_language
from swiss_holidays_mcp.constants import OPENHOLIDAYS_BASE
from swiss_holidays_mcp.guard import EgressError, assert_host_allowed
from swiss_holidays_mcp.server import (
    op_check_date,
    op_get_school_holidays,
    op_list_cantons,
)


@respx.mock
async def test_get_school_holidays_happy_path(client, zh_school_payload):
    respx.get(f"{OPENHOLIDAYS_BASE}/SchoolHolidays").mock(
        return_value=httpx.Response(200, json=zh_school_payload)
    )
    result = await op_get_school_holidays(client, "CH-ZH", "2026-04-01", "2026-05-31")

    assert result.provenance == "live_api"
    assert "CC BY 4.0" in result.source
    assert result.count == 2
    assert result.holidays[0].days == 13
    assert result.holidays[0].cantons == ["CH-ZH"]


@respx.mock
async def test_school_type_filter_separates_volksschule(client, zh_school_payload):
    """FINDING: apparent duplicates are Schulart variants, not noise."""
    respx.get(f"{OPENHOLIDAYS_BASE}/SchoolHolidays").mock(
        return_value=httpx.Response(200, json=zh_school_payload)
    )
    result = await op_get_school_holidays(
        client, "CH-ZH", "2026-04-01", "2026-05-31", school_type="VS"
    )

    assert result.count == 1
    assert result.holidays[0].school_types == ["CH-ZH-VS"]


@respx.mock
async def test_empty_result_sets_explanatory_note(client):
    """A valid canton with no holidays in range returns count 0 + a note (ARCH-003)."""
    respx.get(f"{OPENHOLIDAYS_BASE}/SchoolHolidays").mock(return_value=httpx.Response(200, json=[]))
    result = await op_get_school_holidays(client, "CH-ZH", "2026-01-01", "2026-12-31")

    assert result.count == 0
    assert result.note is not None


async def test_unknown_canton_is_rejected(client):
    """SEC-018: an unknown canton code is a validation error, not a silent empty."""
    with pytest.raises(ValueError, match="Unknown canton"):
        await op_get_school_holidays(client, "CH-XX", "2026-01-01", "2026-12-31")


@respx.mock
async def test_check_date_inside_holiday(client, zh_school_payload):
    respx.get(f"{OPENHOLIDAYS_BASE}/SchoolHolidays").mock(
        return_value=httpx.Response(200, json=zh_school_payload)
    )
    respx.get(f"{OPENHOLIDAYS_BASE}/PublicHolidays").mock(return_value=httpx.Response(200, json=[]))
    result = await op_check_date(client, "2026-04-27", "CH-ZH", school_type="VS")

    assert result.is_school_holiday is True
    assert result.is_public_holiday is False


@respx.mock
async def test_list_cantons_filters_sub_cantonal_codes(client):
    respx.get(f"{OPENHOLIDAYS_BASE}/Subdivisions").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "code": "CH-ZH",
                    "shortName": "ZH",
                    "name": [{"language": "DE", "text": "Zürich"}],
                    "officialLanguages": ["DE"],
                },
                {
                    "code": "CH-AI-AP",
                    "shortName": "AI-AP",
                    "name": [{"language": "DE", "text": "Appenzell"}],
                    "officialLanguages": ["DE"],
                },
            ],
        )
    )
    result = await op_list_cantons(client)
    assert [c.code for c in result.cantons] == ["CH-ZH"]


def test_unsupported_language_rejected_locally():
    """Upstream silently falls back to EN, so we validate before sending."""
    with pytest.raises(ValueError):
        normalise_language("ZZ")


def test_egress_guard_rejects_off_allowlist_host():
    """SEC-004/-021: only the two allow-listed hosts, HTTPS only."""
    assert assert_host_allowed("https://openholidaysapi.org/Countries") == "openholidaysapi.org"
    with pytest.raises(EgressError):
        assert_host_allowed("https://evil.example.com/x")
    with pytest.raises(EgressError):
        assert_host_allowed("http://openholidaysapi.org/x")  # non-HTTPS
