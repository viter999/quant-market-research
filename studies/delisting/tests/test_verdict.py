"""Synthetic unit tests for the trade arithmetic, the funding window, the
verdict items and the outcome lock. No real data is read."""
import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dl import events as E, verdict as V  # noqa: E402
from dl.lock import ARCHIVE, SYNTHETIC, OutcomeLocked  # noqa: E402

S = SYNTHETIC


def ms(*a):
    return int(dt.datetime(*a, tzinfo=dt.timezone.utc).timestamp() * 1000)


def frame(t0, t1, px=100.0):
    t = np.arange(t0, t1, E.MIN)
    return pd.DataFrame({"open": px, "high": px, "low": px, "close": px}, index=pd.Index(t, name="open_time"))


EV = {"symbol": "XUSDT", "episode": "e1", "A_utc": "2024-03-19 05:05:30", "A_ms": ms(2024, 3, 19, 5, 5, 30),
      "D_ms": ms(2024, 3, 21, 9), "N_ms": ms(2024, 3, 21, 8, 30), "restriction_flag": 0}


def world():
    k = frame(ms(2024, 3, 18), ms(2024, 3, 22))
    k.loc[ms(2024, 3, 19, 5, 36), ["open", "close", "low", "high"]] = [100.0, 99.0, 98.0, 101.0]  # entry bar
    k.loc[ms(2024, 3, 21, 8, 0), ["open", "close", "low", "high"]] = [90.0, 91.0, 89.0, 92.0]     # exit bar
    btc = frame(ms(2024, 3, 18), ms(2024, 3, 22), 50000.0)
    btc.loc[ms(2024, 3, 21, 8, 0), "close"] = 51000.0
    fund = pd.DataFrame({"ts": [ms(2024, 3, 19, 0), ms(2024, 3, 19, 5, 36), ms(2024, 3, 20, 8), ms(2024, 3, 21, 8),
                                ms(2024, 3, 21, 16)],
                         "rate": [1.0, 1.0, 0.0003, -0.0001, 1.0]})
    return k, btc, fund


def test_trade_arithmetic_and_funding_window():
    k, btc, fund = world()
    r = V.event_result(EV, k, btc, fund, S)
    gross = (99 - 91) / 99 * 1e4
    assert r["gross_bps"] == pytest.approx(gross)
    assert r["n_funding"] == 2 and r["funding_bps"] == pytest.approx(2.0)  # (entry, exit]: 3 bps - 1 bp
    assert r["net_1x_bps"] == pytest.approx(gross - 10 - 50 + 2)
    assert r["net_2x_bps"] == pytest.approx(gross - 10 - 100 + 2)
    assert r["net_5x_bps"] == pytest.approx(gross - 10 - 250 + 2)
    assert r["btc_ret_bps"] == pytest.approx(200.0)
    assert r["net_1x_btcrel_bps"] == pytest.approx(r["net_1x_bps"] + 200.0)
    assert r["x_bar_extreme_net_1x_bps"] == pytest.approx((98 - 92) / 98 * 1e4 - 60 + 2)
    assert r["x_long_net_1x_bps"] == pytest.approx((90 - 100) / 100 * 1e4 - 60 - 2)


def test_missing_bar_raises():
    k, btc, fund = world()
    with pytest.raises(KeyError):
        V.event_result(EV, k.drop(index=ms(2024, 3, 21, 8, 0)), btc, fund, S)


def test_lock_blocks_real_data(monkeypatch, tmp_path):
    monkeypatch.delenv("DL_RUN_VERDICT", raising=False)
    k, btc, fund = world()
    with pytest.raises(OutcomeLocked):
        V.event_result(EV, k, btc, fund, ARCHIVE)
    p = tmp_path / "x.parquet"
    k.reset_index().to_parquet(p)
    with pytest.raises(OutcomeLocked):
        V.load_prices(p, ARCHIVE)
    monkeypatch.setenv("DL_RUN_VERDICT", "0" * 40)
    with pytest.raises(OutcomeLocked):
        V.load_prices(p, ARCHIVE)


def res_from(ep_values):
    rows = []
    for i, vals in enumerate(ep_values):
        for v in vals:
            rows.append({"episode": f"e{i}", "net_1x_bps": v, "net_2x_bps": v - 50, "net_5x_bps": v - 200,
                         "net_1x_btcrel_bps": v})
    return pd.DataFrame(rows)


def test_verdict_items():
    res = res_from([[200.0, 400.0]] * 20 + [[150.0]] * 15)  # 35 episodes, 55 events, all +150..+300
    v = V.verdict(res)
    assert v["items"]["1_sample"] == {"episodes": 35, "symbol_events": 55, "pass": True}
    assert v["items"]["2_mean_1x"]["mean_bps"] == pytest.approx((20 * 300 + 15 * 150) / 35)
    assert v["status"] == "PASS"
    v = V.verdict(res_from([[200.0]] * 28 + [[200.0] * 20]))  # 29 episodes, 48 events
    assert v["status"] == "NOT EVALUABLE"
    v = V.verdict(res_from([[-30.0]] * 31 + [[1e5]] * 3 + [[50]] * 10))  # mean w/o top 3 = (-930 + 500) / 41
    assert v["items"]["6_mean_1x_without_top3"]["pass"] is False and v["status"] == "KILL"
    v = V.verdict(res_from([[-200.0, -100.0]] * 40))
    assert v["significantly_negative"] is True and v["status"] == "KILL"


def test_bootstrap_deterministic_and_episode_unit():
    x = np.arange(40.0)
    a, b = V.boot_means(x), V.boot_means(x)
    assert np.array_equal(a, b) and len(a) == V.N_BOOT
    res = res_from([[0.0, 0.0, 0.0, 300.0], [100.0]])
    assert list(V.episodes(res)) == [75.0, 100.0]  # episode = mean of its events
