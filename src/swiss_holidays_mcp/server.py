"""MCP server exposing Swiss school and public holiday data.

Architecture (audit SDK-001, ARCH-004): a single shared ``HolidayClient`` --
holding one ``httpx.AsyncClient`` and a persistent 12h cache -- is created in the
FastMCP lifespan and injected into every tool via ``Context``. The tool
functions are thin wrappers over transport-agnostic ``op_*`` operations, which
keeps them testable without a live transport.

Primitives: 13 tools + 1 resource (``holidays://{canton}/{year}``) — within the
15-20 recommended tool budget, with headroom for a Phase 2 extension (city-level
Zurich specifics such as Sechselaeuten and Knabenschiessen, which are not public
holidays and therefore absent upstream).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date, timedelta
from functools import wraps
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
from .ical import build_ics
from .logging_setup import get_logger
from .models import (
    Canton,
    CantonListResponse,
    DateCheckResponse,
    FreeWindow,
    HolidayListResponse,
    HolidayPeriod,
    IcsResponse,
    LongWeekend,
    LongWeekendResponse,
    OverlapResponse,
    OverlapRow,
    SchoolType,
    SchoolTypeListResponse,
    SourceStatus,
    StatusResponse,
    Subdivision,
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


mcp = FastMCP("swiss-holidays-mcp", lifespan=lifespan)

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
Include = Annotated[str, Field(pattern=r"^(?i:all|public|school)$")]


def _safe_tool(fn):
    """Mask unexpected internal errors before they reach the model (audit OBS-002).

    This SDK version has no ``mask_error_details`` flag: FastMCP surfaces any
    exception raised inside a tool to the client as the text of an ``isError``
    result. Deliberate ``ValueError`` messages (input validation, e.g. an
    unknown canton) are user-safe and pass through unchanged; every other
    exception is logged to stderr only (OBS-002) and replaced with a generic
    message, so tracebacks and internal detail never reach the LLM.
    """

    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await fn(*args, **kwargs)
        except ValueError:
            raise
        except Exception as exc:
            _log.error(
                "tool_unexpected_error",
                extra={"context": {"tool": fn.__name__, "error": type(exc).__name__}},
            )
            raise RuntimeError(
                "The server hit an unexpected internal error. Please retry in a "
                "moment; if it persists, the upstream data format may have changed."
            ) from None

    return wrapper


# --------------------------------------------------------------- helpers


def _client(ctx: Context) -> HolidayClient:
    return ctx.request_context.lifespan_context.client


def _canton_of(code: str) -> str:
    """CH-BE-TH-BL -> CH-BE. Sub-cantonal codes are common in holiday records."""
    parts = code.split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else code


def _level_of(code: str) -> str:
    """CH-ZH -> cantonal, CH-ZH-ZH -> district (Bezirk), CH-ZH-ZH-ZH -> municipal."""
    return {2: "district", 3: "municipal"}.get(code.count("-"), "cantonal")


_SCOPE_MAP = {"National": "national", "Regional": "regional", "Local": "local"}


def _scope_of(raw: dict[str, Any]) -> str:
    """Map upstream ``regionalScope`` to national | regional | local.

    Falls back to nationwide when the field is absent (e.g. school holidays), so
    the value is always populated.
    """
    scope = _SCOPE_MAP.get(raw.get("regionalScope", ""))
    if scope:
        return scope
    return "national" if raw.get("nationwide") else "regional"


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
    subs_raw = raw.get("subdivisions") or []
    cantons = sorted({_canton_of(s["code"]) for s in subs_raw})
    # Keep only sub-cantonal areas: those the canton roll-up cannot represent
    # (Bezirk / Gemeinde). This is where the flattening bug used to lose fidelity.
    subdivisions = [
        Subdivision(
            code=s["code"],
            name=s.get("shortName") or s["code"],
            level=_level_of(s["code"]),  # type: ignore[arg-type]
        )
        for s in subs_raw
        if s["code"].count("-") >= 2
    ]
    return HolidayPeriod(
        start_date=start,
        end_date=end,
        name=pick_text(raw.get("name"), language),
        kind=kind,  # type: ignore[arg-type]
        nationwide=bool(raw.get("nationwide")),
        scope=_scope_of(raw),  # type: ignore[arg-type]
        half_day=raw.get("temporalScope") == "HalfDay",
        cantons=cantons,
        subdivisions=subdivisions,
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


def _flatten_localities(tree: list[dict[str, Any]], canton_code: str, lang: str) -> list[tuple]:
    """Return (code, name, level) for every district/municipality under a canton."""
    out: list[tuple] = []

    def walk(node: dict[str, Any]) -> None:
        code = node.get("code", "")
        if code.count("-") >= 2:  # Bezirk or Gemeinde
            out.append((code, pick_text(node.get("name"), lang), _level_of(code)))
        for child in node.get("children") or []:
            walk(child)

    for canton in tree:
        if canton.get("code") == canton_code:
            for child in canton.get("children") or []:
                walk(child)
            break
    return out


def _resolve_locality(
    tree: list[dict[str, Any]], canton_code: str, query: str, lang: str
) -> tuple[str | None, str, list[str]]:
    """Resolve a district/municipality name *or* code within a canton to its code.

    Returns ``(code, display_name, candidates)``. ``code`` is ``None`` on no match,
    in which case ``candidates`` holds a few near suggestions for the error note.
    """
    areas = _flatten_localities(tree, canton_code, lang)
    q = query.strip()
    qu = q.upper()
    for code, name, _level in areas:  # exact code, e.g. "CH-ZH-ZH-ZH"
        if code.upper() == qu:
            return code, name, []
    ql = q.lower()
    exact = [a for a in areas if a[1].lower() == ql]
    if exact:  # a municipality wins over a same-named district
        exact.sort(key=lambda a: 0 if a[2] == "municipal" else 1)
        return exact[0][0], exact[0][1], []
    prefix = [a for a in areas if a[1].lower().startswith(ql)]
    if len(prefix) == 1:
        return prefix[0][0], prefix[0][1], []
    candidates = sorted({a[1] for a in areas if ql in a[1].lower()})[:8]
    return None, "", candidates


async def op_get_local_holidays(
    client: HolidayClient,
    canton: str,
    municipality: str,
    year: int,
    language: str = "DE",
) -> HolidayListResponse:
    lang = normalise_language(language)
    canton_code = _require_known_canton(canton)
    try:
        tree, _prov, _stamp = await client.subdivisions(lang)
    except UpstreamError:
        return HolidayListResponse(**_degraded("subdivisions", _OH), count=0, holidays=[])

    code, display, candidates = _resolve_locality(tree, canton_code, municipality, lang)
    if code is None:
        hint = f" Did you mean: {', '.join(candidates)}?" if candidates else ""
        return HolidayListResponse(
            source=_OH,
            provenance="degraded",
            retrieved_at=utc_now_iso(),
            note=f"No district or municipality matching {municipality!r} in {canton_code}.{hint}",
            count=0,
            holidays=[],
        )

    try:
        raw, provenance, stamp = await client.public_holidays(
            f"{year}-01-01", f"{year}-12-31", lang, code
        )
    except UpstreamError:
        return HolidayListResponse(**_degraded("public_holidays", _OH), count=0, holidays=[])

    periods = sorted(
        (_to_period(entry, lang, "Public") for entry in raw), key=lambda p: p.start_date
    )
    local = [p.name for p in periods if p.scope == "local"]
    if local:
        local_note = f"Specific to {display}: {', '.join(local)}."
    else:
        local_note = (
            f"{display} has no locality-specific public holidays this year — all listed "
            "holidays are inherited from the canton or the confederation."
        )
    note = (
        f"Resolved {municipality!r} → {code} ({display}). {local_note} Holidays with "
        "scope 'regional' or 'national' are inherited, not locality-specific."
    )
    return HolidayListResponse(
        source=_OH,
        provenance=provenance,
        retrieved_at=stamp,
        note=note,
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


async def op_holidays_bundle(
    client: HolidayClient,
    canton: str,
    year: int,
    include: str = "all",
    school_type: str | None = None,
    language: str = "DE",
) -> tuple[str, list[HolidayPeriod], str, str]:
    """Fetch a canton's public and/or school holidays for a whole year.

    Shared by the ICS export and the ``holidays://`` resource. Raises
    ``UpstreamError`` on failure; callers turn that into a degraded envelope.
    """
    lang = normalise_language(language)
    canton_code = _require_known_canton(canton)
    mode = include.lower()
    frm, to = f"{year}-01-01", f"{year}-12-31"

    want_school = mode in ("all", "school")
    want_public = mode in ("all", "public")
    calls = []
    if want_school:
        calls.append(client.school_holidays(frm, to, lang, canton_code))
    if want_public:
        calls.append(client.public_holidays(frm, to, lang, canton_code))
    results = await asyncio.gather(*calls)

    periods: list[HolidayPeriod] = []
    provenance, stamp = "live_api", utc_now_iso()
    cursor = 0
    if want_school:
        raw, provenance, stamp = results[cursor]
        cursor += 1
        periods += [
            p
            for p in (_to_period(e, lang, "School") for e in raw)
            if _matches_school_type(p, school_type)
        ]
    if want_public:
        raw, provenance, stamp = results[cursor]
        periods += [_to_period(e, lang, "Public") for e in raw]

    periods.sort(key=lambda p: (p.start_date, p.kind))
    return canton_code, periods, provenance, stamp


def _bundle_markdown(canton: str, year: int, periods: list[HolidayPeriod], source: str) -> str:
    public = [p for p in periods if p.kind == "Public"]
    school = [p for p in periods if p.kind == "School"]
    lines = [f"# Holidays {canton} {year}", ""]
    if not periods:
        lines.append("_No holidays found for this canton and year._")
    for label, items in (("Public holidays", public), ("School holidays", school)):
        if not items:
            continue
        lines += [f"## {label}", ""]
        for p in items:
            span = f"{p.start_date:%Y-%m-%d}" + (
                f" → {p.end_date:%Y-%m-%d} ({p.days} days)" if p.days > 1 else ""
            )
            suffix = f" — {', '.join(p.school_types)}" if p.school_types else ""
            lines.append(f"- **{p.name}**: {span}{suffix}")
        lines.append("")
    lines.append(f"> Source: {source}")
    return "\n".join(lines)


# ----------------------------------------------------------------- tools


@mcp.tool(annotations=_RO)
@_safe_tool
async def list_cantons(ctx: Context, language: Language = "DE") -> CantonListResponse:
    """List the 26 Swiss cantons with their ISO subdivision codes.

    <use_case>Resolve a canton name to the CH-XX code every other tool needs; call this first when
    the user gives a canton by name.</use_case>

    Use this first to resolve a canton name to the `CH-XX` code that every other
    tool expects.
    """
    return await op_list_cantons(_client(ctx), language)


@mcp.tool(annotations=_RO)
@_safe_tool
async def list_school_types(
    ctx: Context, canton: CantonCode | None = None, language: Language = "DE"
) -> SchoolTypeListResponse:
    """List the Schularten (school types) that publish separate holiday tables.

    <use_case>Discover whether a canton differentiates school holidays by Schulart before querying,
    so VS/MS/BS/EO filters are used only where they exist.</use_case>

    Only a minority of cantons differentiate. For Zurich the codes are
    `CH-ZH-VS` (Volksschulen), `CH-ZH-MS` (Mittelschulen) and `CH-ZH-BS`
    (Berufsfachschulen). Cantons absent from this list publish one table for
    all school types.
    """
    return await op_list_school_types(_client(ctx), canton, language)


@mcp.tool(annotations=_RO)
@_safe_tool
async def get_school_holidays(
    ctx: Context,
    canton: CantonCode,
    valid_from: IsoDate,
    valid_to: IsoDate,
    school_type: SchoolTypeCode = None,
    language: Language = "DE",
) -> HolidayListResponse:
    """Return school holiday periods for one canton in a date range.

    <use_case>Look up a canton's school holidays for planning within an explicit from/to window
    (term breaks, parent events, campaigns).</use_case>
    <important_notes>Apparent duplicates are the same period per Schulart; set school_type to
    collapse them. Cantons that do not differentiate return one table.</important_notes>

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
@_safe_tool
async def get_public_holidays(
    ctx: Context, canton: CantonCode, year: Year, language: Language = "DE"
) -> HolidayListResponse:
    """Return public holidays for one canton and calendar year.

    <use_case>Get a canton's official public holidays for a whole year — cantonal holidays
    (Berchtoldstag, Fronleichnam) differ, so always pass the canton.</use_case>

    Cantonal holidays such as Berchtoldstag differ substantially across
    Switzerland, so always pass the canton rather than assuming the federal set.
    """
    return await op_get_public_holidays(_client(ctx), canton, year, language)


