# MCP-Server Audit-Report — `swiss-holidays-mcp`

**Audit-Datum:** 2026-07-24
**Skill-Version:** 1.0.0
**Catalog-Version:** 68-checks (v0.5.0 catalog)

---

## 1. Executive Summary

Server `swiss-holidays-mcp` wurde gegen 36 anwendbare Best-Practice-Checks geprüft. 34 bestanden, 2 Findings dokumentiert (0 critical, 1 high, 1 medium, 0 low). Production-Readiness: erreicht.

**Production-Readiness:** YES

---

## 2. Profil-Snapshot

| Feld | Wert |
|---|---|
| Server-Name | `swiss-holidays-mcp` |
| Audit-Datum | 2026-07-24 |
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
| ARCH | 10 | 0 | 1 | 0 | 0 |
| CH | 2 | 0 | 0 | 0 | 0 |
| OBS | 4 | 0 | 0 | 0 | 0 |
| OPS | 3 | 0 | 0 | 0 | 0 |
| SCALE | 1 | 0 | 0 | 0 | 0 |
| SDK | 4 | 0 | 0 | 0 | 0 |
| SEC | 10 | 0 | 1 | 0 | 1 |
| **Total** | **34** | **0** | **2** | **0** | **1** |

---

## 4. Findings-Übersicht

_Policy: `fail-or-partial`_

| ID | Category | Severity | Status |
|---|---|---|---|
| SEC-005 | SEC | high | partial |
| ARCH-011 | ARCH | medium | partial |

**Gesamt:** 2 Findings

---

## 5. Detail-Findings

### ARCH-011

