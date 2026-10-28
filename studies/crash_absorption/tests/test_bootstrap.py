import datetime as dt

import numpy as np
import pytest

from ca.bootstrap import bootstrap_mean, bootstrap_paired_diff, lower_bound

D = dt.date(2025, 9, 1)


def _days(n):
    return [D + dt.timedelta(days=i) for i in range(n)]


def test_constant_values():
    reps = bootstrap_mean(np.full(30, 0.0015), _days(30), n_boot=200)
    assert np.allclose(reps, 0.0015)


def test_seeded_and_deterministic():
    v, d = np.random.default_rng(0).normal(size=50), _days(50)
    assert np.array_equal(bootstrap_mean(v, d, n_boot=500), bootstrap_mean(v, d, n_boot=500))
    assert not np.array_equal(bootstrap_mean(v, d, n_boot=500), bootstrap_mean(v, d, n_boot=500, seed=1))


def test_whole_days_are_resampled():
    v = [1.0] * 10 + [0.0]
    d = [D] * 10 + [D + dt.timedelta(days=1)]
    reps = bootstrap_mean(v, d, n_boot=2000)
    assert set(np.round(reps, 12)) <= {1.0, round(10 / 11, 12), 0.0}


def test_seven_day_blocks():
    days = _days(14)
    v = [1.0] * 7 + [0.0] * 7
    reps = bootstrap_mean(v, days, block_days=7, n_boot=2000)
    assert set(np.round(reps, 12)) <= {0.0, 0.5, 1.0}
    reps1 = bootstrap_mean(v, days, block_days=1, n_boot=2000)
    assert len(set(np.round(reps1, 12))) > 3


def test_empty_days_via_all_days():
    v, d = [1.0, 3.0], [D, D + dt.timedelta(days=2)]
    reps = bootstrap_mean(v, d, all_days=_days(3), n_boot=3000)
    ok = {round(x, 12) for x in (1.0, 3.0, 2.0, 5 / 3, 7 / 3)}  # multisets of {1, 3, empty day}
    assert set(np.round(reps[np.isfinite(reps)], 12)) <= ok and np.isnan(reps).any()
    with pytest.raises(ValueError):
        bootstrap_mean(v, [D + dt.timedelta(days=9), D], all_days=_days(3), n_boot=10)


def test_paired_difference_same_days():
    rng = np.random.default_rng(1)
    d = [D + dt.timedelta(days=int(k)) for k in rng.integers(0, 40, 300)]
    a = rng.normal(size=300)
    reps = bootstrap_paired_diff(a, d, a - 0.001, d, n_boot=500)
    assert np.allclose(reps, 0.001)


def test_paired_uses_common_days():
    reps = bootstrap_paired_diff([1.0], [D], [0.0], [D + dt.timedelta(days=1)], n_boot=1000)
    finite = reps[np.isfinite(reps)]
    assert len(finite) < 1000 and np.allclose(finite, 1.0)  # replicates missing either side are NaN


def test_lower_bound_levels():
    reps = np.arange(10_000, dtype=float)
    assert lower_bound(reps, 0.999) == pytest.approx(np.percentile(reps, 0.1))
    assert lower_bound(reps, 0.99) == pytest.approx(np.percentile(reps, 1))
    assert lower_bound(reps, 0.95) == pytest.approx(np.percentile(reps, 5))


def test_default_replicates_10000_and_center():
    v = np.random.default_rng(2).normal(0.002, 0.01, 400)
    d = [D + dt.timedelta(days=i % 80) for i in range(400)]
    reps = bootstrap_mean(v, d)
    assert len(reps) == 10_000 and abs(reps.mean() - v.mean()) < 3e-4
