import datetime as dt

import numpy as np
import pandas as pd
import pytest

from ca import params as P
from ca.events import detect_symbol_events, link_episodes, minute_features
from ca.lock import ARCHIVE, OutcomeLocked, SYNTHETIC
from tests.synth import crash, klines, ms, universe_all

DAY = dt.date(2024, 6, 10)
START = ms(DAY, 0, 0)
U = universe_all(["X"], DAY - dt.timedelta(days=1), 5)


def _kl(n=600, **kw):
    return klines(START, n, **kw)


def _events(kl, universe=U, segment="dev", origin=SYNTHETIC):
    return detect_symbol_events("X", minute_features(kl), universe, segment, origin)


def test_basic_event_and_definitions():
    t = START + 400 * P.MINUTE_MS
    kl = crash(_kl(), t, 0.02, 6.0)
    ev = _events(kl)
    assert list(ev["open_time"]) == [t]
    c = kl.set_index("open_time")["close"]
    r = c / c.shift(1) - 1
    assert ev["r"].iloc[0] == pytest.approx(-0.02)
    assert ev["sigma"].iloc[0] == pytest.approx(r.loc[t - 240 * P.MINUTE_MS: t - P.MINUTE_MS].std(ddof=1))
    assert ev["close_ts"].iloc[0] == t + P.MINUTE_MS and ev["day"].iloc[0] == DAY


def test_one_percent_floor():
    t = START + 400 * P.MINUTE_MS
    assert _events(crash(_kl(ret_sd=0.0001), t, 0.009, 10)).empty
    assert len(_events(crash(_kl(ret_sd=0.0001), t, 0.0101, 10))) == 1


def test_four_sigma_rule():
    t = START + 400 * P.MINUTE_MS
    kl = _kl(ret_sd=0.004)
    sig = minute_features(kl).loc[t, "sigma"]
    assert 4 * sig > 0.012
    assert _events(crash(kl, t, 0.012, 10)).empty
    assert len(_events(crash(kl, t, 4 * sig + 0.001, 10))) == 1


def test_volume_rule_5x_inclusive():
    t = START + 400 * P.MINUTE_MS
    assert _events(crash(_kl(), t, 0.02, 4.99)).empty
    assert len(_events(crash(_kl(), t, 0.02, 5.0))) == 1


@pytest.mark.parametrize("gap_offset,expect", [(1, 0), (120, 0), (240, 0), (241, 0), (242, 1), (0, 0)])
def test_missing_bars(gap_offset, expect):
    """A missing bar t-k for k in 0..241 kills the event (t-241 is needed for r_{t-240});
    t-242 does not matter."""
    t = START + 400 * P.MINUTE_MS
    kl = crash(_kl(), t, 0.02, 6.0)
    kl = kl[kl["open_time"] != t - gap_offset * P.MINUTE_MS]
    assert len(_events(kl)) == expect


def test_cooldown_30_min():
    t1 = START + 400 * P.MINUTE_MS
    kl = crash(crash(_kl(), t1, 0.02, 6.0), t1 + 29 * P.MINUTE_MS, 0.02, 6.0)
    assert len(_events(kl)) == 1
    kl = crash(crash(_kl(), t1, 0.02, 6.0), t1 + 30 * P.MINUTE_MS, 0.02, 6.0)
    assert len(_events(kl)) == 2


def test_cutoff_2330_on_last_segment_day():
    last = P.SEGMENTS["dev"][1]  # 2025-08-24
    u = universe_all(["X"], last - dt.timedelta(days=1), 3)
    kl = klines(ms(last, 18, 0), 7 * 60)
    ok = ms(last, 23, 29)    # closes 23:30
    late = ms(last, 23, 30)  # closes 23:31
    assert len(_events(crash(kl, ok, 0.02, 6), u)) == 1
    assert _events(crash(kl, late, 0.02, 6), u).empty


def test_no_cutoff_on_other_days():
    t = ms(DAY, 23, 45)
    kl = crash(klines(ms(DAY, 18, 0), 7 * 60), t, 0.02, 6)
    assert len(_events(kl)) == 1


def test_embargo_day_excluded_from_both_segments():
    emb = dt.date.fromisoformat(P.SPLITS["embargo_1"]["date"])
    u = universe_all(["X"], emb - dt.timedelta(days=1), 3)
    t = ms(emb, 12, 0)
    kl = crash(klines(ms(emb, 6, 0), 8 * 60), t, 0.02, 6)
    assert _events(kl, u, "dev").empty and _events(kl, u, "verdict").empty


def test_universe_filter():
    t = START + 400 * P.MINUTE_MS
    kl = crash(_kl(), t, 0.02, 6.0)
    assert _events(kl, {DAY: frozenset({"Y"})}).empty


def test_segment_lock_for_real_data(monkeypatch):
    monkeypatch.delenv("CA_RUN_VERDICT", raising=False)
    f = minute_features(_kl())
    with pytest.raises(OutcomeLocked):
        detect_symbol_events("X", f, U, "verdict", ARCHIVE)
    with pytest.raises(OutcomeLocked):
        detect_symbol_events("X", f, U, "holdout", ARCHIVE)
    detect_symbol_events("X", f, U, "dev", ARCHIVE)  # DEV detection is allowed


def _ev(minutes, syms):
    return pd.DataFrame({"symbol": syms, "close_ts": [START + m * P.MINUTE_MS for m in minutes]})


def test_episode_single_linkage_chain():
    assert list(link_episodes(_ev([0, 25, 50, 75], ["A", "B", "C", "A"]))) == [0, 0, 0, 0]


def test_episode_gap_boundary():
    assert list(link_episodes(_ev([0, 30, 61], ["A", "B", "C"]))) == [0, 0, 1]


def test_episode_unsorted_input():
    assert list(link_episodes(_ev([100, 0, 10], ["A", "B", "C"]))) == [1, 0, 0]


def test_no_event_before_period_start():
    """Klines from 2023-12 are lookback only."""
    d = dt.date(2023, 12, 31)
    u = universe_all(["X"], d - dt.timedelta(days=1), 4)
    kl = klines(ms(d, 12, 0), 24 * 60)
    assert _events(crash(kl, ms(d, 18, 0), 0.02, 6), u).empty
    assert len(_events(crash(kl, ms(dt.date(2024, 1, 1), 6, 0), 0.02, 6), u)) == 1
