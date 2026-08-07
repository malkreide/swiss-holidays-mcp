"""HTTP access layer: retry, in-memory cache, egress guard and normalisation.

Design notes from the live probe (2026-07-19):

* OpenHolidays answers an unknown ``countryIsoCode`` with HTTP 200 and ``[]``.
  An empty list is therefore *not* proof of "no holidays" — it can equally mean
  "your filter was wrong". ``UpstreamEmpty`` makes that distinction explicit.
* An unknown ``languageIsoCode`` silently falls back to EN instead of erroring.
  We validate the language locally before sending it.
* Missing required parameters produce a RFC-9110 problem+json body with HTTP
  400. Those are client errors and must not be retried.

Lifecycle (audit SDK-001): in production a single ``HolidayClient`` is created
in the server lifespan with a shared ``httpx.AsyncClient`` and a persistent
cache; tools reuse it rather than opening a client per call. The ``async with``
form is kept for tests, where it owns and closes its own client.
"""

from __future__ import annotations

import asyncio
import os
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from . import guard
from .constants import (
    ATTRIBUTION_NAGER,
    ATTRIBUTION_OPENHOLIDAYS,
    DEFAULT_LANGUAGE,
    NAGER_BASE,
    OPENHOLIDAYS_BASE,
    SUPPORTED_LANGUAGES,
    USER_AGENT,
)
from .logging_setup import get_logger
from .pinning import PinnedResolverTransport

MAX_ATTEMPTS = 4


# --- Retry policy ------------------------------------------------------------
# Adopted from the mcp-data-source-probe reference template (repaired
# 2026-08-07). Three questions: *what* is retried, *how fast*, and *how long*.
# The first is settled in the retry loop (4xx except 429 fails fast); these
# settle the other two.

RETRY_BASE_DELAY = 2.0  # ladder before jitter: 2, 4, 8

# Ceiling on the WHOLE call — every attempt and every wait together. An attempt
# count is not a bound: four attempts against an upstream that takes 30s to time
# out is two minutes inside one tool call, and the number never says so. The
# anchor is measured, not guessed: the Python MCP SDK ships
# MCP_DEFAULT_TIMEOUT = 30.0, so 25s leaves headroom for framing and parsing.
RETRY_TOTAL_BUDGET = 25.0

# Ceiling for a single wait. Bounds the exponential ladder, and bounds a
# `Retry-After` the source may send but we are not obliged to sit through.
RETRY_MAX_DELAY = 20.0

# Jitter spread. Without it every client that hit the same outage retries in
# lockstep, and the load returns as a wave exactly when the source recovers —
# the retry storm extends the outage it was meant to bridge.
RETRY_JITTER_SPREAD = 0.5  # exponential delays land in [0.5x, 1.5x]

# On a `Retry-After`, deliberately one-sided: the source said when to come back,
# so coming back later is fine and coming back earlier is not.
RETRY_AFTER_JITTER = 0.25  # lands in [1.0x, 1.25x]

# Statuses that carry a meaningful `Retry-After` (RFC 9110 section 10.2.3).
RETRY_AFTER_STATUSES = frozenset({429, 503})


def parse_retry_after(resp: httpx.Response | None) -> float | None:
    """Seconds to wait per the response's ``Retry-After``, or ``None``.

    RFC 9110 section 10.2.3 allows two forms — delta-seconds (``120``) and an
    HTTP-date (``Wed, 21 Oct 2026 07:28:00 GMT``). Both appear in the wild, so
    both are read. Anything unparseable yields ``None`` and the caller falls
    back to its own curve: a malformed header must not become a crash on the
    error path, which is the one path already going badly.
    """
    if resp is None or resp.status_code not in RETRY_AFTER_STATUSES:
        return None
    raw = (resp.headers.get("retry-after") or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        return float(raw)
    try:
        when = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:  # RFC 9110 dates are GMT; a naive one means UTC
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())


def compute_delay(attempt: int, last_error: Exception | None) -> float:
    """Seconds to wait before ``attempt`` (1-based for the first retry).

    The source's own answer beats our guess: a ``Retry-After`` on a 429 or 503
    wins over the exponential curve. Everything is spread, then capped.

    The cap wraps the jitter and not the other way round. ``min(cap, base) *
    jitter`` and ``min(cap, base * jitter)`` both contain a cap and a jitter;
    only the second is bounded — a value capped at 20s and then multiplied by
    up to 1.5 lands at 30s, and the constant would claim a ceiling it does not
    hold.
    """
    hinted = parse_retry_after(getattr(last_error, "response", None))
    if hinted is not None:
        return min(
            hinted * (1.0 + random.random() * RETRY_AFTER_JITTER),
            RETRY_MAX_DELAY,
        )
    return min(
        RETRY_BASE_DELAY
        * 2 ** (attempt - 1)
        * (1.0 - RETRY_JITTER_SPREAD + random.random() * 2 * RETRY_JITTER_SPREAD),
        RETRY_MAX_DELAY,
    )


