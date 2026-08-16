"""Jeder externe Endpunkt, gefahren aus einer aufgezeichneten Antwort.

Die handgeschriebenen Stubs im Rest der Suite pruefen die *Fehler*-Pfade — ein
404, ein Timeout, ein leerer Bestand —, die sich nicht auf Zuruf aufzeichnen
lassen und als Erfindung in Ordnung sind. Was sie nicht koennen: die Form einer
Erfolgs-Antwort belegen. Sie stimmen mit dem ueberein, was ihr Autor annahm.
Diese Tests spielen echte Antworten ab, damit ein umbenanntes Feld hier
auffaellt statt in Produktion.

Herkunft, Datum, Auswahlregel und SHA-256 je Datei stehen in
`tests/fixtures/PROVENANCE.md`; neu aufzeichnen mit
`python scripts/record_fixtures.py`.
"""

from __future__ import annotations

import datetime as dt
import re

import httpx
import pytest
import respx
from fixture_data import fixture_json, provenance, recorded_names

from swiss_holidays_mcp.constants import NAGER_BASE, OPENHOLIDAYS_BASE

# Jeder externe Endpunkt dieses Servers und die Aufzeichnungen dazu. Ein
# Endpunkt ohne Aufzeichnung faellt in `test_jeder_endpunkt_hat_eine_aufzeichnung`.
#
# Je Endpunkt eine **Menge**, nicht eine Datei: `/SchoolHolidays` wird in zwei
# Formen abgefragt — mit Kantonsfilter und ohne. Als einzelner Eintrag sah die
# zweite Form aus wie gar keine, und genau daran ist sie lange unbemerkt
# geblieben.
ENDPOINTS = {
    f"{OPENHOLIDAYS_BASE}/Subdivisions": {"subdivisions.json"},
    f"{OPENHOLIDAYS_BASE}/Groups": {"groups.json"},
    f"{OPENHOLIDAYS_BASE}/PublicHolidays": {"public_holidays.json"},
    f"{OPENHOLIDAYS_BASE}/SchoolHolidays": {
        "school_holidays.json",
        "school_holidays_all.json",
    },
    f"{OPENHOLIDAYS_BASE}/Countries": {"countries.json"},
    f"{NAGER_BASE}/LongWeekend": {"long_weekends.json"},
    f"{NAGER_BASE}/AvailableCountries": {"available_countries.json"},
}

#: Alle im Test erwarteten Aufzeichnungen, flach.
ERWARTET = {name for namen in ENDPOINTS.values() for name in namen}

JAHR = 2026
KANTON = "CH-ZH"


def mount(url: str, name: str) -> None:
    """Serviert Fixture `name` unter `url`. Aufgezeichnet wurde durchweg 200."""
    respx.get(url).mock(return_value=httpx.Response(200, json=fixture_json(name)))


def mount_schulferien() -> None:
    """Serviert `/SchoolHolidays` danach, ob ein Kantonsfilter gesetzt ist.

    Das sind zwei Abfrageformen, nicht eine. `op_compare_school_holidays` fragt
    **ohne** `subdivisionCode` ab und gruppiert dann *in* der Antwort nach
    Kanton. Nach URL allein zugeordnet bekam es die kantonale Aufzeichnung — und
    meldete daraufhin fuer jedes Kantonspaar null gemeinsame Tage. Ein
    erfundener Negativbefund, der wie ein Ergebnis aussieht.
    """

    def antwort(request: httpx.Request) -> httpx.Response:
        kanton = request.url.params.get("subdivisionCode")
        name = "school_holidays.json" if kanton else "school_holidays_all.json"
        return httpx.Response(200, json=fixture_json(name))

    respx.get(f"{OPENHOLIDAYS_BASE}/SchoolHolidays").mock(side_effect=antwort)


# --------------------------------------------------------------------------
# Herkunft
# --------------------------------------------------------------------------


def test_provenance_nennt_ein_brauchbares_aufnahmedatum():
    """Eine Aufzeichnung ohne Datum ist eine undatierte Behauptung ueber die Quelle."""
    match = re.search(r"Aufgezeichnet am \*\*(\d{4}-\d{2}-\d{2})\*\*", provenance())
    assert match, "PROVENANCE.md nennt kein Aufnahmedatum im erwarteten Format"
    when = dt.date.fromisoformat(match.group(1))
    assert when <= dt.datetime.now(dt.timezone.utc).date(), "Aufnahmedatum liegt in der Zukunft"


