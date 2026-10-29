import datetime as dt

import numpy as np
import pandas as pd
import pytest

from ca import params as P
from ca.events import minute_features
from ca.placebo import candidate_bars, draw_placebos, match, placebo_counts, sanity_sample
from tests.synth import klines, ms, universe_all

D = dt.date(2024, 6, 9)


@pytest.fixture(scope="module")
def setup():
    start = ms(D - dt.timedelta(days=4))
    f = minute_features(klines(start, 9 * 1440, seed=3))
    uni = universe_all(["X"], D - dt.timedelta(days=4), 9)
    t_ev = ms(D, 12, 0)
    ev_row = f.loc[t_ev - P.MINUTE_MS]  # bar opening 11:59 closes 12:00
    events = pd.DataFrame([{"event_id": 0, "symbol": "X", "segment": "dev", "close_ts": t_ev,
                            "sigma": ev_row["sigma"], "qv60": ev_row["qv60"], "day": D}])
    other_event = ms(D, 15, 0)
    cands = candidate_bars("X", f, np.array([t_ev, other_event]), uni, "dev")
    return f, uni, events, cands, other_event


def test_constraints(setup):
    f, uni, events, cands, other = setup
    pl = draw_placebos(events, {("X", "dev"): cands})
    ev = events.iloc[0]
    assert len(pl) == 5 and pl["close_ts"].is_unique
    ts = pl["close_ts"].to_numpy()
    assert np.all(np.abs(ts - ev["close_ts"]) <= 3 * P.DAY_MS)
    mod = (ts % P.DAY_MS) // P.MINUTE_MS
    assert np.all(np.minimum(np.abs(mod - 720), 1440 - np.abs(mod - 720)) <= 60)
    for t_e in (ev["close_ts"], other):
        assert np.all(np.abs(ts - t_e) > 120 * P.MINUTE_MS)
    assert np.all(np.abs(pl["sigma"] / ev["sigma"] - 1) <= 0.25)
    assert np.all(np.abs(pl["qv60"] / ev["qv60"] - 1) <= 0.5)
    assert (pl["n_candidates"] > 5).all() and (pl["segment"] == "dev").all()


def test_deterministic_seed(setup):
    _, _, events, cands, _ = setup
    a = draw_placebos(events, {("X", "dev"): cands})
    b = draw_placebos(events, {("X", "dev"): cands})
    c = draw_placebos(events, {("X", "dev"): cands}, seed=1)
    assert a.equals(b) and not a["close_ts"].equals(c["close_ts"])


def test_candidate_excludes_near_events_and_requires_universe(setup):
    f, _, events, _, _ = setup
    uni = {D: frozenset({"X"})}
    c = candidate_bars("X", f, np.array([ms(D, 12, 0)]), uni, "dev")
    assert set(c["day"]) == {D}
    t = c["close_ts"].to_numpy()
    assert not np.any(np.abs(t - ms(D, 12, 0)) <= 120 * P.MINUTE_MS)
    assert np.any(t == ms(D, 12, 0) + 121 * P.MINUTE_MS)


def _hand_cands(times, sigma=1.0, qv=1.0):
    return pd.DataFrame({"open_time": np.array(times) - P.MINUTE_MS, "close_ts": times, "close": 1.0,
                         "sigma": sigma, "qv60": qv, "day": [P.ms_to_date(t) for t in times]})


def _hand_event(t):
    return pd.DataFrame([{"event_id": 7, "symbol": "X", "segment": "dev", "close_ts": t, "sigma": 1.0,
                          "qv60": 1.0, "day": P.ms_to_date(t)}])


def test_fewer_than_five_and_zero():
    t = ms(D, 12, 0)
    pl = draw_placebos(_hand_event(t), {("X", "dev"): _hand_cands([t + P.DAY_MS, t - P.DAY_MS, t + 2 * P.DAY_MS])})
    assert len(pl) == 3 and (pl["n_candidates"] == 3).all()
    ev0 = _hand_event(t)
    pl0 = draw_placebos(ev0, {("X", "dev"): _hand_cands([t + 4 * P.DAY_MS])})
    assert pl0.empty and placebo_counts(ev0, pl0).tolist() == [0]


def test_tolerance_edges():
    t = ms(D, 12, 0)
    c = pd.concat([_hand_cands([t + P.DAY_MS], sigma=1.25), _hand_cands([t + 2 * P.DAY_MS], sigma=1.26),
                   _hand_cands([t - P.DAY_MS], qv=1.5), _hand_cands([t - 2 * P.DAY_MS], qv=0.49),
                   _hand_cands([t + 3 * P.DAY_MS]), _hand_cands([t + 3 * P.DAY_MS + P.MINUTE_MS])])
    m = match(_hand_event(t).iloc[0], c)
    assert sorted(m["close_ts"]) == sorted([t + P.DAY_MS, t - P.DAY_MS, t + 3 * P.DAY_MS])


def test_hour_of_day_wraps_midnight():
    t = ms(D, 0, 20)
    c = _hand_cands([ms(D - dt.timedelta(days=1), 23, 20), ms(D - dt.timedelta(days=2), 23, 19),
                     ms(D + dt.timedelta(days=1), 1, 20), ms(D + dt.timedelta(days=1), 1, 21)])
    m = match(_hand_event(t).iloc[0], c)
    assert sorted(m["close_ts"]) == sorted([ms(D - dt.timedelta(days=1), 23, 20), ms(D + dt.timedelta(days=1), 1, 20)])


def test_confined_to_segment_and_last_day_cutoff():
    last = P.SEGMENTS["dev"][1]
    f = minute_features(klines(ms(last - dt.timedelta(days=2)), 4 * 1440, seed=5))
    uni = universe_all(["X"], last - dt.timedelta(days=2), 4)
    c = candidate_bars("X", f, np.array([ms(last, 12, 0)]), uni, "dev")
    assert c["day"].max() == last
    assert c.loc[c["day"] == last, "close_ts"].max() == ms(last, 23, 30)


def test_sanity_sample():
    ev = pd.DataFrame({"symbol": ["X"] * 200, "close_ts": np.arange(200) * P.MINUTE_MS})
    a, b = sanity_sample(ev), sanity_sample(ev)
    assert len(a) == 50 and a.equals(b) and a["close_ts"].is_unique
    assert len(sanity_sample(ev.head(10))) == 10


def test_draw_from_matches_equals_draw_placebos(setup):
    _, _, events, cands, _ = setup
    from ca.placebo import draw_from_matches
    m = {0: match(events.iloc[0], cands.sort_values("close_ts"))}
    assert draw_from_matches(events, m).equals(draw_placebos(events, {("X", "dev"): cands}))
