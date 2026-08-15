# Beitragen

[🇬🇧 English Version](CONTRIBUTING.md)

Vielen Dank für Ihr Interesse an diesem Projekt! Beiträge sind willkommen.

## Wie kann ich beitragen?

**Fehler melden:** Erstellen Sie ein [Issue](../../issues) mit einer klaren Beschreibung des Problems, Schritten zur Reproduktion und der erwarteten vs. tatsächlichen Ausgabe.

**Feature vorschlagen:** Beschreiben Sie den Use Case, idealerweise mit einem Bezug zum Schweizer Schul- und Bildungsplanungskontext (Ferienkoordination, Terminplanung, interkantonale Planung etc.).

**Code beitragen:**

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch: `git checkout -b feature/mein-feature`
3. Installieren Sie die Dev-Abhängigkeiten: `pip install -e ".[dev]"`
4. Schreiben Sie Tests für Ihre Änderungen
5. Lint prüfen: `ruff check src/ tests/`
6. Commit mit aussagekräftiger Nachricht: `git commit -m "feat: kantonale lange Wochenenden ergänzen"`
7. Pull Request erstellen

## Code-Standards

- Python 3.10+, Ruff für Linting
- Docstrings auf Englisch (für internationale Kompatibilität)
- Kommentare und Fehlermeldungen dürfen Deutsch oder Englisch sein
- Alle MCP-Tools müssen `readOnlyHint: True` setzen (nur lesender Zugriff)
- Pydantic-v2-Modelle für alle Tool-Inputs und Antwort-Envelopes
- Jede Antwort trägt `source`, `provenance` (`live_api` / `cached` / `degraded`) und `retrieved_at` — bei einem Upstream-Ausfall nie eine stillschweigend leere Liste

## Tests

Dieses Projekt benötigt **keinen API-Key** für Unit-Tests:

```bash
# Unit-Tests (kein Netzwerk erforderlich — respx-gemockt)
PYTHONPATH=src pytest tests/ -m "not live"

# Live-Smoke-Tests (Internetzugang erforderlich — gegen OpenHolidays / Nager.Date)
PYTHONPATH=src pytest tests/ -m "live"
```

Neue Tools müssen mit mindestens einem Unit-Test und einem Live-Smoke-Test abgedeckt sein. Committen Sie **niemals** persönliche Daten oder Zugangsdaten.

## Sicherheit

Bitte melden Sie Sicherheitsprobleme verantwortungsvoll — siehe [SECURITY.md](SECURITY.md).

## Die Live-Suite: wann sie läuft, und wer ein rotes Ergebnis sieht

**Kadenz:** täglich um 04:00 UTC, dazu jederzeit von Hand über *Actions → Live API Tests → Run
workflow*. Siehe [`.github/workflows/live-tests.yml`](.github/workflows/live-tests.yml).

**Wer es sieht:** Ein roter Lauf öffnet ein Issue mit dem Label `upstream` und dem stabilen Titel «Live-Tests gegen openholidaysapi.org / date.nager.at rot (<Datum>)». Ein zweiter roter Lauf erkennt das offene Issue am Titelanfang und hängt sich an denselben Thread, statt ein zweites aufzumachen. Wird die Suite wieder grün, schliesst sich das Issue selbst.

**Drei Antworten, nicht zwei.** `scripts/classify_live_run.py` liest das JUnit-XML statt des
Exit-Codes und unterscheidet: `clear` (gelaufen, grün), `finding` (gelaufen,
etwas gefallen) und `unknown` (nicht gelaufen — Installation gescheitert, null
Tests eingesammelt, alle übersprungen). Ein `unknown` schliesst nie ein Issue:
Zuzumachen hiesse zu behaupten, der Vergleich sei gelaufen.

**Ein roter Live-Lauf heisst nicht zwingend «unser Fehler».** Er heisst: Der
Vertrag mit der Quelle hat sich geändert, oder die Quelle ist gerade aus. Beides
gehört gesehen, nur das Erste gehört gefixt. Bitte den Lauf lesen, bevor der Job
deaktiviert wird — so stirbt dieser Check, und er ist der einzige im Repo, der
einer falschen Grundannahme über openholidaysapi.org / date.nager.at widersprechen kann. Jeder andere Test
prüft gegen eine Fixture, und die Fixture ist aus derselben Annahme geschrieben
wie der Code.

## Lizenz

Mit Ihrem Beitrag erklären Sie sich einverstanden, dass dieser unter der MIT-Lizenz lizenziert wird — siehe [LICENSE](LICENSE).

---

Dieses Projekt folgt den Konventionen des [Swiss Public Data MCP Portfolios](https://github.com/malkreide).
