"""PREREG v0.2 §3 prices and P&L arithmetic. Outcome-locked (ca.lock): runs on
SYNTHETIC data only until the director says "run VERDICT". EF-1 uses it only in unit tests."""
import numpy as np
import pandas as pd

from ca import params as P
from ca.lock import require_outcome_permission

SPOT_FEE = 0.0010
PERP_FEE = 0.0005
BUFFER_PER_MULT = 0.0005


def bar_at(kl: pd.DataFrame, t0: int) -> pd.Series | None:
    """The 1m bar opening at t0 (the bar [t0, t0+1m)), or None."""
    m = kl["open_time"].to_numpy(np.int64) == t0
    return kl[m].iloc[0] if m.any() else None


def exec_minute(S: int) -> int:
    """First full 1m bar after S: [S+1m, S+2m), with S floored to the minute."""
    return (S // P.MINUTE_MS) * P.MINUTE_MS + P.MINUTE_MS


def entry_prices(spot: pd.DataFrame, perp: pd.DataFrame, S: int, origin: str) -> tuple[float, float]:
    """Worst-of-bar entry: spot BUY at max(open, close), perp SELL at min(open, close)."""
    require_outcome_permission(origin)
    t = exec_minute(S)
    sb, pb = bar_at(spot, t), bar_at(perp, t)
    if sb is None or pb is None:
        raise LookupError("entry bar missing")
    return max(sb["open"], sb["close"]), min(pb["open"], pb["close"])


def exit_prices(spot: pd.DataFrame, perp: pd.DataFrame, t: int, origin: str, at_minute: bool = False) -> tuple[float, float]:
    """Worst-of-bar exit: spot SELL at min(open, close), perp BUY at max(open, close), in the bar
    [S_k+1m, S_k+2m) - or, for a delisting exit, the bar opening at the last common minute t."""
    require_outcome_permission(origin)
    t0 = t if at_minute else exec_minute(t)
    sb, pb = bar_at(spot, t0), bar_at(perp, t0)
    if sb is None or pb is None:
        raise LookupError("exit bar missing")
    return min(sb["open"], sb["close"]), max(pb["open"], pb["close"])


def funding_received(funding: pd.DataFrame, perp: pd.DataFrame, S: int, exit_ts: int, Q: float, origin: str) -> float:
    """Sum over settlements S_j in (S, exit] of f_j * Q * perp close at S_j (close of the bar
    [S_j - 1m, S_j), the mark-price proxy). Signed: the short perp receives positive f."""
    require_outcome_permission(origin)
    f = funding[(funding["ts"] > S) & (funding["ts"] <= exit_ts)]
    total = 0.0
    for ts, rate in zip(f["ts"], f["rate"]):
        b = bar_at(perp, (int(ts) // P.MINUTE_MS) * P.MINUTE_MS - P.MINUTE_MS)
        if b is None:
            raise LookupError(f"perp bar before settlement {ts} missing")
        total += rate * Q * b["close"]
    return float(total)


def trade_pnl(se, pe, sx, px, Q, funding_usdt, buffer_mult: int, delisting: bool = False) -> dict:
    """USDT P&L split (spot leg, perp leg, funding, fees, buffer); delisting exits use the 5x buffer
    on the exit trades. Pure arithmetic on given numbers."""
    spot_leg = Q * (sx - se)
    perp_leg = Q * (pe - px)
    notional = {"spot_in": Q * se, "spot_out": Q * sx, "perp_in": Q * pe, "perp_out": Q * px}
    fees = SPOT_FEE * (notional["spot_in"] + notional["spot_out"]) + PERP_FEE * (notional["perp_in"] + notional["perp_out"])
    m_out = 5 if delisting else buffer_mult
    buffer = BUFFER_PER_MULT * (buffer_mult * (notional["spot_in"] + notional["perp_in"]) + m_out * (notional["spot_out"] + notional["perp_out"]))
    net = spot_leg + perp_leg + funding_usdt - fees - buffer
    return {"spot_leg": spot_leg, "perp_leg": perp_leg, "funding": funding_usdt, "fees": fees, "buffer": buffer, "net": net,
            "net_bps_spot_notional": net / (Q * se) * 1e4}
