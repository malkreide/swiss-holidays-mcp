# MCP-Server Audit-Report — `swiss-holidays-mcp`

**Audit-Datum:** 2026-07-23
**Skill-Version:** 1.0.0
**Catalog-Version:** 68-checks (v0.5.0 catalog)

---

## 1. Executive Summary

Server `swiss-holidays-mcp` wurde gegen 36 anwendbare Best-Practice-Checks geprüft. 26 bestanden, 10 Findings dokumentiert (0 critical, 5 high, 5 medium, 0 low). Production-Readiness: erreicht.

**Production-Readiness:** YES

---

## 2. Profil-Snapshot

| Feld | Wert |
|---|---|
| Server-Name | `swiss-holidays-mcp` |
| Audit-Datum | 2026-07-23 |
| Skill-Version | 1.0.0 |
| Catalog-Version | 68-checks (v0.5.0 catalog) |
| transport | `dual` |
| auth_model | `none` |
| data_class | `Public Open Data` |
| write_capable | `False` |
| deployment | `['local-stdio']` |
| uses_sampling | `False` |
| tools_make_external_requests | `True` |
| stadt_zuerich_context | `False` |
| schulamt_context | `True` |
| data_source.is_swiss_open_data | `True` |

---

## 3. Applicability

### Status pro Kategorie

| Kategorie | Pass | Fail | Partial | Todo | N/A |
|---|---|---|---|---|---|
| ARCH | 8 | 0 | 3 | 0 | 0 |
| CH | 2 | 0 | 0 | 0 | 0 |
| OBS | 2 | 0 | 2 | 0 | 0 |
| OPS | 3 | 0 | 0 | 0 | 0 |
| SCALE | 0 | 0 | 1 | 0 | 0 |
| SDK | 2 | 0 | 2 | 0 | 0 |
| SEC | 9 | 0 | 2 | 0 | 1 |
| **Total** | **26** | **0** | **10** | **0** | **1** |

---

## 4. Findings-Übersicht

_Policy: `fail-or-partial`_

| ID | Category | Severity | Status |
|---|---|---|---|
| OBS-002 | OBS | high | partial |
| SCALE-002 | SCALE | high | partial |
| SDK-004 | SDK | high | partial |
| SEC-005 | SEC | high | partial |
| SEC-021 | SEC | high | partial |
| ARCH-002 | ARCH | medium | partial |
| ARCH-003 | ARCH | medium | partial |
| ARCH-011 | ARCH | medium | partial |
| OBS-003 | OBS | medium | partial |
| SDK-003 | SDK | medium | partial |

**Gesamt:** 10 Findings

---

## 5. Detail-Findings

### ARCH-002

## Finding: ARCH-002 — Tool-Beschreibung mit Use-Case-Tags

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-holidays-mcp` |
| **Check-Reference** | `ARCH-002` |
| **PDF-Reference** | Sec 2.2 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude (mcp-audit skill) |

### Observed Behavior

Alle 13 Tool-Beschreibungen sind mehrsatzig und liefern Kontext (server.py:738-963). Der Use-Case steht jedoch nur als Freitext in der Docstring, z.B. `check_date`: "The everyday question behind this tool: 'Can we schedule the parents' evening on that Thursday?'" (server.py:830-834). Es gibt keine maschinell erkennbaren `<use_case>`- oder `<important_notes>`-Tags.

### Expected Behavior

Der Katalog verlangt einen maschinen-lesbaren Use-Case-Tag (`<use_case>` o.ae.) in mindestens 80 % der Tools und, wo relevant, einen Important-Notes-Tag mit Caveats/Limitierungen zur Tool-Wahl-Zeit.

### Evidence

- File: `src/swiss_holidays_mcp/server.py:738-963`
- Beschreibungen sind qualitativ hochwertig, aber unstrukturiert (kein Tag-Schema).

### Risk Description

Bei mehreren aehnlichen Holiday-Tools (`get_school_holidays`, `get_public_holidays`, `get_local_holidays`, `next_school_holidays`) muss das LLM die Differenzierung aus Prosa ableiten. Ohne strukturierte Tags steigt das Risiko der Tool-Fehlwahl marginal; bei Portfolio-Wachstum (mehr Tools) verschaerft sich das.

### Remediation

Optionalen strukturierten Block an den Anfang jeder Docstring setzen, z.B.:
```
<use_case>Termin-Kollisionspruefung gegen Schul- und Feiertage eines Kantons.</use_case>
<important_notes>Datumsfenster +/-40 Tage; nur offizielle Kantonsdaten.</important_notes>
```
Konsistent ueber alle 13 Tools anwenden.

### Effort Estimate

**S**

### Verification After Fix

Grep auf `<use_case>` in server.py findet >= 11 von 13 Tools; Re-Audit ARCH-002.


### ARCH-003

## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-holidays-mcp` |
| **Check-Reference** | `ARCH-003` |
| **PDF-Reference** | Sec 2.2 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude (mcp-audit skill) |

