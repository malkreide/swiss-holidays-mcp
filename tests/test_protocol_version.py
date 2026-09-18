"""ARCH-012: die beiden Spec-Revisionen, gegen die dieser Server geprueft ist.

`mcp` 2.x bedient ZWEI Protokoll-Aeren ueber denselben Server; die erste
Anfrage einer Verbindung entscheidet, welche gilt:

* die **Legacy-Aera** mit `initialize`-Handshake. Sie deckelt bei
  `LATEST_HANDSHAKE_VERSION`.
* die **Modern-Aera** (Spec `2026-07-28`) mit Pro-Request-Envelope, die
  `LATEST_MODERN_VERSION` erreicht. Sie kennt kein `initialize`: jede Anfrage
  traegt Protokollversion, Client-Info und Client-Capabilities in
  `params._meta`, dazu die Routing-Header `Mcp-Protocol-Version` / `Mcp-Method`
  / `Mcp-Name`.

`source_status` liefert im Feld `mcp_protocol_version` die Revision aus, ueber
die die jeweilige Anfrage hereinkam — gelesen aus `Context.protocol_version`,
nicht aus einer Konstante. Die Konstante `FALLBACK_PROTOCOL_VERSION` greift nur
noch, wo es keinen Request-Kontext gibt.

**Was die vorige Fassung dieses Moduls falsch hatte, zweimal.**

Erstens der Befund: Sie lieferte die Handshake-Obergrenze an *jeden* Aufrufer
aus, mit der Begruendung, das sei die Aera, die ein Client «am ehesten
ausgehandelt» habe. Der Test dazu fuhr den Tool-Aufruf ueber den
In-Process-`Client` und verglich das Ergebnis mit `LATEST_HANDSHAKE_VERSION` —
gruen. Gemessen am 18.9.2026 handelt genau dieser Client aber `2026-07-28` aus.
Der Test bestaetigte also eine Falschauskunft ueber die Verbindung, auf der er
selbst lief. Er war nicht zu schwach, er fragte die falsche Aera ab.

Zweitens der Satz, mit dem die Luecke begruendet wurde: «dieses Repo baut keine
ASGI-App, durch die sich ein `initialize` schicken liesse». Es baut eine —
`mcp.streamable_http_app()`, dieselbe, die `__main__` in Produktion serviert.
Beide Aeren laufen unten durch sie hindurch. Aus «wurde nicht gemessen» war
«ist nicht messbar» geworden, und das hielt die Messung ganze zwei Revisionen
lang auf.
"""

from __future__ import annotations

import json
import pathlib
import re
from typing import Any

import httpx
import pytest
from mcp.shared.inbound import (
    MCP_METHOD_HEADER,
    MCP_NAME_HEADER,
    MCP_PROTOCOL_VERSION_HEADER,
)
from mcp.types.version import (
    LATEST_HANDSHAKE_VERSION,
    LATEST_MODERN_VERSION,
    LATEST_PROTOCOL_VERSION,
)
from mcp_types import (
    CLIENT_CAPABILITIES_META_KEY,
    CLIENT_INFO_META_KEY,
    PROTOCOL_VERSION_META_KEY,
    SERVER_INFO_META_KEY,
)

from swiss_holidays_mcp._version import __version__
from swiss_holidays_mcp.constants import FALLBACK_PROTOCOL_VERSION, HOMEPAGE_URL

REPO = pathlib.Path(__file__).resolve().parents[1]

# Datei und Ueberschrift, unter der die Revisionen dokumentiert stehen.
README_SECTIONS = (
    ("README.md", "## MCP Primitives & Protocol Version"),
    ("README.de.md", "## MCP-Primitive & Protokoll-Version"),
)

# Die beiden Revisionen, die die READMEs nennen. Sie stehen hier und nicht im
# `src/`: der Server setzt sie nicht, das SDK bestimmt sie.
DOCUMENTED_HANDSHAKE_VERSION = "2025-11-25"
DOCUMENTED_MODERN_VERSION = "2026-07-28"


# --------------------------------------------------------------- SDK-Pins


def test_die_moderne_aera_steht_wo_die_readmes_sie_nennen() -> None:
    """Faellt das hier, ist die Loesung nicht, den Wert blind nachzuziehen: erst
    das Spec-Changelog zwischen den beiden Revisionen lesen, das
    Serververhalten pruefen, dann Konstanten, READMEs und `CHANGELOG.md` in
    einem Commit anheben.
    """
    assert LATEST_MODERN_VERSION == DOCUMENTED_MODERN_VERSION, (
        f"das SDK erreicht modern jetzt {LATEST_MODERN_VERSION}, "
        f"die READMEs sagen {DOCUMENTED_MODERN_VERSION}"
    )


