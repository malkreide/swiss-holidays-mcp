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
