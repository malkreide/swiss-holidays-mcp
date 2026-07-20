"""Retry, timeout and graceful-degradation tests (no network)."""

import httpx
import pytest
import respx

from swiss_school_calendar_mcp.constants import OPENHOLIDAYS_BASE
from swiss_school_calendar_mcp.server import op_get_school_holidays, op_source_status


@pytest.fixture(autouse=True)
def no_backoff_delay(monkeypatch):
    """Keep the retry logic, drop the wall-clock wait."""

    async def _instant(_seconds: float) -> None:
        return None

    monkeypatch.setattr("swiss_school_calendar_mcp.client.asyncio.sleep", _instant)


@respx.mock
async def test_retries_on_503_then_succeeds(client, zh_school_payload):
    route = respx.get(f"{OPENHOLIDAYS_BASE}/SchoolHolidays").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(503),
            httpx.Response(200, json=zh_school_payload),
        ]
    )
    result = await op_get_school_holidays(client, "CH-ZH", "2026-04-01", "2026-05-31")

    assert route.call_count == 3
    assert result.count == 2
    assert result.provenance == "live_api"


@respx.mock
async def test_network_failure_degrades_gracefully(client):
    respx.get(f"{OPENHOLIDAYS_BASE}/SchoolHolidays").mock(
        side_effect=httpx.ConnectTimeout("upstream down")
    )
    result = await op_get_school_holidays(client, "CH-ZH", "2026-04-01", "2026-05-31")

    assert result.provenance == "degraded"
    assert result.holidays == []
    assert "retry" in (result.note or "").lower()


@respx.mock
async def test_client_error_is_not_retried(client):
    """400 problem+json means our parameters are wrong — retrying is pointless."""
    route = respx.get(f"{OPENHOLIDAYS_BASE}/SchoolHolidays").mock(
        return_value=httpx.Response(400, json={"title": "validation error"})
    )
    result = await op_get_school_holidays(client, "CH-ZH", "2026-04-01", "2026-05-31")

    assert route.call_count == 1
    assert result.provenance == "degraded"


@respx.mock
async def test_degraded_note_masks_internal_error(client):
    """OBS-002: the raw exception must not leak into the tool result."""
    respx.get(f"{OPENHOLIDAYS_BASE}/SchoolHolidays").mock(
        side_effect=httpx.ConnectError("secret-internal-host:5432 refused")
    )
    result = await op_get_school_holidays(client, "CH-ZH", "2026-04-01", "2026-05-31")

    assert result.provenance == "degraded"
    assert "secret-internal-host" not in (result.note or "")


@respx.mock
async def test_source_status_reports_outage(client):
    respx.get(f"{OPENHOLIDAYS_BASE}/Countries").mock(side_effect=httpx.ConnectError("boom"))
    respx.get(url__regex=r".*nager.*").mock(return_value=httpx.Response(200, json=[]))
    result = await op_source_status(client)

    assert result.all_healthy is False
    assert any(s.reachable is False for s in result.sources)
