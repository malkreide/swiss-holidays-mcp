# Sicherheitsrichtlinie

[🇬🇧 English Version](SECURITY.md)

## Unterstützte Versionen

Sicherheitsupdates werden für die jeweils neueste auf
[PyPI](https://pypi.org/project/swiss-school-calendar-mcp/) veröffentlichte
Version bereitgestellt. Bitte aktualisieren Sie immer auf die aktuellste
Version, bevor Sie ein Problem melden.

## Eine Schwachstelle melden

Bitte melden Sie Sicherheitslücken **vertraulich** — eröffnen Sie für
sicherheitsrelevante Meldungen **kein** öffentliches Issue.

- Nutzen Sie [GitHub Security Advisories](../../security/advisories/new) für
  eine vertrauliche Meldung, **oder**
- kontaktieren Sie den Maintainer über
  [github.com/malkreide](https://github.com/malkreide).

Bitte fügen Sie bei:

- eine Beschreibung der Schwachstelle und ihrer möglichen Auswirkungen
- Schritte zur Reproduktion (Proof of Concept, betroffenes Tool/Endpoint)
- die betroffene Version und Ihre Umgebung (OS, Python-Version, Transport)

Sie erhalten innerhalb von **7 Tagen** eine erste Rückmeldung. Nach
Veröffentlichung eines Fixes nennen wir Sie im Changelog, sofern Sie nicht
anonym bleiben möchten.

## Sicherheitsmodell

Dieser Server ist **nur lesend** und benötigt **keinen API-Key**:

- Alle Tools führen HTTP-`GET`-Anfragen gegen die öffentlichen APIs von
  OpenHolidays und Nager.Date aus — es werden keine Daten geschrieben,
  verändert oder gelöscht.
- Es werden keine personenbezogenen Daten (PII) verarbeitet oder gespeichert.
  Die APIs liefern ausschliesslich aggregierte, öffentliche Feiertagskalender.
- Der Server erzwingt ein Timeout von 20 s pro Anfrage (8 s für Health-Probes)
  und cacht Antworten 12 Stunden im Speicher.
- Retries nutzen exponentielles Backoff (2 s / 4 s / 8 s); `4xx`-Antworten
  ausser `429` werden nicht wiederholt.
- Ein Upstream-Ausfall liefert einen `degraded`-Envelope mit erklärender Note,
  nie eine stillschweigend leere Liste — so bleiben «keine Ferien» und «Quelle
  nicht erreichbar» unterscheidbar.

### Härtung beim Deployment

- Der HTTP/SSE-Transport bindet standardmässig **`127.0.0.1` (Loopback)**
  (`MCP_HOST`). Ein öffentliches Binding (`MCP_HOST=0.0.0.0`) ist ein
  ausdrückliches Opt-in und erzeugt beim Start eine Warnung — der Server hat
  **keine eingebaute Authentifizierung**.
- Für Nicht-Loopback-Betrieb den Server **hinter einem Reverse Proxy mit
  Authentifizierung und per-IP-Rate-Limit** betreiben (z.B. nginx mit
  `limit_req` + OAuth2-Proxy). Für den HTTP-Transport ist DNS-Rebinding-Schutz
  (Host/Origin-Allow-List) aktiv.
- **Egress:** ausgehende Requests sind auf eine Zwei-Host-HTTPS-Allow-List mit
  SSRF-IP-Blocklist beschränkt — siehe [`docs/network-egress.md`](docs/network-egress.md).
- Logs werden auf **stderr** geschrieben und enthalten keine Request-Bodies
  oder Personendaten. Prüfen Sie Ihre Aufbewahrungsrichtlinie, bevor Sie
  ausführliches Logging aktivieren.
- Vollständige Sicherheitsarchitektur: [`docs/security.md`](docs/security.md).

## Geltungsbereich

Im Geltungsbereich: der Code in diesem Repository (MCP-Server, HTTP-Client und
Transport-Schicht). Ausserhalb des Geltungsbereichs: Schwachstellen in
Upstream-Diensten ([OpenHolidays](https://www.openholidaysapi.org/),
[Nager.Date](https://date.nager.at/)) — bitte melden Sie diese direkt den
jeweiligen Anbietern.

---

Dieses Projekt folgt den Konventionen des
[Swiss Public Data MCP Portfolios](https://github.com/malkreide).
