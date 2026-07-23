"""Tests for municipality-level holidays and sub-cantonal scope fidelity (no network)."""

import httpx
import respx

from swiss_holidays_mcp.constants import OPENHOLIDAYS_BASE
from swiss_holidays_mcp.server import _to_period, op_get_local_holidays

# A minimal subdivisions tree: canton ZH -> Bezirk Zürich -> Gemeinde Zürich.
_TREE = [
    {
        "code": "CH-ZH",
        "name": [{"language": "DE", "text": "Zürich"}],
        "children": [
            {
                "code": "CH-ZH-ZH",
                "name": [{"language": "DE", "text": "Zürich"}],
                "children": [
                    {"code": "CH-ZH-ZH-ZH", "name": [{"language": "DE", "text": "Zürich"}]},
                    {"code": "CH-ZH-ZH-KI", "name": [{"language": "DE", "text": "Kilchberg"}]},
                ],
            }
        ],
    }
]

# What subdivisionCode=CH-ZH-ZH-ZH returns: one national, one local (half-day).
_ZH_CITY = [
    {
        "startDate": "2026-08-01",
        "endDate": "2026-08-01",
        "name": [{"language": "DE", "text": "Bundesfeiertag"}],
        "regionalScope": "National",
        "temporalScope": "FullDay",
        "nationwide": True,
        "subdivisions": [],
    },
    {
        "startDate": "2026-04-20",
        "endDate": "2026-04-20",
        "name": [{"language": "DE", "text": "Sechseläuten"}],
        "regionalScope": "Local",
        "temporalScope": "HalfDay",
        "nationwide": False,
        "subdivisions": [{"code": "CH-ZH-ZH-ZH", "shortName": "ZH-ZH-ZH"}],
    },
]


def _mock_subdivisions():
    respx.get(f"{OPENHOLIDAYS_BASE}/Subdivisions").mock(
        return_value=httpx.Response(200, json=_TREE)
    )


def test_to_period_scope_and_subdivisions():
    local = _to_period(_ZH_CITY[1], "DE", "Public")
    assert local.scope == "local"
    assert local.half_day is True
    assert local.cantons == ["CH-ZH"]
    assert [(s.code, s.level) for s in local.subdivisions] == [("CH-ZH-ZH-ZH", "municipal")]

    national = _to_period(_ZH_CITY[0], "DE", "Public")
    assert national.scope == "national"
    assert national.subdivisions == []  # nationwide -> no sub-cantonal detail


@respx.mock
async def test_local_holidays_resolves_name(client):
    _mock_subdivisions()
    respx.get(f"{OPENHOLIDAYS_BASE}/PublicHolidays").mock(
        return_value=httpx.Response(200, json=_ZH_CITY)
    )
    resp = await op_get_local_holidays(client, "CH-ZH", "Zürich", 2026)

    assert resp.count == 2
    local = [p for p in resp.holidays if p.scope == "local"]
    assert [p.name for p in local] == ["Sechseläuten"]
    assert local[0].half_day is True
    assert "CH-ZH-ZH-ZH" in resp.note and "Sechseläuten" in resp.note
    assert resp.match_type == "exact"


@respx.mock
async def test_local_holidays_accepts_full_code(client):
    _mock_subdivisions()
    route = respx.get(f"{OPENHOLIDAYS_BASE}/PublicHolidays").mock(
        return_value=httpx.Response(200, json=_ZH_CITY)
    )
    resp = await op_get_local_holidays(client, "CH-ZH", "CH-ZH-ZH-ZH", 2026)

    assert route.called
    # the request carried the resolved municipality code
    assert route.calls.last.request.url.params["subdivisionCode"] == "CH-ZH-ZH-ZH"
    assert resp.count == 2
    assert resp.match_type == "exact"


@respx.mock
async def test_local_holidays_prefix_match_is_fuzzy(client):
    """ARCH-003: a single prefix hit resolves with match_type 'fuzzy' + a caveat."""
    _mock_subdivisions()
    respx.get(f"{OPENHOLIDAYS_BASE}/PublicHolidays").mock(
        return_value=httpx.Response(200, json=_ZH_CITY)
    )
    resp = await op_get_local_holidays(client, "CH-ZH", "Kilch", 2026)

    assert resp.match_type == "fuzzy"
    assert "prefix match" in resp.note


@respx.mock
async def test_local_holidays_unknown_municipality(client):
    _mock_subdivisions()
    resp = await op_get_local_holidays(client, "CH-ZH", "Nirgendwo", 2026)

    assert resp.count == 0
    assert resp.provenance == "degraded"
    assert resp.match_type == "none"
    assert "No district or municipality matching" in resp.note
