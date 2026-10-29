"""PREREG v0.2 §2 trade and §4 verdict (with CLARIFICATIONS v0.2.1). Pure
functions over price frames; every entry point that touches prices checks the
outcome lock first."""
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from . import events as E
from .lock import ARCHIVE, require_outcome_permission

N_BOOT = 10_000
SEED = 20261103
TAKER_BPS = 5.0
BUFFER_BPS = {1: 25.0, 2: 50.0, 5: 125.0}  # per side
PRICE_COLS = ["open_time", "open", "high", "low", "close"]


def load_prices(path: Path, origin: str) -> pd.DataFrame:
    require_outcome_permission(origin)
    return pd.read_parquet(path, columns=PRICE_COLS).set_index("open_time")


def load_funding(path: Path, origin: str) -> pd.DataFrame:
    require_outcome_permission(origin)
    return pd.read_parquet(path)


def _bar(k: pd.DataFrame, t: int) -> pd.Series:
    if t not in k.index:
        raise KeyError(f"bar {t} missing")
    return k.loc[t]


def event_result(ev: dict, k: pd.DataFrame, btc: pd.DataFrame, fund: pd.DataFrame, origin: str) -> dict:
    """One symbol-event. k/btc: 1m bars indexed by open_time; fund: (ts, rate)."""
    require_outcome_permission(origin)
    w = E.windows(ev)
    eb, xb = _bar(k, w["entry"]), _bar(k, w["exit"])
    entry, exit_ = min(eb["open"], eb["close"]), max(xb["open"], xb["close"])
    gross = (entry - exit_) / entry * 1e4
    f = fund[(fund["ts"] > w["entry"]) & (fund["ts"] <= w["exit"])]
    funding = float(f["rate"].sum()) * 1e4  # short receives positive rates
    out = {"symbol": ev["symbol"], "episode": ev["episode"], "A_utc": ev["A_utc"],
           "restriction_flag": int(ev["restriction_flag"]), "gross_bps": gross, "funding_bps": funding,
           "n_funding": int(len(f))}
    for m, b in BUFFER_BPS.items():
        out[f"net_{m}x_bps"] = gross - 2 * TAKER_BPS - 2 * b + funding
    rb = _bar(btc, w["exit"])["close"] / _bar(btc, w["entry"])["close"] - 1
    out["btc_ret_bps"] = rb * 1e4
    out["net_1x_btcrel_bps"] = out["net_1x_bps"] + out["btc_ret_bps"]
    out.update(exploratory(ev, k, w, entry, fund))
    return out


def _px(k, t, how):
    if t not in k.index:
        return np.nan
    b = k.loc[t]
    return {"short": min(b["open"], b["close"]), "cover": max(b["open"], b["close"]), "low": b["low"],
            "high": b["high"], "close": b["close"], "open": b["open"]}[how]


def exploratory(ev: dict, k: pd.DataFrame, w: dict, entry: float, fund: pd.DataFrame) -> dict:
    """PREREG §5 (descriptive only). Costs at 1x where a trade is implied."""
    c1 = 2 * TAKER_BPS + 2 * BUFFER_BPS[1]
    a0 = E.floor_min(ev["A_ms"])
    xo = {}
    xo["x_react_A_15m_bps"] = (_px(k, a0 + 15 * E.MIN, "close") / _px(k, a0, "open") - 1) * 1e4
    exit_ = _px(k, w["exit"], "cover")
    for lab, d in (("15m", 15), ("60m", 60)):
        t = E.ceil_min(ev["A_ms"] + d * E.MIN)
        e = _px(k, t, "short")
        f = fund[(fund["ts"] > t) & (fund["ts"] <= w["exit"])]["rate"].sum() * 1e4
        xo[f"x_entry_A{lab}_net_1x_bps"] = (e - exit_) / e * 1e4 - c1 + f
    lo, hi = _px(k, w["entry"], "low"), _px(k, w["exit"], "high")
    f_main = fund[(fund["ts"] > w["entry"]) & (fund["ts"] <= w["exit"])]["rate"].sum() * 1e4
    xo["x_bar_extreme_net_1x_bps"] = (lo - hi) / lo * 1e4 - c1 + f_main
    t24 = ev["D_ms"] - E.DAY
    if t24 > w["entry"]:
        x24 = _px(k, t24, "cover")
        f = fund[(fund["ts"] > w["entry"]) & (fund["ts"] <= t24)]["rate"].sum() * 1e4
        xo["x_exit_D24h_net_1x_bps"] = (entry - x24) / entry * 1e4 - c1 + f
    else:
        xo["x_exit_D24h_net_1x_bps"] = np.nan
    # long mirror: buy at max(open, close) of the entry bar, sell at min(open, close) of the exit bar
    le, lx = _px(k, w["entry"], "cover"), _px(k, w["exit"], "short")
    xo["x_long_net_1x_bps"] = (lx - le) / le * 1e4 - c1 - f_main
    hold = k.loc[(k.index >= w["entry"]) & (k.index <= w["exit"]), "high"]
    xo["x_max_adverse_bps"] = (hold.max() / entry - 1) * 1e4 if len(hold) else np.nan
    return xo


def episodes(res: pd.DataFrame, col: str = "net_1x_bps") -> pd.Series:
    return res.groupby("episode")[col].mean()


def boot_means(x: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED) -> np.ndarray:
    idx = np.random.default_rng(seed).integers(0, len(x), size=(n_boot, len(x)))
    return x[idx].mean(1)


def verdict(res: pd.DataFrame) -> dict:
    """PREREG §4 items 1-6 on the usable symbol-events (one row each)."""
    ep = {m: episodes(res, f"net_{m}x_bps") for m in BUFFER_BPS}
    ep_btc = episodes(res, "net_1x_btcrel_bps")
    x1 = ep[1].to_numpy()
    n_ep, n_ev = len(x1), len(res)
    reps = boot_means(x1) if n_ep else np.array([np.nan])
    lb99, ub99 = float(np.percentile(reps, 1)), float(np.percentile(reps, 99))
    top3_removed = np.sort(x1)[:-3] if n_ep > 3 else np.array([])
    items = {
        "1_sample": {"episodes": n_ep, "symbol_events": n_ev, "pass": n_ep >= 30 and n_ev >= 40},
        "2_mean_1x": {"mean_bps": float(x1.mean()), "lb99_one_sided_bps": lb99,
                      "pass": bool(x1.mean() >= 100 and lb99 > 0)},
        "3_mean_2x": {"mean_bps": float(ep[2].mean()), "pass": bool(ep[2].mean() > 0)},
        "4_median_1x": {"median_bps": float(np.median(x1)), "pass": bool(np.median(x1) > 0)},
        "5_btc_relative_mean_1x": {"mean_bps": float(ep_btc.mean()), "pass": bool(ep_btc.mean() > 0)},
        "6_mean_1x_without_top3": {"mean_bps": float(top3_removed.mean()) if len(top3_removed) else float("nan"),
                                   "pass": bool(len(top3_removed) and top3_removed.mean() > 0)},
    }
    passed = all(v["pass"] for v in items.values())
    if not items["1_sample"]["pass"]:
        status = "NOT EVALUABLE"
    else:
        status = "PASS" if passed else "KILL"
    return {"status": status, "items": items, "ub99_one_sided_bps": ub99,
            "significantly_negative": bool(ub99 < 0), "mean_5x_bps": float(ep[5].mean()),
            "n_boot": N_BOOT, "seed": SEED}
