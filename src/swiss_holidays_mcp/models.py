"""Pydantic v2 models.

Every tool returns an envelope that carries `source` and `provenance`, so that
attribution can never be dropped by accident (portfolio rule 3.2).
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Provenance = Literal["live_api", "cached", "degraded"]
MatchType = Literal["exact", "fuzzy", "none"]


class Envelope(BaseModel):
    """Base envelope for every response of this server."""

    source: str = Field(description="Attribution string of the upstream source.")
    provenance: Provenance = Field(
        description="live_api = freshly fetched, cached = in-memory cache, "
        "degraded = upstream unreachable, stale or empty payload."
    )
    retrieved_at: str = Field(description="ISO-8601 UTC timestamp of the underlying fetch.")
    note: str | None = Field(
        default=None, description="Human-readable caveat, set when provenance is 'degraded'."
    )


class Canton(BaseModel):
    code: str = Field(description="ISO subdivision code, e.g. CH-ZH.")
    short_name: str
    name: str
    official_languages: list[str] = Field(default_factory=list)


class SchoolType(BaseModel):
    code: str = Field(description="Group code, e.g. CH-ZH-VS.")
    canton: str = Field(description="Canton code the group belongs to, e.g. CH-ZH.")
    name: str = Field(description="Schulart label, e.g. 'Volksschulen'.")


class Subdivision(BaseModel):
    """A sub-cantonal area a holiday applies to (district or municipality).

    Only carried for holidays that are *not* canton-wide — these are the ones the
    ``cantons`` roll-up cannot represent (e.g. Sechseläuten, which is observed only
    in the municipality of Zurich, ``CH-ZH-ZH-ZH``).
    """

    code: str = Field(description="ISO subdivision code, e.g. CH-ZH-ZH-ZH.")
    name: str = Field(description="Short name of the district or municipality.")
    level: Literal["district", "municipal"] = Field(
        description="'district' (Bezirk, CH-XX-YY) or 'municipal' (Gemeinde, CH-XX-YY-ZZ)."
    )


class HolidayPeriod(BaseModel):
    start_date: date
    end_date: date
    name: str
    kind: Literal["School", "Public"]
    nationwide: bool
    scope: Literal["national", "regional", "local"] = Field(
        default="regional",
        description="Upstream regionalScope: 'national' (whole country), 'regional' "
        "(canton or district), 'local' (single municipality, e.g. Sechseläuten).",
    )
    half_day: bool = Field(
        default=False,
        description="True when the holiday is observed for half a day only "
        "(upstream temporalScope 'HalfDay'), e.g. Sechseläuten, Knabenschiessen.",
    )
    cantons: list[str] = Field(default_factory=list)
    subdivisions: list[Subdivision] = Field(
        default_factory=list,
        description="Sub-cantonal areas (district/municipality) the holiday applies "
        "to. Empty for canton-wide or nationwide holidays.",
    )
    school_types: list[str] = Field(
        default_factory=list,
        description="Group codes, e.g. ['CH-ZH-VS']. Empty when the canton does "
        "not differentiate by Schulart.",
    )
    days: int = Field(description="Inclusive length of the period in calendar days.")


class CantonListResponse(Envelope):
    cantons: list[Canton]


class SchoolTypeListResponse(Envelope):
    school_types: list[SchoolType]


class HolidayListResponse(Envelope):
    match_type: MatchType = Field(
        default="exact",
        description="How the lookup key resolved (audit ARCH-003): 'exact' (code "
        "or full name / validated canton), 'fuzzy' (a single prefix match was "
        "assumed) or 'none' (nothing matched — see `note` for suggestions).",
    )
    count: int
    holidays: list[HolidayPeriod]


class DateCheckResponse(Envelope):
    checked_date: date
    canton: str
    is_school_holiday: bool
    is_public_holiday: bool
    matches: list[HolidayPeriod]


class OverlapRow(BaseModel):
    canton_a: str
    canton_b: str
    overlapping_days: int
    shared_periods: list[str] = Field(default_factory=list)


class OverlapResponse(Envelope):
    year: int
    school_type_filter: str | None
    rows: list[OverlapRow]


class FreeWindow(BaseModel):
    start_date: date
    end_date: date
    days: int
    cantons_on_holiday: list[str]
    cantons_in_school: list[str]


class WindowResponse(Envelope):
    windows: list[FreeWindow]


class LongWeekend(BaseModel):
    start_date: date
    end_date: date
    day_count: int
    needs_bridge_day: bool
    bridge_days: list[date] = Field(default_factory=list)


class LongWeekendResponse(Envelope):
    year: int
    long_weekends: list[LongWeekend]


class SourceStatus(BaseModel):
    name: str
    base_url: str
    reachable: bool
    http_status: int | None = None
    latency_ms: int | None = None
    detail: str | None = None


class StatusResponse(Envelope):
    mcp_protocol_version: str = Field(
        description="MCP wire protocol version this server is built and tested against."
    )
    sources: list[SourceStatus]
    all_healthy: bool


class IcsResponse(Envelope):
    canton: str
    year: int
    event_count: int = Field(description="Number of VEVENTs in the calendar.")
    filename: str = Field(description="Suggested file name, e.g. holidays-CH-ZH-2026.ics.")
    ics: str = Field(description="The full iCalendar (text/calendar) document.")
