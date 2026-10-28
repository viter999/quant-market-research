"""DEV plumbing: universe -> events -> episodes -> placebos -> fills -> counts
and power projection. No exit, return or outcome is computed here."""
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from ca import params as P
from ca.events import detect_symbol_events, link_episodes, minute_features
from ca.fill import simulate_fill
from ca.placebo import candidate_bars, draw_placebos
from ca.universe import build_universe, check_reviewed, load_exclusions


def segment_days(segment: str) -> list[dt.date]:
    a, b = P.SEGMENTS[segment]
    return [a + dt.timedelta(days=i) for i in range((b - a).days + 1)]


def load_daily(data_dir: Path) -> pd.DataFrame:
    parts = []
    for f in sorted((Path(data_dir) / "klines" / "1d").glob("*.parquet")):
        d = pd.read_parquet(f, columns=["open_time", "quote_volume"])
        parts.append(pd.DataFrame({"symbol": f.stem, "day": [P.ms_to_date(t) for t in d["open_time"]],
                                   "quote_volume": d["quote_volume"].to_numpy()}))
    return pd.concat(parts, ignore_index=True)


def detect(segment: str, features: dict[str, pd.DataFrame], universe: dict, origin: str):
    """Events for all symbols, with event_id and episode. Also returns per-symbol
    placebo candidates (needs all events on the symbol first)."""
    evs = [detect_symbol_events(s, f, universe, segment, origin) for s, f in features.items()]
    ev = pd.concat([e for e in evs if len(e)], ignore_index=True) if any(len(e) for e in evs) else pd.DataFrame()
    if ev.empty:
        return ev, {}
    ev = ev.sort_values(["close_ts", "symbol"], kind="stable").reset_index(drop=True)
    ev["event_id"] = np.arange(len(ev))
    ev["episode"] = link_episodes(ev)
    cands = {(s, segment): candidate_bars(s, f, ev.loc[ev["symbol"] == s, "close_ts"].to_numpy(), universe, segment)
             for s, f in features.items() if s in set(ev["symbol"])}
    return ev, cands


def run_detection(segment: str, data_dir: Path, origin: str):
    """Real-data entry point: refuses unless EXCLUSIONS.json is FROZEN and
    reviewed against every downloaded symbol; segment permission is checked
    by the detector itself."""
    ex = load_exclusions(require_frozen=True)
    daily = load_daily(data_dir)
    check_reviewed(daily["symbol"].unique(), ex)
    days = segment_days(segment)
    from ca.downloader import DOWNLOAD_START
    universe = build_universe(daily, ex, days, DOWNLOAD_START)
    members = set().union(*universe.values())
    feats = {f.stem: minute_features(pd.read_parquet(f, columns=["open_time", "close", "quote_volume"]))
             for f in sorted((Path(data_dir) / "klines" / "1m").glob("*.parquet")) if f.stem in members}
    missing = members - set(feats)
    if missing:
        raise FileNotFoundError(f"1m klines missing for universe members: {sorted(missing)[:5]}")
    ev, cands = detect(segment, feats, universe, origin)
    return ev, draw_placebos(ev, cands) if len(ev) else ev, universe


def fill_table(orders: pd.DataFrame, trades_for, depths=(P.PRIMARY_DEPTH,), latencies=P.LATENCIES_S,
               queues=P.QUEUE_MULTS) -> pd.DataFrame:
    """orders: rows with symbol, close_ts, close (events or placebos).
    trades_for(symbol, close_ts) -> Trades covering the order's window."""
    rows = []
    for i, o in orders.iterrows():
        tr = trades_for(o["symbol"], int(o["close_ts"]))
        for d in depths:
            for lat in latencies:
                for q in queues:
                    f = simulate_fill(tr, int(o["close_ts"]), float(o["close"]), d, lat, q)
                    rows.append({"order": i, "depth": d, "latency_s": lat, "queue": q, "filled": f.filled,
                                 "kind": f.kind, "fill_ts": f.fill_ts})
    return pd.DataFrame(rows)


def power_projection(dev_events: pd.DataFrame, dev_fills: pd.DataFrame) -> dict:
    """§8 power check from DEV counts only (primary spec), scaled by 200/602."""
    prim = dev_fills[(dev_fills["depth"] == P.PRIMARY_DEPTH) & (dev_fills["latency_s"] == P.PRIMARY_LATENCY_S)
                     & (dev_fills["queue"] == P.PRIMARY_QUEUE_MULT) & dev_fills["filled"]]
    filled = dev_events.loc[prim["order"].unique()]
    dev = {"fills": len(prim), "episodes": int(filled["episode"].nunique()), "days": int(filled["day"].nunique())}
    proj = {k: v * P.POWER_SCALE for k, v in dev.items()}
    ok = proj["fills"] >= P.MIN_FILLS and proj["episodes"] >= P.MIN_EPISODES and proj["days"] >= P.MIN_DAYS
    return {"dev": dev, "projected_verdict": proj, "scale": P.POWER_SCALE, "meets_minimum": ok}