### Observed Behavior

`get_local_holidays` bietet bei Nichttreffer Fuzzy-Vorschlaege an (`_resolve_locality`, server.py:354-377, 394-404: "Did you mean: ...?"). `get_school_holidays` setzt bei leerem Ergebnis eine erklaerende `note` (server.py:294-300). Es gibt aber kein strukturiertes `match_type`-Feld (exact/fuzzy/none) im Envelope.

### Expected Behavior

Leere Ergebnisse triggern Fuzzy-Match/Suggestion (erfuellt fuer local), und die Response traegt ein `match_type`-Feld o.ae., damit das LLM zuverlaessig verzweigen kann statt Prosa zu parsen.

### Evidence

- File: `src/swiss_holidays_mcp/server.py:394-404` (candidates)
- File: `src/swiss_holidays_mcp/server.py:294-300` (note)
- Kein `match_type` in `models.py` Envelope.

### Risk Description

Das LLM muss den Treffer-Typ aus dem Freitext-`note` erschliessen. In seltenen Faellen fuehrt das zu falscher Interpretation (z.B. Fuzzy-Treffer als exakt behandelt). Geringer, aber realer Robustheits-Verlust.

### Remediation

Optionales `match_type: Literal['exact','fuzzy','none']`-Feld in `HolidayListResponse` ergaenzen und in `_resolve_locality`-Pfaden setzen. Rueckwaertskompatibel (Default z.B. 'exact').

### Effort Estimate

**S**

### Verification After Fix

Response von `get_local_holidays` mit Tippfehler enthaelt `match_type='none'` + candidates; Re-Audit ARCH-003.


### ARCH-011

## Finding: ARCH-011 — Standardisierte Repo-Struktur (src-Layout, tests, README.de.md)

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-holidays-mcp` |
| **Check-Reference** | `ARCH-011` |
| **PDF-Reference** | Anhang A8 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude (mcp-audit skill) |

### Observed Behavior

Repo-Struktur ist weitgehend vorbildlich: README.md, README.de.md, CHANGELOG.md, LICENSE, pyproject.toml, korrektes src-Layout, tests/, .github/workflows/. Zwei Abweichungen: (1) 13 Tools liegen in einer einzigen 987-Zeilen-Datei `server.py`, ohne `tools/`-Package-Aufteilung. (2) Doku-Drift: `docs/security.md` und `docs/roadmap.md` sprechen von "all 10 tools", roadmap nennt "active (v0.2.0)" - tatsaechlich 13 Tools und pyproject 0.5.0.

### Expected Behavior

Bei > 5 Tools ein `tools/`-Verzeichnis mit File-pro-Gruppe. Doku konsistent zur Implementierung (Tool-Anzahl, Versionsstand).

### Evidence

- File: `src/swiss_holidays_mcp/server.py` (987 Zeilen, 13 @mcp.tool)
- File: `docs/roadmap.md:9-10` ("all 10 tools", "active (v0.2.0)")
- File: `docs/security.md:43` ("all 10 tools are read-only")

### Risk Description

Grosse Einzeldatei erschwert Code-Review und Test-Isolierung. Doku-Drift fuehrt dazu, dass Leser (und Auditoren) veraltete Tool-Zahlen/Versionen als Wahrheit nehmen - Vertrauens- und Audit-Trail-Problem, kein Sicherheitsrisiko.

### Remediation

Kurzfristig (S): Zahlen in `docs/security.md` und `docs/roadmap.md` auf 13 Tools / v0.5.0 korrigieren. Mittelfristig (M): `op_*`-Logik und Tool-Wrapper in ein `tools/`-Package aufteilen (z.B. `tools/holidays.py`, `tools/compare.py`, `tools/export.py`, `tools/status.py`), oder die Einzeldatei im README explizit als bewusste Entscheidung begruenden (Katalog erlaubt begruendete Abweichung).

### Effort Estimate

**M**

### Verification After Fix

Doku nennt 13 Tools/0.5.0; entweder `tools/`-Split existiert oder README begruendet die Abweichung; Re-Audit ARCH-011.


### OBS-002

## Finding: OBS-002 — Mask Error Details: keine Stacktraces / SQL ans LLM

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-holidays-mcp` |
| **Check-Reference** | `OBS-002` |
| **PDF-Reference** | Sec 6.2 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude (mcp-audit skill) |

