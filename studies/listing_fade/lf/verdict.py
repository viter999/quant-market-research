"""PREREG v0.2 §2 trade and §4 verdict (with CLARIFICATIONS v0.2.1). Every entry
point that loads prices or computes an outcome checks the outcome lock first."""
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from . import events as E
from .lock import require_outcome_permission

N_BOOT = 10_000
SEED = 20261104
TAKER_BPS = 5.0
BUFFER_BPS = {1: 15.0, 2: 30.0, 5: 75.0}  # per side
ORIGIN_DAY = dt.date(2024, 1, 1)           # 7-day blocks aligned to the first TEST day
STOP = 0.20


class Dropped(Exception):
    pass


def load_parquet(path: Path, origin: str, columns=None) -> pd.DataFrame:
    require_outcome_permission(origin)
    return pd.read_parquet(path, columns=columns)


def vwap(tr: pd.DataFrame, seller: bool, lo: int) -> tuple[float, int] | None:
    """VWAP of seller-initiated (ibm true, at the bid) or buyer-initiated trades in
    [lo, lo+1m); if none, [lo+1m, lo+2m). Returns (price, window start used)."""
    for start in (lo, lo + E.MIN):
        m = (tr["ts"] >= start) & (tr["ts"] < start + E.MIN) & (tr["ibm"] == seller)
        if m.any():
            q = tr.loc[m, "qty"].to_numpy(float)
            p = tr.loc[m, "price"].to_numpy(float)
            return float((p * q).sum() / q.sum()), start
    return None


def funding_sum(fund: pd.DataFrame, lo: int, hi: int) -> tuple[float, int]:
    assert fund["rate"].notna().all(), "NaN funding rate in the funding file"
    f = fund[(fund["ts"] > lo) & (fund["ts"] <= hi)]
    return float(f["rate"].sum()), int(len(f))


def _btc_close(btc: pd.Series, t: int) -> float:
    k = E.floor_min(t)
    if k not in btc.index:
        raise Dropped("btc_bar_missing")
    return float(btc.loc[k])


def event_result(ev: dict, t0: int, launch: pd.DataFrame, exit_tr: pd.DataFrame, kl: pd.DataFrame,
                 fund: pd.DataFrame, btc: pd.Series, origin: str) -> dict:
    """One symbol-event. launch/exit_tr: aggTrades (ts, price, qty, ibm); kl: 1m bars
    (open_time, open, high, low, close); fund: (ts, rate); btc: close by open_time."""
    require_outcome_permission(origin)
    en = vwap(launch, True, t0 + 60 * E.MIN)
    if en is None:
        raise Dropped("no_entry_trades")
    ex = vwap(exit_tr, False, t0 + 72 * E.HOUR)
    if ex is None:
        raise Dropped("no_exit_trades")
    (pe, te), (px, tx) = en, ex
    gross = (pe - px) / pe * 1e4
    fr, nf = funding_sum(fund, te, tx)
    out = {"episode": ev["episode"], "symbol": ev["symbol"], "L_utc": ev["L_utc"],
           "premarket_flag": int(ev["premarket_flag"]), "entry_fallback": int(te != t0 + 60 * E.MIN),
           "exit_fallback": int(tx != t0 + 72 * E.HOUR), "gross_bps": gross, "funding_bps": fr * 1e4,
           "n_settlements": nf}
    for m, b in BUFFER_BPS.items():
        out[f"net_{m}x_bps"] = gross - 2 * TAKER_BPS - 2 * b + fr * 1e4
    out["btc_ret_bps"] = (_btc_close(btc, tx) / _btc_close(btc, te) - 1) * 1e4
    out["net_1x_btcrel_bps"] = out["net_1x_bps"] + out["btc_ret_bps"]
    out.update(exploratory(ev, t0, launch, exit_tr, kl, fund, pe, te, px, tx))
    return out


def exploratory(ev, t0, launch, exit_tr, kl, fund, pe, te, px, tx) -> dict:
    """PREREG §5, descriptive only; 1x costs. NaN where the data window does not reach."""
    c1 = 2 * TAKER_BPS + 2 * BUFFER_BPS[1]
    L, span_end = ev["L_ms"], ev["L_ms"] + E.LAUNCH_SPAN
    x = {}
    for lab, t in (("L5m", L + 5 * E.MIN), ("L24h", L + 24 * E.HOUR)):
        v = vwap(launch, True, t) if t + 2 * E.MIN <= span_end else None
        if v is None:
            x[f"x_entry_{lab}_net_1x_bps"] = np.nan
        else:
            f, _ = funding_sum(fund, v[1], tx)
            x[f"x_entry_{lab}_net_1x_bps"] = (v[0] - px) / v[0] * 1e4 - c1 + f * 1e4
    for lab, h in (("4h", 4), ("24h", 24)):
        t = t0 + h * E.HOUR
        v = vwap(launch, False, t) if t + 2 * E.MIN <= span_end else None
        if v is None:
            x[f"x_hold_{lab}_net_1x_bps"] = np.nan
        else:
            f, _ = funding_sum(fund, te, v[1])
            x[f"x_hold_{lab}_net_1x_bps"] = (pe - v[0]) / pe * 1e4 - c1 + f * 1e4
    x["x_hold_7d_net_1x_bps"] = np.nan  # no data past max(L, T0)+73h was downloaded
    le, ls = vwap(launch, False, t0 + 60 * E.MIN), vwap(exit_tr, True, t0 + 72 * E.HOUR)
    if le is None or ls is None:
        x["x_long_net_1x_bps"] = np.nan
    else:
        f, _ = funding_sum(fund, le[1], ls[1])
        x["x_long_net_1x_bps"] = (ls[0] - le[0]) / le[0] * 1e4 - c1 - f * 1e4
    hold = kl[(kl["open_time"] >= E.floor_min(te)) & (kl["open_time"] <= E.floor_min(tx))]
    x["x_max_adverse_bps"] = (hold["high"].max() / pe - 1) * 1e4 if len(hold) else np.nan
    after = hold[hold["open_time"] > E.floor_min(te)]
    hit = after[after["high"] >= pe * (1 + STOP)]
    f_all, _ = funding_sum(fund, te, tx)
    if len(after) == 0:
        x["x_stop20_net_1x_bps"] = np.nan
    elif hit.empty:
        x["x_stop20_net_1x_bps"] = (pe - px) / pe * 1e4 - c1 + f_all * 1e4
    else:
        b = hit.iloc[0]
        fill = max(pe * (1 + STOP), float(b["open"]))
        f, _ = funding_sum(fund, te, int(b["open_time"]))
        x["x_stop20_net_1x_bps"] = (pe - fill) / pe * 1e4 - c1 + f * 1e4
    return x