@mcp.tool(annotations=_RO)
@_safe_tool
async def get_local_holidays(
    ctx: Context,
    canton: CantonCode,
    municipality: str,
    year: Year,
    language: Language = "DE",
) -> HolidayListResponse:
    """Public holidays for a single municipality or district, incl. local specifics.

    <use_case>Answer the locality question the canton-level tools flatten away: which holidays are
    observed only in this town (e.g. Zurich's Sechselaeuten)?</use_case>
    <important_notes>scope is 'local' (specific here), 'regional' (canton/district) or 'national'
    (inherited). Accepts a name or a full subdivision code.</important_notes>

    Answers the local question the canton-level tools flatten away: which holidays
    are observed *only* here? The city of Zurich, for example, keeps Sechseläuten
    and Knabenschiessen (both half-day), which the rest of the canton does not.

    `municipality` accepts a name (e.g. "Zürich", "Morschach") or a full
    subdivision code (e.g. "CH-ZH-ZH-ZH"). The result lists every holiday that
    applies in that locality; each carries a `scope` of `local` (specific to this
    place), `regional` (inherited from the canton/district) or `national`.
    """
    return await op_get_local_holidays(_client(ctx), canton, municipality, year, language)


@mcp.tool(annotations=_RO)
@_safe_tool
async def check_date(
    ctx: Context,
    check_date_iso: IsoDate,
    canton: CantonCode,
    school_type: SchoolTypeCode = None,
    language: Language = "DE",
) -> DateCheckResponse:
    """Check whether a given date falls into school holidays or a public holiday.

    <use_case>The everyday scheduling question: can we hold the parents' evening on that Thursday?
    Checks one date against both school and public holidays.</use_case>

    The everyday question behind this tool: "Can we schedule the parents'
    evening on that Thursday?"
    """
    return await op_check_date(_client(ctx), check_date_iso, canton, school_type, language)


