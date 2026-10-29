"""Phase 0 fill-model check (PHASE0_FILL_CHECK.md). Prices and agreement only:
nothing here computes a return, markout or PnL, and no function receives both an
entry price and an exit price."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ca import params as P
from ca.fill import simulate_fill
from ca.trades import Trades

LATENCIES_S = (2, 5, 10)
PRIMARY_LATENCY_S = 2
DEPTH = 0.005
PROXY_WINDOW_MS = 1000
HOLD_MS = 15 * P.MINUTE_MS


@dataclass(frozen=True)
class Book:
    """bookTicker updates sorted by (ts, update_id); ts = transaction_time (ms)."""
    ts: np.ndarray
    update_id: np.ndarray
    bid: np.ndarray
    bid_qty: np.ndarray
    ask: np.ndarray
    ask_qty: np.ndarray

    @classmethod
    def from_frame(cls, df: pd.DataFrame) -> "Book":
        df = df.sort_values(["ts", "update_id"], kind="stable")
        return cls(df["ts"].to_numpy(np.int64), df["update_id"].to_numpy(np.int64), df["bid"].to_numpy(float),
                   df["bid_qty"].to_numpy(float), df["ask"].to_numpy(float), df["ask_qty"].to_numpy(float))


def quote_at(book: Book, t: int) -> int:
    """Index of the quote in force at t: the last update with ts <= t; among updates
    with the same ts, the one with the highest update_id. -1 if none."""
    return int(np.searchsorted(book.ts, t, side="right")) - 1


def real_fill(book: Book, tau: int, limit: float, qty: float) -> dict:
    """REAL (quote-based) IOC fill at tau: best ask <= L and best-ask qty >= order qty."""
    i = quote_at(book, tau)
    if i < 0:
        return {"status": "no_quote"}
    ask, askq, bid = book.ask[i], book.ask_qty[i], book.bid[i]
    status = "full" if ask <= limit and askq >= qty else ("partial" if ask <= limit else "none")
    return {"status": status, "ask": float(ask), "ask_qty": float(askq), "bid": float(bid),
            "quote_age_ms": int(tau - book.ts[i])}


def proxy_fill(tr: Trades, tau: int, limit: float) -> dict:
    """PROXY (PREREG v0.1 §1): first buyer-initiated aggTrade in [tau, tau+1 s] at price <= L."""
    buy = ~tr.is_buyer_maker
    ts, px = tr.ts[buy], tr.price[buy]
    i = int(np.searchsorted(ts, tau, side="left"))
    if i >= len(ts) or ts[i] > tau + PROXY_WINDOW_MS or px[i] > limit:
        return {"filled": False}
    return {"filled": True, "entry": float(px[i] * (1 + P.GAP_SLIPPAGE)), "trade_ts": int(ts[i])}


def old_fill(tr: Trades, close_ts: int, close: float, latency_s: int) -> dict:
    """OLD rule = the frozen crash-absorption gap case (ca.fill.simulate_fill)."""
    f = simulate_fill(tr, close_ts, close, DEPTH, latency_s, P.PRIMARY_QUEUE_MULT)
    return {"filled": f.kind == "gap", "entry": f.entry if f.kind == "gap" else None}


def exit_proxy_price(tr: Trades, T: int) -> float | None:
    """Exit-price proxy at T (crash-absorption §6 rule): the lower of the seller-initiated
    VWAP in [T, T+10 s] and the last seller-initiated trade <= T within 60 s. A PRICE only
    (authorised by PHASE0_FILL_CHECK.md §4); it is never combined with an entry."""
    sell = tr.is_buyer_maker
    ts, px, q = tr.ts[sell], tr.price[sell], tr.qty[sell]
    a0 = int(np.searchsorted(ts, T, side="left"))
    a1 = int(np.searchsorted(ts, T + P.EXIT_VWAP_S * 1000, side="right"))
    vwap = float(np.dot(px[a0:a1], q[a0:a1]) / q[a0:a1].sum()) if a1 > a0 else None
    b = int(np.searchsorted(ts, T, side="right")) - 1
    last = float(px[b]) if b >= 0 and ts[b] >= T - P.EXIT_LAST_MAX_AGE_S * 1000 else None
    cands = [x for x in (vwap, last) if x is not None]
    return min(cands) if cands else None


def bps(a: float, b: float) -> float:
    """(a - b) / b in bps: a price DIFFERENCE at the same moment, not a return."""
    return (a - b) / b * 1e4


def stats(x) -> dict:
    x = np.asarray(list(x), float)
    if not len(x):
        return {"n": 0, "mean": None, "median": None, "p10": None, "p90": None}
    return {"n": int(len(x)), "mean": float(x.mean()), "median": float(np.median(x)),
            "p10": float(np.percentile(x, 10)), "p90": float(np.percentile(x, 90))}


def confusion(real: np.ndarray, pred: np.ndarray) -> dict:
    real, pred = np.asarray(real, bool), np.asarray(pred, bool)
    tp, fp = int((real & pred).sum()), int((~real & pred).sum())
    fn, tn = int((real & ~pred).sum()), int((~real & ~pred).sum())
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": tp / (tp + fp) if tp + fp else None, "recall": tp / (tp + fn) if tp + fn else None}


def decision(n_real: int, conf: dict, entry_bias_mean, exit_bias_mean) -> dict:
    """PHASE0 rules (a)-(d) at 2 s."""
    a = n_real >= 30
    b = conf["precision"] is not None and conf["recall"] is not None and conf["precision"] >= 0.85 and conf["recall"] >= 0.85
    c = entry_bias_mean is not None and entry_bias_mean >= -5.0
    d = exit_bias_mean is not None and exit_bias_mean <= 5.0
    verdict = "NOT ENOUGH DATA" if not a else ("ACCEPTED" if (b and c and d) else "NOT ACCEPTED")
    return {"a_real_fills_ge_30": a, "b_precision_recall_ge_0.85": b, "c_mean_entry_bias_ge_-5bps": c,
            "d_mean_exit_bias_le_5bps": d, "decision": verdict}