# ------------------------------------------------------------------ verdict
def episodes(res: pd.DataFrame, col: str) -> pd.Series:
    return res.groupby("episode")[col].mean()


def episode_days(res: pd.DataFrame) -> pd.Series:
    """Launch day of an episode = UTC day of its earliest usable L."""
    return res.groupby("episode")["L_utc"].min().str[:10].map(dt.date.fromisoformat)


def boot_means(x: np.ndarray, units: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED) -> np.ndarray:
    """Resample units (launch days or 7-day blocks) with replacement; replicate =
    mean over all episodes in the drawn units."""
    u, pos = np.unique(units, return_inverse=True)
    s = np.bincount(pos, weights=x, minlength=len(u))
    c = np.bincount(pos, minlength=len(u)).astype(float)
    idx = np.random.default_rng(seed).integers(0, len(u), size=(n_boot, len(u)))
    return s[idx].sum(1) / c[idx].sum(1)


REQUIRED = ["net_1x_bps", "net_2x_bps", "net_5x_bps", "net_1x_btcrel_bps"]


def check_rows(res: pd.DataFrame) -> None:
    """Fail loud: no usable row may carry a NaN net or BTC-relative net (raise, never drop)."""
    bad = res[res[REQUIRED].isna().any(axis=1)]
    if len(bad):
        raise ValueError(f"NaN in required columns for {len(bad)} rows: {bad['symbol'].tolist()[:10]}")


def verdict(res: pd.DataFrame) -> dict:
    check_rows(res)
    ep = {m: episodes(res, f"net_{m}x_bps") for m in BUFFER_BPS}
    days = episode_days(res).reindex(ep[1].index)
    x1 = ep[1].to_numpy(float)
    d1 = np.array([(d - ORIGIN_DAY).days for d in days])
    d7 = d1 // 7
    n_ep, n_days = len(x1), len(set(d1.tolist()))
    r1, r7 = boot_means(x1, d1), boot_means(x1, d7)
    lb1, lb7 = float(np.percentile(r1, 1)), float(np.percentile(r7, 1))
    ub7 = float(np.percentile(r7, 99))
    rest_without_best5 = np.sort(x1)[:-5] if n_ep > 5 else np.array([])
    btc = episodes(res, "net_1x_btcrel_bps")
    items = {
        "1_sample": {"episodes": n_ep, "launch_days": n_days, "pass": n_ep >= 120 and n_days >= 70},
        "2_mean_1x": {"mean_bps": float(x1.mean()), "lb99_1day_bps": lb1, "lb99_7day_bps": lb7,
                      "pass": bool(x1.mean() >= 100 and lb1 > 0 and lb7 > 0)},
        "3_mean_2x": {"mean_bps": float(ep[2].mean()), "pass": bool(ep[2].mean() > 0)},
        "4_median_1x": {"median_bps": float(np.median(x1)), "pass": bool(np.median(x1) > 0)},
        "5_btc_relative_mean_1x": {"mean_bps": float(btc.mean()), "pass": bool(btc.mean() > 0)},
        "6_mean_1x_without_top5": {"mean_bps": float(rest_without_best5.mean()) if len(rest_without_best5)
                                   else float("nan"),
                                   "pass": bool(len(rest_without_best5) and rest_without_best5.mean() > 0)},
    }
    if not items["1_sample"]["pass"]:
        status = "NOT EVALUABLE"
    else:
        status = "PASS" if all(v["pass"] for v in items.values()) else "KILL"
    return {"status": status, "items": items, "ub99_7day_bps": ub7, "significantly_negative": bool(ub7 < 0),
            "mean_5x_bps": float(ep[5].mean()), "n_boot": N_BOOT, "seed": SEED}


def funding_stress(res: pd.DataFrame, all_rates: np.ndarray) -> dict:
    """Descriptive: every settlement in a hold set to the pooled 95th-percentile
    adverse value for a short (the 5th percentile of all rates in the holds)."""
    q = float(np.percentile(all_rates, 5)) if len(all_rates) else float("nan")
    st = res["net_1x_bps"] - res["funding_bps"] + res["n_settlements"] * q * 1e4
    ep = st.groupby(res["episode"]).mean()
    return {"adverse_rate_p5": q, "mean_net_1x_stress_bps": float(ep.mean()), "episodes": int(len(ep))}
