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
