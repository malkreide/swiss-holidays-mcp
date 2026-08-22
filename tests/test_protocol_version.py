"""ARCH-012: der Protokoll-Pin wird an Aufrufer ausgeliefert — er muss stimmen.

`MCP_PROTOCOL_VERSION` ist hier keine Doku-Zeile. `op_source_status` gibt ihn
als Feld `mcp_protocol_version` in der Antwort zurueck; ein Modell liest das
als Tatsache ueber diesen Server.

Der Wert stand auf `2025-06-18` — zwei Revisionen hinter dem `2026-07-28`, das
das gepinnte SDK spricht. Jede `source_status`-Abfrage hat diese veraltete
Angabe als Tatsache ausgeliefert. Aufgefallen ist es nicht, weil ihn nichts mit
irgendetwas verglichen hat.

Der Vergleich steht jetzt hier: gegen das, was das installierte SDK tatsaechlich
aushandelt.
"""

from __future__ import annotations

import re

from mcp.types import LATEST_PROTOCOL_VERSION

from swiss_holidays_mcp.constants import MCP_PROTOCOL_VERSION


def test_der_pin_nennt_die_revision_des_installierten_sdk() -> None:
    """Faellt, wenn ein SDK-Update die Protokollversion verschiebt.

    Die Loesung ist dann nicht, die Konstante blind nachzuziehen: erst das
    Spec-Changelog lesen, das Serververhalten pruefen, dann Konstante und
    `CHANGELOG.md` in einem Commit anheben.
    """
    assert MCP_PROTOCOL_VERSION == LATEST_PROTOCOL_VERSION, (
        f"gepinnt {MCP_PROTOCOL_VERSION}, das SDK handelt {LATEST_PROTOCOL_VERSION} aus"
    )


def test_der_pin_ist_ein_datum_und_kein_bewegliches_ziel() -> None:
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", MCP_PROTOCOL_VERSION), MCP_PROTOCOL_VERSION


async def test_source_status_liefert_genau_diesen_pin_aus() -> None:
    """Die Zusicherung, die den Unterschied zu einer Doku-Zeile macht.

    Ohne sie koennte die Konstante stimmen und das Feld trotzdem etwas anderes
    tragen — und dieses Feld ist es, das beim Aufrufer ankommt.
    """
    from swiss_holidays_mcp.models import StatusResponse

    assert "mcp_protocol_version" in StatusResponse.model_fields, (
        "source_status traegt das Feld nicht mehr — dann gehoert dieser Test angepasst, "
        "nicht geloescht"
    )
