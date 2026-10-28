import numpy as np
import pytest

from ca import params as P
from ca.exits import Funding, FundingCoverageError, exit_price, net_return, trade_outcome
from ca.fill import simulate_fill
from ca.lock import ARCHIVE, OutcomeLocked
from ca.trades import Trades
from tests.synth import trades

F = 1_750_000_000_000
T = F + 15 * 60_000


def test_both_sources_take_lower():
    rows = [(T - 5000, 100.0, 1.0, True), (T, 99.0, 1.0, True), (T + 10_000, 101.0, 3.0, True)]
    ex = exit_price(trades(rows), F)
    # (a) VWAP over [T, T+10s] = (99*1 + 101*3)/4 = 100.5 ; (b) last seller <= T is the trade at T = 99
    assert ex.ok and ex.exit_ts == T and ex.source == "min" and ex.price == pytest.approx(99.0)


def test_min_picks_vwap_when_lower():
    rows = [(T - 1000, 100.0, 1.0, True), (T + 1000, 98.0, 1.0, True)]
    ex = exit_price(trades(rows), F)
    assert ex.source == "min" and ex.price == pytest.approx(98.0)


def test_only_vwap():
    rows = [(T - 61_000, 100.0, 1.0, True), (T + 2000, 99.0, 2.0, True), (T + 3000, 102.0, 2.0, True)]
    ex = exit_price(trades(rows), F)
    assert ex.source == "vwap" and ex.price == pytest.approx(100.5)


def test_only_last_at_exactly_60s():
    ex = exit_price(trades([(T - 60_000, 100.0, 1.0, True)]), F)
    assert ex.source == "last" and ex.price == 100.0


def test_neither_drops():
    rows = [(T - 60_001, 100.0, 1.0, True), (T + 10_001, 100.0, 1.0, True)]
    ex = exit_price(trades(rows), F)
    assert not ex.ok and ex.source == "drop" and ex.price is None


def test_buyer_initiated_trades_ignored():
    rows = [(T - 1000, 100.0, 1.0, False), (T + 1000, 100.0, 1.0, False)]
    assert exit_price(trades(rows), F).source == "drop"


def test_hold_parameter():
    rows = [(F + 30 * 60_000, 100.0, 1.0, True)]
    assert exit_price(trades(rows), F, hold_min=30).ok
    assert not exit_price(trades(rows), F).ok


def test_lock_refuses_archive_trades(monkeypatch):
    monkeypatch.delenv("CA_RUN_VERDICT", raising=False)
    tr = Trades(np.array([T]), np.array([100.0]), np.array([1.0]), np.array([True]), ARCHIVE)
    with pytest.raises(OutcomeLocked):
        exit_price(tr, F)


def test_lock_refuses_wrong_token(monkeypatch):
    monkeypatch.setenv("CA_RUN_VERDICT", "deadbeef")
    tr = Trades(np.array([T]), np.array([100.0]), np.array([1.0]), np.array([True]), ARCHIVE)
    with pytest.raises(OutcomeLocked):
        exit_price(tr, F)


def _funding(ts, rates):
    return Funding(np.array(ts, dtype=np.int64), np.array(rates), 0, 2 ** 62)


def test_funding_sign_long_pays_positive_receives_negative():
    assert _funding([F + 1000], [0.0001]).paid(F, T) == pytest.approx(0.0001)
    assert _funding([F + 1000], [-0.0002]).paid(F, T) == pytest.approx(-0.0002)
    pos = net_return(100, 100, P.FEE_MAKER, 0.0001, 1)["net"]
    neg = net_return(100, 100, P.FEE_MAKER, -0.0001, 1)["net"]
    assert neg - pos == pytest.approx(0.0002)


def test_funding_boundaries():
    f = _funding([F, T, T + 1], [0.1, 0.01, 1.0])
    assert f.paid(F, T) == pytest.approx(0.01)  # s == fill excluded, s == exit included, after exit excluded


def test_funding_coverage_raises():
    f = Funding(np.array([], dtype=np.int64), np.array([]), 0, T - 1)
    with pytest.raises(FundingCoverageError):
        f.paid(F, T)


@pytest.mark.parametrize("mult,buffer_bps", [(1, 5), (2, 10), (5, 25)])
def test_costs_buffer_scales_fees_do_not(mult, buffer_bps):
    maker = net_return(100.0, 101.0, P.FEE_MAKER, 0.0, mult)
    assert maker["gross"] == pytest.approx(0.01)
    assert maker["net"] == pytest.approx(0.01 - 0.0002 - 0.0005 - buffer_bps * 1e-4)
    taker = net_return(100.0, 101.0, P.FEE_TAKER, 0.0, mult)
    assert taker["net"] == pytest.approx(0.01 - 0.0005 - 0.0005 - buffer_bps * 1e-4)


def test_invalid_buffer_mult():
    with pytest.raises(ValueError):
        net_return(100, 100, P.FEE_MAKER, 0, 3)


def test_trade_outcome_end_to_end_synthetic():
    ref, live = F - 10_000, F - 8000
    rows = [(live, 100.0, 1.0, False), (live + 2000, 99.0, 200.0, True)]  # maker fill at live+2000 = F-6000
    tr_fill = simulate_fill(trades(rows), ref, 100.0)
    fill_ts = tr_fill.fill_ts
    t_exit = fill_ts + 900_000
    rows += [(t_exit - 1000, 100.0, 1.0, True)]
    out = trade_outcome(trades(rows), tr_fill, _funding([fill_ts + 1], [0.0001]))
    assert not out["dropped"] and out["exit_source"] == "last"
    assert out["gross"] == pytest.approx(100.0 / 99.5 - 1)
    assert out["net"] == pytest.approx(100.0 / 99.5 - 1 - 0.0002 - 0.0005 - 0.0005 - 0.0001)


def test_trade_outcome_drop_counted():
    ref = F - 10_000
    rows = [(ref + 2000, 99.0, 1.0, True)]
    fl = simulate_fill(trades(rows), ref, 100.0)
    assert fl.kind == "gap"
    assert trade_outcome(trades(rows), fl, _funding([], [])) == {"dropped": True, "exit_source": "drop"}
