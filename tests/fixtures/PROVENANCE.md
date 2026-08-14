# Herkunft der Fixtures

**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**

Aufgezeichnet am **2026-08-14** von den beiden Quellen dieses Servers:
`https://openholidaysapi.org` und `https://date.nager.at/api/v3`.

Ohne Datum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht
mehr zu unterscheiden — die Datei sieht gleich aus.

**Feiertage altern jahrweise.** Diese Fixtures belegen die *Form* der
Antwort und den Stand fuer ein festes Jahr (2026) und einen festen
Kanton (CH-ZH) — nicht «dieses Jahr». Waere die Auswahl vom
Zeitpunkt des Laufs abhaengig, erzeugte jedes Aufzeichnen einen anderen
Diff, ohne dass sich an der Quelle etwas geaendert haette. Zusicherungen
in den Tests leiten ihre Erwartungen deshalb aus der Fixture ab, statt
Datumsangaben hineinzuschreiben.

**`/Subdivisions` ist gekuerzt, aber nicht beschnitten.** Der Vollabzug
waere 399 kB, fast alles davon verschachtelte `children`. Aufgezeichnet
sind drei Kantone, gewaehlt statt genommen: `CH-ZH` tief verschachtelt
und mit Schultypen, `CH-BS` mit wenigen Untereinheiten, `CH-AR` ganz
ohne — die drei Formen, die der Code unterscheiden muss. Innerhalb der
Datensaetze ist kein Feld entfernt. Die Kantonsliste selbst steht in
`constants.py` und haengt nicht an dieser Antwort.

Fehlerpfade — 404, Timeouts, maskierte 4xx — bleiben handgeschrieben.
Die lassen sich nicht auf Zuruf aufzeichnen.

## `subdivisions.json`

- **Quelle:** `https://openholidaysapi.org/Subdivisions?countryIsoCode=CH&languageIsoCode=DE`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** 3 von 26 Kantonen: CH-ZH, CH-BS, CH-AR — tief verschachtelt, flach und ganz ohne `children`; Satzform unangetastet
- **Groesse:** 79040 B
- **SHA-256:** `5815f6e9c1f426bd8563c54154dd1ef837cc065b0788dedf8456de0ab9e0236d`

## `groups.json`

- **Quelle:** `https://openholidaysapi.org/Groups?countryIsoCode=CH&languageIsoCode=DE`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** die ersten 3 von 11 Gruppen; Satzform unangetastet
- **Groesse:** 6345 B
- **SHA-256:** `27b4d7baedf4b2d57bf38207c18a75ccd588c2e803afc3c35140fc9e5b1e5623`

## `public_holidays.json`

- **Quelle:** `https://openholidaysapi.org/PublicHolidays?countryIsoCode=CH&languageIsoCode=DE&validFrom=2026-01-01&validTo=2026-12-31&subdivisionCode=CH-ZH`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendig; CH-ZH, Jahr 2026 (13 Feiertage)
- **Groesse:** 16359 B
- **SHA-256:** `54a4e514ea1120be00e722cd80781aa2b293d72b76ca9ba12598b6213442a351`

## `school_holidays.json`

- **Quelle:** `https://openholidaysapi.org/SchoolHolidays?countryIsoCode=CH&languageIsoCode=DE&validFrom=2026-01-01&validTo=2026-12-31&subdivisionCode=CH-ZH`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendig; CH-ZH, Jahr 2026 (10 Ferien)
- **Groesse:** 5439 B
- **SHA-256:** `3fca8cfbd6b2ab1c7d5342e2459faf428db84cff1cf71e9dc497529abdf8c453`

## `countries.json`

- **Quelle:** `https://openholidaysapi.org/Countries?languageIsoCode=DE`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendig; 36 Laender (Health-Probe)
- **Groesse:** 6069 B
- **SHA-256:** `508069c4c48c0a7af79756940e70fc542e22f5f450ccdeed7d1e4bf3fe09a8d5`

## `long_weekends.json`

- **Quelle:** `https://date.nager.at/api/v3/LongWeekend/2026/CH`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendig; Jahr 2026, CH (3 lange Wochenenden)
- **Groesse:** 460 B
- **SHA-256:** `6e939ec14f6a91e08615a324b9cd57b7009ea22eae08abcf44a476f7f5140f3f`

## `available_countries.json`

- **Quelle:** `https://date.nager.at/api/v3/AvailableCountries`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendig; 204 Laender (Health-Probe)
- **Groesse:** 11963 B
- **SHA-256:** `bdb24f821fe637805a4dc78bd0d752e108cff582de2d3ae44feedc98ddbca91e`
