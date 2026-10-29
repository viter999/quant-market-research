import datetime as dt

import numpy as np
import pandas as pd
import pytest

from ca import params as P
from ca.lock import ARCHIVE, OutcomeLocked, SYNTHETIC
from ca.verdict import KILL, NOT_EVALUABLE, PASS, evaluate_holdout, evaluate_verdict

S = dt.date(2025, 8, 26)


def make(n_events=600, n_days=120, fill_rate=0.8, mean=0.004, sd=0.003, pl_mean=0.0, pl_fill=0.8,
         n_pl=5, seed=0, ep_size=2):
    rng = np.random.default_rng(seed)
    day_idx = np.sort(rng.integers(0, n_days, n_events))
    orders = pd.DataFrame({
        "event_id": np.arange(n_events), "day": [S + dt.timedelta(days=int(i)) for i in day_idx],
        "episode": np.arange(n_events) // ep_size, "filled": rng.random(n_events) < fill_rate, "dropped": False,
        "kind": np.where(rng.random(n_events) < 0.1, "gap", "maker")})
    net = rng.normal(mean, sd, n_events)
    orders["net_1x"] = np.where(orders["filled"], net, np.nan)
    orders["net_2x"] = orders["net_1x"] - 0.0005
    pl = pd.DataFrame({"event_id": np.repeat(orders["event_id"], n_pl),
                       "event_day": np.repeat(orders["day"].to_numpy(), n_pl)})
    pl["filled"] = rng.random(len(pl)) < pl_fill
    pl["dropped"] = False
    pl["net_1x"] = np.where(pl["filled"], rng.normal(pl_mean, sd, len(pl)), np.nan)
    return orders, pl


def test_pass_with_item_values():
    o, pl = make()
    r = evaluate_verdict(o, pl, S, SYNTHETIC)
    assert r["verdict"] == PASS
    it = r["items"]
    assert it["1_sample_size"]["fills"] == int(o["filled"].sum()) and it["1_sample_size"]["days"] >= 40
    assert it["2_mean_net_1x"]["mean_net_1x"] == pytest.approx(o["net_1x"].mean())
    assert it["2_mean_net_1x"]["lb999_block1"] > 0 and it["2_mean_net_1x"]["lb999_block7"] > 0
    assert it["3_mean_net_2x"]["mean_net_2x"] == pytest.approx(o["net_2x"].mean())
    assert it["4_beats_placebo"]["per_fill_diff"] >= 0.001 and it["4_beats_placebo"]["per_order_lb99"] > 0
    assert r["counts"]["gap_fills"] == int(((o["kind"] == "gap") & o["filled"]).sum())


def test_deterministic():
    o, pl = make()
    assert evaluate_verdict(o, pl, S, SYNTHETIC) == evaluate_verdict(o, pl, S, SYNTHETIC)


@pytest.mark.parametrize("kw,which", [
    ({"n_events": 300, "fill_rate": 0.9}, "1_sample_size"),        # < 300 fills
    ({"ep_size": 7}, "1_sample_size"),                             # 86 < 100 episodes
    ({"n_days": 30}, "1_sample_size"),                             # < 40 days
])
def test_not_evaluable(kw, which):
    o, pl = make(**kw)
    r = evaluate_verdict(o, pl, S, SYNTHETIC)
    assert r["verdict"] == NOT_EVALUABLE and not r["items"][which]["pass"]


def test_kill_mean_below_15bps():
    o, pl = make(mean=0.0012, sd=0.0005, pl_mean=-0.01)
    r = evaluate_verdict(o, pl, S, SYNTHETIC)
    assert r["verdict"] == KILL and not r["items"]["2_mean_net_1x"]["pass"]
    assert r["items"]["2_mean_net_1x"]["lb999_block1"] > 0  # fails on the point threshold alone


def test_kill_lower_bound():
    o, pl = make(mean=0.0016, sd=0.05, pl_mean=-0.5)
    r = evaluate_verdict(o, pl, S, SYNTHETIC)
    assert r["verdict"] == KILL and r["items"]["2_mean_net_1x"]["lb999_block1"] <= 0


