"""Day-block bootstrap (PREREG §8, CLARIFICATIONS v0.3.1/v0.3.2).
Units are whole UTC days (or non-overlapping 7-day blocks aligned to the
segment's first day) that contain >= 1 primary order (event); they are
resampled with replacement and the statistic is the mean over all rows in the
resampled units. Placebo rows carry their EVENT's day."""
import datetime as dt

import numpy as np

from ca import params as P


def _blocks(days, block_days: int, origin: dt.date) -> np.ndarray:
    return np.array([(d - origin).days // block_days for d in days], dtype=np.int64)


def _units(order_days, block_days: int, origin: dt.date) -> np.ndarray:
    if len(order_days) == 0:
        raise ValueError("no primary-order days")
    return np.unique(_blocks(order_days, block_days, origin))


def _sums(values, blocks, units):
    if not np.isin(blocks, units).all():
        raise ValueError("rows on days without a primary order")
    pos = np.searchsorted(units, blocks)
    s = np.bincount(pos, weights=np.asarray(values, float), minlength=len(units))
    c = np.bincount(pos, minlength=len(units)).astype(float)
    return s, c


def _draw(n_units: int, n_boot: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, n_units, size=(n_boot, n_units))


def bootstrap_mean(values, days, order_days, origin: dt.date, block_days: int = 1,
                   n_boot: int = P.N_BOOT, seed: int = P.SEED_BOOTSTRAP) -> np.ndarray:
    """values/days: the rows (e.g. fills, with their event day). order_days: the
    days of all primary orders (defines the resampling units). origin: segment start."""
    units = _units(order_days, block_days, origin)
    s, c = _sums(values, _blocks(days, block_days, origin), units)
    idx = _draw(len(units), n_boot, seed)
    with np.errstate(invalid="ignore", divide="ignore"):
        return s[idx].sum(1) / c[idx].sum(1)


def bootstrap_paired_diff(a_values, a_days, b_values, b_days, order_days, origin: dt.date, block_days: int = 1,
                          n_boot: int = P.N_BOOT, seed: int = P.SEED_BOOTSTRAP) -> np.ndarray:
    """mean(a) - mean(b), both recomputed on the same resampled units per replicate."""
    units = _units(order_days, block_days, origin)
    sa, ca_ = _sums(a_values, _blocks(a_days, block_days, origin), units)
    sb, cb = _sums(b_values, _blocks(b_days, block_days, origin), units)
    idx = _draw(len(units), n_boot, seed)
    with np.errstate(invalid="ignore", divide="ignore"):
        return sa[idx].sum(1) / ca_[idx].sum(1) - sb[idx].sum(1) / cb[idx].sum(1)


def lower_bound(replicates: np.ndarray, level: float) -> float:
    """One-sided percentile lower bound, e.g. level=0.999 -> 0.1th percentile.
    NaN replicates (a resample with no rows) make the bound NaN, which fails any
    '> 0' test; their count is reported by the caller."""
    r = np.asarray(replicates, float)
    if np.isnan(r).any():
        return float("nan")
    return float(np.percentile(r, 100.0 * (1.0 - level)))
