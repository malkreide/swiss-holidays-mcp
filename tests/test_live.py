"""Live tests against the real upstream. Excluded from CI via -m "not live"."""

import pytest

from swiss_school_calendar_mcp.server import (
    op_compare_school_holidays,
    op_get_school_holidays,
    op_list_cantons,
    op_list_school_types,
    op_source_status,
)

pytestmark = pytest.mark.live


async def test_live_all_26_cantons(client):
    result = await op_list_cantons(client)
    assert len(result.cantons) == 26


async def test_live_zurich_school_types(client):
    result = await op_list_school_types(client, canton="CH-ZH")
    codes = {t.code for t in result.school_types}
    assert {"CH-ZH-VS", "CH-ZH-MS", "CH-ZH-BS"} <= codes


async def test_live_zurich_volksschule_has_summer_break(client):
    result = await op_get_school_holidays(
        client, "CH-ZH", "2026-01-01", "2026-12-31", school_type="VS"
    )
    names = {h.name for h in result.holidays}
    assert "Sommerferien" in names


async def test_live_overlap_zh_zg(client):
    result = await op_compare_school_holidays(client, ["CH-ZH", "CH-ZG"], 2026)
    assert result.rows and result.rows[0].overlapping_days > 0


async def test_live_sources_healthy(client):
    assert (await op_source_status(client)).all_healthy is True