@mcp.tool(annotations=_RO)
@_safe_tool
async def compare_school_holidays(
    ctx: Context,
    cantons: list[CantonCode],
    year: Year,
    school_type: SchoolTypeCode = "VS",
    language: Language = "DE",
) -> OverlapResponse:
    """Compare school holiday overlap between cantons for a calendar year.

    <use_case>Quantify inter-cantonal school-holiday overlap (pairwise day counts) for coordinating
    events or campaigns across cantonal borders.</use_case>

    Returns a pairwise matrix of overlapping holiday days. Defaults to `VS`
    (Volksschule) because that is the level most inter-cantonal coordination
    concerns.
    """
    return await op_compare_school_holidays(_client(ctx), cantons, year, school_type, language)


@mcp.tool(annotations=_RO)
@_safe_tool
async def find_common_free_window(
    ctx: Context,
    cantons: list[CantonCode],
    year: Year,
    min_days: Annotated[int, Field(ge=1, le=90)] = 5,
    school_type: SchoolTypeCode = "VS",
    language: Language = "DE",
) -> WindowResponse:
    """Find date ranges in which all listed cantons are simultaneously on holiday.

    <use_case>Find a common free window across several cantons — joint events, maintenance or
    campaigns when every listed canton is on holiday.</use_case>

    Useful for planning campaigns, joint events or maintenance windows across
    cantonal borders.
    """
    return await op_find_common_free_window(
        _client(ctx), cantons, year, min_days, school_type, language
    )


