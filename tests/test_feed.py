"""Tests for the holiday bundle / ICS export / resource feed (no network)."""

import httpx
import respx

from swiss_holidays_mcp.constants import OPENHOLIDAYS_BASE
from swiss_holidays_mcp.ical import build_ics
from swiss_holidays_mcp.server import _bundle_markdown, op_holidays_bundle

_NEUJAHR = [
    {
        "startDate": "2026-01-01",
        "endDate": "2026-01-01",
        "name": [{"language": "DE", "text": "Neujahr"}],
        "nationwide": True,
        "subdivisions": [{"code": "CH-ZH"}],
    }
]


@respx.mock
async def test_bundle_combines_and_sorts(client, zh_school_payload):
    respx.get(f"{OPENHOLIDAYS_BASE}/SchoolHolidays").mock(
        return_value=httpx.Response(200, json=zh_school_payload)
    )
    respx.get(f"{OPENHOLIDAYS_BASE}/PublicHolidays").mock(
        return_value=httpx.Response(200, json=_NEUJAHR)
    )
    canton, periods, provenance, _ = await op_holidays_bundle(client, "CH-ZH", 2026)

    assert canton == "CH-ZH"
    assert {p.kind for p in periods} == {"School", "Public"}
    assert periods[0].name == "Neujahr"  # 1 Jan sorts before the spring break

    # feeds built from the bundle
    md = _bundle_markdown(canton, 2026, periods, "src")
    assert "## Public holidays" in md and "## School holidays" in md
    ics = build_ics((p.model_dump() for p in periods), calendar_name="c", source="src")
    assert ics.count("BEGIN:VEVENT") == len(periods)


@respx.mock
async def test_bundle_include_public_only(client):
    route = respx.get(f"{OPENHOLIDAYS_BASE}/PublicHolidays").mock(
        return_value=httpx.Response(200, json=_NEUJAHR)
    )
    canton, periods, _, _ = await op_holidays_bundle(client, "CH-ZH", 2026, include="public")

    assert route.called
    assert [p.kind for p in periods] == ["Public"]


@respx.mock
async def test_bundle_school_type_filter(client, zh_school_payload):
    respx.get(f"{OPENHOLIDAYS_BASE}/SchoolHolidays").mock(
        return_value=httpx.Response(200, json=zh_school_payload)
    )
    _, periods, _, _ = await op_holidays_bundle(
        client, "CH-ZH", 2026, include="school", school_type="VS"
    )
    assert len(periods) == 1
    assert periods[0].school_types == ["CH-ZH-VS"]
