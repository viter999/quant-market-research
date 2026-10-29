import datetime as dt

import numpy as np
import pandas as pd
import pytest

from ca import params as P
from ca.lock import ARCHIVE, OutcomeLocked, SYNTHETIC
from ef import core as C
from ef import pnl as N

H = C.HOUR
T0 = P.date_to_ms(dt.date(2024, 6, 1))


def fund(times_h, rates, jitter_ms=0):
    return pd.DataFrame({"ts": [T0 + int(h * H) + jitter_ms for h in times_h], "rate": rates})


# ---------------- interval change skip and h_S
def test_interval_change_skip_and_h():
    ft = C.funding_table(fund([0, 8, 16, 20, 24, 28], [0.001, 0.001, 0.001, 0.002, 0.002, 0.002]))
    assert ft["status"].tolist() == ["no_history", "no_history", "ok", "interval_change", "ok", "ok"]
    assert ft["I_S"].tolist()[1:] == [8, 8, 4, 4, 4]
    assert ft.loc[2, "h_S"] == pytest.approx(0.001 / 8) and ft.loc[4, "h_S"] == pytest.approx(0.002 / 4)


def test_interval_rounding_absorbs_ms_jitter():
    d = fund([0, 8, 16], [0.001] * 3)
    d.loc[2, "ts"] += 5  # archive fundingTime with +5 ms
    ft = C.funding_table(d)
    assert ft.loc[2, "I_S"] == 8 and ft.loc[2, "status"] == "ok"


def test_threshold_values():
    assert C.H_ENTRY * 8 == pytest.approx(0.001) and C.H_EXIT * 8 == pytest.approx(0.0003)


# ---------------- OI lookup
def test_oi_lookup_last_row_at_or_before_s_minus_5min():
    S = T0 + 10 * H
    ts = [S - 24 * H - 10 * P.MINUTE_MS, S - 24 * H - 5 * P.MINUTE_MS, S - 10 * P.MINUTE_MS, S - 5 * P.MINUTE_MS, S]
    m = pd.DataFrame({"ts": ts, "sum_open_interest": [90.0, 100.0, 104.0, 106.0, 999.0]})
    now, before = C.oi_rise(m, S)
    assert now == 106.0 and before == 100.0  # the row at S itself is not used; rows exactly at the cut are
    assert C.oi_at(m, ts[0] - 1) is None
    m2 = m[m["ts"] != S - 5 * P.MINUTE_MS]
    assert C.oi_rise(m2, S)[0] == 104.0


# ---------------- spot liquidity
def test_spot_liquidity_counts_missing_minutes_as_zero():
    S = T0 + 2 * C.DAY
    ot = S - C.DAY + np.arange(720) * P.MINUTE_MS  # only half the day present
    spot = pd.DataFrame({"open_time": ot, "quote_volume": np.full(720, 10_000.0)})
    r = C.spot_liquidity(spot, S)
    assert r["bars"] == 720 and r["qv_24h"] == pytest.approx(7.2e6) and r["median_1m_qv"] == pytest.approx(5_000.0)


# ---------------- entry cutoff
def test_entry_cutoff_before_segment_end():
    cut = C.segment_cutoff_ms("dev")
    end = P.date_to_ms(P.SEGMENTS["dev"][1] + dt.timedelta(days=1)) - 1
    assert end - cut == 8 * C.DAY
    assert P.ms_to_date(cut) == dt.date(2025, 8, 16)
    assert C.entry_segment(T0) == "dev" and C.entry_segment(P.date_to_ms(dt.date(2025, 8, 25))) is None


# ---------------- exit times (funding only) and delisting
def test_exit_on_low_funding_or_max_hold_or_delisting():
    times = [0] + [8 * k for k in range(1, 30)]
    ft = C.funding_table(fund(times, [0.002] * 3 + [0.0002] + [0.002] * 26))
    S = T0 + 16 * H
    assert C.exit_time(ft, S, None) == (T0 + 24 * H, "funding")              # 0.0002/8h -> h below exit threshold
    ft2 = C.funding_table(fund(times, [0.002] * 30))
    assert C.exit_time(ft2, S, None) == (S + 7 * C.DAY, "max_hold")            # first settlement on/after S+7d
    assert C.exit_time(ft2, S, S + 3 * C.DAY + 5 * P.MINUTE_MS) == (S + 3 * C.DAY + 5 * P.MINUTE_MS, "delisting")
    short = C.funding_table(fund(times[:5], [0.002] * 5))                      # funding stops: no later settlement
    assert C.exit_time(short, T0 + 32 * H, T0 + 40 * H) == (T0 + 40 * H, "delisting")


