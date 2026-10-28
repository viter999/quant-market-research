import datetime as dt

import numpy as np
import pytest

from ca.bootstrap import bootstrap_mean, bootstrap_paired_diff, lower_bound

D = dt.date(2025, 9, 1)


def _days(n, start=0):
    return [D + dt.timedelta(days=start + i) for i in range(n)]


def test_constant_values():
    d = _days(30)
    assert np.allclose(bootstrap_mean(np.full(30, 0.0015), d, d, D, n_boot=200), 0.0015)


def test_seeded_and_deterministic():
    v, d = np.random.default_rng(0).normal(size=50), _days(50)
    a = bootstrap_mean(v, d, d, D, n_boot=500)
    assert np.array_equal(a, bootstrap_mean(v, d, d, D, n_boot=500))
    assert not np.array_equal(a, bootstrap_mean(v, d, d, D, n_boot=500, seed=1))


def test_whole_days_are_resampled():
    v = [1.0] * 10 + [0.0]
    d = [D] * 10 + [D + dt.timedelta(days=1)]
    reps = bootstrap_mean(v, d, d, D, n_boot=2000)
    assert set(np.round(reps, 12)) <= {1.0, round(10 / 11, 12), 0.0}


def test_units_are_primary_order_days_only():
    """Fills on days 0 and 2; day 1 has an unfilled order (unit with no rows);
    day 5 has no order and is never a unit."""
    order_days = [D, D + dt.timedelta(days=1), D + dt.timedelta(days=2)]
    reps = bootstrap_mean([1.0, 3.0], [D, D + dt.timedelta(days=2)], order_days, D, n_boot=3000)
    ok = {round(x, 12) for x in (1.0, 3.0, 2.0, 5 / 3, 7 / 3)}
    assert set(np.round(reps[np.isfinite(reps)], 12)) <= ok and np.isnan(reps).any()
    with pytest.raises(ValueError):
        bootstrap_mean([1.0], [D + dt.timedelta(days=5)], order_days, D, n_boot=10)


def test_seven_day_blocks_aligned_to_segment_start_and_need_an_order_day():
    days = _days(14)
    v = [1.0] * 7 + [0.0] * 7
    reps = bootstrap_mean(v, days, days, D, block_days=7, n_boot=2000)
    assert set(np.round(reps, 12)) <= {0.0, 0.5, 1.0}
    # origin shifted by 3 days -> 3 blocks: days 0-3, 4-10, 11-13 relative to D
    reps3 = bootstrap_mean(v, days, days, D - dt.timedelta(days=3), block_days=7, n_boot=4000)
    assert len(set(np.round(reps3, 12))) > 3
    # orders only in days 0..6 -> a single 7-day unit
    reps1 = bootstrap_mean([1.0, 3.0], [D, D + dt.timedelta(days=6)], [D, D + dt.timedelta(days=6)], D,
                           block_days=7, n_boot=100)
    assert np.allclose(reps1, 2.0)


def test_paired_difference_same_days():
    rng = np.random.default_rng(1)
    d = [D + dt.timedelta(days=int(k)) for k in rng.integers(0, 40, 300)]
    a = rng.normal(size=300)
    assert np.allclose(bootstrap_paired_diff(a, d, a - 0.001, d, d, D, n_boot=500), 0.001)


def test_paired_placebos_on_event_day():
    """Placebo rows are passed with their event's day, so they move with it."""
    ev_days = [D, D + dt.timedelta(days=1)]
    reps = bootstrap_paired_diff([1.0, 2.0], ev_days, [0.5, 1.5], ev_days, ev_days, D, n_boot=1000)
    assert np.allclose(reps, 0.5)


def test_lower_bound_levels_and_nan():
    reps = np.arange(10_000, dtype=float)
    assert lower_bound(reps, 0.999) == pytest.approx(np.percentile(reps, 0.1))
    assert lower_bound(reps, 0.99) == pytest.approx(np.percentile(reps, 1))
    assert lower_bound(reps, 0.95) == pytest.approx(np.percentile(reps, 5))
    assert np.isnan(lower_bound(np.array([1.0, np.nan]), 0.95))


def test_default_replicates_10000_and_center():
    v = np.random.default_rng(2).normal(0.002, 0.01, 400)
    d = [D + dt.timedelta(days=i % 80) for i in range(400)]
    reps = bootstrap_mean(v, d, d, D)
    assert len(reps) == 10_000 and abs(reps.mean() - v.mean()) < 3e-4
