"""data.binance.vision downloads for TEST launches. Every URL is guarded and every
zip is verified against its CHECKSUM. aggTrades are streamed: only the requested
windows are kept (columns ts, price, qty, ibm), then the zip is deleted."""
import datetime as dt
import hashlib
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "crash_absorption"))
from ca.downloader import AGG_COLS, HttpFetcher, _csv_member, _read_csv_member, parse_klines  # noqa: E402,F401

from .guard import MAX_ALLOWED, assert_allowed, last_covered_date

ARCHIVE = "https://data.binance.vision"
UM = "data/futures/um"


class ChecksumError(RuntimeError):
    pass


def kline_url(sym: str, d: dt.date) -> str:
    return f"{ARCHIVE}/{UM}/daily/klines/{sym}/1m/{sym}-1m-{d.isoformat()}.zip"


def agg_url(sym: str, d: dt.date) -> str:
    return f"{ARCHIVE}/{UM}/daily/aggTrades/{sym}/{sym}-aggTrades-{d.isoformat()}.zip"


def funding_url(sym: str, month: str) -> str:
    return f"{ARCHIVE}/{UM}/monthly/fundingRate/{sym}/{sym}-fundingRate-{month}.zip"


def fetch_zip(fetch, url: str, tmpdir: Path) -> Path | None:
    assert_allowed(url)
    path = tmpdir / url.rsplit("/", 1)[-1]
    if not fetch.download(url, path):
        return None
    assert_allowed(url + ".CHECKSUM")
    body = fetch.get(url + ".CHECKSUM")
    if body is None:
        raise ChecksumError(f"no CHECKSUM for {url}")
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    if h.hexdigest() != body.decode().split()[0].lower():
        raise ChecksumError(f"sha256 mismatch for {url}")
    return path


def agg_windows(sym: str, days: list[dt.date], lo: int, hi: int, fetch) -> tuple[pd.DataFrame, list[str]]:
    """aggTrades with lo <= ts < hi from the given daily files; returns (frame, missing days)."""
    parts, missing = [], []
    with tempfile.TemporaryDirectory() as td:
        for d in days:
            z = fetch_zip(fetch, agg_url(sym, d), Path(td))
            if z is None:
                missing.append(d.isoformat())
                continue
            with _csv_member(z, AGG_COLS, chunksize=2_000_000) as reader:
                for ch in reader:
                    ch.columns = AGG_COLS[: len(ch.columns)]
                    ts = ch["transact_time"].astype(np.int64)
                    if len(ts) and ts.max() > 10 ** 14:
                        raise RuntimeError(f"{sym} {d}: aggTrades transact_time not in ms")
                    m = (ts >= lo) & (ts < hi)
                    if m.any():
                        c = ch.loc[m]
                        ibm = c["is_buyer_maker"]
                        if ibm.dtype != bool:
                            ibm = ibm.astype(str).str.lower().map({"true": True, "false": False})
                            if ibm.isna().any():
                                raise RuntimeError(f"{sym} {d}: bad is_buyer_maker")
                        parts.append(pd.DataFrame({"ts": ts[m].to_numpy(), "price": c["price"].to_numpy(float),
                                                   "qty": c["quantity"].to_numpy(float), "ibm": ibm.to_numpy(bool),
                                                   "agg_id": c["agg_trade_id"].to_numpy(np.int64)}))
            z.unlink()
    df = pd.concat(parts) if parts else pd.DataFrame({"ts": [], "price": [], "qty": [], "ibm": [], "agg_id": []})
    return df.sort_values(["ts", "agg_id"], kind="stable").reset_index(drop=True), missing


def klines(sym: str, days: list[dt.date], fetch) -> tuple[pd.DataFrame | None, list[str]]:
    parts, missing = [], []
    with tempfile.TemporaryDirectory() as td:
        for d in days:
            z = fetch_zip(fetch, kline_url(sym, d), Path(td))
            if z is None:
                missing.append(d.isoformat())
                continue
            parts.append(parse_klines(z, "daily", d.isoformat()))
            z.unlink()
    if not parts:
        return None, missing
    df = pd.concat(parts).sort_values("open_time").reset_index(drop=True)
    if df["open_time"].duplicated().any():
        raise RuntimeError(f"{sym}: duplicate kline open_time")
    return df, missing


def funding(sym: str, months: list[str], fetch) -> tuple[pd.DataFrame | None, list[str], list[str]]:
    """Monthly files. A month whose file would cover dates after the guard limit
    (2026-03) is never requested; it is reported as missing ('YYYY-MM:beyond_guard'),
    so those settlements count as missing records, never as zero."""
    parts, present, missing = [], [], []
    with tempfile.TemporaryDirectory() as td:
        for m in months:
            if last_covered_date(funding_url(sym, m)) > MAX_ALLOWED:
                missing.append(f"{m}:beyond_guard")
                continue
            z = fetch_zip(fetch, funding_url(sym, m), Path(td))
            if z is None:
                missing.append(m)
                continue
            df = _read_csv_member(z, ["calc_time", "funding_interval_hours", "last_funding_rate"])
            df = df.rename(columns={"calc_time": "ts", "last_funding_rate": "rate"})
            y, mo = map(int, m.split("-"))
            a = int(dt.datetime(y, mo, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
            b = int(dt.datetime(y + (mo == 12), mo % 12 + 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
            if len(df) and (df["ts"].min() < a or df["ts"].max() >= b):
                raise RuntimeError(f"{sym} funding {m}: calc_time outside month")
            parts.append(df[["ts", "funding_interval_hours", "rate"]])
            present.append(m)
            z.unlink()
    if not parts:
        return None, present, missing
    return pd.concat(parts).sort_values("ts").drop_duplicates("ts").reset_index(drop=True), present, missing
