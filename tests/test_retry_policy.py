"""Retry policy: Retry-After, jitter, and the cap.

Adopted together with the hardened retry from the mcp-data-source-probe
reference template. These assert the behaviour, not the constants: a
deterministic ladder and an unread `Retry-After` are what a sweep across eleven
servers found on 2026-08-03, and every one of them looked fine.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
import pytest
import respx

from swiss_holidays_mcp import client
from swiss_holidays_mcp.constants import OPENHOLIDAYS_BASE

# eleven servers found on 2026-08-03, and every one of them looked fine.


def _retry_after_error(value: str) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.invalid/")
    return httpx.HTTPStatusError(
        "",
        request=request,
        response=httpx.Response(429, headers={"Retry-After": value}, request=request),
    )


def test_retry_after_reads_both_rfc9110_forms() -> None:
    def resp(status: int, headers: dict[str, str]) -> httpx.Response:
        request = httpx.Request("GET", "https://example.invalid/")
        return httpx.Response(status, headers=headers, request=request)

    assert client.parse_retry_after(resp(429, {"Retry-After": "120"})) == 120.0

    later = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=90))
    seconds = client.parse_retry_after(resp(503, {"Retry-After": later}))
    assert seconds is not None and 80 < seconds <= 90

    # A date in the past means "now", never a negative wait.
    past = "Wed, 21 Oct 2020 07:28:00 GMT"
    assert client.parse_retry_after(resp(503, {"Retry-After": past})) == 0.0

    # Unparseable falls back to the curve. It must not crash on the error path,
    # which is the one path already going badly.
    assert client.parse_retry_after(resp(429, {"Retry-After": "bald"})) is None
    assert client.parse_retry_after(resp(429, {})) is None

    # 500 does not carry a meaningful Retry-After.
    assert client.parse_retry_after(resp(500, {"Retry-After": "120"})) is None
    assert client.parse_retry_after(None) is None


def test_backoff_is_jittered() -> None:
    delays = {client.compute_delay(3, None) for _ in range(300)}
    # attempt 3 -> 2 * 2**2 = 8s, spread into [0.5x, 1.5x]
    assert len(delays) > 1, "a deterministic ladder synchronises every client"
    assert min(delays) >= 4.0
    assert max(delays) <= 12.0


def test_cap_binds_after_the_jitter() -> None:
    # Capping first and then multiplying by up to 1.5 would land at 30s, and
    # the constant would claim a ceiling it does not hold.
    deep = {client.compute_delay(9, None) for _ in range(200)}
    assert max(deep) <= client.RETRY_MAX_DELAY

    hinted = _retry_after_error("600")
    assert {client.compute_delay(1, hinted) for _ in range(100)} == {client.RETRY_MAX_DELAY}


def test_retry_after_jitter_is_one_sided() -> None:
    """The source said when. Later is polite; earlier ignores the value read."""
    delays = {client.compute_delay(1, _retry_after_error("4")) for _ in range(300)}
    assert min(delays) >= 4.0, "never earlier than the source asked for"
    assert max(delays) <= 5.0  # 4 * 1.25


# --- The seams the loop is driven through -----------------------------------
#
# Everything above tests `compute_delay`, a pure function. It answers *how
# fast*, never *how long*: nothing here drove the loop, so `RETRY_TOTAL_BUDGET`
# and the `asyncio.wait_for` deadline that enforces it had no coverage at all.
# The tests below close that, and they need a wait a test can take over — hence
# the seams.


def test_die_beiden_nahtstellen_gehoeren_dem_modul() -> None:
    """`_sleep` and `_monotonic` must be what the retry loop actually calls.

    Read off the source, not off behaviour: a loop back on `asyncio.sleep` still
    passes every test that patches the stdlib function, because that is the one
    those tests then observe. The difference shows only in what *else* the patch
    takes down with it.
    """
    import inspect

    quelle = inspect.getsource(client.HolidayClient._fetch_with_retry)
    assert "await _sleep(" in quelle, "the retry loop no longer waits through the alias"
    assert "asyncio.sleep" not in quelle, "back on the stdlib function — patching it is global"
    assert "time.monotonic" not in quelle, "back on the stdlib clock — patching it stops the loop"
    assert "_monotonic()" in quelle, "the budget reads a clock the module does not own"


def test_das_uebernehmen_der_naht_laesst_den_prozess_in_ruhe(monkeypatch) -> None:
    """Patching the seam must not replace the function for everyone else.

    `monkeypatch.setattr("swiss_holidays_mcp.client.asyncio.sleep", ...)`
    resolves `client.asyncio` to the stdlib module and swaps `sleep` there. The
    autouse fixture in `test_resilience.py` did exactly that, so the reach
    covered every test in that file.
    """
    import asyncio
    import time

    vorher_sleep, vorher_uhr = asyncio.sleep, time.monotonic

    async def _nichts(_seconds: float) -> None:
        return None

    monkeypatch.setattr(client, "_sleep", _nichts)
    monkeypatch.setattr(client, "_monotonic", lambda: 0.0)
    assert client._sleep is _nichts, "the seam was not taken over at all"
    assert asyncio.sleep is vorher_sleep, "asyncio.sleep was replaced process-wide"
    assert time.monotonic is vorher_uhr, "time.monotonic was replaced process-wide"


@pytest.fixture
def fake_clock(monkeypatch):
    """A clock that only advances when the retry loop waits.

    Without it the budget can never run out in a test: a taken-over sleep costs
    no wall-clock time, so the deadline never arrives and the test passes
    whatever the budget logic does.

    Deliberately on `client._monotonic` and not on the stdlib module. The event
    loop reads `time.monotonic` from the same object, so freezing it there stops
    `loop.time()` — and `asyncio.wait_for`, the very deadline the budget
    promises, then waits for a moment that never comes.
    """
    jetzt = {"t": 1000.0}
    geschlafen: list[float] = []

    async def _sleep(seconds: float) -> None:
        geschlafen.append(seconds)
        jetzt["t"] += seconds

    monkeypatch.setattr(client, "_monotonic", lambda: jetzt["t"])
    monkeypatch.setattr(client, "_sleep", _sleep)
    return geschlafen


@respx.mock
async def test_das_budget_kuerzt_die_leiter(fake_clock) -> None:
    """Fewer than MAX_ATTEMPTS requests go out once the waits outlast the budget.

    Two guards enforce this, and the attempt count alone cannot tell them
    apart: the loop stops *before* a wait it cannot afford, and it stops again
    when the budget is gone by the time it comes back. The last assertion
    separates them — taking a wait longer than what is left is exactly what the
    comment in `_fetch_with_retry` promises never to do, and without it the
    test stayed green when that guard was deleted.
    """
    route = respx.get(f"{OPENHOLIDAYS_BASE}/Subdivisions").mock(
        side_effect=httpx.ConnectTimeout("weg")
    )
    budget = 6.0  # ladder is 2, 4, 8 before jitter
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(client, "RETRY_TOTAL_BUDGET", budget)
        async with client.HolidayClient(httpx.AsyncClient()) as c:
            with pytest.raises(client.UpstreamError):
                await c.subdivisions("DE")
    assert route.call_count < client.MAX_ATTEMPTS, "the budget did not bound the ladder"
    assert route.call_count >= 1, "the first attempt must always go out"
    assert sum(fake_clock) <= budget, (
        f"waited {sum(fake_clock)}s against a {budget}s budget — a wait that "
        "outlasts the budget is a wait for nobody"
    )


@respx.mock
async def test_ein_weites_budget_kuerzt_nichts(fake_clock) -> None:
    """Counter-direction: without it the test above would also pass on a broken loop."""
    route = respx.get(f"{OPENHOLIDAYS_BASE}/Subdivisions").mock(
        side_effect=httpx.ConnectTimeout("weg")
    )
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(client, "RETRY_TOTAL_BUDGET", 600.0)
        async with client.HolidayClient(httpx.AsyncClient()) as c:
            with pytest.raises(client.UpstreamError):
                await c.subdivisions("DE")
    assert route.call_count == client.MAX_ATTEMPTS, f"only {route.call_count} attempts"


@respx.mock
async def test_eine_langsame_antwort_wird_von_der_wanduhr_geschnitten() -> None:
    """The budget must bind even when no single httpx timeout ever fires.

    httpx bounds each *operation* and restarts its read timeout with every
    chunk, so a slowly trickling response outlives a per-operation limit without
    any single read expiring. `asyncio.wait_for` is the wall-clock bound the
    budget actually promises.

    Deliberately without `fake_clock`: this guarantee is about real time, and a
    clock that only moves when something sleeps cannot refute it. It is also the
    assurance a globally frozen clock made impossible — under one, the deadline
    below never fires and the test hangs instead of failing.
    """
    import asyncio as echtes_asyncio
    import time as echte_zeit

    async def _langsam(request: httpx.Request) -> httpx.Response:
        await echtes_asyncio.sleep(1.0)
        return httpx.Response(200, json=[])

    respx.get(f"{OPENHOLIDAYS_BASE}/Subdivisions").mock(side_effect=_langsam)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(client, "RETRY_TOTAL_BUDGET", 0.05)
        begonnen = echte_zeit.monotonic()
        async with client.HolidayClient(httpx.AsyncClient()) as c:
            with pytest.raises(client.UpstreamError):
                await c.subdivisions("DE")
        verstrichen = echte_zeit.monotonic() - begonnen
    assert verstrichen < 0.6, f"the deadline did not cut: {verstrichen:.2f}s"
