"""Synthetic unit tests: VWAP sides and fallback, trade arithmetic, funding
window, BTC leg, stop variant, verdict items, block bootstrap and the lock."""
import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lf import events as E, verdict as V  # noqa: E402
from lf.lock import ARCHIVE, SYNTHETIC as S, OutcomeLocked  # noqa: E402

L = int(dt.datetime(2024, 5, 1, 10, tzinfo=dt.timezone.utc).timestamp() * 1000)
T0 = L + 30_000
EV = {"episode": "e1", "symbol": "XUSDT", "L_ms": L, "L_utc": "2024-05-01 10:00:00", "premarket_flag": 0}


def trades(rows):
    return pd.DataFrame(rows, columns=["ts", "price", "qty", "ibm"])


def world():
    e0 = T0 + 60 * E.MIN
    launch = trades([(e0 - 1, 50.0, 1.0, True),            # before the window: ignored
                     (e0 + 10, 100.0, 1.0, True), (e0 + 20, 98.0, 3.0, True),   # seller VWAP 98.5
                     (e0 + 30, 200.0, 5.0, False)])          # buyer: ignored for the short entry
    x0 = T0 + 72 * E.HOUR
    exit_tr = trades([(x0 + 5, 1.0, 9.0, True), (x0 + 70_000, 90.0, 1.0, False)])  # buyer only in the fallback minute
    kl = pd.DataFrame({"open_time": np.arange(E.floor_min(e0), E.floor_min(x0) + E.MIN, E.MIN)})
    kl["open"] = kl["high"] = kl["low"] = kl["close"] = 98.5
    fund = pd.DataFrame({"ts": [e0, e0 + 1, x0 + E.MIN, x0 + E.MIN + 1], "rate": [1.0, 0.001, -0.0004, 1.0]})
    btc = pd.Series(100.0, index=kl["open_time"])
    btc.loc[E.floor_min(x0 + E.MIN)] = 102.0
    return launch, exit_tr, kl, fund, btc


def test_trade_arithmetic():
    la, xt, kl, fu, btc = world()
    r = V.event_result(EV, T0, la, xt, kl, fu, btc, S)
    gross = (98.5 - 90.0) / 98.5 * 1e4
    assert r["gross_bps"] == pytest.approx(gross)
    assert r["exit_fallback"] == 1 and r["entry_fallback"] == 0
    assert r["n_settlements"] == 2 and r["funding_bps"] == pytest.approx(6.0)  # (entry, exit-used] = +10 - 4 bps
    assert r["net_1x_bps"] == pytest.approx(gross - 10 - 30 + 6)
    assert r["net_2x_bps"] == pytest.approx(gross - 10 - 60 + 6)
    assert r["net_5x_bps"] == pytest.approx(gross - 10 - 150 + 6)
    assert r["btc_ret_bps"] == pytest.approx(200.0)
    assert r["net_1x_btcrel_bps"] == pytest.approx(r["net_1x_bps"] + 200.0)


def test_drop_when_no_side_trades():
    la, xt, kl, fu, btc = world()
    with pytest.raises(V.Dropped, match="no_entry_trades"):
        V.event_result(EV, T0, la.assign(ibm=False), xt, kl, fu, btc, S)
    with pytest.raises(V.Dropped, match="no_exit_trades"):
        V.event_result(EV, T0, la, xt.assign(ibm=True), kl, fu, btc, S)


def test_stop_variant_fills_at_worse_of_stop_and_open():
    la, xt, kl, fu, btc = world()
    k = kl.copy()
    k.loc[5, ["open", "high"]] = [130.0, 131.0]   # gap through the 20% stop (118.2)
    r = V.event_result(EV, T0, la, xt, k, fu, btc, S)
    f = 10.0  # only the settlement just after entry precedes the stop bar
    assert r["x_stop20_net_1x_bps"] == pytest.approx((98.5 - 130.0) / 98.5 * 1e4 - 40 + f)
    assert r["x_max_adverse_bps"] == pytest.approx((131.0 / 98.5 - 1) * 1e4)


def test_lock(monkeypatch, tmp_path):
    monkeypatch.delenv("LF_RUN_VERDICT", raising=False)
    la, xt, kl, fu, btc = world()
    with pytest.raises(OutcomeLocked):
        V.event_result(EV, T0, la, xt, kl, fu, btc, ARCHIVE)
    p = tmp_path / "x.parquet"
    la.to_parquet(p)
    for token in (None, "f" * 40):
        if token:
            monkeypatch.setenv("LF_RUN_VERDICT", token)
        with pytest.raises(OutcomeLocked):
            V.load_parquet(p, ARCHIVE)


def res_from(values, day_of=lambda i: i):
    rows = []
    for i, vals in enumerate(values):
        d = (dt.date(2024, 1, 1) + dt.timedelta(days=day_of(i))).isoformat()
        for v in vals:
            rows.append({"episode": f"e{i}", "L_utc": d + " 10:00:00", "net_1x_bps": v, "net_2x_bps": v - 30,
                         "net_5x_bps": v - 120, "net_1x_btcrel_bps": v})
    return pd.DataFrame(rows)


def test_verdict_items_and_counts():
    v = V.verdict(res_from([[300.0, 100.0]] * 130))
    assert v["items"]["1_sample"] == {"episodes": 130, "launch_days": 130, "pass": True} and v["status"] == "PASS"
    v = V.verdict(res_from([[300.0]] * 130, day_of=lambda i: i // 2))   # 65 launch days
    assert v["items"]["1_sample"]["launch_days"] == 65 and v["status"] == "NOT EVALUABLE"
    v = V.verdict(res_from([[-30.0]] * 125 + [[1e6]] * 5))
    assert v["items"]["6_mean_1x_without_top5"]["pass"] is False and v["status"] == "KILL"
    v = V.verdict(res_from([[-300.0, -100.0]] * 130))
    assert v["significantly_negative"] is True


def test_episode_day_is_earliest_L_and_blocks():
    r = res_from([[1.0], [2.0]])
    r.loc[1, "episode"] = "e0"
    assert V.episode_days(r)["e0"] == dt.date(2024, 1, 1)
    x = np.array([1.0, 2.0, 3.0, 10.0])
    a = V.boot_means(x, np.array([0, 0, 1, 1]))
    assert np.array_equal(a, V.boot_means(x, np.array([0, 0, 1, 1])))
    assert set(np.round(np.unique(a), 6)) <= {1.5, 6.5, 4.0}   # whole blocks are drawn


def test_fail_loud_guards():
    la, xt, kl, fu, btc = world()
    with pytest.raises(AssertionError):
        V.event_result(EV, T0, la, xt, kl, fu.assign(rate=[np.nan, 0.001, -0.0004, 1.0]), btc, S)
    r = res_from([[100.0]] * 130).assign(symbol="X")
    r.loc[3, "net_1x_btcrel_bps"] = np.nan
    with pytest.raises(ValueError):
        V.verdict(r)
