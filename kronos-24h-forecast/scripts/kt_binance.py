"""Public Binance data from data.binance.vision (no keys, no login).

Every zip is checked against Binance's published .CHECKSUM (SHA-256) and logged to logs/downloads.log.
Zips are read in place with zipfile (never extracted to disk), one CSV member each.
"""
import datetime as dt
import hashlib
import io
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

import pandas as pd

import kt_common as kt

BASE = "https://data.binance.vision/"
S3_LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
RAW = os.path.join(kt.DATA, "raw", "futures_um_monthly_klines")
LOG = os.path.join(kt.ROOT, "logs", "downloads.log")
UA = {"User-Agent": "kronos-test/1.0 (public data research)"}
KLINE_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
              "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]

_log_lock = threading.Lock()


def _log(line):
    with _log_lock:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + " " + line + "\n")


def _get(url, retries=4):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == retries - 1:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == retries - 1:
                raise
        time.sleep(2 * (attempt + 1))


def list_um_kline_symbols():
    """All symbols that have a USDT-M monthly klines folder, including since-delisted ones."""
    prefix = "data/futures/um/monthly/klines/"
    ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
    symbols, marker = [], ""
    while True:
        q = urllib.parse.urlencode({"delimiter": "/", "prefix": prefix, "marker": marker})
        root = ET.fromstring(_get(f"{S3_LIST}?{q}"))
        for p in root.findall("s3:CommonPrefixes/s3:Prefix", ns):
            symbols.append(p.text[len(prefix):].strip("/"))
        if root.findtext("s3:IsTruncated", default="false", namespaces=ns) != "true":
            break
        marker = root.findtext("s3:NextMarker", namespaces=ns) or (prefix + symbols[-1] + "/")
    return sorted(set(symbols))


def monthly_zip(symbol, interval, yyyymm):
    """Download (once) and verify one monthly klines zip. Returns local path, or None if Binance has no file."""
    name = f"{symbol}-{interval}-{yyyymm}.zip"
    rel = f"data/futures/um/monthly/klines/{symbol}/{interval}/{name}"
    local_dir = os.path.join(RAW, symbol, interval)
    local = os.path.join(local_dir, name)
    missing_marker = local + ".missing"
    if os.path.exists(local):
        return local
    if os.path.exists(missing_marker):
        return None
    url = BASE + urllib.parse.quote(rel)   # a few symbols have non-ASCII names
    body = _get(url)
    if body is None:
        os.makedirs(local_dir, exist_ok=True)
        open(missing_marker, "w").close()
        _log(f"404 {rel}")
        return None
    checksum = _get(url + ".CHECKSUM")
    digest = hashlib.sha256(body).hexdigest()
    expected = checksum.decode().split()[0].lower() if checksum else None
    if expected != digest:
        _log(f"CHECKSUM-FAIL {rel} got={digest} expected={expected}")
        raise RuntimeError(f"checksum mismatch for {rel}")
    os.makedirs(local_dir, exist_ok=True)
    with open(local + ".part", "wb") as f:
        f.write(body)
    os.replace(local + ".part", local)
    _log(f"OK {rel} bytes={len(body)} sha256={digest} checksum=match")
    return local


def read_klines(path, usecols=None):
    """Read one monthly klines zip. usecols=['open_time'] reads timestamps only (no prices)."""
    with zipfile.ZipFile(path) as z:
        members = [m for m in z.namelist() if m.endswith(".csv")]
        if len(members) != 1 or "/" in members[0] or "\\" in members[0] or ".." in members[0]:
            raise RuntimeError(f"unexpected zip layout in {path}: {z.namelist()}")
        raw = z.read(members[0])
    first = raw.split(b"\n", 1)[0]
    header = 0 if first[:1].isalpha() else None
    idx = [KLINE_COLS.index(c) for c in usecols] if usecols else None
    df = pd.read_csv(io.BytesIO(raw), header=header, usecols=idx)
    df.columns = [KLINE_COLS[i] for i in (idx or range(len(KLINE_COLS)))]
    t = df["open_time"].astype("int64")
    unit = "us" if t.max() > 10**14 else "ms"   # Binance moved some datasets to microseconds
    df["open_time"] = pd.to_datetime(t, unit=unit, utc=True)
    return df


def local_zip(symbol, interval, yyyymm):
    return os.path.join(RAW, symbol, interval, f"{symbol}-{interval}-{yyyymm}.zip")


def load_1h_bars(symbol, first_month, last_month):
    """All local 1h bars for a symbol, indexed by tz-naive UTC open_time, in Kronos column names.

    Uses only zips already on disk (frozen and hash-checked); never downloads.
    """
    parts = []
    for m in months(first_month, last_month):
        path = local_zip(symbol, "1h", m)
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        parts.append(read_klines(path))
    df = pd.concat(parts, ignore_index=True)
    df["open_time"] = df["open_time"].dt.tz_localize(None)
    df = df.set_index("open_time").sort_index()
    if not df.index.is_unique:
        raise RuntimeError(f"duplicate bars for {symbol}")
    out = df[["open", "high", "low", "close", "volume"]].astype(float)
    out["amount"] = df["quote_volume"].astype(float)
    return out


def months(start, end):
    """'YYYY-MM' strings from start to end inclusive."""
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out
