#!/usr/bin/env python3
"""Zeichnet echte Antworten der beiden Quellen nach `tests/fixtures/` auf.

Warum: eine handgeschriebene Fixture kodiert die Annahme ihres Autors und kann
sie deshalb nicht widerlegen. In `i14y-mcp` blieb genau deshalb eine ganze Suite
gruen, waehrend drei Tools produktiv leere Titel lieferten — die Stubs hatten
einen Schluessel erfunden und stimmten dem Mapper zu statt der Quelle.

Herkunft, Datum, Auswahlregel und SHA-256 je Datei schreibt dieses Skript nach
`tests/fixtures/PROVENANCE.md`. Neu aufzeichnen:

    python scripts/record_fixtures.py

Braucht Netzzugang zu `openholidaysapi.org` und `date.nager.at`.
Entwicklungswerkzeug; weder das Paket noch die Testsuite importieren es.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

OPENHOLIDAYS = "https://openholidaysapi.org"
NAGER = "https://date.nager.at/api/v3"
FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

# Festes Jahr und fester Kanton, nicht «dieses Jahr» und nicht «hier»: eine
# Auswahl, die vom Zeitpunkt des Laufs abhaengt, erzeugt bei jedem Aufzeichnen
# einen anderen Diff, ohne dass sich an der Quelle etwas geaendert haette.
YEAR = 2026
SUBDIVISION = "CH-ZH"
LANGUAGE = "DE"

# Drei Kantone mit Absicht, nicht die ersten drei: ZH ist tief verschachtelt und
# fuehrt Schultypen, BS traegt wenige Untereinheiten, AR gar keine. Damit belegt
# die Aufzeichnung alle drei Formen, die der Code unterscheiden muss. Der
# Vollabzug waere 399 kB, fast alles davon `children`.
SUBDIVISION_CODES = ("CH-ZH", "CH-BS", "CH-AR")
GROUP_COUNT = 3


def get(base: str, path: str, params: dict[str, Any] | None = None) -> tuple[str, Any, str]:
    url = f"{base}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"
    req = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "swiss-holidays-mcp-recorder"},
    )
    with urlopen(req, timeout=90) as resp:
        raw = resp.read().decode("utf-8")
    return raw, json.loads(raw), url


def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    recorded_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entries: list[dict[str, Any]] = []
    print(f"Zeichne auf von {OPENHOLIDAYS} und {NAGER}")

    def write(name: str, payload: Any, url: str, rule: str) -> None:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        (FIXTURES / name).write_text(text, encoding="utf-8")
        blob = text.encode("utf-8")
        entries.append(
            {
                "name": name,
                "url": url,
                "rule": rule,
                "bytes": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(),
            }
        )
        print(f"  ok  {name:<28} {len(blob):>7} B")

    base_params = {"countryIsoCode": "CH", "languageIsoCode": LANGUAGE}
    span = {"validFrom": f"{YEAR}-01-01", "validTo": f"{YEAR}-12-31"}

    # --- OpenHolidays ----------------------------------------------------
    _, subdivisions, url = get(OPENHOLIDAYS, "/Subdivisions", base_params)
    picked = [s for s in subdivisions if s.get("code") in SUBDIVISION_CODES]
    if len(picked) != len(SUBDIVISION_CODES):
        got = sorted(s.get("code") for s in subdivisions)
        print(f"!! nicht alle gewaehlten Kantone gefunden. Vorhanden: {got}")
        return 1
    write(
        "subdivisions.json",
        picked,
        url,
        f"{len(picked)} von {len(subdivisions)} Kantonen: {', '.join(SUBDIVISION_CODES)} — "
        "tief verschachtelt, flach und ganz ohne `children`; Satzform unangetastet",
    )

    _, groups, url = get(OPENHOLIDAYS, "/Groups", base_params)
    write(
        "groups.json",
        groups[:GROUP_COUNT],
        url,
        f"die ersten {GROUP_COUNT} von {len(groups)} Gruppen; Satzform unangetastet",
    )

    params = {**base_params, **span, "subdivisionCode": SUBDIVISION}
    _, public, url = get(OPENHOLIDAYS, "/PublicHolidays", params)
    write(
        "public_holidays.json",
        public,
        url,
        f"vollstaendig; {SUBDIVISION}, Jahr {YEAR} ({len(public)} Feiertage)",
    )

    _, school, url = get(OPENHOLIDAYS, "/SchoolHolidays", params)
    write(
        "school_holidays.json",
        school,
        url,
        f"vollstaendig; {SUBDIVISION}, Jahr {YEAR} ({len(school)} Ferien)",
    )

    _, countries, url = get(OPENHOLIDAYS, "/Countries", {"languageIsoCode": LANGUAGE})
    write(
        "countries.json", countries, url, f"vollstaendig; {len(countries)} Laender (Health-Probe)"
    )

    # --- Nager.Date ------------------------------------------------------
    _, long_weekends, url = get(NAGER, f"/LongWeekend/{YEAR}/CH")
    write(
        "long_weekends.json",
        long_weekends,
        url,
        f"vollstaendig; Jahr {YEAR}, CH ({len(long_weekends)} lange Wochenenden)",
    )

    _, available, url = get(NAGER, "/AvailableCountries")
    write(
        "available_countries.json",
        available,
        url,
        f"vollstaendig; {len(available)} Laender (Health-Probe)",
    )

    _write_provenance(recorded_at, entries)
    print(f"\nPROVENANCE.md geschrieben, Aufzeichnungsdatum {recorded_at}")
    return 0


def _write_provenance(recorded_at: str, entries: list[dict[str, Any]]) -> None:
    lines = [
        "# Herkunft der Fixtures",
        "",
        "**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**",
        "",
        f"Aufgezeichnet am **{recorded_at}** von den beiden Quellen dieses Servers:",
        f"`{OPENHOLIDAYS}` und `{NAGER}`.",
        "",
        "Ohne Datum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht",
        "mehr zu unterscheiden — die Datei sieht gleich aus.",
        "",
        "**Feiertage altern jahrweise.** Diese Fixtures belegen die *Form* der",
        f"Antwort und den Stand fuer ein festes Jahr ({YEAR}) und einen festen",
        f"Kanton ({SUBDIVISION}) — nicht «dieses Jahr». Waere die Auswahl vom",
        "Zeitpunkt des Laufs abhaengig, erzeugte jedes Aufzeichnen einen anderen",
        "Diff, ohne dass sich an der Quelle etwas geaendert haette. Zusicherungen",
        "in den Tests leiten ihre Erwartungen deshalb aus der Fixture ab, statt",
        "Datumsangaben hineinzuschreiben.",
        "",
        "**`/Subdivisions` ist gekuerzt, aber nicht beschnitten.** Der Vollabzug",
        "waere 399 kB, fast alles davon verschachtelte `children`. Aufgezeichnet",
        "sind drei Kantone, gewaehlt statt genommen: `CH-ZH` tief verschachtelt",
        "und mit Schultypen, `CH-BS` mit wenigen Untereinheiten, `CH-AR` ganz",
        "ohne — die drei Formen, die der Code unterscheiden muss. Innerhalb der",
        "Datensaetze ist kein Feld entfernt. Die Kantonsliste selbst steht in",
        "`constants.py` und haengt nicht an dieser Antwort.",
        "",
        "Fehlerpfade — 404, Timeouts, maskierte 4xx — bleiben handgeschrieben.",
        "Die lassen sich nicht auf Zuruf aufzeichnen.",
        "",
    ]
    for e in entries:
        lines += [
            f"## `{e['name']}`",
            "",
            f"- **Quelle:** `{e['url']}`",
            f"- **Aufgezeichnet:** {recorded_at}",
            f"- **Auswahl:** {e['rule']}",
            f"- **Groesse:** {e['bytes']} B",
            f"- **SHA-256:** `{e['sha256']}`",
            "",
        ]
    (FIXTURES / "PROVENANCE.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
