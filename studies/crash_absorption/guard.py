"""HOLDOUT guard (PREREG §3): refuse any data file that covers a date after
the VERDICT end in SPLITS.json. Every downloader/reader must call
assert_allowed() before requesting or opening a file."""
import calendar
import datetime as dt
import json
import re
from pathlib import Path

_SPLITS = json.loads((Path(__file__).parent / "SPLITS.json").read_text())
MAX_ALLOWED = dt.date.fromisoformat(_SPLITS["download_guard"]["max_allowed_date"])

_DAILY = re.compile(r"(\d{4})-(\d{2})-(\d{2})(?=\.zip|\.csv|$|[^\d])")
_MONTHLY = re.compile(r"(\d{4})-(\d{2})(?=\.zip|\.csv)")


class HoldoutViolation(RuntimeError):
    pass


def last_covered_date(name: str) -> dt.date:
    """Last calendar day covered by an archive file name or URL."""
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
    """For REST queries: endTime (ms since epoch, UTC) must not pass VERDICT end."""
    limit = dt.datetime.combine(MAX_ALLOWED + dt.timedelta(days=1), dt.time(), dt.timezone.utc)
    if end_ms >= int(limit.timestamp() * 1000):
        raise HoldoutViolation(f"endTime {end_ms} is after {MAX_ALLOWED} (HOLDOUT); refusing")
