import datetime as dt

import numpy as np
import pandas as pd
import pytest

from ca import params as P
from ca.exits import exit_price
from ca.lock import SYNTHETIC
from ca.trades import Trades
from phase0 import core as C
from phase0.stream import COLS, filter_chunks, windows_for

TAU = 1_704_153_600_000 + 3_600_000  # 2024-01-02 01:00:00 UTC


def book(rows):
    """rows: (ts, update_id, bid, bid_qty, ask, ask_qty)"""
    return C.Book.from_frame(pd.DataFrame(rows, columns=["ts", "update_id", "bid", "bid_qty", "ask", "ask_qty"]))


def trades(rows):
    return Trades.from_rows(rows, SYNTHETIC)


# ---------------- quote lookup
def test_last_update_at_or_before_tau():
    b = book([(TAU - 3000, 1, 99, 1, 100, 5), (TAU - 1, 2, 98, 1, 99, 5), (TAU + 1, 3, 90, 1, 91, 5)])
    assert C.quote_at(b, TAU) == 1 and b.ask[C.quote_at(b, TAU)] == 99


def test_update_exactly_at_tau_is_in_force():
    b = book([(TAU - 5, 1, 99, 1, 100, 5), (TAU, 2, 98, 1, 99.5, 5)])
    assert b.ask[C.quote_at(b, TAU)] == 99.5


def test_ties_same_ms_take_highest_update_id():
    b = book([(TAU, 7, 98, 1, 99.0, 5), (TAU, 9, 97, 1, 98.0, 5), (TAU, 8, 96, 1, 97.0, 5)])  # unsorted input
    i = C.quote_at(b, TAU)
    assert b.update_id[i] == 9 and b.ask[i] == 98.0


def test_missing_quote_before_tau():
    b = book([(TAU + 1, 1, 99, 1, 100, 5)])
    assert C.quote_at(b, TAU) == -1
    assert C.real_fill(b, TAU, 99.5, 1.0) == {"status": "no_quote"}
    assert C.quote_at(book([]), TAU) == -1


def test_real_fill_full_partial_none_and_age():
    L, q = 99.5, 5.0
    assert C.real_fill(book([(TAU - 40, 1, 99, 1, 99.4, 5.0)]), TAU, L, q)["status"] == "full"
    assert C.real_fill(book([(TAU - 40, 1, 99, 1, 99.5, 6.0)]), TAU, L, q)["status"] == "full"   # ask == L
    assert C.real_fill(book([(TAU - 40, 1, 99, 1, 99.4, 4.99)]), TAU, L, q)["status"] == "partial"
    r = C.real_fill(book([(TAU - 40, 1, 99, 1, 99.51, 50)]), TAU, L, q)
    assert r["status"] == "none" and r["quote_age_ms"] == 40


# ---------------- proxy / old / exit
def test_proxy_first_buyer_trade_in_one_second():
    L = 99.5
    tr = trades([(TAU - 1, 90.0, 1, False), (TAU + 10, 99.0, 1, True), (TAU + 500, 99.4, 1, False), (TAU + 900, 50.0, 1, False)])
    r = C.proxy_fill(tr, TAU, L)  # seller print at TAU+10 ignored; first buyer print at TAU+500 is 99.4
    assert r["filled"] and r["entry"] == pytest.approx(99.4 * 1.0005) and r["trade_ts"] == TAU + 500
    assert not C.proxy_fill(trades([(TAU + 1001, 90.0, 1, False)]), TAU, L)["filled"]           # outside [tau, tau+1 s]
    assert C.proxy_fill(trades([(TAU + 1000, 90.0, 1, False)]), TAU, L)["filled"]               # boundary inclusive
    assert not C.proxy_fill(trades([(TAU, 99.6, 1, False), (TAU + 5, 90.0, 1, False)]), TAU, L)["filled"]  # first buy > L


def test_old_rule_is_the_frozen_gap_case():
    close_ts, close = TAU - 2000, 100.0
    seller_print = trades([(TAU, 99.0, 1, True)])
    o = C.old_fill(seller_print, close_ts, close, 2)
    assert o["filled"] and o["entry"] == pytest.approx(min(99.0 * 1.0005, 99.5))
    assert not C.proxy_fill(seller_print, TAU, 99.5)["filled"]  # the bid print the proxy no longer accepts
    assert not C.old_fill(trades([(TAU, 99.6, 1, True)]), close_ts, close, 2)["filled"]


