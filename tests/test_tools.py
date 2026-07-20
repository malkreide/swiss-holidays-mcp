"""Happy-path and filter-logic tests (no network)."""

import httpx
import pytest
import respx

from swiss_school_calendar_mcp.client import normalise_language
from swiss_school_calendar_mcp.constants import OPENHOLIDAYS_BASE
from swiss_school_calendar_mcp.server import (
    check_date,
    get_school_holidays,
    list_cantons,
)


@respx.mock
async def test_get_school_holidays_happy_path(zh_school_payload):
    respx.get(f"{OPENHOLIDAYS_BASE}/SchoolHolidays").mock(
        return_value=httpx.Response(200, json=zh_school_payload)
    )
    result = await get_school_holidays("CH-ZH", "2026-04-01", "2026-05-31")

    assert result.provenance == "live_api"
    assert "CC BY 4.0" in result.source
    assert result.count == 2
    assert result.holidays[0].days == 13
    assert result.holidays[0].cantons == ["CH-ZH"]


@respx.mock
async def test_school_type_filter_separates_volksschule(zh_school_payload):
    """FINDING: apparent duplicates are Schulart variants, not noise."""
    respx.get(f"{OPENHOLIDAYS_BASE}/SchoolHolidays").mock(
        return_value=httpx.Response(200, json=zh_school_payload)
    )
    result = await get_school_holidays("CH-ZH", "2026-04-01", "2026-05-31", school_type="VS")

    assert result.count == 1
    assert result.holidays[0].school_types == ["CH-ZH-VS"]


@respx.mock
async def test_empty_result_sets_explanatory_note():
    """An unknown canton yields HTTP 200 + [] upstream — never a 404."""
    respx.get(f"{OPENHOLIDAYS_BASE}/SchoolHolidays").mock(return_value=httpx.Response(200, json=[]))
    result = await get_school_holidays("CH-XX", "2026-01-01", "2026-12-31")

    assert result.count == 0
    assert result.note is not None
    assert "unknown code" in result.note


@respx.mock
async def test_check_date_inside_holiday(zh_school_payload):
    respx.get(f"{OPENHOLIDAYS_BASE}/SchoolHolidays").mock(
        return_value=httpx.Response(200, json=zh_school_payload)
    )
    respx.get(f"{OPENHOLIDAYS_BASE}/PublicHolidays").mock(return_value=httpx.Response(200, json=[]))
    result = await check_date("2026-04-27", "CH-ZH", school_type="VS")

    assert result.is_school_holiday is True
    assert result.is_public_holiday is False


@respx.mock
async def test_list_cantons_filters_sub_cantonal_codes():
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
    result = await list_cantons()
    assert [c.code for c in result.cantons] == ["CH-ZH"]


def test_unsupported_language_rejected_locally():
    """Upstream silently falls back to EN, so we validate before sending."""
    with pytest.raises(ValueError):
        normalise_language("ZZ")