### Observed Behavior

FastMCP wird ohne `mask_error_details=True` konstruiert (server.py:88: `mcp = FastMCP("swiss-holidays-mcp", lifespan=lifespan)`). Die tatsaechlichen Fehlerpfade sind bereits sauber: Upstream-Fehler werden gefangen und als `degraded`-Envelope mit generischer Note zurueckgegeben (server.py:198-210), Rohdetails gehen nur nach stderr (client.py:134-167). Validierungsfehler werfen bewusst user-sichere `ValueError` (server.py:150-153).

### Expected Behavior

FastMCP-Init mit `mask_error_details=True` (Defense-in-Depth), sodass auch eine unerwartete/ungefangene Exception dem LLM keine Interna offenlegt.

### Evidence

- File: `src/swiss_holidays_mcp/server.py:88`
- Test: `grep -rn mask_error_details src/` -> kein Treffer
- Gegenkontrolle: alle bewussten Fehlerpfade sind bereits maskiert (client.py:134-167).

### Risk Description

Ein unerwarteter Bug (z.B. `KeyError` in `_to_period`, wenn Upstream sein Schema aendert) wuerde als ungefangene Exception den FastMCP-Default-Pfad nehmen und die Exception-Message dem LLM zeigen. Praktisches Leck-Risiko gering (keine Secrets/PII, keine DB), aber Datei-/Codestruktur-Hinweise koennten durchsickern.

### Remediation

```diff
- mcp = FastMCP("swiss-holidays-mcp", lifespan=lifespan)
+ mcp = FastMCP("swiss-holidays-mcp", lifespan=lifespan, mask_error_details=True)
```
Ein-Zeilen-Fix; bestehende degraded-Envelopes und user-sichere ValueErrors bleiben unveraendert wirksam.

### Effort Estimate

**S**

### Verification After Fix

`mask_error_details=True` gesetzt; Test, der eine kuenstliche Exception in einem Tool ausloest, sieht generische statt detaillierter Fehlermeldung; Re-Audit OBS-002.


### OBS-003

