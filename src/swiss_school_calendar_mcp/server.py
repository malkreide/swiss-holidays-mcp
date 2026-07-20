"""MCP server exposing Swiss school and public holiday data.

Architecture (audit SDK-001, ARCH-004): a single shared ``HolidayClient`` --
holding one ``httpx.AsyncClient`` and a persistent 12h cache -- is created in the
FastMCP lifespan and injected into every tool via ``Context``. The tool
functions are thin wrappers over transport-agnostic ``op_*`` operations, which
keeps them testable without a live transport.

Tool budget: 10 of the 15-20 recommended maximum, leaving headroom for a
Phase 2 extension (city-level Zurich specifics such as Sechselaeuten and
Knabenschiessen, which are not public holidays and therefore absent upstream).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import combinations
from typing import Annotated, Any

from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field

from .client import (
    ATTRIBUTIONS,
    HolidayClient,
    UpstreamError,
    build_http_client,
    normalise_language,
    pick_text,
    utc_now_iso,
)
from .constants import (
    CANTON_CODES,
    MAX_YEAR,
    MCP_PROTOCOL_VERSION,
    MIN_YEAR,
    NAGER_BASE,
    OPENHOLIDAYS_BASE,
    SCHOOL_TYPE_SUFFIX,
)
from .logging_setup import get_logger
from .models import (
    Canton,
    CantonListResponse,
    DateCheckResponse,
    FreeWindow,
    HolidayListResponse,
    HolidayPeriod,
    LongWeekend,
    LongWeekendResponse,
    OverlapResponse,
    OverlapRow,
    SchoolType,
    SchoolTypeListResponse,
    SourceStatus,
    StatusResponse,
    WindowResponse,
)

_log = get_logger()


@dataclass
class AppState:
    """Lifespan-scoped state shared by all tool calls."""

    client: HolidayClient


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[AppState]:
    """Create one HTTP client + cache for the whole server lifetime (SDK-001)."""
    http = build_http_client()
    try:
        yield AppState(client=HolidayClient(http=http))
    finally:
        await http.aclose()


mcp = FastMCP("swiss-school-calendar-mcp", lifespan=lifespan)

_OH = ATTRIBUTIONS["openholidays"]
_NG = ATTRIBUTIONS["nager"]

# Tool annotations (audit ARCH-009): every tool is read-only, non-destructive,
# idempotent (plain GETs) and reaches an external system (open world).
_RO = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}

# Validated tool-input aliases (audit SEC-018).
CantonCode = Annotated[
    str, Field(pattern=r"^[A-Za-z]{2}-[A-Za-z]{2}$", description="ISO code, e.g. CH-ZH")
]
IsoDate = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="Date as YYYY-MM-DD")]
Year = Annotated[int, Field(ge=MIN_YEAR, le=MAX_YEAR)]
SchoolTypeCode = Annotated[str | None, Field(pattern=r"^(?i:VS|MS|BS|EO)$")]
Language = Annotated[str, Field(pattern=r"^(?i:DE|FR|IT|EN)$")]


# --------------------------------------------------------------- helpers


def _client(ctx: Context) -> HolidayClient:
    return ctx.request_context.lifespan_context.client


def _canton_of(code: str) -> str:
    """CH-BE-TH-BL -> CH-BE. Sub-cantonal codes are common in holiday records."""
    parts = code.split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else code


def _require_known_canton(code: str) -> str:
    """Normalise + validate a canton against the 26 known codes (SEC-018)."""
    normalised = code.strip().upper()
    if normalised not in CANTON_CODES:
        raise ValueError(
            f"Unknown canton {code!r}. Call list_cantons for the 26 valid CH-XX codes."
        )
    return normalised


def _to_period(raw: dict[str, Any], language: str, kind: str) -> HolidayPeriod:
    start = date.fromisoformat(raw["startDate"])
    end = date.fromisoformat(raw["endDate"])
    cantons = sorted({_canton_of(s["code"]) for s in raw.get("subdivisions", [])})
    return HolidayPeriod(
        start_date=start,
        end_date=end,
        name=pick_text(raw.get("name"), language),
        kind=kind,  # type: ignore[arg-type]
        nationwide=bool(raw.get("nationwide")),
        cantons=cantons,
        school_types=[g["code"] for g in raw.get("groups", [])],
        days=(end - start).days + 1,
    )


def _matches_school_type(period: HolidayPeriod, school_type: str | None) -> bool:
    """Filter by Schulart. `None` keeps everything, including undifferentiated rows."""
    if school_type is None:
        return True
    wanted = school_type.upper()
    if not period.school_types:
        # Canton does not differentiate — the record applies to every school type.
        return True
    return any(code.upper().endswith(f"-{wanted}") for code in period.school_types)


def _degraded(reason: str, attribution: str) -> dict[str, Any]:
    """Build a degraded envelope. ``reason`` is a short, user-safe string; the raw
    error is only ever in the stderr log (audit OBS-002)."""
    _log.warning("degraded_response", extra={"context": {"reason": reason}})
    return {
        "source": attribution,
        "provenance": "degraded",
        "retrieved_at": utc_now_iso(),
        "note": (
            "The upstream source is currently unavailable and no cached copy exists "
            "for this query. Please retry in about 10 minutes."
        ),
    }


def _days_in(period: HolidayPeriod) -> set[date]:
    return {period.start_date + timedelta(days=i) for i in range(period.days)}


# ------------------------------------------------------- operations (logic)


async def op_list_cantons(client: HolidayClient, language: str = "DE") -> CantonListResponse:
    lang = normalise_language(language)
    try:
        raw, provenance, stamp = await client.subdivisions(lang)
    except UpstreamError:
        return CantonListResponse(**_degraded("subdivisions", _OH), cantons=[])

    cantons = [
        Canton(
            code=entry["code"],
            short_name=entry["shortName"],
            name=pick_text(entry.get("name"), lang),
            official_languages=entry.get("officialLanguages", []),
        )
        for entry in raw
        if entry["code"] in CANTON_CODES
    ]
    return CantonListResponse(
        source=_OH,
        provenance=provenance,
        retrieved_at=stamp,
        cantons=sorted(cantons, key=lambda c: c.code),
    )


async def op_list_school_types(
    client: HolidayClient, canton: str | None = None, language: str = "DE"
) -> SchoolTypeListResponse:
    lang = normalise_language(language)
    try:
        raw, provenance, stamp = await client.groups(lang)
    except UpstreamError:
        return SchoolTypeListResponse(**_degraded("groups", _OH), school_types=[])

    types = [
        SchoolType(
            code=entry["code"],
            canton=_canton_of(entry["code"]),
            name=pick_text(entry.get("name"), lang),
        )
        for entry in raw
    ]
    if canton:
        wanted = _require_known_canton(canton)
        types = [t for t in types if t.canton.upper() == wanted]
    return SchoolTypeListResponse(
        source=_OH,
        provenance=provenance,
        retrieved_at=stamp,
        school_types=sorted(types, key=lambda t: t.code),
    )


async def op_get_school_holidays(
    client: HolidayClient,
    canton: str,
    valid_from: str,
    valid_to: str,
    school_type: str | None = None,
    language: str = "DE",
) -> HolidayListResponse:
    lang = normalise_language(language)
    canton_code = _require_known_canton(canton)
    try:
        raw, provenance, stamp = await client.school_holidays(
            valid_from, valid_to, lang, canton_code
        )
    except UpstreamError:
        return HolidayListResponse(**_degraded("school_holidays", _OH), count=0, holidays=[])

    periods = [_to_period(entry, lang, "School") for entry in raw]
    periods = [p for p in periods if _matches_school_type(p, school_type)]
    periods.sort(key=lambda p: p.start_date)

    note = None
    if not periods:
        note = (
            f"No school holidays returned for {canton_code} between {valid_from} and "
            f"{valid_to}. This canton may not differentiate this Schulart, or the range "
            "holds no holidays."
        )
    return HolidayListResponse(
        source=_OH,
        provenance=provenance,
        retrieved_at=stamp,
        note=note,
        count=len(periods),
        holidays=periods,
    )


async def op_get_public_holidays(
    client: HolidayClient, canton: str, year: int, language: str = "DE"
) -> HolidayListResponse:
    lang = normalise_language(language)
    canton_code = _require_known_canton(canton)
    try:
        raw, provenance, stamp = await client.public_holidays(
            f"{year}-01-01", f"{year}-12-31", lang, canton_code
        )
    except UpstreamError:
        return HolidayListResponse(**_degraded("public_holidays", _OH), count=0, holidays=[])

    periods = sorted(
        (_to_period(entry, lang, "Public") for entry in raw), key=lambda p: p.start_date
    )
    return HolidayListResponse(
        source=_OH,
        provenance=provenance,
        retrieved_at=stamp,
        count=len(periods),
        holidays=periods,
    )


async def op_check_date(
    client: HolidayClient,
    check_date_iso: str,
    canton: str,
    school_type: str | None = None,
    language: str = "DE",
) -> DateCheckResponse:
    lang = normalise_language(language)
    canton_code = _require_known_canton(canton)
    target = date.fromisoformat(check_date_iso)
    window_from = (target - timedelta(days=40)).isoformat()
    window_to = (target + timedelta(days=40)).isoformat()

    try:
        # Aggregate the two upstream lookups concurrently (audit ARCH-007).
        (school_raw, provenance, stamp), (public_raw, _, _) = await asyncio.gather(
            client.school_holidays(window_from, window_to, lang, canton_code),
            client.public_holidays(window_from, window_to, lang, canton_code),
        )
    except UpstreamError:
        return DateCheckResponse(
            **_degraded("check_date", _OH),
            checked_date=target,
            canton=canton_code,
            is_school_holiday=False,
            is_public_holiday=False,
            matches=[],
        )

    school = [
        p
        for p in (_to_period(e, lang, "School") for e in school_raw)
        if p.start_date <= target <= p.end_date and _matches_school_type(p, school_type)
    ]
    public = [
        p
        for p in (_to_period(e, lang, "Public") for e in public_raw)
        if p.start_date <= target <= p.end_date
    ]
    return DateCheckResponse(
        source=_OH,
        provenance=provenance,
        retrieved_at=stamp,
        checked_date=target,
        canton=canton_code,
        is_school_holiday=bool(school),
        is_public_holiday=bool(public),
        matches=school + public,
    )


async def op_compare_school_holidays(
    client: HolidayClient,
    cantons: list[str],
    year: int,
    school_type: str | None = "VS",
    language: str = "DE",
) -> OverlapResponse:
    lang = normalise_language(language)
    wanted = [_require_known_canton(c) for c in cantons]

    try:
        raw, provenance, stamp = await client.school_holidays(
            f"{year}-01-01", f"{year}-12-31", lang
        )
    except UpstreamError:
        return OverlapResponse(
            **_degraded("compare", _OH), year=year, school_type_filter=school_type, rows=[]
        )

    by_canton: dict[str, list[HolidayPeriod]] = {c: [] for c in wanted}
    for entry in raw:
        period = _to_period(entry, lang, "School")
        if not _matches_school_type(period, school_type):
            continue
        for canton in period.cantons:
            if canton in by_canton:
                by_canton[canton].append(period)

    rows: list[OverlapRow] = []
    for a, b in combinations(wanted, 2):
        days_a = set().union(*(_days_in(p) for p in by_canton[a])) if by_canton[a] else set()
        days_b = set().union(*(_days_in(p) for p in by_canton[b])) if by_canton[b] else set()
        shared = days_a & days_b
        names = sorted(
            {p.name for p in by_canton[a] if _days_in(p) & shared}
            | {p.name for p in by_canton[b] if _days_in(p) & shared}
        )
        rows.append(
            OverlapRow(canton_a=a, canton_b=b, overlapping_days=len(shared), shared_periods=names)
        )

    return OverlapResponse(
        source=_OH,
        provenance=provenance,
        retrieved_at=stamp,
        year=year,
        school_type_filter=school_type,
        rows=sorted(rows, key=lambda r: -r.overlapping_days),
    )


async def op_find_common_free_window(
    client: HolidayClient,
    cantons: list[str],
    year: int,
    min_days: int = 5,
    school_type: str | None = "VS",
    language: str = "DE",
) -> WindowResponse:
    lang = normalise_language(language)
    wanted = [_require_known_canton(c) for c in cantons]

    try:
        raw, provenance, stamp = await client.school_holidays(
            f"{year}-01-01", f"{year}-12-31", lang
        )
    except UpstreamError:
        return WindowResponse(**_degraded("free_window", _OH), windows=[])

    day_sets: dict[str, set[date]] = {c: set() for c in wanted}
    for entry in raw:
        period = _to_period(entry, lang, "School")
        if not _matches_school_type(period, school_type):
            continue
        for canton in period.cantons:
            if canton in day_sets:
                day_sets[canton] |= _days_in(period)

    common = set.intersection(*day_sets.values()) if day_sets else set()
    windows: list[FreeWindow] = []
    for day in sorted(common):
        if windows and day - windows[-1].end_date == timedelta(days=1):
            windows[-1].end_date = day
            windows[-1].days += 1
        else:
            windows.append(
                FreeWindow(
                    start_date=day,
                    end_date=day,
                    days=1,
                    cantons_on_holiday=wanted,
                    cantons_in_school=[],
                )
            )

    return WindowResponse(
        source=_OH,
        provenance=provenance,
        retrieved_at=stamp,
        windows=[w for w in windows if w.days >= min_days],
    )


async def op_next_school_holidays(
    client: HolidayClient,
    canton: str,
    count: int = 3,
    school_type: str | None = "VS",
    language: str = "DE",
) -> HolidayListResponse:
    lang = normalise_language(language)
    canton_code = _require_known_canton(canton)
    today = date.today()
    try:
        raw, provenance, stamp = await client.school_holidays(
            today.isoformat(), (today + timedelta(days=420)).isoformat(), lang, canton_code
        )
    except UpstreamError:
        return HolidayListResponse(**_degraded("next_holidays", _OH), count=0, holidays=[])

    periods = sorted(
        (
            p
            for p in (_to_period(e, lang, "School") for e in raw)
            if p.end_date >= today and _matches_school_type(p, school_type)
        ),
        key=lambda p: p.start_date,
    )[: max(1, count)]
    return HolidayListResponse(
        source=_OH,
        provenance=provenance,
        retrieved_at=stamp,
        count=len(periods),
        holidays=periods,
    )


async def op_get_long_weekends(client: HolidayClient, year: int) -> LongWeekendResponse:
    try:
        raw, provenance, stamp = await client.long_weekends(year)
    except UpstreamError:
        return LongWeekendResponse(**_degraded("long_weekends", _NG), year=year, long_weekends=[])

    weekends = [
        LongWeekend(
            start_date=date.fromisoformat(entry["startDate"]),
            end_date=date.fromisoformat(entry["endDate"]),
            day_count=entry["dayCount"],
            needs_bridge_day=entry["needBridgeDay"],
            bridge_days=[date.fromisoformat(d) for d in entry.get("bridgeDays", [])],
        )
        for entry in raw
    ]
    return LongWeekendResponse(
        source=_NG,
        provenance=provenance,
        retrieved_at=stamp,
        year=year,
        long_weekends=weekends,
    )


async def op_source_status(client: HolidayClient) -> StatusResponse:
    probes = [
        await client.probe("OpenHolidays API", f"{OPENHOLIDAYS_BASE}/Countries"),
        await client.probe("Nager.Date", f"{NAGER_BASE}/AvailableCountries"),
    ]
    sources = [SourceStatus(**p) for p in probes]
    return StatusResponse(
        source=f"{_OH} | {_NG}",
        provenance="live_api",
        retrieved_at=utc_now_iso(),
        mcp_protocol_version=MCP_PROTOCOL_VERSION,
        sources=sources,
        all_healthy=all(s.reachable for s in sources),
    )


# ----------------------------------------------------------------- tools


@mcp.tool(annotations=_RO)
async def list_cantons(ctx: Context, language: Language = "DE") -> CantonListResponse:
    """List the 26 Swiss cantons with their ISO subdivision codes.

    Use this first to resolve a canton name to the `CH-XX` code that every other
    tool expects.
    """
    return await op_list_cantons(_client(ctx), language)


@mcp.tool(annotations=_RO)
async def list_school_types(
    ctx: Context, canton: CantonCode | None = None, language: Language = "DE"
) -> SchoolTypeListResponse:
    """List the Schularten (school types) that publish separate holiday tables.

    Only a minority of cantons differentiate. For Zurich the codes are
    `CH-ZH-VS` (Volksschulen), `CH-ZH-MS` (Mittelschulen) and `CH-ZH-BS`
    (Berufsfachschulen). Cantons absent from this list publish one table for
    all school types.
    """
    return await op_list_school_types(_client(ctx), canton, language)


@mcp.tool(annotations=_RO)
async def get_school_holidays(
    ctx: Context,
    canton: CantonCode,
    valid_from: IsoDate,
    valid_to: IsoDate,
    school_type: SchoolTypeCode = None,
    language: Language = "DE",
) -> HolidayListResponse:
    """Return school holiday periods for one canton in a date range.

    Args:
        canton: ISO subdivision code, e.g. `CH-ZH`.
        valid_from: Inclusive start date, `YYYY-MM-DD`.
        valid_to: Inclusive end date, `YYYY-MM-DD`.
        school_type: Optional Schulart suffix -- `VS`, `MS`, `BS` or `EO`.
            Use `VS` for compulsory schooling (Volksschule).
        language: `DE`, `FR`, `IT` or `EN`.

    Records that look duplicated are usually the same period published for a
    different Schulart. Set `school_type` to collapse them.
    """
    return await op_get_school_holidays(
        _client(ctx), canton, valid_from, valid_to, school_type, language
    )


@mcp.tool(annotations=_RO)
async def get_public_holidays(
    ctx: Context, canton: CantonCode, year: Year, language: Language = "DE"
) -> HolidayListResponse:
    """Return public holidays for one canton and calendar year.

    Cantonal holidays such as Berchtoldstag differ substantially across
    Switzerland, so always pass the canton rather than assuming the federal set.
    """
    return await op_get_public_holidays(_client(ctx), canton, year, language)


@mcp.tool(annotations=_RO)
async def check_date(
    ctx: Context,
    check_date_iso: IsoDate,
    canton: CantonCode,
    school_type: SchoolTypeCode = None,
    language: Language = "DE",
) -> DateCheckResponse:
    """Check whether a given date falls into school holidays or a public holiday.

    The everyday question behind this tool: "Can we schedule the parents'
    evening on that Thursday?"
    """
    return await op_check_date(_client(ctx), check_date_iso, canton, school_type, language)


@mcp.tool(annotations=_RO)
async def compare_school_holidays(
    ctx: Context,
    cantons: list[CantonCode],
    year: Year,
    school_type: SchoolTypeCode = "VS",
    language: Language = "DE",
) -> OverlapResponse:
    """Compare school holiday overlap between cantons for a calendar year.

    Returns a pairwise matrix of overlapping holiday days. Defaults to `VS`
    (Volksschule) because that is the level most inter-cantonal coordination
    concerns.
    """
    return await op_compare_school_holidays(_client(ctx), cantons, year, school_type, language)


@mcp.tool(annotations=_RO)
async def find_common_free_window(
    ctx: Context,
    cantons: list[CantonCode],
    year: Year,
    min_days: Annotated[int, Field(ge=1, le=90)] = 5,
    school_type: SchoolTypeCode = "VS",
    language: Language = "DE",
) -> WindowResponse:
    """Find date ranges in which all listed cantons are simultaneously on holiday.

    Useful for planning campaigns, joint events or maintenance windows across
    cantonal borders.
    """
    return await op_find_common_free_window(
        _client(ctx), cantons, year, min_days, school_type, language
    )


@mcp.tool(annotations=_RO)
async def next_school_holidays(
    ctx: Context,
    canton: CantonCode,
    count: Annotated[int, Field(ge=1, le=20)] = 3,
    school_type: SchoolTypeCode = "VS",
    language: Language = "DE",
) -> HolidayListResponse:
    """Return the next upcoming school holiday periods for a canton."""
    return await op_next_school_holidays(_client(ctx), canton, count, school_type, language)


@mcp.tool(annotations=_RO)
async def get_long_weekends(ctx: Context, year: Year) -> LongWeekendResponse:
    """Return Swiss long weekends and the bridge days needed to create them.

    Sourced from Nager.Date, which computes these from federal public holidays;
    cantonal-only holidays are not considered.
    """
    return await op_get_long_weekends(_client(ctx), year)


@mcp.tool(annotations=_RO)
async def source_status(ctx: Context) -> StatusResponse:
    """Report reachability and latency of both upstream sources.

    Always returns an evaluable status rather than an empty result set, so that
    "no data" can be distinguished from "source down".
    """
    return await op_source_status(_client(ctx))


__all__ = ["mcp", "SCHOOL_TYPE_SUFFIX"]
