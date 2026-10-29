"""Point-in-time universe (PREREG §2, CLARIFICATIONS §2): top 80 eligible USDT
perps by mean 1d quote volume over the 7 full days before the event day."""
import datetime as dt
import json

import numpy as np
import pandas as pd

from ca import params as P

EXCLUSIONS_PATH = P.STUDY_DIR / "EXCLUSIONS.json"


class ExclusionsNotFrozen(RuntimeError):
    pass


def load_exclusions(require_frozen: bool = True) -> dict:
    ex = json.loads(EXCLUSIONS_PATH.read_text())
    if require_frozen and ex.get("status") != "FROZEN":
        raise ExclusionsNotFrozen(f"EXCLUSIONS.json status is {ex.get('status')!r}; must be FROZEN before detection")
    return ex


def is_candidate_symbol(symbol: str, exclusions: dict) -> bool:
    suffixes = tuple(exclusions.get("perp_suffixes", ["USDT"]))
    if not symbol.endswith(suffixes) or "_" in symbol:  # USDT-margined perpetuals only (no quarterlies)
        return False
    if any(symbol.startswith(p) for p in exclusions["excluded_prefixes"]):
        return False
    return symbol not in set().union(*exclusions["excluded_symbols"].values())


def check_reviewed(symbols, exclusions: dict) -> None:
    """Every archive symbol must have been seen when the list was made."""
    missing = sorted(set(symbols) - set(exclusions.get("reviewed_symbols", [])))
    if missing:
        raise ExclusionsNotFrozen(f"{len(missing)} symbols not reviewed for exclusion, e.g. {missing[:5]}")


def build_universe(daily: pd.DataFrame, exclusions: dict, days, first_archive_day: dt.date) -> dict:
    """daily: symbol, day (date), quote_volume from 1d klines.
    A symbol's first archive day is a partial (listing) day unless it equals
    first_archive_day (the start of what was downloaded). Returns {day: frozenset}."""
    daily = daily[daily["symbol"].map(lambda s: is_candidate_symbol(s, exclusions))]
    for sym, bad_days in exclusions.get("excluded_days", {}).items():  # e.g. SETTLED/base overlap
        bad = {dt.date.fromisoformat(d) for d in bad_days}
        daily = daily[~((daily["symbol"] == sym) & daily["day"].isin(bad))]
    wide = daily.pivot_table(index="day", columns="symbol", values="quote_volume", aggfunc="sum")
    cal = pd.Index([min(wide.index) + dt.timedelta(days=i)
                    for i in range((max(max(days), max(wide.index)) - min(wide.index)).days + 1)], name="day")
    wide = wide.reindex(cal)
    first = daily.groupby("symbol")["day"].min()
    for sym, d0 in first.items():
        if d0 != first_archive_day:
            wide.loc[d0, sym] = np.nan  # listing day is not a full day
    mean7 = wide.rolling(P.RANK_DAYS, min_periods=P.RANK_DAYS).mean().shift(1)  # days D-7..D-1
    out = {}
    for d in days:
        row = mean7.loc[d].dropna() if d in mean7.index else pd.Series(dtype=float)
        ranked = sorted(row.items(), key=lambda kv: (-kv[1], kv[0]))[: P.UNIVERSE_SIZE]
        out[d] = frozenset(s for s, _ in ranked)
    return out