def test_der_rueckfall_nennt_die_handshake_obergrenze() -> None:
    """Die Aera, die bestehende Clients sprechen — und der Wert ohne Kontext.

    Ein Client, der ueber den `initialize`-Handshake nach der modernen Revision
    fragt, bekommt diese Obergrenze zurueck, nicht das, wonach er gefragt hat
    (unten gemessen). Deshalb ist sie der Rueckfall, wenn gar nichts
    ausgehandelt wurde.
    """
    assert LATEST_HANDSHAKE_VERSION == DOCUMENTED_HANDSHAKE_VERSION, (
        f"das SDK deckelt den Handshake jetzt bei {LATEST_HANDSHAKE_VERSION}, "
        f"die READMEs sagen {DOCUMENTED_HANDSHAKE_VERSION}"
    )
    assert FALLBACK_PROTOCOL_VERSION == LATEST_HANDSHAKE_VERSION, (
        f"die Konstante nennt {FALLBACK_PROTOCOL_VERSION}, das SDK deckelt bei "
        f"{LATEST_HANDSHAKE_VERSION} — sie ist wieder ein Literal geworden"
    )


def test_latest_protocol_version_ist_der_alias_auf_die_moderne_aera() -> None:
    """Die Falle, gegen die dieses Repo abgesichert wird, benannt.

    Die urspruengliche Zusicherung lautete `PIN == LATEST_PROTOCOL_VERSION` und
    las sich vollstaendig. Sie war es nicht, und man sieht es dem Namen nicht
    an. Faellt dieser Test, hat das SDK die Bedeutung des Alias geaendert —
    dann ist die Aufteilung oben neu zu bewerten, nicht nur eine Zahl.
    """
    assert LATEST_PROTOCOL_VERSION == LATEST_MODERN_VERSION
    assert LATEST_PROTOCOL_VERSION != LATEST_HANDSHAKE_VERSION


def test_die_beiden_aeren_sind_verschieden() -> None:
    """Sagt, wann die Aufteilung oben wieder verschwinden darf: legt das SDK
    die Aeren eines Tages zusammen, ist sie redundant und gehoert zurueckgebaut.
    """
    assert LATEST_MODERN_VERSION > LATEST_HANDSHAKE_VERSION


def test_die_pins_sind_datierte_revisionen_und_keine_beweglichen_ziele() -> None:
    """«latest» oder eine Spanne waeren keine Festlegung."""
    for value in (
        FALLBACK_PROTOCOL_VERSION,
        DOCUMENTED_HANDSHAKE_VERSION,
        DOCUMENTED_MODERN_VERSION,
    ):
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", value), value


def test_beide_readmes_nennen_beide_revisionen() -> None:
    """Ein Pin, den die Doku anders angibt, ist kein Pin.

    Jede Sprache einzeln geprueft: im Portfolio sind EN und DE desselben Repos
    schon dreimal auseinandergelaufen, weil nur eine Fassung nachgezogen wurde
    und niemand die andere daneben gelegt hat.
    """
    for name, anchor in README_SECTIONS:
        text = (REPO / name).read_text(encoding="utf-8")
        parts = text.split(anchor, 1)
        assert len(parts) > 1, f"{name} hat keinen Abschnitt «{anchor}»"
        body = parts[1][:2500]
        for value in (DOCUMENTED_HANDSHAKE_VERSION, DOCUMENTED_MODERN_VERSION):
            assert value in body, f"{name} nennt {value} nicht im Abschnitt «{anchor}»"


# ------------------------------------------------- gemessen, nicht geschlossen
#
# Ab hier laeuft alles durch `__main__._build_http_app` — die ASGI-App, die
# dieses Repo in Produktion serviert, samt Host-Allowlist (SEC-005) und
# CORS-Schicht. Kein zweiter Server, kein In-Process-Kurzschluss: die Aera
# entscheidet sich an dem, was wirklich ueber die Leitung geht.
#
# `BASE_URL` ist nicht beliebig. Die DNS-Rebinding-Abwehr prueft den
# Host-Header gegen `{host}:{port}`; ein Phantasiename wie `mcp.test` bekommt
# `421 Misdirected Request`, bevor ein MCP-Byte fliesst. Hier zuerst passiert,
# und es ist derselbe Mechanismus, den `tests/test_transport_security.py` von
# der anderen Seite prueft.
_HTTP_PORT = 8000
BASE_URL = f"http://127.0.0.1:{_HTTP_PORT}"