CACHE_TTL_SECONDS = 60 * 60 * 12  # holiday tables change a few times per year
REQUEST_TIMEOUT = 20.0
PROBE_TIMEOUT = 8.0

_log = get_logger()


class UpstreamError(RuntimeError):
    """Upstream unreachable after all retries (message is log-safe, no internals)."""


class UpstreamEmpty(RuntimeError):
    """Upstream answered 200 but with an empty payload — usually a bad filter."""


def _forward_proxy_active() -> bool:
    """True if an HTTPS/ALL forward proxy is configured via the environment.

    When a proxy is in play it — not this process — resolves DNS, so client-side
    pinning is both moot and harmful (rewriting the URL to an IP breaks the proxy
    CONNECT). We conservatively disable pinning if any such proxy var is set.
    """
    return any(
        os.environ.get(var) for var in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy")
    )


def build_http_client() -> httpx.AsyncClient:
    """Create the shared HTTP client used for the whole server lifetime.

    On a direct connection the client pins DNS via ``PinnedResolverTransport``
    (SEC-005): the guard resolves each host once to an SSRF-safe IP and the
    connection uses exactly that IP, closing the DNS-rebinding TOCTOU window.
    Behind a forward proxy the proxy owns resolution, so pinning is skipped and
    a network-layer egress policy is the recommended control (see ``deploy/``).
    """
    base: dict[str, Any] = {
        "timeout": httpx.Timeout(REQUEST_TIMEOUT),
        "headers": {"User-Agent": USER_AGENT},
        "follow_redirects": False,  # never chase a redirect off the allow-listed host
    }
    if _forward_proxy_active():
        return httpx.AsyncClient(**base)  # trust_env picks up the proxy; no pinning
    transport = PinnedResolverTransport(httpx.AsyncHTTPTransport())
    return httpx.AsyncClient(transport=transport, trust_env=False, **base)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalise_language(language: str | None) -> str:
    """Guard against the silent EN fallback of the upstream API."""
    if not language:
        return DEFAULT_LANGUAGE
    code = language.upper()
    if code not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language {language!r}. Supported: {', '.join(SUPPORTED_LANGUAGES)}."
        )
    return code


def pick_text(entries: list[dict[str, Any]] | None, language: str) -> str:
    """Extract the localised text from OpenHolidays' ``[{language, text}]`` shape."""
    if not entries:
        return ""
    for entry in entries:
        if entry.get("language", "").upper() == language:
            return entry.get("text", "")
    return entries[0].get("text", "")


