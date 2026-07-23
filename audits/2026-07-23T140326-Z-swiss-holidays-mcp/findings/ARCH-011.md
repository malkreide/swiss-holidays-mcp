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
