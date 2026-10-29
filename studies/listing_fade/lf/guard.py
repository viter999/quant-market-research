"""HOLDOUT guard (PREREG v0.2 §3). TEST = L from 2024-01-01 to 2026-03-05, so every
window ends by 2026-03-13. HOLDOUT launches (L from 2026-03-15) are never
price-downloaded. No file whose covered dates pass 2026-03-13 is requested."""
import calendar
import datetime as dt
import re

MAX_ALLOWED = dt.date(2026, 3, 13)
TEST_L = (dt.date(2024, 1, 1), dt.date(2026, 3, 5))
LIMIT_MS = int(dt.datetime.combine(MAX_ALLOWED + dt.timedelta(days=1), dt.time(), dt.timezone.utc).timestamp() * 1000)

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


def assert_ms_allowed(t_ms: int) -> None:
    if t_ms >= LIMIT_MS:
        raise HoldoutViolation(f"time {t_ms} is after {MAX_ALLOWED}; refusing")


def assert_event_allowed(ev: dict) -> None:
    lday = dt.datetime.fromtimestamp(int(ev["L_ms"]) / 1000, dt.timezone.utc).date()
    if ev["segment"] != "TEST" or not (TEST_L[0] <= lday <= TEST_L[1]):
        raise HoldoutViolation(f"{ev['symbol']} L={lday} segment={ev['segment']} is not TEST; refusing")