def test_jede_fixture_steht_in_der_provenance():
    """Sonst waechst der Ordner und der Nachweis bleibt zurueck."""
    text = provenance()
    fehlend = [n for n in recorded_names() if f"## `{n}`" not in text]
    assert not fehlend, f"ohne Eintrag in PROVENANCE.md: {fehlend}"


def test_jeder_endpunkt_hat_eine_aufzeichnung():
    """Bewacht die Regel selbst: eine aufgezeichnete Antwort je externem Endpunkt."""
    fehlend = sorted(ERWARTET - set(recorded_names()))
    assert not fehlend, f"Endpunkte ohne Aufzeichnung: {fehlend}"


@pytest.mark.parametrize("name", sorted(ERWARTET))
def test_jede_aufzeichnung_ist_nicht_leer(name):
    """Eine leere Aufzeichnung sieht aus wie eine gueltige und prueft nichts."""
    assert fixture_json(name), f"{name} ist leer — neu aufzeichnen"


# --------------------------------------------------------------------------
# OpenHolidays
# --------------------------------------------------------------------------


@respx.mock
async def test_public_holidays_aus_der_aufzeichnung(client):
    rows = fixture_json("public_holidays.json")
    mount(f"{OPENHOLIDAYS_BASE}/PublicHolidays", "public_holidays.json")
    payload, quelle, _ = await client.public_holidays(
        f"{JAHR}-01-01", f"{JAHR}-12-31", "DE", KANTON
    )
    assert len(payload) == len(rows)
    assert quelle == "live_api"
    # Die Feldnamen der Quelle, nicht die erwarteten. `name` ist eine Liste von
    # Sprachobjekten, kein String — genau die Art Annahme, die ein Stub festschreibt.
    assert all(h["startDate"] for h in payload)
    assert all(isinstance(h["name"], list) and h["name"] for h in payload)
    assert all(h["name"][0]["language"] for h in payload)


@respx.mock
async def test_school_holidays_aus_der_aufzeichnung(client):
    rows = fixture_json("school_holidays.json")
    mount_schulferien()
    payload, _, _ = await client.school_holidays(f"{JAHR}-01-01", f"{JAHR}-12-31", "DE", KANTON)
    assert len(payload) == len(rows)
    assert all(h["startDate"] and h["endDate"] for h in payload)
    assert all(h["startDate"] <= h["endDate"] for h in payload), "Ferien enden nicht vor Beginn"


@respx.mock
async def test_der_kantonsvergleich_findet_ueberhaupt_ueberschneidungen(client):
    """Der Vergleich fragt schweizweit ab und gruppiert *in* der Antwort.

    Mit der kantonalen Aufzeichnung daneben — der einzigen, die es gab — kam
    fuer jedes Kantonspaar null heraus: «keine gemeinsamen Ferientage in der
    ganzen Schweiz». Das ist kein Ergebnis, das ist die Aufzeichnung, die zur
    Abfrage nicht passt.

    Diese Zusicherung faellt, sobald der Vergleich wieder aus einer Antwort
    rechnet, die nur einen Kanton fuehrt.
    """
    from swiss_holidays_mcp import server

    mount_schulferien()
    ergebnis = await server.op_compare_school_holidays(client, ["CH-ZH", "CH-BE", "CH-VD"], JAHR)
    assert ergebnis.rows, "der Vergleich liefert keine Zeilen"
    assert any(r.overlapping_days > 0 for r in ergebnis.rows), (
        "kein einziges Kantonspaar teilt einen Ferientag — die Antwort, aus der "
        "gerechnet wird, fuehrt offenbar nur einen Kanton"
    )


@respx.mock
async def test_die_schweizweite_aufzeichnung_fuehrt_mehr_als_einen_kanton():
    """Sonst belegte die zweite Datei nichts.

    Der Vergleich kann nur finden, was in der Liste steht. Eine schweizweite
    Aufzeichnung, die doch nur einen Kanton fuehrt, waere von der kantonalen
    nicht zu unterscheiden — und der Test darueber waere Zierde.
    """
    alle = fixture_json("school_holidays_all.json")
    kantone = {s.get("code") for e in alle for s in (e.get("subdivisions") or [])}
    assert len(kantone) > 5, f"nur {len(kantone)} Kanton(e) in der Aufzeichnung: {sorted(kantone)}"
    kantonal = fixture_json("school_holidays.json")
    nur_kantonal = {s.get("code") for e in kantonal for s in (e.get("subdivisions") or [])}
    assert nur_kantonal == {KANTON}, f"die kantonale Aufzeichnung fuehrt {nur_kantonal}"


