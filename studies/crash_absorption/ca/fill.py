"""Fill engine (PREREG §5, CLARIFICATIONS §5). Computes whether and when a
resting buy limit fills and at what entry price. No post-fill prices are read
here, so it may run on DEV archive data (fill rates are allowed)."""
from dataclasses import dataclass

import numpy as np

from ca import params as P
from ca.trades import Trades


@dataclass(frozen=True)
class Fill:
    filled: bool
    kind: str | None      # "gap" (taker) | "maker" | None
    fill_ts: int | None
    entry: float | None
    entry_fee: float | None
    limit: float
    qty: float
    live_ts: int
    cancel_ts: int


def simulate_fill(trades: Trades, ref_ts: int, ref_close: float, depth: float = P.PRIMARY_DEPTH,
                  latency_s: float = P.PRIMARY_LATENCY_S, queue_mult: float = P.PRIMARY_QUEUE_MULT) -> Fill:
    """ref_ts = close time of bar t (open_time + 60 s), ref_close = its close."""
    limit = ref_close * (1.0 - depth)
    qty = P.NOTIONAL_USD / limit
    live = int(ref_ts + round(latency_s * 1000))
    cancel = live + P.CANCEL_AFTER_S * 1000
    i0 = int(np.searchsorted(trades.ts, live, side="left"))      # ts >= live
    i1 = int(np.searchsorted(trades.ts, cancel, side="right"))   # ts <= cancel
    none = Fill(False, None, None, None, None, limit, qty, live, cancel)
    if i0 >= i1:
        return none
    first = trades.price[i0]
    if first <= limit:
        entry = min(first * (1.0 + P.GAP_SLIPPAGE), limit)
        return Fill(True, "gap", int(trades.ts[i0]), entry, P.FEE_TAKER, limit, qty, live, cancel)
    below = trades.price[i0:i1] < limit
    cum = np.cumsum(np.where(below, trades.qty[i0:i1], 0.0))
    k = int(np.searchsorted(cum, queue_mult * qty, side="left"))  # first cum >= threshold
    if k >= len(cum):
        return none
    return Fill(True, "maker", int(trades.ts[i0 + k]), limit, P.FEE_MAKER, limit, qty, live, cancel)


def kline_touch(open_time: np.ndarray, low: np.ndarray, live_ts: int, cancel_ts: int, limit: float) -> bool:
    """Sanity check (§7): did any 1m bar overlapping [live, cancel] trade below L?"""
    m = (open_time + P.MINUTE_MS > live_ts) & (open_time <= cancel_ts)
    return bool(np.any(low[m] < limit))
