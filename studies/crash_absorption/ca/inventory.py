"""Archive inventory from date-bounded S3 listings (metadata: names and sizes).
The XML listing API is served by the S3 host that backs data.binance.vision
(allow-listed by Shawn, CLARIFICATIONS v0.3.2); data files are still fetched
from data.binance.vision. Every listing prefix passes the guard."""
import calendar
import datetime as dt
import urllib.parse
import xml.etree.ElementTree as ET

from ca.guard import MAX_ALLOWED, assert_allowed, assert_file_listing_allowed

LISTING_BASE = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
NS = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
UM = "data/futures/um"


def list_files(fetch, prefix: str) -> list[tuple[str, int]]:
    """(key, size) of .zip files under a date-bounded prefix."""
    assert_file_listing_allowed(prefix)
    out, token = [], None
    while True:
        q = {"list-type": "2", "prefix": prefix}
        if token:
            q["continuation-token"] = token
        body = fetch.get(f"{LISTING_BASE}/?{urllib.parse.urlencode(q)}")
        root = ET.fromstring(body)
        for c in root.findall("s:Contents", NS):
            key = c.findtext("s:Key", namespaces=NS)
            if key.endswith(".zip"):
                assert_allowed(key)
                out.append((key, int(c.findtext("s:Size", namespaces=NS))))
        if root.findtext("s:IsTruncated", namespaces=NS) != "true":
            return out
        token = root.findtext("s:NextContinuationToken", namespaces=NS)


def _full(a: dt.date, b: dt.date, start: dt.date, end: dt.date) -> bool:
    return start <= a and b <= end


def date_fragments(freq: str, start: dt.date, end: dt.date = MAX_ALLOWED) -> list[str]:
    """Fewest name fragments covering exactly [start, end]: whole years, whole
    months, then (daily only) tens of days and single days with a trailing '.'."""
    frags, d = [], start
    while d <= end:
        ye = dt.date(d.year, 12, 31)
        me = d.replace(day=calendar.monthrange(d.year, d.month)[1])
        if d.month == 1 and d.day == 1 and ye <= end:
            frags.append(f"{d.year}-")
            d = ye + dt.timedelta(days=1)
        elif d.day == 1 and me <= end:
            frags.append(f"{d:%Y-%m}" if freq == "monthly" else f"{d:%Y-%m}-")
            d = me + dt.timedelta(days=1)
        elif freq == "monthly":
            break  # partial month: no monthly file allowed
        elif d.day % 10 == 0 and d.day >= 10 and d.replace(day=min(d.day + 9, me.day)) <= end and d.day + 9 <= me.day and d.day < 30:
            frags.append(f"{d:%Y-%m}-{d.day // 10}")
            d = d + dt.timedelta(days=10)
        elif d.day == 1 and d.replace(day=9) <= end:
            frags.append(f"{d:%Y-%m}-0")
            d = d.replace(day=10)
        else:
            frags.append(f"{d:%Y-%m-%d}.")
            d += dt.timedelta(days=1)
    return frags


def kline_prefixes(symbol: str, interval: str, start: dt.date) -> list[str]:
    """Monthly files for full months, daily files for the partial month."""
    mf = date_fragments("monthly", start)
    last_full = start
    for f in mf:
        y, *m = f.rstrip("-").split("-")
        last_full = dt.date(int(y), 12, 31) if not m else dt.date(int(y), int(m[0]), calendar.monthrange(int(y), int(m[0]))[1])
    out = [f"{UM}/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{f}" for f in mf]
    rest = last_full + dt.timedelta(days=1)
    if rest <= MAX_ALLOWED:
        out += [f"{UM}/daily/klines/{symbol}/{interval}/{symbol}-{interval}-{f}" for f in date_fragments("daily", rest)]
    return out


def aggtrades_prefixes(symbol: str, start: dt.date) -> list[str]:
    return [f"{UM}/daily/aggTrades/{symbol}/{symbol}-aggTrades-{f}" for f in date_fragments("daily", start)]


def period_of(key: str) -> tuple[str, str]:
    """('monthly'|'daily', 'YYYY-MM'|'YYYY-MM-DD') from an archive key."""
    freq = key.split("/")[3]
    stem = key.rsplit("/", 1)[-1][: -len(".zip")]
    n = 7 if freq == "monthly" else 10
    return freq, stem[-n:]
