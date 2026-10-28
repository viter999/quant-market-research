"""Downloader for data.binance.vision (USD-M): klines 1m and 1d, fundingRate,
aggTrades (streamed). Every request passes the HOLDOUT guard first. Files are
addressed by constructed URLs; a 404 means the symbol has no file there.
The fetcher is injectable so all logic is testable offline."""
import calendar
import contextlib
import datetime as dt
import hashlib
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from ca import params as P
from ca.guard import MAX_ALLOWED, SYMBOL_LISTING_PREFIX, assert_allowed, assert_listing_allowed

ARCHIVE = "https://data.binance.vision"
UM = "data/futures/um"
KLINE_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume",
              "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]
AGG_COLS = ["agg_trade_id", "price", "quantity", "first_trade_id", "last_trade_id", "transact_time",
            "is_buyer_maker"]
# Lookback inputs before 2024-01-01 (240-min sigma, 7-day ranking). Not outcome data.
DOWNLOAD_START = dt.date(2023, 12, 1)


class ChecksumError(RuntimeError):
    pass


class DataValidationError(RuntimeError):
    pass


# ---------------------------------------------------------------- fetching
class HttpFetcher:
    """get(url) -> bytes | None (404); download(url, path) -> bool (False on 404)."""

    def __init__(self, timeout: int = 120):
        self.timeout = timeout

    def _open(self, url):
        try:
            return urllib.request.urlopen(url, timeout=self.timeout)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise

    def get(self, url: str) -> bytes | None:
        r = self._open(url)
        if r is None:
            return None
        with r:
            return r.read()

    def download(self, url: str, path: Path) -> bool:
        r = self._open(url)
        if r is None:
            return False
        with r, open(path, "wb") as out:
            shutil.copyfileobj(r, out, 1 << 20)
        return True


def _guarded(url: str) -> str:
    assert_allowed(url)
    return url


def list_symbols(fetch, listing_base: str = ARCHIVE) -> list[str]:
    """Symbol directory names under um/monthly/klines/ (names only). The XML
    listing API must be served from `listing_base`; nothing else is tried."""
    assert_listing_allowed(SYMBOL_LISTING_PREFIX, "/")
    out, token = [], None
    ns = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
    while True:
        q = {"list-type": "2", "prefix": SYMBOL_LISTING_PREFIX, "delimiter": "/"}
        if token:
            q["continuation-token"] = token
        body = fetch.get(f"{listing_base}/?{urllib.parse.urlencode(q)}")
        try:
            root = ET.fromstring(body or b"")
        except ET.ParseError as e:
            raise DataValidationError(f"{listing_base} did not return an XML listing") from e
        if root.find("s:Contents", ns) is not None:
            raise DataValidationError("listing returned file entries; refusing")
        out += [p.find("s:Prefix", ns).text.rstrip("/").rsplit("/", 1)[-1] for p in root.findall("s:CommonPrefixes", ns)]
        if root.findtext("s:IsTruncated", namespaces=ns) != "true":
            return sorted(out)
        token = root.findtext("s:NextContinuationToken", namespaces=ns)


def file_periods(start: dt.date = DOWNLOAD_START, end: dt.date = MAX_ALLOWED):
    """('monthly', 'YYYY-MM') for full months <= end, then ('daily', 'YYYY-MM-DD')."""
    d = start.replace(day=1)
    while True:
        last = d.replace(day=calendar.monthrange(d.year, d.month)[1])
        if last > end:
            break
        yield "monthly", d.strftime("%Y-%m")
        d = last + dt.timedelta(days=1)
    while d <= end:
        yield "daily", d.isoformat()
        d += dt.timedelta(days=1)


def kline_url(symbol: str, interval: str, freq: str, period: str) -> str:
    return f"{ARCHIVE}/{UM}/{freq}/klines/{symbol}/{interval}/{symbol}-{interval}-{period}.zip"


def funding_url(symbol: str, month: str) -> str:
    return f"{ARCHIVE}/{UM}/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{month}.zip"


