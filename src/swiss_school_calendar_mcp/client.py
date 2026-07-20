"""HTTP access layer: retry, in-memory cache, and payload normalisation.

Design notes from the live probe (2026-07-19):

* OpenHolidays answers an unknown ``countryIsoCode`` with HTTP 200 and ``[]``.
  An empty list is therefore *not* proof of "no holidays" — it can equally mean
  "your filter was wrong". ``UpstreamEmpty`` makes that distinction explicit.
* An unknown ``languageIsoCode`` silently falls back to EN instead of erroring.
  We validate the language locally before sending it.
* Missing required parameters produce a RFC-9110 problem+json body with HTTP
  400. Those are client errors and must not be retried.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from .constants import (
    ATTRIBUTION_NAGER,
    ATTRIBUTION_OPENHOLIDAYS,
    DEFAULT_LANGUAGE,
    NAGER_BASE,
    OPENHOLIDAYS_BASE,
    SUPPORTED_LANGUAGES,
    USER_AGENT,
)

MAX_ATTEMPTS = 4
CACHE_TTL_SECONDS = 60 * 60 * 12  # holiday tables change a few times per year


class UpstreamError(RuntimeError):
    """Upstream unreachable after all retries."""


class UpstreamEmpty(RuntimeError):
    """Upstream answered 200 but with an empty payload — usually a bad filter."""


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
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(20.0), headers={"User-Agent": USER_AGENT}
            )
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._owns_http and self._http is not None:
            await self._http.aclose()
            self._http = None

    # ------------------------------------------------------------------ core

    async def _fetch_with_retry(self, url: str, params: dict[str, Any] | None = None) -> Any:
        """GET with exponential backoff. 4xx (except 429) are not retried."""
        assert self._http is not None, "HolidayClient must be used as an async context manager"
        last_error: Exception | None = None

        for attempt in range(MAX_ATTEMPTS):
            if attempt > 0:
                await asyncio.sleep(2**attempt)  # 2s, 4s, 8s
            try:
                response = await self._http.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code
                if 400 <= status < 500 and status != 429:
                    detail = exc.response.text[:300]
                    raise UpstreamError(f"HTTP {status} from {url}: {detail}") from exc
            except (httpx.RequestError, ValueError) as exc:
                last_error = exc

        raise UpstreamError(f"Upstream unreachable after {MAX_ATTEMPTS} attempts: {last_error}")

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
            response = await self._http.get(url, timeout=8.0)
            return {
                "name": name,
                "base_url": url,
                "reachable": response.status_code < 500,
                "http_status": response.status_code,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "detail": None,
            }
        except httpx.RequestError as exc:
            return {
                "name": name,
                "base_url": url,
                "reachable": False,
                "http_status": None,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "detail": f"{type(exc).__name__}: {exc}",
            }


ATTRIBUTIONS = {
    "openholidays": ATTRIBUTION_OPENHOLIDAYS,
    "nager": ATTRIBUTION_NAGER,
}
