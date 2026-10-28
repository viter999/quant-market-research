"""Exit engine and returns (PREREG §6, CLARIFICATIONS §6). Reads post-fill
prices, so every entry point is behind the outcome lock: synthetic data only
until the director says "run VERDICT"."""
from dataclasses import dataclass

import numpy as np

from ca import params as P
from ca.lock import require_outcome_permission
from ca.trades import Trades


class FundingCoverageError(RuntimeError):
    pass


@dataclass(frozen=True)
class Exit:
    ok: bool
    exit_ts: int          # T
    price: float | None
    source: str           # "min" | "vwap" | "last" | "drop"


def exit_price(trades: Trades, fill_ts: int, hold_min: float = P.PRIMARY_HOLD_MIN) -> Exit:
    require_outcome_permission(trades.origin)
    T = int(fill_ts + round(hold_min * P.MINUTE_MS))
    sell = trades.is_buyer_maker
    ts, px, q = trades.ts[sell], trades.price[sell], trades.qty[sell]
    a0 = int(np.searchsorted(ts, T, side="left"))
    a1 = int(np.searchsorted(ts, T + P.EXIT_VWAP_S * 1000, side="right"))
    vwap = float(np.dot(px[a0:a1], q[a0:a1]) / q[a0:a1].sum()) if a1 > a0 else None
    b = int(np.searchsorted(ts, T, side="right")) - 1
    last = float(px[b]) if b >= 0 and ts[b] >= T - P.EXIT_LAST_MAX_AGE_S * 1000 else None
    if vwap is not None and last is not None:
        return Exit(True, T, min(vwap, last), "min")
    if vwap is not None:
        return Exit(True, T, vwap, "vwap")
    if last is not None:
        return Exit(True, T, last, "last")
    return Exit(False, T, None, "drop")


@dataclass(frozen=True)
class Funding:
    """Settlements for one symbol. [cover_start, cover_end] is the time span the
    loaded archive files cover; a hold outside it raises instead of silently
    assuming zero funding."""
    ts: np.ndarray
    rate: np.ndarray
    cover_start: int
    cover_end: int

    def paid(self, fill_ts: int, exit_ts: int) -> float:
        if fill_ts < self.cover_start or exit_ts > self.cover_end:
            raise FundingCoverageError(f"hold ({fill_ts}, {exit_ts}] outside funding coverage")
        m = (self.ts > fill_ts) & (self.ts <= exit_ts)
        return float(self.rate[m].sum())  # signed: long pays positive, receives negative


def net_return(entry: float, exit_px: float, entry_fee: float, funding_paid: float, buffer_mult: int) -> dict:
    if buffer_mult not in P.BUFFER_MULTS:
        raise ValueError(buffer_mult)
    gross = (exit_px - entry) / entry
    net = gross - entry_fee - P.FEE_TAKER - P.BUFFER_PER_MULT * buffer_mult - funding_paid
    return {"gross": gross, "net": net}


def trade_outcome(trades: Trades, fill, funding: Funding, buffer_mult: int = 1,
                  hold_min: float = P.PRIMARY_HOLD_MIN) -> dict:
    """Per-fill outcome row for a filled order; non-fills are handled by the caller (count as 0 per order)."""
    require_outcome_permission(trades.origin)
    if not fill.filled:
        raise ValueError("unfilled order has no per-fill outcome")
    ex = exit_price(trades, fill.fill_ts, hold_min)
    if not ex.ok:
        return {"dropped": True, "exit_source": ex.source}
    fpaid = funding.paid(fill.fill_ts, ex.exit_ts)
    return {"dropped": False, "exit_source": ex.source, "exit": ex.price, "funding": fpaid,
            **net_return(fill.entry, ex.price, fill.entry_fee, fpaid, buffer_mult)}
