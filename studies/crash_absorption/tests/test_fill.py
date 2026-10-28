import numpy as np
import pytest

from ca import params as P
from ca.fill import kline_touch, simulate_fill
from tests.synth import trades

REF = 1_750_000_020_000  # bar close (ms)
CLOSE = 100.0
L = CLOSE * (1 - P.PRIMARY_DEPTH)  # 99.5
QTY = P.NOTIONAL_USD / L
LIVE = REF + 2000
CANCEL = LIVE + 300_000


def test_order_quantity_is_500_over_L():
    f = simulate_fill(trades([(LIVE, 101.0, 1.0, True)]), REF, CLOSE)
    assert f.limit == pytest.approx(99.5) and f.qty == pytest.approx(500 / 99.5)
    assert f.live_ts == LIVE and f.cancel_ts == CANCEL and not f.filled


def test_gap_entry_capped_at_L():
    f = simulate_fill(trades([(LIVE, 99.48, 1.0, True)]), REF, CLOSE)  # 99.48*1.0005 = 99.5297 > L
    assert f.filled and f.kind == "gap" and f.entry == L and f.entry_fee == P.FEE_TAKER and f.fill_ts == LIVE


def test_gap_entry_slippage_when_deep():
    f = simulate_fill(trades([(LIVE + 5, 98.0, 1.0, False)]), REF, CLOSE)
    assert f.kind == "gap" and f.entry == pytest.approx(98.0 * 1.0005)


def test_gap_at_exactly_L():
    f = simulate_fill(trades([(LIVE, L, 1.0, True)]), REF, CLOSE)
    assert f.kind == "gap" and f.entry == L


def test_live_time_inclusive_and_earlier_trades_ignored():
    rows = [(LIVE - 1, 90.0, 1e6, True), (LIVE, 100.5, 1.0, False)]
    f = simulate_fill(trades(rows), REF, CLOSE)
    assert not f.filled  # 1e6 qty below L traded 1 ms before live: ignored; first live trade above L


def test_maker_crossing_inside_one_aggtrade():
    rows = [(LIVE, 100.0, 1.0, False), (LIVE + 10_000, 99.4, 50.0, True), (LIVE + 20_000, 99.3, 60.0, True)]
    f = simulate_fill(trades(rows), REF, CLOSE)  # cum 50 < 100.5, then 110 >= 100.5
    assert f.kind == "maker" and f.fill_ts == LIVE + 20_000 and f.entry == L and f.entry_fee == P.FEE_MAKER


def test_maker_exact_threshold_fills():
    rows = [(LIVE, 100.0, 1.0, False), (LIVE + 1000, 99.0, 20 * QTY, True)]
    assert simulate_fill(trades(rows), REF, CLOSE).fill_ts == LIVE + 1000


def test_trades_at_L_do_not_count_for_maker():
    rows = [(LIVE, 100.0, 1.0, False), (LIVE + 1000, L, 1e6, True)]
    assert not simulate_fill(trades(rows), REF, CLOSE).filled


def test_fill_at_exactly_cancel_time_included():
    rows = [(LIVE, 100.0, 1.0, False), (CANCEL, 99.0, 1000.0, True)]
    f = simulate_fill(trades(rows), REF, CLOSE)
    assert f.filled and f.fill_ts == CANCEL


def test_trade_after_cancel_excluded():
    rows = [(LIVE, 100.0, 1.0, False), (CANCEL + 1, 99.0, 1000.0, True)]
    assert not simulate_fill(trades(rows), REF, CLOSE).filled


def test_gap_after_cancel_is_no_fill():
    assert not simulate_fill(trades([(CANCEL + 1, 90.0, 1.0, True)]), REF, CLOSE).filled


@pytest.mark.parametrize("queue,filled", [(5, True), (10, True), (20, False)])
def test_queue_multiples(queue, filled):
    rows = [(LIVE, 100.0, 1.0, False), (LIVE + 1000, 99.0, 60.0, True)]  # 60 vs 25.1 / 50.3 / 100.5
    assert simulate_fill(trades(rows), REF, CLOSE, queue_mult=queue).filled is filled


def test_queue_multiples_fill_times_differ():
    rows = [(LIVE, 100.0, 1.0, False)] + [(LIVE + 1000 * k, 99.0, 26.0, True) for k in range(1, 5)]
    t = {q: simulate_fill(trades(rows), REF, CLOSE, queue_mult=q).fill_ts for q in (5, 10, 20)}
    assert t == {5: LIVE + 1000, 10: LIVE + 2000, 20: LIVE + 4000}


def test_latencies():
    rows = [(REF + 3000, 99.0, 1.0, True), (REF + 6000, 100.0, 1.0, False), (REF + 11_000, 99.0, 200.0, True)]
    f2, f5, f10 = (simulate_fill(trades(rows), REF, CLOSE, latency_s=s) for s in (2, 5, 10))
    assert (f2.kind, f2.fill_ts) == ("gap", REF + 3000)
    assert (f5.kind, f5.fill_ts) == ("maker", REF + 11_000)
    assert (f10.kind, f10.fill_ts) == ("gap", REF + 11_000)
    assert f10.cancel_ts == REF + 10_000 + 300_000


def test_depths():
    rows = [(LIVE, 100.0, 1.0, False), (LIVE + 1000, 99.6, 1e4, True)]
    assert simulate_fill(trades(rows), REF, CLOSE, depth=0.0025).filled
    assert not simulate_fill(trades(rows), REF, CLOSE, depth=0.005).filled


def test_no_trades():
    assert not simulate_fill(trades([]), REF, CLOSE).filled


def test_same_ms_ties_use_agg_id_order():
    rows = [(LIVE, 100.0, 1.0, False), (LIVE, 99.0, 1.0, True)]  # first by agg_id is above L
    f = simulate_fill(trades(rows), REF, CLOSE)
    assert not f.filled or f.kind != "gap"


def test_kline_touch():
    ot = np.array([REF, REF + 60_000, REF + 360_000])
    low = np.array([99.0, 99.6, 98.0])
    assert kline_touch(ot, low, LIVE, CANCEL, L)          # first bar overlaps [live, cancel]
    assert not kline_touch(ot[1:2], low[1:2], LIVE, CANCEL, L)
    assert not kline_touch(ot[2:], low[2:], LIVE, CANCEL, L)  # opens after cancel
