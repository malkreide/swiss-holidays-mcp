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
