"""PASS / KILL / NOT EVALUABLE (PREREG §8) and the HOLDOUT confirm.
Inputs are per-order outcome tables for the PRIMARY spec (d = 0.5 %, 20x
queue, 2 s latency, 15-min exit), produced by the outcome-locked exit engine:

orders:   event_id, day (event day), episode, filled, dropped, net_1x, net_2x
placebos: event_id, event_day, filled, dropped, net_1x

A dropped fill (no exit price) is excluded from per-fill AND per-order
statistics and counted. Per order, an unfilled order counts as 0."""
import datetime as dt

import numpy as np
import pandas as pd

from ca import params as P
from ca.bootstrap import bootstrap_mean, bootstrap_paired_diff, lower_bound
from ca.lock import require_outcome_permission

PASS, KILL, NOT_EVALUABLE = "PASS", "KILL", "NOT EVALUABLE"


def _per_order(df: pd.DataFrame) -> np.ndarray:
    return np.where(df["filled"], df["net_1x"], 0.0)


def _valid(df: pd.DataFrame) -> pd.DataFrame:
    return df[~(df["filled"] & df["dropped"])]


def _nan_count(reps) -> int:
    return int(np.isnan(reps).sum())


def evaluate_verdict(orders: pd.DataFrame, placebos: pd.DataFrame, segment_start: dt.date, origin: str) -> dict:
    require_outcome_permission(origin)
    order_days = list(orders["day"])
    valid = _valid(orders)
    fills = valid[valid["filled"]]
    out = {"counts": {"orders": len(orders), "fills": len(fills),
                      "gap_fills": None, "dropped": int((orders["filled"] & orders["dropped"]).sum()),
                      "unfilled": int((~orders["filled"]).sum()), "order_days": len(set(order_days))}}

    # 1. sample size
    n_ep, n_days = int(fills["episode"].nunique()), int(fills["day"].nunique())
    i1 = {"fills": len(fills), "episodes": n_ep, "days": n_days,
          "pass": len(fills) >= P.MIN_FILLS and n_ep >= P.MIN_EPISODES and n_days >= P.MIN_DAYS}

    # 2. mean net per fill at 1x, 99.9 % one-sided LB > 0 under 1- and 7-day blocks
    i2 = {"mean_net_1x": float(fills["net_1x"].mean()) if len(fills) else float("nan")}
    for b in (1, 7):
        if len(fills):
            reps = bootstrap_mean(fills["net_1x"], fills["day"], order_days, segment_start, block_days=b)
            i2[f"lb999_block{b}"], i2[f"nan_reps_block{b}"] = lower_bound(reps, P.PASS_LB_LEVEL), _nan_count(reps)
        else:
            i2[f"lb999_block{b}"], i2[f"nan_reps_block{b}"] = float("nan"), None
    i2["pass"] = bool(i2["mean_net_1x"] >= P.PASS_MEAN_1X and i2["lb999_block1"] > 0 and i2["lb999_block7"] > 0)

    # 3. mean net per fill at 2x
    m2 = float(fills["net_2x"].mean()) if len(fills) else float("nan")
    i3 = {"mean_net_2x": m2, "pass": bool(m2 >= P.PASS_MEAN_2X)}

    # 4. beats placebo (events with >= 1 placebo only; placebos on their event's day; 1-day blocks)
    with_pl = set(placebos["event_id"])
    ev = valid[valid["event_id"].isin(with_pl)]
    pl = _valid(placebos)
    ev_f, pl_f = ev[ev["filled"]], pl[pl["filled"]]
    i4 = {"events_compared": len(ev), "events_without_placebo": int((~orders["event_id"].isin(with_pl)).sum()),
          "placebo_orders": len(pl), "placebo_fills": len(pl_f)}
    if len(ev_f) and len(pl_f):
        d_fill = float(ev_f["net_1x"].mean() - pl_f["net_1x"].mean())
        reps = bootstrap_paired_diff(ev_f["net_1x"], ev_f["day"], pl_f["net_1x"], pl_f["event_day"],
                                     order_days, segment_start)
        lb_fill, nan_fill = lower_bound(reps, P.PASS_PLACEBO_LB_LEVEL), _nan_count(reps)
    else:
        d_fill, lb_fill, nan_fill = float("nan"), float("nan"), None
    if len(ev) and len(pl):
        d_order = float(_per_order(ev).mean() - _per_order(pl).mean())
        reps = bootstrap_paired_diff(_per_order(ev), ev["day"], _per_order(pl), pl["event_day"],
                                     order_days, segment_start)
        lb_order, nan_order = lower_bound(reps, P.PASS_PLACEBO_LB_LEVEL), _nan_count(reps)
    else:
        d_order, lb_order, nan_order = float("nan"), float("nan"), None
    i4.update({"per_fill_diff": d_fill, "per_fill_lb99": lb_fill, "per_fill_nan_reps": nan_fill,
               "per_order_diff": d_order, "per_order_lb99": lb_order, "per_order_nan_reps": nan_order,
               "pass": bool(d_fill >= P.PASS_PLACEBO_MARGIN and lb_fill > 0 and d_order > 0 and lb_order > 0)})

    items = {"1_sample_size": i1, "2_mean_net_1x": i2, "3_mean_net_2x": i3, "4_beats_placebo": i4}
    if not i1["pass"]:
        verdict = NOT_EVALUABLE
    elif all(it["pass"] for it in items.values()):
        verdict = PASS
    else:
        verdict = KILL
    # descriptive (v0.3.3): per-order mean with dropped fills counted as 0
    po_all = np.where(orders["filled"] & ~orders["dropped"], orders["net_1x"], 0.0)
    out["descriptive"] = {"per_order_mean_dropped_as_0": float(po_all.mean()) if len(orders) else float("nan"),
                          "per_order_mean_dropped_excluded": float(_per_order(valid).mean()) if len(valid) else float("nan")}
    out.update({"verdict": verdict, "items": items})
    if "kind" in orders.columns:
        out["counts"]["gap_fills"] = int((fills["kind"] == "gap").sum())
    return out


def evaluate_holdout(orders: pd.DataFrame, segment_start: dt.date, origin: str) -> dict:
    """HOLDOUT confirm: mean net per fill at 1x >= +8 bps and 95 % LB > 0 (1-day blocks)."""
    require_outcome_permission(origin)
    fills = _valid(orders)
    fills = fills[fills["filled"]]
    mean = float(fills["net_1x"].mean()) if len(fills) else float("nan")
    lb = lower_bound(bootstrap_mean(fills["net_1x"], fills["day"], list(orders["day"]), segment_start),
                     P.HOLDOUT_LB_LEVEL) if len(fills) else float("nan")
    ok = bool(mean >= P.HOLDOUT_MEAN_1X and lb > 0)
    return {"fills": len(fills), "mean_net_1x": mean, "lb95": lb, "confirmed": ok}