@mcp.tool(annotations=_RO)
@_safe_tool
async def next_school_holidays(
    ctx: Context,
    canton: CantonCode,
    count: Annotated[int, Field(ge=1, le=20)] = 3,
    school_type: SchoolTypeCode = "VS",
    language: Language = "DE",
) -> HolidayListResponse:
    """Return the next upcoming school holiday periods for a canton.

    <use_case>Forward-looking planning: the next N school-holiday periods for a canton from today,
    without computing a date range by hand.</use_case>
    """
    return await op_next_school_holidays(_client(ctx), canton, count, school_type, language)


@mcp.tool(annotations=_RO)
@_safe_tool
async def get_long_weekends(ctx: Context, year: Year) -> LongWeekendResponse:
    """Return Swiss long weekends and the bridge days needed to create them.

    <use_case>Plan bridge days: which long weekends exist this year and which working days must be
    taken off to extend them.</use_case>
    <important_notes>Computed from federal public holidays (Nager.Date); cantonal-only holidays are
    not considered.</important_notes>

    Sourced from Nager.Date, which computes these from federal public holidays;
    cantonal-only holidays are not considered.
    """
    return await op_get_long_weekends(_client(ctx), year)


@mcp.tool(annotations=_RO)
@_safe_tool
async def source_status(ctx: Context) -> StatusResponse:
    """Report reachability and latency of both upstream sources.

    <use_case>Health check before a batch of queries, or to distinguish 'no data' from 'source
    down' — always returns an evaluable status.</use_case>

    Always returns an evaluable status rather than an empty result set, so that
    "no data" can be distinguished from "source down".
    """
    return await op_source_status(_client(ctx))