@pytest.mark.parametrize("rows", [
    [(0, 100.0, 1.0, True), (5_000, 99.0, 1.0, True), (20_000, 101.0, 3.0, True)],
    [(-61_000, 100.0, 1.0, True), (2_000, 99.0, 2.0, True)],
    [(-60_000, 100.0, 1.0, True)],
    [(-60_001, 100.0, 1.0, True), (10_001, 100.0, 1.0, True)],
    [(-1000, 100.0, 1.0, False), (1000, 100.0, 1.0, False)],
])
def test_exit_proxy_matches_frozen_exit_engine(rows):
    T = TAU + C.HOLD_MS
    tr = trades([(T + dt_, p, q, m) for dt_, p, q, m in rows])
    ref = exit_price(tr, T - C.HOLD_MS, 15)  # locked engine, synthetic data only
    got = C.exit_proxy_price(tr, T)
    assert (got is None and not ref.ok) or got == pytest.approx(ref.price)


# ---------------- stream filter, windows, stats, decision
def _chunk(rows):
    return pd.DataFrame(rows, columns=COLS)


def test_filter_keeps_windows_plus_carry_in():
    day = P.ms_to_date(TAU)
    lo, hi = P.date_to_ms(day), P.date_to_ms(day + dt.timedelta(days=1))
    a, b = TAU - 5000, TAU + 10_000
    c1 = _chunk([(1, 99, 1, 100, 1, TAU - 60_000, 0), (3, 99, 1, 100, 1, TAU - 7000, 0), (2, 99, 1, 100, 1, TAU - 7000, 0)])
    c2 = _chunk([(4, 99, 1, 100, 1, TAU - 4000, 0), (5, 99, 1, 100, 1, TAU + 10_001, 0)])
    df = filter_chunks([c1, c2], [(a, b)], lo, hi, "x")
    assert df["update_id"].tolist() == [3, 4]  # carry-in = latest before a (tie on ts -> highest update_id), then in-window
    bk = C.Book.from_frame(df)
    assert bk.update_id[C.quote_at(bk, a + 500)] == 3  # exact quote in force at a time with no in-window update yet


def test_filter_rejects_wrong_columns_and_units():
    with pytest.raises(Exception):
        filter_chunks([pd.DataFrame({"x": [1]})], [(0, 1)], 0, 1, "x")
    with pytest.raises(Exception):
        filter_chunks([_chunk([(1, 1, 1, 1, 1, TAU * 1000, 0)])], [(0, 1)], TAU - 10, TAU + 10, "x")


def test_windows_split_and_merge():
    mid = P.date_to_ms(dt.date(2024, 1, 3))
    w = windows_for([(mid - 5000, mid + 10_000), (mid + 5000, mid + 20_000), (mid + 100_000, mid + 110_000)])
    assert w[dt.date(2024, 1, 2)] == [(mid - 5000, mid - 1)]
    assert w[dt.date(2024, 1, 3)] == [(mid, mid + 20_000), (mid + 100_000, mid + 110_000)]


def test_confusion_and_decision():
    c = C.confusion([1, 1, 1, 0, 0, 1], [1, 1, 0, 1, 0, 1])
    assert (c["tp"], c["fp"], c["fn"], c["tn"]) == (3, 1, 1, 1) and c["precision"] == 0.75 and c["recall"] == 0.75
    good = {"precision": 0.9, "recall": 0.86}
    assert C.decision(29, good, 0, 0)["decision"] == "NOT ENOUGH DATA"
    assert C.decision(30, good, -5.0, 5.0)["decision"] == "ACCEPTED"
    assert C.decision(30, good, -5.01, 0)["decision"] == "NOT ACCEPTED"
    assert C.decision(30, good, 0, 5.01)["decision"] == "NOT ACCEPTED"
    assert C.decision(30, {"precision": 0.84, "recall": 0.9}, 0, 0)["decision"] == "NOT ACCEPTED"
    assert C.decision(30, {"precision": None, "recall": None}, 0, 0)["decision"] == "NOT ACCEPTED"
    assert C.stats([])["n"] == 0 and C.stats([1, 2, 3])["median"] == 2


def test_no_function_combines_entry_and_exit():
    import inspect
    assert "entry" not in inspect.signature(C.exit_proxy_price).parameters
    assert set(inspect.signature(C.bps).parameters) == {"a", "b"}
