"""data.binance.vision downloads for TEST events: daily 1m klines and monthly
fundingRate, every file guarded and verified against its CHECKSUM."""
import datetime as dt
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "crash_absorption"))
from ca.downloader import HttpFetcher, parse_klines, _read_csv_member  # noqa: E402,F401  (pure helpers)

from .guard import assert_allowed

ARCHIVE = "https://data.binance.vision"
UM = "data/futures/um"


class ChecksumError(RuntimeError):
    pass


def kline_url(symbol: str, day: dt.date) -> str:
    return f"{ARCHIVE}/{UM}/daily/klines/{symbol}/1m/{symbol}-1m-{day.isoformat()}.zip"


def funding_url(symbol: str, month: str) -> str:
    return f"{ARCHIVE}/{UM}/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{month}.zip"


def fetch_zip(fetch, url: str, tmpdir: Path) -> Path | None:
    """Guarded download + sha256 check; None on 404."""
    assert_allowed(url)
    path = tmpdir / url.rsplit("/", 1)[-1]
    if not fetch.download(url, path):
        return None
    assert_allowed(url + ".CHECKSUM")
    body = fetch.get(url + ".CHECKSUM")
    if body is None:
        raise ChecksumError(f"no CHECKSUM for {url}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != body.decode().split()[0].lower():
        raise ChecksumError(f"sha256 mismatch for {url}")
    return path


def download_klines(symbol: str, days: list[dt.date], out: Path, fetch) -> dict:
    """Daily 1m files for `days` -> one parquet; returns {'present': [...], 'missing': [...]}."""
    parts, present, missing = [], [], []
    with tempfile.TemporaryDirectory() as td:
        for d in days:
            z = fetch_zip(fetch, kline_url(symbol, d), Path(td))
            if z is None:
                missing.append(d.isoformat())
                continue
            parts.append(parse_klines(z, "daily", d.isoformat()))
            present.append(d.isoformat())
            z.unlink()
    out.parent.mkdir(parents=True, exist_ok=True)
    if parts:
        df = pd.concat(parts).sort_values("open_time").reset_index(drop=True)
        if df["open_time"].duplicated().any():
            raise RuntimeError(f"{symbol}: duplicate open_time across files")
        df.to_parquet(out, index=False)
    man = {"symbol": symbol, "present": present, "missing": missing}
    out.with_suffix(".manifest.json").write_text(json.dumps(man))
    return man


def download_funding(symbol: str, months: list[str], out: Path, fetch) -> dict:
    """Monthly fundingRate files -> parquet (ts, rate); coverage lists only months whose file exists."""
    parts, present, missing = [], [], []
    with tempfile.TemporaryDirectory() as td:
        for m in months:
            z = fetch_zip(fetch, funding_url(symbol, m), Path(td))
            if z is None:
                missing.append(m)
                continue
            df = _read_csv_member(z, ["calc_time", "funding_interval_hours", "last_funding_rate"])
            df = df[["calc_time", "last_funding_rate"]].rename(columns={"calc_time": "ts", "last_funding_rate": "rate"})
            y, mo = map(int, m.split("-"))
            a = int(dt.datetime(y, mo, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
            b = int(dt.datetime(y + (mo == 12), mo % 12 + 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
            if len(df) and (df["ts"].min() < a or df["ts"].max() >= b):
                raise RuntimeError(f"{symbol} funding {m}: calc_time outside month (units?)")
            parts.append(df)
            present.append(m)
            z.unlink()
    out.parent.mkdir(parents=True, exist_ok=True)
    if parts:
        pd.concat(parts).sort_values("ts").drop_duplicates("ts").reset_index(drop=True).to_parquet(out, index=False)
    man = {"symbol": symbol, "present": present, "missing": missing}
    out.with_suffix(".manifest.json").write_text(json.dumps(man))
    return man
