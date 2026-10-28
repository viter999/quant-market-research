"""Synthetic data builders for tests. Nothing here touches real data."""
import datetime as dt

import numpy as np
import pandas as pd

from ca import params as P
from ca.lock import SYNTHETIC
from ca.trades import Trades


def ms(day: dt.date, hh: int = 0, mm: int = 0, ss: float = 0) -> int:
    return P.date_to_ms(day) + (hh * 3600 + mm * 60) * 1000 + int(round(ss * 1000))


def klines(start_ms: int, n: int, seed: int = 0, ret_sd: float = 0.001, qv: float = 1000.0,
           price0: float = 100.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    r = rng.normal(0, ret_sd, n)
    r[0] = 0.0
    close = price0 * np.cumprod(1 + r)
    return pd.DataFrame({"open_time": start_ms + np.arange(n, dtype=np.int64) * P.MINUTE_MS,
                         "close": close, "quote_volume": np.full(n, qv)})


def crash(kl: pd.DataFrame, open_time: int, drop: float, qv_mult: float) -> pd.DataFrame:
    """Make the bar opening at open_time close `drop` below the previous close
    (later bars shifted by the same factor) with qv_mult x base volume."""
    kl = kl.copy()
    i = int(np.flatnonzero(kl["open_time"].to_numpy() == open_time)[0])
    factor = (kl["close"].iloc[i - 1] * (1 - drop)) / kl["close"].iloc[i]
    kl.loc[kl.index[i:], "close"] *= factor
    kl.loc[kl.index[i], "quote_volume"] *= qv_mult
    return kl


def trades(rows) -> Trades:
    return Trades.from_rows(rows, SYNTHETIC)


def universe_all(symbols, start: dt.date, n_days: int) -> dict:
    return {start + dt.timedelta(days=i): frozenset(symbols) for i in range(n_days)}