# ---------------- cap ordering and one position per symbol
def test_cap_ordering_by_h_and_symbol_open():
    S1, S2 = T0, T0 + 8 * H
    sig = pd.DataFrame({"symbol": ["A", "B", "C", "D", "E", "F", "G", "A"],
                        "S": [S1] * 7 + [S2], "h_S": [1, 7, 3, 6, 5, 4, 2, 9]})
    tr, dr = C.simulate(sig, lambda s, S: (S + 24 * H, "funding"))
    assert tr["symbol"].tolist() == ["B", "D", "E", "F", "C"]               # top 5 by h_S at S1
    caps = dr[dr["reason"] == "cap"]
    assert sorted(caps.loc[caps["S"] == S1, "symbol"]) == ["A", "G"]
    assert caps.loc[caps["S"] == S2, "symbol"].tolist() == ["A"]  # still 5 open at S2 (A was never entered)
    assert tr.attrs["max_open"] == 5
    sig2 = pd.DataFrame({"symbol": ["A", "A", "B"], "S": [S1, S2, S2], "h_S": [5, 5, 5]})
    tr2, dr2 = C.simulate(sig2, lambda s, S: (S + 24 * H, "funding"))
    assert dr2.to_dict("records") == [{"symbol": "A", "S": S2, "reason": "symbol_open"}]


def test_exits_free_slots_before_entries_at_same_settlement():
    S1, S2 = T0, T0 + 8 * H
    sig = pd.DataFrame({"symbol": list("ABCDE") + ["F"], "S": [S1] * 5 + [S2], "h_S": [1] * 6})
    tr, dr = C.simulate(sig, lambda s, S: (S2, "funding") if s == "A" else (S + 100 * H, "funding"))
    assert "F" in tr["symbol"].tolist() and dr.empty and C.max_concurrent(tr) == 5


def test_tie_on_h_broken_by_symbol_name():
    sig = pd.DataFrame({"symbol": list("FEDCBA"), "S": [T0] * 6, "h_S": [1.0] * 6})
    tr, _ = C.simulate(sig, lambda s, S: (S + H, "funding"))
    assert tr["symbol"].tolist() == list("ABCDE")


# ---------------- worst-of-bar prices and funding sum (locked; synthetic only)
def _bars(t0, rows):
    return pd.DataFrame({"open_time": [t0 + i * P.MINUTE_MS for i in range(len(rows))],
                         "open": [r[0] for r in rows], "close": [r[1] for r in rows]})


def test_worst_of_bar_prices():
    S = T0 + 8 * H + 5  # settlement with +5 ms jitter -> bar [S+1m, S+2m) on the minute grid
    m0 = T0 + 8 * H
    spot = _bars(m0, [(1, 1), (100.0, 101.0), (5, 5)])
    perp = _bars(m0, [(1, 1), (100.5, 99.5), (5, 5)])
    assert N.entry_prices(spot, perp, S, SYNTHETIC) == (101.0, 99.5)
    assert N.exit_prices(spot, perp, S, SYNTHETIC) == (100.0, 100.5)
    assert N.exit_prices(spot, perp, m0, SYNTHETIC, at_minute=True) == (1, 1)  # delisting: bar at the last common minute


def test_prices_locked_on_real_data(monkeypatch):
    monkeypatch.delenv("CA_RUN_VERDICT", raising=False)
    spot = _bars(T0, [(1, 1)] * 3)
    with pytest.raises(OutcomeLocked):
        N.entry_prices(spot, spot, T0, ARCHIVE)
    with pytest.raises(OutcomeLocked):
        N.funding_received(fund([8], [0.001]), spot, T0, T0 + H, 1.0, ARCHIVE)


def test_funding_sum_on_entry_exit_half_open_interval():
    S, X = T0 + 8 * H, T0 + 32 * H
    f = fund([8, 16, 24, 32, 40], [0.01, 0.02, -0.005, 0.03, 0.5])  # S itself and after X excluded; X included
    perp = pd.DataFrame({"open_time": np.arange(T0, T0 + 48 * H, P.MINUTE_MS)})
    perp["close"] = 100.0 + (perp["open_time"] - T0) / H  # close of bar ending at S_j = 100 + hours - 1/60
    got = N.funding_received(f, perp, S, X, 2.0, SYNTHETIC)
    want = sum(r * 2.0 * (100 + h - 1 / 60) for h, r in [(16, 0.02), (24, -0.005), (32, 0.03)])
    assert got == pytest.approx(want)


def test_trade_pnl_split_and_delisting_buffer():
    r = N.trade_pnl(100, 100.5, 101, 101.2, 5.0, 2.0, 1)
    assert r["spot_leg"] == pytest.approx(5.0) and r["perp_leg"] == pytest.approx(-3.5)
    fees = 0.001 * (500 + 505) + 0.0005 * (502.5 + 506)
    buf = 0.0005 * (500 + 502.5 + 505 + 506)
    assert r["fees"] == pytest.approx(fees) and r["buffer"] == pytest.approx(buf)
    assert r["net"] == pytest.approx(5.0 - 3.5 + 2.0 - fees - buf)
    d = N.trade_pnl(100, 100.5, 101, 101.2, 5.0, 2.0, 1, delisting=True)
    assert d["buffer"] == pytest.approx(0.0005 * (500 + 502.5) + 0.0025 * (505 + 506))
