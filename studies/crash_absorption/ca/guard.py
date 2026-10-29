"""HOLDOUT guard (PREREG §3): refuse any data file that covers a date after
the VERDICT end in SPLITS.json. Every downloader/reader must call
assert_allowed() before requesting or opening a file."""
import calendar
import datetime as dt
import json
import re
from pathlib import Path

_SPLITS = json.loads((Path(__file__).resolve().parents[1] / "SPLITS.json").read_text())
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


SYMBOL_LISTING_PREFIX = "data/futures/um/monthly/klines/"


def assert_listing_allowed(prefix: str, delimiter: str | None) -> None:
    """Only the symbol-directory listing is allowed (it returns symbol names,
    no file names, dates or sizes). Per-file listings are never needed: files
    are addressed by constructed URLs and a 404 means "no file"."""
    if prefix != SYMBOL_LISTING_PREFIX or delimiter != "/":
        raise HoldoutViolation(f"listing {prefix!r} (delimiter={delimiter!r}) not allowed; refusing")


REST_ALLOWED = {("fapi.binance.com", "/fapi/v1/fundingRate")}


def assert_rest_allowed(url: str) -> None:
    """fapi requests: only allow-listed endpoints, and endTime is mandatory and
    must not pass the VERDICT end (without endTime fapi returns the latest data)."""
    import urllib.parse
    u = urllib.parse.urlsplit(url)
    if (u.hostname, u.path) not in REST_ALLOWED:
        raise HoldoutViolation(f"REST endpoint {u.hostname}{u.path} not allowed; refusing")
    q = urllib.parse.parse_qs(u.query)
    if "endTime" not in q or "startTime" not in q:
        raise HoldoutViolation(f"REST request without startTime/endTime: {url!r}; refusing")
    start, end = int(q["startTime"][0]), int(q["endTime"][0])
    if start > end:
        raise HoldoutViolation(f"startTime > endTime in {url!r}; refusing")
    assert_ms_allowed(end)


_FRAG = re.compile(r"-(\d{4}(?:-\d{0,2}){0,2})(\.?)$")


def _completions(frag: str, exact: bool, monthly: bool):
    """Last covered day of every archive period whose name starts with frag."""
    for y in range(2017, 2031):
        for mo in range(1, 13):
            if monthly:
                name = f"{y}-{mo:02d}"
                if name == frag or (not exact and name.startswith(frag)):
                    yield dt.date(y, mo, calendar.monthrange(y, mo)[1])
            else:
                for d in range(1, calendar.monthrange(y, mo)[1] + 1):
                    name = f"{y}-{mo:02d}-{d:02d}"
                    if name == frag or (not exact and name.startswith(frag)):
                        yield dt.date(y, mo, d)


def assert_file_listing_allowed(prefix: str) -> None:
    """Per-file listings are allowed only when every file name the prefix can
    match covers dates <= MAX_ALLOWED (e.g. 'BTCUSDT-1m-2025-' or
    'BTCUSDT-1m-2026-03-1' is refused because it matches 2026-03-14..19)."""
    if not prefix.startswith("data/futures/um/") or "/" in prefix.rsplit("/", 1)[-1]:
        raise HoldoutViolation(f"listing {prefix!r} not allowed; refusing")
    freq = prefix.split("/")[3]
    m = _FRAG.search(prefix.rsplit("/", 1)[-1])
    if freq not in ("monthly", "daily") or not m:
        raise HoldoutViolation(f"listing {prefix!r} has no date bound; refusing")
    ends = list(_completions(m.group(1), bool(m.group(2)), freq == "monthly"))
    if not ends or max(ends) > MAX_ALLOWED:
        raise HoldoutViolation(f"listing {prefix!r} can match dates after {MAX_ALLOWED}; refusing")
