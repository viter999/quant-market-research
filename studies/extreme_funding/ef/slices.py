"""Daily slices for extreme-funding (guarded + CHECKSUM via the frozen downloader):
spot 1m klines, perp 1m klines (only days the crash-absorption parquet lacks) and
metrics (5-min OI). Cached per symbol-day as parquet; a 404 is cached as 'absent'."""
import datetime as dt
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

from ca import downloader as DL
from ca import params as P
from ef.archive import ARCHIVE, fetch_csv

KCOLS = DL.KLINE_COLS
MCOLS = ["create_time", "symbol", "sum_open_interest", "sum_open_interest_value", "count_toptrader_long_short_ratio",
         "sum_toptrader_long_short_ratio", "count_long_short_ratio", "sum_taker_long_short_vol_ratio"]


def kline_key(market: str, symbol: str, day: dt.date) -> str:
    root = "data/spot" if market == "spot" else "data/futures/um"
    return f"{root}/daily/klines/{symbol}/1m/{symbol}-1m-{day.isoformat()}.zip"


def metrics_key(symbol: str, day: dt.date) -> str:
    return f"data/futures/um/daily/metrics/{symbol}/{symbol}-metrics-{day.isoformat()}.zip"


def to_ms(open_time: pd.Series, day: dt.date) -> np.ndarray:
    """Spot klines switched to microseconds on 2025-01-01. Detect the unit from the
    magnitude and validate against the file's day; anything else is an error."""
    v = open_time.astype(np.int64).to_numpy()
    lo, hi = P.date_to_ms(day), P.date_to_ms(day + dt.timedelta(days=1))
    for scale in (1, 1000):
        ms = v // scale
        if len(ms) == 0 or (ms.min() >= lo and ms.max() < hi):
            return ms
    raise DL.DataValidationError(f"open_time not in {day} as ms or us")


def create_time_ms(col: pd.Series) -> np.ndarray:
    """'YYYY-MM-DD HH:MM:SS' (UTC) -> epoch ms, independent of pandas' datetime resolution."""
    t = pd.to_datetime(col, utc=True)
    return ((t - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(milliseconds=1)).to_numpy(np.int64)


def _cache(base: Path, symbol: str, day: dt.date) -> Path:
    return base / symbol / f"{day.isoformat()}.parquet"


def _write(df: pd.DataFrame, p: Path) -> None:
    """Atomic: unique temp file, then rename (threads may fetch the same symbol-day)."""
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f"{p.name}.{uuid.uuid4().hex}.tmp")
    df.to_parquet(tmp, index=False)
    tmp.replace(p)


def get_klines(fetch, base: Path, market: str, symbol: str, day: dt.date) -> pd.DataFrame | None:
    p = _cache(base, symbol, day)
    absent = p.with_suffix(".absent")
    if p.exists():
        return pd.read_parquet(p)
    if absent.exists():
        return None
    try:
        df = fetch_csv(fetch, kline_key(market, symbol, day), KCOLS)
    except FileNotFoundError:
        absent.parent.mkdir(parents=True, exist_ok=True)
        absent.touch()
        return None
    df.columns = KCOLS[: len(df.columns)]
    out = pd.DataFrame({"open_time": to_ms(df["open_time"], day), "open": df["open"].astype(float), "high": df["high"].astype(float),
                        "low": df["low"].astype(float), "close": df["close"].astype(float),
                        "quote_volume": df["quote_volume"].astype(float)}).sort_values("open_time")
    if out["open_time"].duplicated().any():
        raise DL.DataValidationError(f"{market} {symbol} {day}: duplicate open_time")
    _write(out, p)
    return out


def check_metrics_day(ts: np.ndarray, day: dt.date) -> None:
    lo, hi = P.date_to_ms(day), P.date_to_ms(day + dt.timedelta(days=1))
    tol = 5 * P.MINUTE_MS
    if len(ts) and (ts.min() < lo - tol or ts.max() > hi + tol):
        raise DL.DataValidationError(f"metrics {day}: create_time outside its day")


def get_metrics(fetch, base: Path, symbol: str, day: dt.date) -> pd.DataFrame | None:
    p = _cache(base, symbol, day)
    absent = p.with_suffix(".absent")
    if p.exists():
        return pd.read_parquet(p)
    if absent.exists():
        return None
    try:
        df = fetch_csv(fetch, metrics_key(symbol, day), MCOLS)
    except FileNotFoundError:
        absent.parent.mkdir(parents=True, exist_ok=True)
        absent.touch()
        return None
    ts = create_time_ms(df["create_time"])
    check_metrics_day(ts, day)  # tolerance one 5-min period: end-of-day rows are stamped e.g. 00:00:01 next day
    out = pd.DataFrame({"ts": ts, "sum_open_interest": df["sum_open_interest"].astype(float)}).sort_values("ts")
    _write(out, p)
    return out


def days_between(a_ms: int, b_ms: int) -> list[dt.date]:
    d0, d1 = P.ms_to_date(a_ms), P.ms_to_date(b_ms)
    return [d0 + dt.timedelta(days=i) for i in range((d1 - d0).days + 1)]