@mcp.tool(annotations=_RO)
@_safe_tool
async def export_holidays_ics(
    ctx: Context,
    canton: CantonCode,
    year: Year,
    include: Include = "all",
    school_type: SchoolTypeCode = None,
    language: Language = "DE",
) -> IcsResponse:
    """Export a canton's holidays for a year as an iCalendar (.ics) document.

    <use_case>Produce a ready-to-import .ics calendar of a canton's holidays for a year, filtered
    by public/school and Schulart.</use_case>

    Returns a ready-to-save `text/calendar` document with one all-day event per
    holiday. `include` selects `all` (default), `public` or `school`; combine
    with `school_type` (`VS`/`MS`/`BS`/`EO`) to narrow school holidays.
    """
    try:
        canton_code, periods, provenance, stamp = await op_holidays_bundle(
            _client(ctx), canton, year, include, school_type, language
        )
    except UpstreamError:
        return IcsResponse(
            **_degraded("ics", _OH),
            canton=canton.strip().upper(),
            year=year,
            event_count=0,
            filename=f"holidays-{canton.strip().upper()}-{year}.ics",
            ics="",
        )

    ics = build_ics(
        (p.model_dump() for p in periods),
        calendar_name=f"Swiss holidays {canton_code} {year}",
        source=_OH,
    )
    return IcsResponse(
        source=_OH,
        provenance=provenance,
        retrieved_at=stamp,
        canton=canton_code,
        year=year,
        event_count=len(periods),
        filename=f"holidays-{canton_code}-{year}.ics",
        ics=ics,
    )


@mcp.tool(annotations=_RO)
@_safe_tool
async def is_holiday_today(
    ctx: Context, canton: CantonCode, school_type: SchoolTypeCode = None, language: Language = "DE"
) -> DateCheckResponse:
    """Is today a school or public holiday in the given canton?

    <use_case>One-call convenience for the everyday 'are we off today?' question in a given
    canton.</use_case>

    Convenience wrapper over `check_date` for the everyday question
    "are we off today?".
    """
    return await op_check_date(
        _client(ctx), date.today().isoformat(), canton, school_type, language
    )


@mcp.resource("holidays://{canton}/{year}")
async def holidays_resource(canton: str, year: str, ctx: Context) -> str:
    """All public + school holidays for a canton and year, as a Markdown feed.

    URI example: `holidays://CH-ZH/2026`.
    """
    try:
        parsed_year = int(year)
    except ValueError:
        return f"Invalid year {year!r}. Use e.g. holidays://CH-ZH/2026."
    if not MIN_YEAR <= parsed_year <= MAX_YEAR:
        return f"Year {parsed_year} is out of the supported range {MIN_YEAR}-{MAX_YEAR}."
    try:
        canton_code, periods, _, _ = await op_holidays_bundle(_client(ctx), canton, parsed_year)
    except ValueError as exc:
        return str(exc)
    except UpstreamError:
        return "The upstream source is currently unavailable. Please retry shortly."
    return _bundle_markdown(canton_code, parsed_year, periods, _OH)


__all__ = ["mcp", "SCHOOL_TYPE_SUFFIX"]
