"""Placebo drawer (PREREG §7 B1, CLARIFICATIONS §7) and the sanity-check sample."""
import numpy as np
import pandas as pd

from ca import params as P
from ca.events import bar_day, in_universe_mask, usable_mask


def candidate_bars(symbol: str, f: pd.DataFrame, event_close_ts: np.ndarray, universe: dict,
                   segment: str) -> pd.DataFrame:
    """Bars on `symbol` that may serve as placebo times for an event in `segment`."""
    ok = usable_mask(f, segment) & in_universe_mask(f, symbol, universe)
    for col in ("close", "sigma", "qv60"):
        ok &= np.isfinite(f[col].to_numpy())
    ts = f["close_ts"].to_numpy()
    if len(event_close_ts):
        ev = np.sort(np.asarray(event_close_ts))
        lim = P.PLACEBO_NO_EVENT_MIN * P.MINUTE_MS
        lo = np.searchsorted(ev, ts - lim, side="left")
        hi = np.searchsorted(ev, ts + lim, side="right")
        ok &= hi == lo  # no same-symbol event within ±120 min
    c = f.loc[ok, ["close", "sigma", "qv60", "close_ts"]].reset_index()
    c["day"] = [P.ms_to_date(t) for t in c["open_time"]]
    return c


def _minute_of_day(ts: np.ndarray) -> np.ndarray:
    return (ts % P.DAY_MS) // P.MINUTE_MS


def match(event: pd.Series, cands: pd.DataFrame) -> pd.DataFrame:
    """Candidates matching one event (±3 days, hour ±60 min circular, σ ±25 %,
    60-min quote volume ±50 %), sorted by close_ts. cands must be sorted by close_ts."""
    ts_all = cands["close_ts"].to_numpy()
    lo = np.searchsorted(ts_all, event["close_ts"] - P.PLACEBO_MAX_DAYS * P.DAY_MS, side="left")
    hi = np.searchsorted(ts_all, event["close_ts"] + P.PLACEBO_MAX_DAYS * P.DAY_MS, side="right")
    c = cands.iloc[lo:hi]
    ts = c["close_ts"].to_numpy()
    d = np.abs(_minute_of_day(ts) - _minute_of_day(np.array([event["close_ts"]]))[0])
    hour = np.minimum(d, 1440 - d) <= P.PLACEBO_HOUR_TOL_MIN
    sig = np.abs(c["sigma"].to_numpy() - event["sigma"]) <= P.PLACEBO_SIGMA_TOL * event["sigma"]
    qv = np.abs(c["qv60"].to_numpy() - event["qv60"]) <= P.PLACEBO_QV_TOL * event["qv60"]
    return c[hour & sig & qv]


PLACEBO_COLS = ["event_id", "symbol", "segment", "open_time", "close_ts", "close", "sigma", "qv60",
                "day", "event_day", "n_candidates"]


def draw_from_matches(events: pd.DataFrame, matches: dict, seed: int = P.SEED_PLACEBO) -> pd.DataFrame:
    """matches[event_id] = match(...) result. Events are processed in
    (close_ts, symbol) order with one generator: the draw is a deterministic
    function of the seed and the events."""
    rng = np.random.default_rng(seed)
    rows = []
    for _, ev in events.sort_values(["close_ts", "symbol"], kind="stable").iterrows():
        m = matches[ev["event_id"]]
        k = min(P.N_PLACEBO, len(m))
        if k:
            pick = m.iloc[np.sort(rng.choice(len(m), size=k, replace=False))]
            for _, p in pick.iterrows():
                rows.append({"event_id": ev["event_id"], "symbol": ev["symbol"], "segment": ev["segment"],
                             "open_time": p["open_time"], "close_ts": p["close_ts"], "close": p["close"],
                             "sigma": p["sigma"], "qv60": p["qv60"], "day": p["day"],
                             "event_day": ev["day"], "n_candidates": len(m)})
    return pd.DataFrame(rows, columns=PLACEBO_COLS)


def draw_placebos(events: pd.DataFrame, candidates: dict[tuple[str, str], pd.DataFrame],
                  seed: int = P.SEED_PLACEBO) -> pd.DataFrame:
    """events: detector output with an `event_id` column. candidates[(symbol, segment)]
    from candidate_bars."""
    matches = {ev["event_id"]: match(ev, candidates[(ev["symbol"], ev["segment"])].sort_values("close_ts"))
               for _, ev in events.iterrows()}
    return draw_from_matches(events, matches, seed)


def placebo_counts(events: pd.DataFrame, placebos: pd.DataFrame) -> pd.Series:
    """Placebos per event (0 included), for reporting."""
    return placebos.groupby("event_id").size().reindex(events["event_id"], fill_value=0)


def sanity_sample(dev_events: pd.DataFrame, n: int = P.N_SANITY, seed: int = P.SEED_SANITY) -> pd.DataFrame:
    ev = dev_events.sort_values(["close_ts", "symbol"], kind="stable").reset_index(drop=True)
    rng = np.random.default_rng(seed)
    return ev.iloc[np.sort(rng.choice(len(ev), size=min(n, len(ev)), replace=False))]
