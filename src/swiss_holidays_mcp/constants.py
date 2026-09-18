"""Constants, attribution strings and Swiss-specific lookup tables.

Findings from the live probe (2026-07-19) that shaped this module are marked
with `FINDING:` so that they survive future refactorings.
"""

from __future__ import annotations

from mcp.types.version import LATEST_HANDSHAKE_VERSION

from ._version import __version__

OPENHOLIDAYS_BASE = "https://openholidaysapi.org"
NAGER_BASE = "https://date.nager.at/api/v3"

# SEC-021 / SEC-004: code-layer egress allow-list. Immutable (frozenset), not
# config-mutable. Every outbound request is checked against this set before the
# socket is opened (see guard.assert_host_allowed). Extending it is a code change
# + review, documented in docs/network-egress.md.
ALLOWED_HOSTS = frozenset({"openholidaysapi.org", "date.nager.at"})

# ARCH-012: der Rueckfall fuer die Revision, die `source_status` meldet.
#
# `mcp` 2.x bedient zwei Protokoll-Aeren ueber denselben Server: den
# `initialize`-Handshake, der bei `LATEST_HANDSHAKE_VERSION` deckelt, und den
# Pro-Request-Envelope, der `LATEST_MODERN_VERSION` erreicht. Welche gilt,
# entscheidet die erste Anfrage einer Verbindung — nicht der Server.
#
# Deshalb steht hier kein ausgelieferter Wert mehr, sondern nur der Rueckfall.
# `source_status` liest die tatsaechlich ausgehandelte Revision pro Anfrage aus
# `Context.protocol_version` und kommt hierher nur, wo es keinen Request-Kontext
# gibt: der `op_*`-Layer, den die Unit-Tests direkt aufrufen. Dort hat niemand
# etwas ausgehandelt, und die Handshake-Obergrenze ist das, was ein Aufrufer am
# ehesten bekaeme.
#
# Die vorige Fassung hiess `MCP_PROTOCOL_VERSION` und ging als EINZIGE Antwort
# an jeden Aufrufer, auch an einen, der `2026-07-28` ausgehandelt hatte. Am
# 18.9.2026 durch die ASGI-App gemessen: ein moderner Envelope bekam
# `2025-11-25` zurueck — eine Falschauskunft ueber genau die Verbindung, ueber
# die sie lief. Der Test dazu war gruen, weil er den gelieferten Wert gegen
# `LATEST_HANDSHAKE_VERSION` hielt und der In-Process-`Client` der Tests
# unbemerkt schon modern spricht. Eine Zusicherung, die die falsche Aera
# abfragt, ist mit jedem Wert gruen.
#
# Abgeleitet statt hingeschrieben: ein Literal waere eine zweite Wahrheit neben
# dem SDK, und zweite Wahrheiten driften. Diese hier stand zwei Revisionen lang
# auf "2025-06-18", waehrend jede `source_status`-Abfrage sie als Tatsache
# ausgab. Nichts fiel auf, weil nichts sie mit etwas verglich.
FALLBACK_PROTOCOL_VERSION = LATEST_HANDSHAKE_VERSION

# SEC-018: bounds for numeric tool inputs (no unbounded ranges).
MIN_YEAR = 1970
MAX_YEAR = 2100

HOMEPAGE_URL = "https://github.com/malkreide/swiss-holidays-mcp"

USER_AGENT = f"swiss-holidays-mcp/{__version__} (+{HOMEPAGE_URL})"

ATTRIBUTION_OPENHOLIDAYS = (
    "Data: OpenHolidays API (openholidaysapi.org) — CC BY 4.0. "
    "Unofficial aggregation; the cantonal authority remains the authoritative source."
)
ATTRIBUTION_NAGER = (
    "Data: Nager.Date (date.nager.at) — MIT. "
    "Unofficial aggregation; the cantonal authority remains the authoritative source."
)

# FINDING (live probe 2026-07-19): OpenHolidays returns apparent duplicates for
# Zurich school holidays. They are NOT duplicates — they are differentiated by
# `groups[].code`, which encodes the *Schulart*:
#   CH-ZH-VS = Volksschulen      <- Schulamt Stadt Zuerich remit
#   CH-ZH-MS = Mittelschulen
#   CH-ZH-BS = Berufsfachschulen
# Naive de-duplication would destroy exactly the distinction that matters.
SCHOOL_TYPE_SUFFIX = {
    "VS": "Volksschulen",
    "MS": "Mittelschulen",
    "BS": "Berufsfachschulen",
    "EO": "Obligatorische Schulen",
}

# FINDING: only 11 Schulart groups exist nationwide. Most cantons publish a
# single undifferentiated holiday set, i.e. `groups` is absent there.
CANTONS_WITH_SCHOOL_TYPES = ("AI", "AR", "BE", "GR", "SO", "ZH")

DEFAULT_LANGUAGE = "DE"
SUPPORTED_LANGUAGES = ("DE", "FR", "IT", "EN")

# FINDING: /Subdivisions?countryIsoCode=CH returns 26 top-level cantons, but
# holiday records may carry sub-cantonal codes (e.g. CH-AI-AP, CH-BE-TH-BL).
# Always match on the CH-XX prefix, never on string equality.
CANTON_CODES = (
    "CH-AG",
    "CH-AI",
    "CH-AR",
    "CH-BE",
    "CH-BL",
    "CH-BS",
    "CH-FR",
    "CH-GE",
    "CH-GL",
    "CH-GR",
    "CH-JU",
    "CH-LU",
    "CH-NE",
    "CH-NW",
    "CH-OW",
    "CH-SG",
    "CH-SH",
    "CH-SO",
    "CH-SZ",
    "CH-TG",
    "CH-TI",
    "CH-UR",
    "CH-VD",
    "CH-VS",
    "CH-ZG",
    "CH-ZH",
)