## Finding: OBS-003 — Structured Logging mit RFC 5424 Severity-Stufen

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-holidays-mcp` |
| **Check-Reference** | `OBS-003` |
| **PDF-Reference** | Sec 6.3 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude (mcp-audit skill) |

### Observed Behavior

Logging nutzt das stdlib-`logging`-Modul mit eigenem key=value-Formatter (logging_setup.py:18-28), pinned auf stderr. Mehrere Severity-Stufen (info/warning/error) werden genutzt. Es fehlen: eine Structured-Logging-Library (structlog/loguru) und ein pro-Tool-Call gebundener Kontext (session_id/correlation_id).

### Expected Behavior

Structured Logger (structlog/loguru) in Dependencies, JSON/logfmt-Output, mind. 4 Severity-Stufen, und pro Tool-Call gebundener Kontext (tool name, session_id, correlation_id).

### Evidence

- File: `src/swiss_holidays_mcp/logging_setup.py:18-28` (stdlib Formatter)
- Kein structlog/loguru in `pyproject.toml`
- Kein correlation_id/session_id-Binding im Log-Kontext.

### Risk Description

Ohne correlation_id lassen sich zusammengehoerige Log-Zeilen eines Tool-Calls in einem Aggregator schwerer korrelieren. Fuer einen Single-Instance-stdio-Server tolerierbar; bei HTTP/Multi-Client-Betrieb erschwert es das Debugging.

### Remediation

Option A (leichtgewichtig, S): bei jedem `op_*`-Aufruf eine `correlation_id` (uuid4) erzeugen und via `extra={'context': {...}}` mitloggen. Option B (M): auf `structlog` mit `WriteLoggerFactory(file=sys.stderr)` migrieren und Kontext via `bind()` fuehren - erhaelt OBS-004 (stderr).

### Effort Estimate

**M**

### Verification After Fix

Log-Zeilen eines Tool-Calls tragen dieselbe correlation_id; strukturierter Logger im Einsatz; Re-Audit OBS-003.


### SCALE-002

## Finding: SCALE-002 — Stateful Load Balancing fuer Streamable HTTP / SSE

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-holidays-mcp` |
| **Check-Reference** | `SCALE-002` |
| **PDF-Reference** | Sec 5.2 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude (mcp-audit skill) |

### Observed Behavior

Primaerer/Default-Transport ist stdio (Einzelprozess, keine LB-Flaeche). Der ausgelieferte streamable-http-Transport (Dockerfile) hat keine dokumentierte Session-Affinitaets-Strategie. Einzige Server-Seite-State ist ein In-Process-12h-Cache (client.py:98).

### Expected Behavior

Fuer HTTP/SSE mind. eines: Sticky Sessions auf LB-Ebene basierend auf `Mcp-Session-Id`, oder ein Shared-State-Session-Manager (Redis/Durable Objects). Plus explizite Session-TTL und Failover-Nachweis.

### Evidence

- File: `Dockerfile` (liefert streamable-http, EXPOSE 8000)
- Keine LB-/Session-Store-Konfiguration im Repo
- State: `src/swiss_holidays_mcp/client.py:98` (In-Process-Cache).

### Risk Description

Eine horizontal skalierte HTTP-Bereitstellung (mehrere Container hinter einem LB) wuerde die SDK-Session-Kontinuitaet brechen, da Sessions in-memory pro Instanz gehalten werden - Requests koennten eine Session auf der falschen Instanz treffen. Nur relevant bei Scale-Out; Single-Instance (der dokumentierte Fall) ist nicht betroffen.

### Remediation

Kurzfristig (S): In README/docs explizit dokumentieren, dass die HTTP-Bereitstellung Single-Instance ist bzw. Sticky Sessions auf `Mcp-Session-Id` am Reverse-Proxy erfordert. Mittelfristig (M) bei Bedarf: Sticky-Session-Beispiel (Nginx/Traefik) beilegen oder Session-Manager auf Redis umstellen.

### Effort Estimate

**M**

### Verification After Fix

README dokumentiert die Skalierungs-/Affinitaets-Anforderung; optional Beispiel-Config; Re-Audit SCALE-002.


### SDK-003