def aggtrades_url(symbol: str, day: dt.date) -> str:
    return f"{ARCHIVE}/{UM}/daily/aggTrades/{symbol}/{symbol}-aggTrades-{day.isoformat()}.zip"


def _verify(fetch, url: str, data_path: Path) -> None:
    body = fetch.get(_guarded(url + ".CHECKSUM"))
    if body is None:
        raise ChecksumError(f"no CHECKSUM for {url}")
    want = body.decode().split()[0].lower()
    h = hashlib.sha256()
    with open(data_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    if h.hexdigest() != want:
        raise ChecksumError(f"sha256 mismatch for {url}")


def _fetch_zip(fetch, url: str, tmpdir: Path) -> Path | None:
    path = tmpdir / url.rsplit("/", 1)[-1]
    if not fetch.download(_guarded(url), path):
        return None
    _verify(fetch, url, path)
    return path


@contextlib.contextmanager
def _csv_member(zpath: Path, names: list[str], **kw):
    """Yield pandas' reader (a DataFrame, or an iterator with chunksize) for the
    single csv in the zip; header row detected (old files have none)."""
    with zipfile.ZipFile(zpath) as zf:
        members = [m for m in zf.namelist() if m.endswith(".csv")]
        if len(members) != 1:
            raise DataValidationError(f"{zpath.name}: expected one csv, got {members}")
        with zf.open(members[0]) as fh:
            first = fh.readline().decode()
        has_header = not first.split(",")[0].strip().lstrip("-").isdigit()
        with zf.open(members[0]) as fh:
            yield pd.read_csv(fh, header=0 if has_header else None, names=None if has_header else names, **kw)


def _read_csv_member(zpath: Path, names: list[str]) -> pd.DataFrame:
    with _csv_member(zpath, names) as df:
        return df


def _period_bounds(freq: str, period: str) -> tuple[int, int]:
    if freq == "monthly":
        y, m = map(int, period.split("-"))
        a = dt.date(y, m, 1)
        b = a.replace(day=calendar.monthrange(y, m)[1]) + dt.timedelta(days=1)
    else:
        a = dt.date.fromisoformat(period)
        b = a + dt.timedelta(days=1)
    return P.date_to_ms(a), P.date_to_ms(b)


def parse_klines(zpath: Path, freq: str, period: str) -> pd.DataFrame:
    df = _read_csv_member(zpath, KLINE_COLS)
    df.columns = KLINE_COLS[: len(df.columns)]
    df = df[["open_time", "open", "high", "low", "close", "volume", "quote_volume", "count"]]
    df["open_time"] = df["open_time"].astype(np.int64)
    a, b = _period_bounds(freq, period)
    if len(df) and (df["open_time"].min() < a or df["open_time"].max() >= b):
        raise DataValidationError(f"{zpath.name}: open_time outside {period} (ms units?)")
    if df["open_time"].duplicated().any():
        raise DataValidationError(f"{zpath.name}: duplicate open_time")
    return df


def download_klines(symbol: str, interval: str, out_dir: Path, fetch, periods=None) -> Path | None:
    """All allowed periods for one symbol/interval -> one parquet."""
    parts = []
    with tempfile.TemporaryDirectory() as td:
        for freq, period in periods or file_periods():
            z = _fetch_zip(fetch, kline_url(symbol, interval, freq, period), Path(td))
            if z is not None:
                parts.append(parse_klines(z, freq, period))
                z.unlink()
    if not parts:
        return None
    df = pd.concat(parts).sort_values("open_time")
    if df["open_time"].duplicated().any():
        raise DataValidationError(f"{symbol} {interval}: overlapping files")
    out = Path(out_dir) / "klines" / interval / f"{symbol}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    return out


def download_funding(symbol: str, out_dir: Path, fetch, periods=None) -> Path | None:
    """Monthly archive files only. Months not fully <= MAX_ALLOWED are refused by
    the guard, so funding coverage ends at the last full allowed month."""
    parts, months = [], [p for f, p in (periods or file_periods()) if f == "monthly"]
    with tempfile.TemporaryDirectory() as td:
        for m in months:
            z = _fetch_zip(fetch, funding_url(symbol, m), Path(td))
            if z is not None:
                df = _read_csv_member(z, ["calc_time", "funding_interval_hours", "last_funding_rate"])
                parts.append(df[["calc_time", "last_funding_rate"]].rename(
                    columns={"calc_time": "ts", "last_funding_rate": "rate"}))
                z.unlink()
    if not parts:
        return None
    df = pd.concat(parts).sort_values("ts").drop_duplicates("ts")
    out = Path(out_dir) / "funding" / f"{symbol}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    return out


# ---------------------------------------------------------------- aggTrades
def trade_windows(ref_ts) -> dict[dt.date, list[tuple[int, int]]]:
    """Needed windows [t-5 min, t+25 min] per UTC day (split at midnight, merged)."""
    spans = sorted((int(t) - P.WINDOW_PRE_MIN * P.MINUTE_MS, int(t) + P.WINDOW_POST_MIN * P.MINUTE_MS) for t in ref_ts)
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    out: dict[dt.date, list] = {}
    for a, b in merged:
        while a <= b:
            day_end = (a // P.DAY_MS + 1) * P.DAY_MS - 1
            out.setdefault(P.ms_to_date(a), []).append((a, min(b, day_end)))
            a = day_end + 1
    return out


def _in_windows(ts: np.ndarray, windows) -> np.ndarray:
    m = np.zeros(len(ts), bool)
    for a, b in windows:
        m |= (ts >= a) & (ts <= b)
    return m


def _filter_chunks(reader, windows, lo: int, hi: int, name: str):
    for chunk in reader:
        chunk.columns = AGG_COLS
        ts = chunk["transact_time"].to_numpy(np.int64)
        if len(ts) and (ts.min() < lo or ts.max() >= hi):
            raise DataValidationError(f"{name}: transact_time outside its day (ms units?)")
        c = chunk[_in_windows(ts, windows)]
        yield pd.DataFrame({
            "ts": c["transact_time"].astype(np.int64), "price": c["price"].astype(float),
            "qty": c["quantity"].astype(float), "agg_id": c["agg_trade_id"].astype(np.int64),
            "is_buyer_maker": c["is_buyer_maker"].astype(str).str.lower().map({"true": True, "false": False}),
        })


def stream_aggtrades(symbol: str, day: dt.date, windows, out_dir: Path, fetch, chunksize: int = 2_000_000):
    """Download one day zip, keep only rows inside `windows`, write parquet,
    delete the zip (always, also on error). Returns the parquet path or None (404)."""
    tmpdir = Path(tempfile.mkdtemp(prefix="aggtrades-"))
    try:
        z = _fetch_zip(fetch, aggtrades_url(symbol, day), tmpdir)
        if z is None:
            return None
        lo, hi = P.date_to_ms(day), P.date_to_ms(day + dt.timedelta(days=1))
        with _csv_member(z, AGG_COLS, chunksize=chunksize) as reader:
            kept = list(_filter_chunks(reader, windows, lo, hi, z.name))
        z.unlink()
        kept = [k for k in kept if len(k)]
        df = (pd.concat(kept) if kept else pd.DataFrame({
            "ts": pd.Series(dtype=np.int64), "price": pd.Series(dtype=float), "qty": pd.Series(dtype=float),
            "agg_id": pd.Series(dtype=np.int64), "is_buyer_maker": pd.Series(dtype=bool)}))
        df = df.sort_values(["ts", "agg_id"], kind="stable")
        if df["is_buyer_maker"].isna().any():
            raise DataValidationError(f"{symbol} {day}: unparseable is_buyer_maker")
        if df["agg_id"].duplicated().any():
            raise DataValidationError(f"{symbol} {day}: duplicate agg_trade_id")
        out = Path(out_dir) / "aggtrades" / symbol / f"{day.isoformat()}.parquet"
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out, index=False)
        return out
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def load_aggtrades(path: Path):
    """Archive-origin Trades (outcome-locked downstream)."""
    from ca.lock import ARCHIVE as ORIGIN_ARCHIVE
    from ca.trades import Trades
    return Trades.from_frame(pd.read_parquet(path), ORIGIN_ARCHIVE)