def _production_app():
    from swiss_holidays_mcp.__main__ import _build_http_app
    from swiss_holidays_mcp.settings import Settings

    return _build_http_app(Settings(transport="streamable-http", host="127.0.0.1", port=_HTTP_PORT))


@pytest.fixture
def _stubbed_probes(monkeypatch: pytest.MonkeyPatch) -> None:
    """`source_status` ohne Netz.

    Handgeschrieben und trotzdem unbedenklich: geprueft wird hier ausschliesslich
    `mcp_protocol_version`, und dieses Feld beruehrt die Probe nicht. Die
    aufgezeichneten Upstream-Antworten liegen in `tests/test_recorded_fixtures.py`,
    wo sie etwas widerlegen koennen.
    """

    async def _probe(self: Any, name: str, url: str) -> dict[str, Any]:
        return {
            "name": name,
            "base_url": url,
            "reachable": True,
            "http_status": 200,
            "latency_ms": 1,
            "detail": None,
        }

    monkeypatch.setattr("swiss_holidays_mcp.client.HolidayClient.probe", _probe)


def _parse(response: httpx.Response) -> dict[str, Any]:
    """JSON-Body oder erstes SSE-`data:`-Ereignis.

    Die moderne Einstiegsstelle antwortet auf einen stillen Handler mit
    `application/json`, die Legacy-Streamable-HTTP-Strecke mit
    `text/event-stream`. Beide Formen kommen hier vor.
    """
    if response.headers.get("content-type", "").startswith("text/event-stream"):
        for line in response.text.splitlines():
            if line.startswith("data: "):
                return json.loads(line[6:])
        raise AssertionError(f"kein data:-Ereignis im SSE-Body: {response.text!r}")
    return response.json()


def _modern_request(
    method: str, params: dict[str, Any] | None = None, *, name: str | None = None
) -> tuple[dict[str, Any], dict[str, str]]:
    """Body + Header einer Anfrage nach Spec 2026-07-28.

    Der Envelope ist Pflicht: fehlt `params._meta` die Protokollversion oder
    die Client-Capabilities, weist die Klassifizierungsleiter des SDK die
    Anfrage mit `INVALID_PARAMS` ab, bevor ein Handler sie sieht. Die
    Routing-Header muessen dem Body entsprechen, sonst `HEADER_MISMATCH` — und
    genau deshalb muessen sie auch durch CORS kommen (`tests/test_cors.py`).
    """
    body_params = dict(params or {})
    body_params["_meta"] = {
        PROTOCOL_VERSION_META_KEY: LATEST_MODERN_VERSION,
        CLIENT_CAPABILITIES_META_KEY: {},
        CLIENT_INFO_META_KEY: {"name": "pytest", "version": "0"},
    }
    headers = {
        MCP_PROTOCOL_VERSION_HEADER: LATEST_MODERN_VERSION,
        MCP_METHOD_HEADER: method,
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if name is not None:
        headers[MCP_NAME_HEADER] = name
    return {"jsonrpc": "2.0", "id": 1, "method": method, "params": body_params}, headers


async def _post_modern(
    method: str, params: dict[str, Any] | None = None, *, name: str | None = None
) -> dict[str, Any]:
    """Eine Pro-Request-Envelope-Anfrage durch die echte ASGI-App."""
    app = _production_app()
    body, headers = _modern_request(method, params, name=name)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as http:
            response = await http.post("/mcp", json=body, headers=headers)
    assert response.status_code == 200, response.text
    return _parse(response)["result"]


async def _call_tool_over_handshake(asked_version: str) -> tuple[str, dict[str, Any]]:
    """`initialize` + `source_status` durch dieselbe App. Gibt (ausgehandelte
    Revision, Tool-Result) zurueck."""
    app = _production_app()
    base = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as http:
            init = await http.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": asked_version,
                        "capabilities": {},
                        "clientInfo": {"name": "pytest", "version": "0"},
                    },
                },
                headers=base,
            )
            assert init.status_code == 200, init.text
            negotiated = _parse(init)["result"]["protocolVersion"]
            session = {
                **base,
                "Mcp-Session-Id": init.headers["mcp-session-id"],
                "MCP-Protocol-Version": negotiated,
            }
            await http.post(
                "/mcp",
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                headers=session,
            )
            called = await http.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "source_status", "arguments": {}},
                },
                headers=session,
            )
    assert called.status_code == 200, called.text
    return negotiated, _parse(called)["result"]