## Finding: SDK-003 — Context Injection fuer Progress Reports und Logging

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-holidays-mcp` |
| **Check-Reference** | `SDK-003` |
| **PDF-Reference** | Sec 3.1 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude (mcp-audit skill) |

### Observed Behavior

Tools nehmen `ctx: Context` (server.py:737-963), und nicht-fatale Degradierungen werden geloggt statt stumm verschluckt. Es fehlt: `ctx.report_progress()` in den netzwerkgebundenen Tools, und Body-Logging laeuft ueber den stdlib-Logger (`_log`) statt `ctx.info()`/`ctx.warning()`.

### Expected Behavior

Tools mit Laufzeit > 2s rufen `ctx.report_progress()` (1-2s-Takt); Logging im Body via `ctx.info()`/`ctx.warning()` (fuer stdio kritisch).

### Evidence

- File: `src/swiss_holidays_mcp/server.py:220-711` (op_* machen externes HTTP, kein report_progress)
- File: `src/swiss_holidays_mcp/server.py:201` (`_log.warning` statt `ctx.warning`).

### Risk Description

Bei langsamer Upstream-Antwort (mehrere Sekunden, Retries mit 2/4/8s-Backoff) erhaelt der Client keinen Fortschritt und wirkt haengend. Kein Sicherheitsrisiko, reines UX-/Beobachtbarkeits-Defizit.

### Remediation

In `op_*` mit potenziell langem Upstream (z.B. `op_source_status`, `op_check_date`, `op_holidays_bundle`) `await ctx.report_progress(...)` vor/zwischen den `gather`-Calls senden. Optional Body-Logs auf `ctx.info()`/`ctx.warning()` umstellen (haelt stderr-Disziplin bei; OBS-004).

### Effort Estimate

**S**

### Verification After Fix

Langlaufender Tool-Call sendet Progress-Notifications; Re-Audit SDK-003.


### SDK-004

## Finding: SDK-004 — CORS Mcp-Session-Id Exposure bei HTTP/SSE

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-holidays-mcp` |
| **Check-Reference** | `SDK-004` |
| **PDF-Reference** | Sec 3.1 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude (mcp-audit skill) |

### Observed Behavior

Der HTTP-Transport aktiviert die DNS-Rebinding-Protection des SDK mit expliziter Host/Origin-Allow-List (__main__.py:18-34). Es ist jedoch keine CORS-Middleware konfiguriert, daher steht `Mcp-Session-Id` nicht in `expose_headers`/`allow_headers`.

### Expected Behavior

Bei aktivem HTTP/SSE: CORS-Middleware mit `expose_headers` und `allow_headers` inkl. `Mcp-Session-Id`, `allow_origins` als explizite Liste (keine Wildcard in Production).

### Evidence

- File: `src/swiss_holidays_mcp/__main__.py:18-34` (TransportSecuritySettings, aber keine CORS-Middleware)
- Kein `expose_headers`/`CORSMiddleware` im Repo.

### Risk Description

Ein Browser-basierter MCP-Client auf einem anderen Origin koennte den `Mcp-Session-Id`-Header nicht lesen und damit keine Folge-Requests der Session zuordnen - die HTTP-Bereitstellung ist fuer Browser-Clients faktisch unbenutzbar. Aktuell gemildert durch die vorgesehene Reverse-Proxy-Bereitstellung, aber der Katalog verlangt explizite CORS-Konfiguration.

### Remediation

Bei HTTP-Transport eine Starlette-`CORSMiddleware` ergaenzen:
```python
from starlette.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware,
    allow_origins=[...],           # explizite Liste, keine '*'
    allow_headers=["Mcp-Session-Id", "Content-Type"],
    expose_headers=["Mcp-Session-Id"])
```
Nur im HTTP-Zweig (`settings.is_http`), stdio bleibt unberuehrt.

### Effort Estimate

**S**

### Verification After Fix

OPTIONS-Preflight gegen den HTTP-Server zeigt `Access-Control-Expose-Headers: Mcp-Session-Id`; Re-Audit SDK-004.


### SEC-005

