# Scaling & Session Affinity

Audit reference: **SCALE-002** (stateful load balancing for Streamable HTTP / SSE).

This server is primarily a **local stdio** tool. The HTTP/SSE transports exist
for browser access and are the only case where load balancing is relevant. This
page documents how to run them at each scale.

## What state the server holds

| State | Scope | Consequence for scaling |
|---|---|---|
| MCP session (Streamable HTTP / SSE) | Per **instance**, in memory | A follow-up request routed to a *different* instance does not find its session → broken stream. |
| 12 h upstream cache (`HolidayClient`) | Per **instance**, in memory | Not a correctness issue — a cache miss on another instance just re-fetches. |

There is **no** per-user or persisted state (no auth, no database). The only
thing that must stay pinned to one instance is the live MCP session.

## Deployment tiers

### 1. stdio (default) — no load balancing

`MCP_TRANSPORT` unset → one process per client, spawned by the host (Claude
Desktop). Nothing to balance. This is the recommended production shape.

### 2. HTTP, single instance — works out of the box

```bash
MCP_TRANSPORT=streamable-http MCP_HOST=127.0.0.1 python -m swiss_holidays_mcp
```

One instance behind an authenticating reverse proxy. Sessions live in that one
process, so no affinity configuration is needed. This covers the vast majority
of self-hosted authority deployments.

### 3. HTTP, horizontally scaled — sticky sessions required

If you run **more than one instance** behind a load balancer, you MUST pin each
MCP session to the instance that created it, keyed on the `Mcp-Session-Id`
header (which the CORS layer already exposes — see SDK-004). Otherwise a
follow-up request can land on an instance that never saw the session.

**nginx (`ip_hash` is not enough — hash on the session header):**

```nginx
upstream mcp_backends {
    hash $http_mcp_session_id consistent;
    server 10.0.0.11:8000;
    server 10.0.0.12:8000;
}
server {
    listen 443 ssl;
    location /mcp {
        proxy_pass http://mcp_backends;
        proxy_http_version 1.1;
        proxy_set_header Connection "";        # keep SSE streams open
        proxy_buffering off;                   # stream, don't buffer
        proxy_read_timeout 3600s;
    }
}
```

**Traefik (sticky by the session header via a cookie fallback):** enable sticky
sessions on the service, or route on `Mcp-Session-Id` with a header-hash
middleware; keep read timeouts high for SSE.

**Kubernetes:** use a `Service` with `sessionAffinity: ClientIP` only as a
coarse fallback; prefer an ingress controller that can hash on the
`Mcp-Session-Id` header. Set the ingress `proxy-read-timeout` high for SSE.

### Session lifetime

Sessions are held only as long as the client keeps the stream open; there is no
long-lived server-side session store to expire. For a hardened deployment, cap
idle streams at the proxy (e.g. `proxy_read_timeout 3600s`) so orphaned sessions
are reclaimed.

## If you would rather not pin sessions

A future option is FastMCP's stateless HTTP mode (`stateless_http=True`), which
serves each request independently and removes the affinity requirement — at the
cost of server-initiated streaming. It is **not** enabled today; this server
ships the stateful transport. Track this in the roadmap before enabling it, as
it is a protocol-behaviour change.
