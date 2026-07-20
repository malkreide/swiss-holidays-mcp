"""Live tests against the real upstream. Excluded from CI via -m "not live"."""

import pytest

from swiss_school_calendar_mcp.server import (
    compare_school_holidays,
    get_school_holidays,
    list_cantons,
    list_school_types,
    source_status,
)

pytestmark = pytest.mark.live


async def test_live_all_26_cantons():
    result = await list_cantons()
    assert len(result.cantons) == 26


async def test_live_zurich_school_types():
    result = await list_school_types(canton="CH-ZH")
    codes = {t.code for t in result.school_types}
    assert {"CH-ZH-VS", "CH-ZH-MS", "CH-ZH-BS"} <= codes


async def test_live_zurich_volksschule_has_summer_break():
    result = await get_school_holidays(
        "CH-ZH", "2026-01-01", "2026-12-31", school_type="VS"
    )
    names = {h.name for h in result.holidays}
    assert "Sommerferien" in names


async def test_live_overlap_zh_zg():
    result = await compare_school_holidays(["CH-ZH", "CH-ZG"], 2026)
    assert result.rows and result.rows[0].overlapping_days > 0


async def test_live_sources_healthy():
    assert (await source_status()).all_healthy is True