## Finding: SEC-005 — DNS-Rebinding-Prevention: DNS-Pinning gegen TOCTOU

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-holidays-mcp` |
| **Check-Reference** | `SEC-005` |
| **PDF-Reference** | Sec 4.4 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude (mcp-audit skill) |

### Observed Behavior

Der Guard resolved den Host einmal vor dem Request und blockt SSRF-IPs (guard.py:66-73). Die resolved IP wird aber NICHT fuer die eigentliche TCP-Connection wiederverwendet - httpx resolved zur Connect-Zeit erneut (TOCTOU-Fenster). Dies ist als akzeptiertes Restrisiko dokumentiert (docs/network-egress.md 'Residual risk').

### Expected Behavior

Einmalige DNS-Aufloesung, deren IP fuer die TCP-Verbindung gepinnt wird (gepinnte URL oder Custom-Resolver), waehrend Host-Header + SNI + Zertifikatspruefung auf dem Original-Hostnamen laufen.

### Evidence

- File: `src/swiss_holidays_mcp/guard.py:66-73` (Resolve nur zur Pruefung)
- File: `src/swiss_holidays_mcp/client.py:126` (`self._http.get(url,...)` - httpx re-resolved)
- File: `docs/network-egress.md` Abschnitt 'Residual risk (accepted)'.

### Risk Description

Zwischen Guard-Check und httpx-Connect koennte ein Angreifer mit Kontrolle ueber DNS eines Allow-List-Hosts die Aufloesung auf eine interne IP umbiegen (DNS-Rebinding). Praktisch stark eingegrenzt durch die 2-Host-frozen-Allow-List und TLS-Validierung gegen den Original-Hostnamen; das Fenster ist real, aber schmal.

### Remediation

Optionen: (1) httpx-`transport` mit gepinnter Resolver-Map (resolved IP -> Connection) und `Host`-Header + SNI = Original-Host. (2) Network-Layer-Egress-Policy (NetworkPolicy/Security Group), die Egress nur zu den zwei Hosts erlaubt - vom Repo bereits als Defense-in-Depth empfohlen. Fuer die dokumentierte lokale stdio-Nutzung ist das Restrisiko vertretbar.

### Effort Estimate

**M**

### Verification After Fix

Test zeigt genau 1 DNS-Call pro Request und Connect zur gepinnten IP; oder Network-Layer-Egress-Policy dokumentiert/aktiv; Re-Audit SEC-005.


### SEC-021

## Finding: SEC-021 — Egress-Allow-List: Code-Layer und Network-Layer

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-holidays-mcp` |
| **Check-Reference** | `SEC-021` |
| **PDF-Reference** | Anhang B5 + B12 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude (mcp-audit skill) |

### Observed Behavior

Code-Layer voll erfuellt: immutable `frozenset` `ALLOWED_HOSTS` (constants.py:16), Pre-Request-`assert_host_allowed` vor jedem Egress (client.py:117, guard.py:33-46), Hosts + Erweiterungsverfahren dokumentiert (docs/network-egress.md). Es fehlt der Network-Layer (NetworkPolicy/Security Group/Cloudflare WARP).

### Expected Behavior

Beide Ebenen: Code-Layer-Allow-List (erfuellt) UND Network-Layer-Egress-Control als Defense-in-Depth.

### Evidence

- File: `src/swiss_holidays_mcp/constants.py:16` (frozenset)
- File: `src/swiss_holidays_mcp/client.py:117` (Pre-Request-Check)
- File: `docs/network-egress.md` (dokumentiert, empfiehlt Network-Layer explizit als offen).

### Risk Description

Sollte der Code-Layer-Check je umgangen werden (Bug, neue Egress-Stelle ohne Guard), gibt es fuer eine Cloud-Bereitstellung kein zweites Netz. Fuer die lokale stdio-Nutzung nicht anwendbar; fuer eine gehaertete Cloud-Bereitstellung fehlt die zweite Ebene.

### Remediation

Kein Code-Change noetig fuer lokal. Fuer Cloud: Beispiel-NetworkPolicy (K8s) oder Security-Group-Regel beilegen, die Egress auf `openholidaysapi.org` + `date.nager.at` (Port 443) plus DNS beschraenkt - `docs/network-egress.md` benennt dies bereits als empfohlene Massnahme, liefert aber noch kein konkretes Manifest.

### Effort Estimate

**M**

### Verification After Fix

Deployment-Doku enthaelt ein konkretes Network-Layer-Egress-Manifest; Re-Audit SEC-021.


---

## 6. Remediation-Plan

### Empfohlene Reihenfolge

1. **OBS-002** (high, partial)
2. **SCALE-002** (high, partial)
3. **SDK-004** (high, partial)
4. **SEC-005** (high, partial)
5. **SEC-021** (high, partial)
6. **ARCH-002** (medium, partial)
7. **ARCH-003** (medium, partial)
8. **ARCH-011** (medium, partial)
9. **OBS-003** (medium, partial)
10. **SDK-003** (medium, partial)

---

## 7. Audit-Metadata

| Feld | Wert |
|---|---|
| skill_version | `1.0.0` |
| catalog_version | `68-checks (v0.5.0 catalog)` |
| audit_date | `2026-07-23` |


_Generated by tools/build_report.py — do not edit by hand._