def test_kill_2x():
    o, pl = make()
    o["net_2x"] = o["net_1x"] - 0.004
    r = evaluate_verdict(o, pl, S, SYNTHETIC)
    assert r["verdict"] == KILL and not r["items"]["3_mean_net_2x"]["pass"] and r["items"]["2_mean_net_1x"]["pass"]


def test_kill_placebo_margin():
    o, pl = make(pl_mean=0.0035)  # per-fill diff ~5 bps < 10 bps
    r = evaluate_verdict(o, pl, S, SYNTHETIC)
    i4 = r["items"]["4_beats_placebo"]
    assert r["verdict"] == KILL and not i4["pass"] and i4["per_fill_diff"] < 0.001


def test_kill_per_order_when_placebo_fills_more():
    """Per-fill edge but the event order fills rarely: per order (non-fill = 0) loses to placebo."""
    o, pl = make(fill_rate=0.6, n_events=900, mean=0.0040, pl_mean=0.0028, pl_fill=1.0)
    r = evaluate_verdict(o, pl, S, SYNTHETIC)
    i4 = r["items"]["4_beats_placebo"]
    assert i4["per_fill_diff"] >= 0.001 and i4["per_order_diff"] < 0 and r["verdict"] == KILL


def test_dropped_excluded_and_counted():
    o, pl = make()
    o.loc[o.index[:10], ["filled", "dropped"]] = [True, True]
    o.loc[o.index[:10], "net_1x"] = -1.0  # must not enter any mean
    r = evaluate_verdict(o, pl, S, SYNTHETIC)
    assert r["counts"]["dropped"] == 10
    assert r["items"]["2_mean_net_1x"]["mean_net_1x"] == pytest.approx(o["net_1x"].iloc[10:].mean())


def test_events_without_placebo_excluded_from_comparison_only():
    o, pl = make()
    pl = pl[pl["event_id"] >= 20]
    r = evaluate_verdict(o, pl, S, SYNTHETIC)
    assert r["items"]["4_beats_placebo"]["events_without_placebo"] == 20
    assert r["items"]["4_beats_placebo"]["events_compared"] == len(o) - 20
    assert r["items"]["1_sample_size"]["fills"] == int(o["filled"].sum())


def test_no_fills():
    o, pl = make(fill_rate=0.0)
    assert evaluate_verdict(o, pl, S, SYNTHETIC)["verdict"] == NOT_EVALUABLE


def test_locked_on_real_data(monkeypatch):
    monkeypatch.delenv("CA_RUN_VERDICT", raising=False)
    o, pl = make(n_events=10)
    with pytest.raises(OutcomeLocked):
        evaluate_verdict(o, pl, S, ARCHIVE)
    with pytest.raises(OutcomeLocked):
        evaluate_holdout(o, S, ARCHIVE)


def test_holdout_confirm():
    h = dt.date(2026, 3, 15)
    o, _ = make(mean=0.002, sd=0.003)
    o["day"] = [h + (d - S) for d in o["day"]]
    assert evaluate_holdout(o, h, SYNTHETIC)["confirmed"]
    o2, _ = make(mean=0.0007, sd=0.0001)
    assert not evaluate_holdout(o2, S, SYNTHETIC)["confirmed"]  # below +8 bps
    o3, _ = make(mean=0.001, sd=0.05)
    assert not evaluate_holdout(o3, S, SYNTHETIC)["confirmed"]  # LB <= 0


def test_descriptive_per_order_dropped_as_zero():
    o, pl = make()
    o.loc[o.index[:10], ["filled", "dropped"]] = [True, True]
    o.loc[o.index[:10], "net_1x"] = -1.0
    d = evaluate_verdict(o, pl, S, SYNTHETIC)["descriptive"]
    po = np.where(o["filled"] & ~o["dropped"], o["net_1x"], 0.0)
    assert d["per_order_mean_dropped_as_0"] == pytest.approx(po.mean())
    assert d["per_order_mean_dropped_excluded"] == pytest.approx(po[10:].mean())