@respx.mock
async def test_subdivisions_aus_der_aufzeichnung(client):
    """Die Aufzeichnung deckt drei Formen ab: tief verschachtelt, flach, ohne `children`."""
    rows = fixture_json("subdivisions.json")
    mount(f"{OPENHOLIDAYS_BASE}/Subdivisions", "subdivisions.json")
    payload, _, _ = await client.subdivisions("DE")
    assert len(payload) == len(rows)
    codes = {s["code"] for s in payload}
    assert "CH-ZH" in codes
    kinderzahl = sorted(len(s.get("children") or []) for s in payload)
    assert kinderzahl[0] == 0, "ein Kanton ohne Untereinheiten gehoert dazu"
    assert kinderzahl[-1] > 0, "ein tief verschachtelter Kanton gehoert dazu"


@respx.mock
async def test_groups_aus_der_aufzeichnung(client):
    rows = fixture_json("groups.json")
    mount(f"{OPENHOLIDAYS_BASE}/Groups", "groups.json")
    payload, _, _ = await client.groups("DE")
    assert len(payload) == len(rows)
    assert all(g.get("code") for g in payload)


# --------------------------------------------------------------------------
# Nager.Date
# --------------------------------------------------------------------------


@respx.mock
async def test_long_weekends_aus_der_aufzeichnung(client):
    rows = fixture_json("long_weekends.json")
    mount(f"{NAGER_BASE}/LongWeekend/{JAHR}/CH", "long_weekends.json")
    payload, _, _ = await client.long_weekends(JAHR)
    assert len(payload) == len(rows)
    assert all(w["startDate"] and w["endDate"] for w in payload)
    assert all(w["dayCount"] >= 3 for w in payload), "ein langes Wochenende hat mindestens 3 Tage"


def test_die_beiden_quellen_benennen_ihre_felder_verschieden():
    """Haelt einen Unterschied fest, den nur eine Aufzeichnung zeigen kann.

    OpenHolidays fuehrt `name` als Liste von Sprachobjekten, Nager.Date kennt
    dieses Feld gar nicht und liefert `dayCount`. Ein handgeschriebener Stub
    haette beide Quellen leicht gleich geformt — und der Unterschied waere erst
    produktiv aufgefallen.
    """
    feiertag = fixture_json("public_holidays.json")[0]
    wochenende = fixture_json("long_weekends.json")[0]
    assert isinstance(feiertag["name"], list)
    assert "name" not in wochenende
    assert "dayCount" in wochenende


# --------------------------------------------------------------------------
# Der Nachweis, nachgerechnet
# --------------------------------------------------------------------------
@pytest.mark.parametrize("name", sorted(n for n in recorded_names() if n != "PROVENANCE.md"))
def test_die_pruefsumme_im_nachweis_stimmt(name):
    """Eine Pruefsumme, die niemand nachrechnet, ist Zierde.

    Sie steht im Nachweis, um genau einen Fall zu fangen: eine Aufzeichnung,
    die nach dem Lauf von Hand nachgebessert wurde. Eine korrigierte Antwort
    ist wieder eine erfundene — und von aussen ist ihr das nicht anzusehen.
    Ohne diesen Test faengt die Summe nichts.

    Gerechnet wird ueber die Bytes auf der Platte, nicht ueber den Loader:
    genau die hat der Recorder gehasht, und ein Loader, der unterwegs dekodiert
    oder normalisiert, wuerde die Pruefung gegen sich selbst fuehren.
    """
    import hashlib
    import re
    from pathlib import Path

    teile = provenance().split(f"## `{name}`", 1)
    assert len(teile) == 2, f"{name} hat keinen Block in PROVENANCE.md"
    treffer = re.search(r"\*\*SHA-256:\*\*\s*`([0-9a-f]{64})`", teile[1].split("## ", 1)[0])
    assert treffer, f"{name} steht ohne Pruefsumme im Nachweis"
    roh = (Path(__file__).resolve().parent / "fixtures" / name).read_bytes()
    assert hashlib.sha256(roh).hexdigest() == treffer.group(1), (
        f"{name} weicht vom Nachweis ab — von Hand nachgebessert? Neu aufzeichnen."
    )
