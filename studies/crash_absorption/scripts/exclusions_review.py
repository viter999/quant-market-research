"""Exclusion review rules 2, 3, 5 (director, 2026-10-29). Price-based checks
use 1d klines only. Rule 2 uses DEV days only (<= 2025-08-24); no outcome is
computed. Usage: python -I scripts/exclusions_review.py <data_dir>"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ca import params as P  # noqa: E402

DEV_END = P.SEGMENTS["dev"][1]
EQUITIES = ["TSLAUSDT", "AMZNUSDT", "COINUSDT", "CRCLUSDT", "HOODUSDT", "INTCUSDT", "MSTRUSDT", "PLTRUSDT"]
COLLISIONS = ["ONUSDT", "TUSDT", "ROBOUSDT", "INXUSDT"]
MIN_RETURNS = 30


def load(data_dir, sym):
    d = pd.read_parquet(Path(data_dir) / "klines" / "1d" / f"{sym}.parquet")
    d["day"] = [P.ms_to_date(t) for t in d["open_time"]]
    return d.set_index("day").sort_index()


def daily_returns(d):
    """Close-to-close returns between consecutive calendar days on which the
    symbol traded (quote volume > 0 on the day AND the previous day), v0.3.4."""
    c = d["close"]
    ordinal = np.array([x.toordinal() for x in c.index])
    consecutive = np.r_[False, np.diff(ordinal) == 1][: len(c)]
    qv = d["quote_volume"].to_numpy()
    traded = np.r_[False, (qv[1:] > 0) & (qv[:-1] > 0)][: len(c)]
    return (c / c.shift(1) - 1)[consecutive & traded]


def main(data_dir):
    data_dir = Path(data_dir)
    syms = sorted(f.stem for f in (data_dir / "klines" / "1d").glob("*.parquet"))
    perps = [s for s in syms if (s.endswith("USDT") or s.endswith("USDTSETTLED")) and "_" not in s]
    btc = daily_returns(load(data_dir, "BTCUSDT").loc[:DEV_END])
    rule2, not_eval = [], []
    for s in perps:
        if s == "BTCUSDT":
            continue
        r = daily_returns(load(data_dir, s).loc[:DEV_END]).dropna()
        if len(r) < MIN_RETURNS:
            not_eval.append({"symbol": s, "dev_returns": len(r)})
            continue
        med_abs = float(r.abs().median())
        j = pd.concat([r, btc], axis=1, join="inner").dropna()
        corr = float(j.iloc[:, 0].corr(j.iloc[:, 1])) if len(j) >= MIN_RETURNS else float("nan")
        med_dev = float((j.iloc[:, 0] - j.iloc[:, 1]).abs().median()) if len(j) >= MIN_RETURNS else float("nan")
        why = []
        if med_abs < 0.005:
            why.append("stablecoin-like")
        if corr > 0.98 and med_dev < 0.003:
            why.append("BTC-pegged")
        if why:
            rule2.append({"symbol": s, "why": why, "median_abs_ret": med_abs, "corr_btc": corr,
                          "median_abs_ret_minus_btc": med_dev, "dev_returns": len(r)})
    first_day = {s: load(data_dir, s).index.min() for s in EQUITIES + COLLISIONS}
    eq_first = min(first_day[s] for s in EQUITIES)
    rule3 = {s: {"first_1d_day": str(first_day[s]), "exclude": bool(first_day[s] >= eq_first)} for s in COLLISIONS}
    rule5 = {}
    for s in [x for x in syms if x.endswith("USDTSETTLED")]:
        base = s[: -len("SETTLED")]
        a = load(data_dir, s)
        b = load(data_dir, base) if (data_dir / "klines" / "1d" / f"{base}.parquet").exists() else None
        ov = sorted(set(a.index) & set(b.index)) if b is not None else []
        rule5[s] = {"settled_days": f"{a.index.min()}..{a.index.max()} ({len(a)})",
                    "base_days": f"{b.index.min()}..{b.index.max()} ({len(b)})" if b is not None else None,
                    "overlap_days": [str(d) for d in ov],
                    "overlap_1d_closes_identical": bool(np.allclose(a.loc[ov, "close"], b.loc[ov, "close"], rtol=0, atol=0))
                    if ov else None}
    out = {"rule2_excluded": rule2, "rule2_not_evaluable_on_dev": not_eval,
           "rule3_first_equity_listing_day": str(eq_first), "rule3": rule3, "rule5": rule5}
    (data_dir / "exclusions_review.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items() if k != "rule2_not_evaluable_on_dev"}, indent=1, default=str))
    print("rule2 not evaluable (<30 DEV daily returns):", len(not_eval))


if __name__ == "__main__":
    main(sys.argv[1])
