"""Day-block bootstrap (PREREG §8, CLARIFICATIONS §8). Whole UTC days (or
non-overlapping 7-day blocks) are resampled with replacement; the statistic is
the mean over all rows in the resampled blocks."""
import datetime as dt

import numpy as np

from ca import params as P


def _blocks(days, block_days: int, origin: dt.date) -> np.ndarray:
    return np.array([(d - origin).days // block_days for d in days], dtype=np.int64)


def _sums(values, blocks, units):
    if not np.isin(blocks, units).all():
        raise ValueError("data days outside all_days")
    pos = np.searchsorted(units, blocks)
    s = np.bincount(pos, weights=np.asarray(values, float), minlength=len(units))
    c = np.bincount(pos, minlength=len(units)).astype(float)
    return s, c


def _units(block_arrays, all_days, block_days, origin):
    if all_days is not None:
        return np.unique(_blocks(all_days, block_days, origin))
    return np.unique(np.concatenate(block_arrays))


def bootstrap_mean(values, days, block_days: int = 1, n_boot: int = P.N_BOOT, seed: int = P.SEED_BOOTSTRAP,
                   all_days=None, origin: dt.date | None = None) -> np.ndarray:
    """Replicate means. all_days (optional) = every calendar day of the segment,
    so empty days are resampled too; origin aligns the 7-day blocks (default:
    first day of all_days or of the data)."""
    origin = origin or min(all_days if all_days is not None else days)
    b = _blocks(days, block_days, origin)
    units = _units([b], all_days, block_days, origin)
    s, c = _sums(values, b, units)
    idx = np.random.default_rng(seed).integers(0, len(units), size=(n_boot, len(units)))
    with np.errstate(invalid="ignore", divide="ignore"):
        return s[idx].sum(1) / c[idx].sum(1)


def bootstrap_paired_diff(a_values, a_days, b_values, b_days, block_days: int = 1, n_boot: int = P.N_BOOT,
                          seed: int = P.SEED_BOOTSTRAP, all_days=None, origin: dt.date | None = None) -> np.ndarray:
    """mean(a) - mean(b), both recomputed on the same resampled days per replicate."""
    origin = origin or min(all_days if all_days is not None else list(a_days) + list(b_days))
    ba, bb = _blocks(a_days, block_days, origin), _blocks(b_days, block_days, origin)
    units = _units([ba, bb], all_days, block_days, origin)
    sa, ca_ = _sums(a_values, ba, units)
    sb, cb = _sums(b_values, bb, units)
    idx = np.random.default_rng(seed).integers(0, len(units), size=(n_boot, len(units)))
    with np.errstate(invalid="ignore", divide="ignore"):
        return sa[idx].sum(1) / ca_[idx].sum(1) - sb[idx].sum(1) / cb[idx].sum(1)


def lower_bound(replicates: np.ndarray, level: float) -> float:
    """One-sided percentile lower bound, e.g. level=0.999 -> 0.1th percentile."""
    return float(np.percentile(replicates, 100.0 * (1.0 - level)))
