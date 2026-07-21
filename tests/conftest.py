import httpx
import pytest
import pytest_asyncio

from swiss_holidays_mcp.client import HolidayClient


@pytest.fixture(autouse=True)
def _no_dns(monkeypatch):
    """Keep unit tests offline: the egress guard's scheme + allow-list check
    still runs, but the DNS/IP resolution is stubbed (respx mocks httpx, not
    the socket layer)."""
    monkeypatch.setattr("swiss_holidays_mcp.guard.assert_resolved_ip_safe", lambda host: None)


@pytest_asyncio.fixture
async def client():
    """A HolidayClient over a real httpx.AsyncClient (respx patches the transport)."""
    async with HolidayClient(httpx.AsyncClient()) as c:
        yield c


@pytest.fixture
def zh_school_payload():
    """Two records for the same period, differentiated by Schulart (real shape)."""
    return [
        {
            "id": "a751cd88",
            "startDate": "2026-04-20",
            "endDate": "2026-05-02",
            "type": "School",
            "name": [{"language": "DE", "text": "Frühlingsferien"}],
            "regionalScope": "Regional",
            "nationwide": False,
            "subdivisions": [{"code": "CH-ZH", "shortName": "ZH"}],
            "groups": [{"code": "CH-ZH-VS", "shortName": "ZH-VS"}],
            "tags": ["Recommended"],
        },
        {
            "id": "9b183e08",
            "startDate": "2026-04-20",
            "endDate": "2026-05-02",
            "type": "School",
            "name": [{"language": "DE", "text": "Frühlingsferien"}],
            "regionalScope": "Regional",
            "nationwide": False,
            "subdivisions": [{"code": "CH-ZH", "shortName": "ZH"}],
            "groups": [
                {"code": "CH-ZH-BS", "shortName": "ZH-BS"},
                {"code": "CH-ZH-MS", "shortName": "ZH-MS"},
            ],
        },
    ]