## Finding: ARCH-011 — Standardisierte Repo-Struktur (src-Layout, tests, README.de.md)

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-holidays-mcp` |
| **Check-Reference** | `ARCH-011` |
| **PDF-Reference** | Anhang A8 |
| **Audit-Datum** | 2026-07-24 |
| **Auditor** | Claude (mcp-audit skill, re-audit) |

### Observed Behavior

Die Doku-Drift des Erst-Audits ist behoben (`docs/security.md` und `docs/roadmap.md`
nennen jetzt 13 Tools / v0.5.0). Die Repo-Struktur ist ansonsten vorbildlich:
alle Pflicht-Files, korrektes src-Layout, `tests/`, `.github/workflows/`,
paralleles `README.de.md`. **Einziger verbleibender Punkt:** die 13 Tools liegen
weiterhin in einer einzigen ~1109-Zeilen-Datei `server.py`, ohne `tools/`-Package
(File-pro-Gruppe) und ohne dokumentierte Begründung für das Einzeldatei-Layout.

### Expected Behavior

Bei > 5 Tools verlangt der Katalog ein `tools/`-Verzeichnis mit Aufteilung
pro Tool-Gruppe — oder eine im README begründete, bewusste Abweichung.

### Evidence

- File: `src/swiss_holidays_mcp/server.py` (1109 Zeilen, 13 `@mcp.tool`)
- Kein `src/swiss_holidays_mcp/tools/`-Verzeichnis
- README-Projektstruktur nennt `server.py` ohne Begründung der Nicht-Aufteilung

### Risk Description

Kein Sicherheits- oder Korrektheitsrisiko. Die grosse Einzeldatei erschwert
Code-Review und Test-Isolierung mit weiterem Wachstum; rein wartungsbezogen.

### Remediation

Zwei gleichwertige Optionen:
1. **Split (M):** `op_*`-Logik + Tool-Wrapper in ein `tools/`-Package aufteilen,
   z.B. `tools/holidays.py`, `tools/compare.py`, `tools/export.py`, `tools/status.py`;
   `server.py` behält nur Lifespan + Registrierung.
2. **Begründen (S):** Im README einen kurzen Absatz ergänzen, warum das
   Einzeldatei-Layout bewusst gewählt ist (thin Wrapper über `op_*`, gemeinsamer
   Kontext) — der Katalog akzeptiert eine begründete Abweichung explizit.

### Effort Estimate

S (Begründung) bzw. M (Split)

### Verification After Fix

`tools/`-Package existiert **oder** README enthält die begründete Abweichung; Re-Audit ARCH-011.


### SEC-005

## Finding: SEC-005 — DNS-Rebinding-Prevention: DNS-Pinning gegen TOCTOU

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open (mitigated) |
| **Server** | `swiss-holidays-mcp` |
| **Check-Reference** | `SEC-005` |
| **PDF-Reference** | Sec 4.4 |
| **Audit-Datum** | 2026-07-24 |
| **Auditor** | Claude (mcp-audit skill, re-audit) |

### Observed Behavior

Der Guard resolved den Host einmal vor dem Request und prüft die IP gegen die
SSRF-Blocklist; TLS validiert gegen den Original-Hostnamen; die 2-Host-frozen-
Allow-List begrenzt die Exposition. **Neu seit Erst-Audit:** eine Network-Layer-
Egress-Policy (`deploy/cilium-egress-fqdn.yaml`, Cilium `toFQDNs`) ist beigelegt —
deren DNS-Proxy ist die Autorität über erreichbare IPs und schliesst das
Rebinding-Fenster zur Deploy-Zeit robust. **Weiterhin offen:** clientseitiges
DNS-Pinning im Code (Wiederverwendung der resolved IP für die TCP-Verbindung,
TOCTOU-frei) ist nicht implementiert — httpx resolved zur Connect-Zeit erneut.

### Expected Behavior

Einmalige DNS-Auflösung, deren IP für die TCP-Verbindung gepinnt wird, während
Host-Header + SNI + Zertifikatsprüfung auf dem Original-Hostnamen laufen; Test
verifiziert genau 1 DNS-Call pro Request.

### Evidence

- File: `src/swiss_holidays_mcp/guard.py:66-73` (Resolve nur zur Prüfung)
- File: `src/swiss_holidays_mcp/client.py` (`self._http.get(...)` — httpx re-resolved; kein `sni_hostname`/Pinning)
- File: `deploy/cilium-egress-fqdn.yaml` (Network-Layer-Mitigation)
- File: `docs/network-egress.md` (dokumentiertes Restrisiko + Network-Layer-Closure)

### Risk Description

Zwischen Guard-Check und httpx-Connect könnte ein Angreifer mit DNS-Kontrolle
über einen Allow-List-Host die Auflösung auf eine interne IP umbiegen. Praktisch
stark eingegrenzt (2-Host-Allow-List, TLS-Validierung gegen Hostname) und im
Deployment durch die Network-Layer-Policy geschlossen; das Code-Fenster bleibt
formal offen.

### Remediation

Bewusste Abweichung akzeptiert: echtes Socket-Level-Pinning via IP-URL +
SNI-Override ist fragil und bricht hinter einem HTTP-Proxy (der Proxy resolved).
Robuste Closure ist die beigelegte Network-Layer-Policy; für eine gehärtete
Cloud-Bereitstellung `deploy/cilium-egress-fqdn.yaml` anwenden. Optional
langfristig: httpx-Custom-Transport mit gepinntem Resolver, sofern kein Proxy im
Pfad liegt.

### Effort Estimate

M (Code-Pinning) — als akzeptiertes Restrisiko mit Network-Layer-Mitigation dokumentiert.

### Verification After Fix

Test zeigt 1 DNS-Call/Request und Connect zur gepinnten IP, **oder** Network-Layer-
Egress-Policy im Ziel-Deployment aktiv; Re-Audit SEC-005.


---

## 6. Remediation-Plan

### Empfohlene Reihenfolge

1. **SEC-005** (high, partial)
2. **ARCH-011** (medium, partial)

---

## 7. Audit-Metadata

| Feld | Wert |
|---|---|
| skill_version | `1.0.0` |
| catalog_version | `68-checks (v0.5.0 catalog)` |
| audit_date | `2026-07-24` |


_Generated by tools/build_report.py — do not edit by hand._