class HolidayClient:
    """Thin async client over OpenHolidays and Nager.Date."""

    def __init__(self, http: httpx.AsyncClient | None = None) -> None:
        self._http = http
        self._owns_http = http is None
        self._cache: dict[str, tuple[float, Any]] = {}
        self._last_success: dict[str, str] = {}

    async def __aenter__(self) -> HolidayClient:
        if self._http is None:
            self._http = build_http_client()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._owns_http and self._http is not None:
            await self._http.aclose()
            self._http = None

    # ------------------------------------------------------------------ core

    async def _fetch_with_retry(self, url: str, params: dict[str, Any] | None = None) -> Any:
        """GET with exponential backoff. 4xx (except 429) are not retried."""
        assert self._http is not None, "HolidayClient must be used as an async context manager"

        # Egress guard (SEC-004/-021): scheme + allow-list, then IP blocklist.
        host = guard.assert_host_allowed(url)
        guard.assert_resolved_ip_safe(host)

        last_error: Exception | None = None
        deadline = time.monotonic() + RETRY_TOTAL_BUDGET
        attempts = 0

        for attempt in range(MAX_ATTEMPTS):
            if attempt > 0:
                delay = compute_delay(attempt, last_error)
                # A wait that outlasts the budget is a wait for nobody: the
                # caller has given up by the time it ends. Stop instead.
                if delay >= deadline - time.monotonic():
                    break
                await asyncio.sleep(delay)

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            attempts += 1
            try:
                # httpx bounds each operation and restarts its read timeout
                # with every chunk, so a slowly trickling response outlives a
                # per-operation limit without any single read expiring.
                # `asyncio.wait_for` is the wall-clock bound the budget
                # actually promises (`asyncio.timeout` needs 3.11; this package
                # supports 3.10).
                response = await asyncio.wait_for(self._http.get(url, params=params), remaining)
                response.raise_for_status()
                return response.json()
            except asyncio.TimeoutError as exc:  # budget gone, not just this try
                last_error = exc
                _log.warning(
                    "upstream_budget_spent",
                    extra={"context": {"url": url, "attempt": attempt + 1}},
                )
                break
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code
                if 400 <= status < 500 and status != 429:
                    # Client error: log the detail, surface only the status (OBS-002).
                    _log.warning(
                        "upstream_client_error",
                        extra={"context": {"url": url, "status": status}},
                    )
                    raise UpstreamError(f"upstream returned HTTP {status}") from exc
                _log.warning(
                    "upstream_retryable_status",
                    extra={"context": {"url": url, "status": status, "attempt": attempt + 1}},
                )
            except (httpx.RequestError, ValueError) as exc:
                last_error = exc
                _log.warning(
                    "upstream_request_error",
                    extra={
                        "context": {
                            "url": url,
                            "error": type(exc).__name__,
                            "attempt": attempt + 1,
                        }
                    },
                )

        _log.error(
            "upstream_unreachable",
            extra={
                "context": {
                    "url": url,
                    "host": host,
                    "attempts": attempts,
                    # The TYPE, not `str(last_error)`. `httpx.ConnectTimeout`,
                    # `ReadTimeout` and `ConnectError` all carry an empty
                    # `str()` and are the only errors an outage produces — this
                    # log line was already right about that, and stays so.
                    "last_error": type(last_error).__name__ if last_error else None,
                    # Which of the two limits ran out: "all attempts used" and
                    # "the budget ran out after 2" call for different fixes.
                    "limit": ("attempts" if attempts >= MAX_ATTEMPTS else "time_budget"),
                }
            },
        )
        # Message is intentionally generic — the detail is only in the log (OBS-002).
        raise UpstreamError(f"upstream unreachable after {attempts} attempt(s)")

    async def _cached(self, key: str, url: str, params: dict[str, Any]) -> tuple[Any, str, str]:
        """Return ``(payload, provenance, retrieved_at)``."""
        now = time.monotonic()
        hit = self._cache.get(key)
        if hit is not None and now - hit[0] < CACHE_TTL_SECONDS:
            return hit[1], "cached", self._last_success.get(key, utc_now_iso())

        payload = await self._fetch_with_retry(url, params)
        stamp = utc_now_iso()
        self._cache[key] = (now, payload)
        self._last_success[key] = stamp
        return payload, "live_api", stamp

    # -------------------------------------------------------- openholidays

    async def subdivisions(self, language: str) -> tuple[list[dict], str, str]:
        return await self._cached(
            f"subdiv:{language}",
            f"{OPENHOLIDAYS_BASE}/Subdivisions",
            {"countryIsoCode": "CH", "languageIsoCode": language},
        )

    async def groups(self, language: str) -> tuple[list[dict], str, str]:
        return await self._cached(
            f"groups:{language}",
            f"{OPENHOLIDAYS_BASE}/Groups",
            {"countryIsoCode": "CH", "languageIsoCode": language},
        )

    async def school_holidays(
        self, valid_from: str, valid_to: str, language: str, subdivision: str | None = None
    ) -> tuple[list[dict], str, str]:
        params: dict[str, Any] = {
            "countryIsoCode": "CH",
            "languageIsoCode": language,
            "validFrom": valid_from,
            "validTo": valid_to,
        }
        if subdivision:
            params["subdivisionCode"] = subdivision
        key = f"school:{valid_from}:{valid_to}:{language}:{subdivision or 'ALL'}"
        return await self._cached(key, f"{OPENHOLIDAYS_BASE}/SchoolHolidays", params)

    async def public_holidays(
        self, valid_from: str, valid_to: str, language: str, subdivision: str | None = None
    ) -> tuple[list[dict], str, str]:
        params: dict[str, Any] = {
            "countryIsoCode": "CH",
            "languageIsoCode": language,
            "validFrom": valid_from,
            "validTo": valid_to,
        }
        if subdivision:
            params["subdivisionCode"] = subdivision
        key = f"public:{valid_from}:{valid_to}:{language}:{subdivision or 'ALL'}"
        return await self._cached(key, f"{OPENHOLIDAYS_BASE}/PublicHolidays", params)

    # --------------------------------------------------------------- nager

    async def long_weekends(self, year: int) -> tuple[list[dict], str, str]:
        return await self._cached(f"lw:{year}", f"{NAGER_BASE}/LongWeekend/{year}/CH", {})

    # -------------------------------------------------------------- health

    async def probe(self, name: str, url: str) -> dict[str, Any]:
        assert self._http is not None
        started = time.perf_counter()
        try:
            guard.assert_host_allowed(url)
            guard.assert_resolved_ip_safe(urlparse(url).hostname or "")
            response = await self._http.get(url, timeout=PROBE_TIMEOUT)
            return {
                "name": name,
                "base_url": url,
                "reachable": response.status_code < 500,
                "http_status": response.status_code,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "detail": None,
            }
        except (httpx.RequestError, guard.EgressError) as exc:
            return {
                "name": name,
                "base_url": url,
                "reachable": False,
                "http_status": None,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "detail": type(exc).__name__,
            }


ATTRIBUTIONS = {
    "openholidays": ATTRIBUTION_OPENHOLIDAYS,
    "nager": ATTRIBUTION_NAGER,
}
