import pytest


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