async def test_ein_moderner_envelope_bekommt_die_moderne_revision_gemeldet(
    _stubbed_probes: None,
) -> None:
    """Der Befund, der diese Aenderung ausgeloest hat.

    Vorher meldete dieselbe Anfrage `2025-11-25` — ueber eine Verbindung, auf
    der `2026-07-28` ausgehandelt war. Wer das wieder auf eine Konstante
    zurueckdreht, faellt hier.
    """
    result = await _post_modern(
        "tools/call", {"name": "source_status", "arguments": {}}, name="source_status"
    )
    assert result["structuredContent"]["mcp_protocol_version"] == LATEST_MODERN_VERSION


async def test_der_handshake_bekommt_seine_obergrenze_gemeldet(_stubbed_probes: None) -> None:
    """Die andere Aera, mit beiden Zweigen gefahren.

    Auch der Client, der im Handshake nach der MODERNEN Revision fragt, bekommt
    die Obergrenze als Gegenangebot — und muss sie gemeldet bekommen, nicht das,
    wonach er gefragt hat. Genau dieser Satz stand bisher als an
    Schwester-Servern gemessen in der README; hier ist er es jetzt selbst.
    """
    for asked in (LATEST_HANDSHAKE_VERSION, LATEST_MODERN_VERSION):
        negotiated, result = await _call_tool_over_handshake(asked)
        assert negotiated == LATEST_HANDSHAKE_VERSION, (
            f"nach {asked} gefragt, {negotiated} ausgehandelt"
        )
        assert result["structuredContent"]["mcp_protocol_version"] == LATEST_HANDSHAKE_VERSION


async def test_ohne_request_kontext_greift_der_rueckfall(client) -> None:
    """Der `op_*`-Layer hat keine Verbindung, ueber die etwas ausgehandelt waere.

    Ein `None` oder ein leeres Feld waere hier schlechter als die
    Handshake-Obergrenze: das Feld ist im Modell nicht optional, und ein
    Aufrufer haette keinen Hinweis, dass die Angabe fehlt.
    """
    import swiss_holidays_mcp.server as server

    async def _probe(name: str, url: str) -> dict[str, Any]:
        return {
            "name": name,
            "base_url": url,
            "reachable": True,
            "http_status": 200,
            "latency_ms": 1,
            "detail": None,
        }

    client.probe = _probe  # type: ignore[method-assign]
    status = await server.op_source_status(client)
    assert status.mcp_protocol_version == FALLBACK_PROTOCOL_VERSION


async def test_discover_nennt_genau_die_modernen_revisionen() -> None:
    """`server/discover` ersetzt `initialize` in der modernen Aera.

    Antwortet es hier mit mehr oder weniger als dem, was das SDK als moderne
    Aera fuehrt, stimmt die Annahme dieses Moduls nicht mehr.
    """
    result = await _post_modern("server/discover")
    assert result["supportedVersions"] == [LATEST_MODERN_VERSION]


async def test_der_serverinfo_stempel_traegt_namen_und_paketversion() -> None:
    """Spec 2026-07-28 kennt kein `initialize` — der `_meta`-Stempel ist alles.

    Ohne `version=` am `MCPServer` stempelt das SDK `""`; es setzt nie eine
    eigene ein. Ein leeres Feld ist schlechter als ein fehlendes, weil es wie
    eine Angabe aussieht: ein Client, der Fassungen unterscheiden will, haette
    nichts zu unterscheiden und wuesste nicht, dass etwas fehlt.
    """
    for method in ("server/discover", "tools/list"):
        stamp = (await _post_modern(method))["_meta"][SERVER_INFO_META_KEY]
        assert stamp["name"] == "swiss-holidays-mcp"
        assert stamp["version"] == __version__, f"{method}: {stamp['version']!r}"
        assert stamp["version"], f"{method}: leere Version gestempelt"
        assert stamp["websiteUrl"] == HOMEPAGE_URL, f"{method}: {stamp.get('websiteUrl')!r}"
