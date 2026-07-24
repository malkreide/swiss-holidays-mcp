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
