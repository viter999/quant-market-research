"""HOLDOUT guard (PREREG v0.2 §3). TEST events have A in 2022-02-17 .. 2026-03-13;
HOLDOUT events (A from 2026-03-15) are never downloaded before the TEST result is
committed. No file whose covered dates pass 2026-03-13 is requested or opened."""
import calendar
import datetime as dt
import re

MAX_ALLOWED = dt.date(2026, 3, 13)
TEST_A = (dt.date(2022, 2, 17), dt.date(2026, 3, 13))
_LIMIT_MS = int(dt.datetime.combine(MAX_ALLOWED + dt.timedelta(days=1), dt.time(), dt.timezone.utc).timestamp() * 1000)

_DAILY = re.compile(r"(\d{4})-(\d{2})-(\d{2})(?=\.zip|\.csv|$|[^\d])")
_MONTHLY = re.compile(r"(\d{4})-(\d{2})(?=\.zip|\.csv)")


class HoldoutViolation(RuntimeError):
    pass


def last_covered_date(name: str) -> dt.date:
    base = name.rsplit("/", 1)[-1]
    m = _DAILY.search(base)
    if m:
        return dt.date(*map(int, m.groups()))
    m = _MONTHLY.search(base)
    if m:
        y, mo = map(int, m.groups())
        return dt.date(y, mo, calendar.monthrange(y, mo)[1])
    raise HoldoutViolation(f"cannot determine covered dates of {name!r}; refusing")


def assert_allowed(name: str) -> None:
    last = last_covered_date(name)
    if last > MAX_ALLOWED:
        raise HoldoutViolation(f"{name!r} covers {last} > {MAX_ALLOWED} (HOLDOUT); refusing")


def assert_ms_allowed(end_ms: int) -> None:
    if end_ms >= _LIMIT_MS:
        raise HoldoutViolation(f"time {end_ms} is after {MAX_ALLOWED}; refusing")


def assert_event_allowed(ev: dict) -> None:
    """Only TEST events whose whole window [A-24h, D] lies on or before 2026-03-13."""
    a = dt.datetime.fromtimestamp(int(ev["A_ms"]) / 1000, dt.timezone.utc).date()
    if ev["segment"] != "TEST" or not (TEST_A[0] <= a <= TEST_A[1]):
        raise HoldoutViolation(f"{ev['symbol']} A={a} segment={ev['segment']} is not TEST; refusing")
    assert_ms_allowed(int(ev["D_ms"]))
