"""Event detector (PREREG §4, CLARIFICATIONS §3/§4). Inputs known at bar close only."""
import datetime as dt

import numpy as np
import pandas as pd

from ca import params as P
from ca.lock import require_segment_permission


def minute_features(kl: pd.DataFrame) -> pd.DataFrame:
    """kl: one symbol's 1m klines with open_time (ms), close, quote_volume.
    Returns a gap-free minute grid indexed by open_time with r, sigma, qv_med,
    qv60 and the bar close time. Missing minutes are NaN, so any window that
    touches one yields NaN (=> no event / not a placebo candidate)."""
    kl = kl.drop_duplicates("open_time").set_index("open_time").sort_index()
    if kl.index.size == 0:
        return pd.DataFrame(columns=["close", "quote_volume", "r", "sigma", "qv_med", "qv60", "close_ts"])
    if np.any(kl.index.to_numpy() % P.MINUTE_MS):
        raise ValueError("open_time not on minute boundaries")
    grid = np.arange(kl.index[0], kl.index[-1] + P.MINUTE_MS, P.MINUTE_MS, dtype=np.int64)
    f = kl[["close", "quote_volume"]].reindex(grid)
    f.index.name = "open_time"
    f["r"] = f["close"] / f["close"].shift(1) - 1.0
    # sigma_t over r_{t-240..t-1}; min_periods = window => every return present
    f["sigma"] = f["r"].shift(1).rolling(P.SIGMA_WINDOW, min_periods=P.SIGMA_WINDOW).std(ddof=1)
    f["qv_med"] = f["quote_volume"].shift(1).rolling(P.VOL_WINDOW, min_periods=P.VOL_WINDOW).median()
    f["qv60"] = f["quote_volume"].shift(1).rolling(P.PLACEBO_QV_WINDOW, min_periods=P.PLACEBO_QV_WINDOW).sum()
    f["close_ts"] = f.index.to_numpy() + P.MINUTE_MS
    return f


def bar_day(open_time: np.ndarray) -> np.ndarray:
    """UTC day a bar belongs to = day of its open time."""
    return (open_time // P.DAY_MS).astype(np.int64)


def usable_mask(f: pd.DataFrame, segment: str) -> np.ndarray:
    """Bars whose day is in `segment`, honouring the 23:30 cutoff on its last day."""
    start, end = P.SEGMENTS[segment]
    days = bar_day(f.index.to_numpy())
    s, e = (start - dt.date(1970, 1, 1)).days, (end - dt.date(1970, 1, 1)).days
    close_min_of_last_day = (f["close_ts"].to_numpy() - e * P.DAY_MS) // P.MINUTE_MS
    return (days >= s) & (days <= e) & ~((days == e) & (close_min_of_last_day > P.LAST_DAY_CUTOFF_MIN))


def in_universe_mask(f: pd.DataFrame, symbol: str, universe: dict[dt.date, frozenset]) -> np.ndarray:
    days = bar_day(f.index.to_numpy())
    ok_days = {(d - dt.date(1970, 1, 1)).days for d, syms in universe.items() if symbol in syms}
    return np.isin(days, list(ok_days))


def detect_symbol_events(symbol: str, f: pd.DataFrame, universe: dict, segment: str, origin: str) -> pd.DataFrame:
    require_segment_permission(segment, origin)
    thr = -np.maximum(P.SIGMA_MULT * f["sigma"].to_numpy(), P.MIN_DROP)
    qv, med = f["quote_volume"].to_numpy(), f["qv_med"].to_numpy()
    cand = (f["r"].to_numpy() <= thr) & (qv >= P.VOL_MULT * med)  # NaN compares False
    cand &= np.isfinite(f["sigma"].to_numpy()) & np.isfinite(med)
    cand &= usable_mask(f, segment) & in_universe_mask(f, symbol, universe)
    idx = np.flatnonzero(cand)
    keep, last = [], None
    for i in idx:  # cooldown: next event >= 30 min after the previous accepted one
        t = f.index[i]
        if last is None or t - last >= P.COOLDOWN_MIN * P.MINUTE_MS:
            keep.append(i)
            last = t
    ev = f.iloc[keep][["close", "r", "sigma", "quote_volume", "qv_med", "qv60", "close_ts"]].reset_index()
    ev.insert(0, "symbol", symbol)
    ev["day"] = [P.ms_to_date(t) for t in ev["open_time"]]
    ev["segment"] = segment
    return ev


def link_episodes(events: pd.DataFrame) -> pd.Series:
    """Single linkage across symbols: an event joins the current episode if it
    starts <= 30 min after the previous event in that episode (start = bar close)."""
    order = events.sort_values(["close_ts", "symbol"], kind="stable")
    ep, cur, prev = [], -1, None
    for t in order["close_ts"].to_numpy():
        if prev is None or t - prev > P.EPISODE_GAP_MIN * P.MINUTE_MS:
            cur += 1
        ep.append(cur)
        prev = t
    return pd.Series(ep, index=order.index, name="episode").reindex(events.index)
