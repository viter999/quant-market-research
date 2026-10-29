"""Extreme-funding carry (PREREG v0.2): candidate events, entry filters and the
portfolio simulation of entry/exit TIMES. No price, return or P&L is computed here;
exit decisions use funding rates only (allowed by EF-1)."""
import datetime as dt
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ca import params as P

H_ENTRY = 0.000125      # 0.0125 % per hour (= 0.10 % per 8h)
H_EXIT = 0.0000375      # 0.00375 % per hour (= 0.03 % per 8h)
OI_RISE = 1.05
OI_LAG_MS = 5 * P.MINUTE_MS
DAY = P.DAY_MS
HOUR = 3_600_000
MAX_HOLD_MS = 7 * DAY
CAP = 10  # v0.3 (was 5)
PERP_24H_QV_MIN = 20_000_000.0  # v0.3 universe: perp 24h quote volume from 1m bars in [S-24h, S)
SPOT_24H_QV_MIN = 5_000_000.0
SPOT_MED_1M_QV_MIN = 50_000.0


# ----------------------------------------------------------------- §2 signal
def funding_table(df: pd.DataFrame) -> pd.DataFrame:
    """df: ts (settlement time, ms), rate. Adds I_S (hours, rounded to the nearest whole
    hour from S minus the previous fundingTime), the previous interval, h_S = f_S / I_S
    and a status: 'ok', 'no_history' (first two settlements) or 'interval_change'."""
    d = df.sort_values("ts").drop_duplicates("ts").reset_index(drop=True).copy()
    gap_h = d["ts"].diff() / HOUR
    d["I_S"] = gap_h.round()
    d["I_prev"] = d["I_S"].shift(1)
    d["h_S"] = d["rate"] / d["I_S"]
    status = np.where(d["I_S"].isna() | d["I_prev"].isna(), "no_history",
                      np.where(d["I_S"] != d["I_prev"], "interval_change", "ok"))
    d["status"] = status
    return d


def segment_cutoff_ms(segment: str) -> int:
    """Last allowed entry time: 7 days + 1 day before the segment end (end = last day 23:59:59.999)."""
    end = P.date_to_ms(P.SEGMENTS[segment][1] + dt.timedelta(days=1)) - 1
    return end - MAX_HOLD_MS - DAY


def entry_segment(S: int) -> str | None:
    return P.segment_of(P.ms_to_date(S))


# ----------------------------------------------------------------- §2 OI, §4 spot liquidity
def oi_at(metrics: pd.DataFrame, t: int) -> float | None:
    """sum_open_interest of the last 5-min metrics row timestamped <= t (None if none)."""
    ts = metrics["ts"].to_numpy(np.int64)
    i = int(np.searchsorted(ts, t, side="right")) - 1
    return None if i < 0 else float(metrics["sum_open_interest"].to_numpy()[i])


def oi_rise(metrics: pd.DataFrame, S: int) -> tuple[float | None, float | None]:
    """(OI now, OI 24h earlier): the last row <= S - 5 min, and the last row <= S - 5 min - 24 h."""
    return oi_at(metrics, S - OI_LAG_MS), oi_at(metrics, S - OI_LAG_MS - DAY)


def perp_qv_24h(perp: pd.DataFrame, S: int) -> float:
    """v0.3 universe input: perp quote volume summed over its 1m bars in [S-24h, S)."""
    m = (perp["open_time"] >= S - DAY) & (perp["open_time"] < S)
    return float(perp.loc[m, "quote_volume"].sum())


def spot_liquidity(spot: pd.DataFrame, S: int) -> dict:
    """Spot 1m bars in [S-24h, S): count, 24h quote volume, median 1-min quote volume
    (missing minutes count as 0 in the median)."""
    m = (spot["open_time"] >= S - DAY) & (spot["open_time"] < S)
    qv = spot.loc[m, "quote_volume"].to_numpy(float)
    padded = np.concatenate([qv, np.zeros(max(0, 1440 - len(qv)))])
    return {"bars": int(m.sum()), "qv_24h": float(qv.sum()), "median_1m_qv": float(np.median(padded)) if len(padded) else 0.0}


# ----------------------------------------------------------------- §3 exit time (funding only)
def exit_time(ft: pd.DataFrame, S: int, data_end: int | None) -> tuple[int, str]:
    """Exit decision time for an entry at settlement S, using funding only:
    the first later settlement S_k with h_{S_k} < 0.00375 %/h ('funding'), or the first
    settlement on or after S + 7 days ('max_hold'). If the last common data minute comes
    before that settlement (or no such settlement exists), exit at that minute ('delisting')."""
    later = ft[ft["ts"] > S]
    hit = later[(later["h_S"] < H_EXIT) | (later["ts"] >= S + MAX_HOLD_MS)]
    if len(hit):
        r = hit.iloc[0]
        t, why = int(r["ts"]), ("funding" if r["h_S"] < H_EXIT else "max_hold")
        if data_end is None or data_end >= t:
            return t, why
    if data_end is None:
        raise ValueError("no exit settlement and no data end")
    return int(data_end), "delisting"


# ----------------------------------------------------------------- cap / one position per symbol
@dataclass
class Book:
    cap: int = CAP
    open: dict = field(default_factory=dict)   # symbol -> exit time
    max_open: int = 0


def simulate(signals: pd.DataFrame, exit_for, cap: int = CAP) -> tuple[pd.DataFrame, pd.DataFrame]:
    """signals: symbol, S, h_S (all non-portfolio filters already passed).
    Processed by S; at each S, positions whose exit time is <= S are closed first, then
    the signals at S are taken in order of highest h_S (ties: symbol name). A signal is
    dropped if its symbol already has an open position or if `cap` positions are open.
    exit_for(symbol, S) -> (exit_time, reason). Returns (trades, drops)."""
    book, trades, drops = Book(cap=cap), [], []
    for S, g in signals.sort_values(["S"]).groupby("S", sort=True):
        for sym in [s for s, e in book.open.items() if e <= S]:
            del book.open[sym]
        for r in g.sort_values(["h_S", "symbol"], ascending=[False, True]).itertuples():
            if r.symbol in book.open:
                drops.append({"symbol": r.symbol, "S": int(S), "reason": "symbol_open"})
                continue
            if len(book.open) >= book.cap:
                drops.append({"symbol": r.symbol, "S": int(S), "reason": "cap"})
                continue
            t, why = exit_for(r.symbol, int(S))
            book.open[r.symbol] = t
            book.max_open = max(book.max_open, len(book.open))
            trades.append({"symbol": r.symbol, "S": int(S), "h_S": float(r.h_S), "exit_ts": t, "exit_reason": why,
                           "hold_h": (t - int(S)) / HOUR, "open_after_entry": len(book.open)})
    tr = pd.DataFrame(trades, columns=["symbol", "S", "h_S", "exit_ts", "exit_reason", "hold_h", "open_after_entry"])
    tr.attrs["max_open"] = book.max_open
    return tr, pd.DataFrame(drops, columns=["symbol", "S", "reason"])


def max_concurrent(trades: pd.DataFrame) -> int:
    """Max positions open at once from (S, exit_ts) intervals (exits at t free the slot at t)."""
    ev = sorted([(int(s), 1) for s in trades["S"]] + [(int(e), -1) for e in trades["exit_ts"]], key=lambda x: (x[0], x[1]))
    cur = best = 0
    for _, d in ev:
        cur += d
        best = max(best, cur)
    return best
