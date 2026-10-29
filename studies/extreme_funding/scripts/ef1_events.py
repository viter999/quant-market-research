"""EF-1 steps 2b-5 (counts only; no prices, no P&L).
  candidates  funding scan (DEV + VERDICT): (symbol, S, f_S, I_S, h_S), interval-change skips
  filters     DEV only: cutoff, universe, spot pair (listing first), spot liquidity, OI, then the
              cap / one-per-symbol simulation with exit TIMES from funding
  report      DEV counts and the power projection
Usage: python -I scripts/ef1_events.py <step>"""
import concurrent.futures as cf
import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

EF = Path(__file__).resolve().parents[1]
CA = EF.parent / "crash_absorption"
sys.path.insert(0, str(EF))
sys.path.insert(0, str(CA))
from ca import downloader as DL  # noqa: E402
from ca import params as P  # noqa: E402
from ef import archive as A  # noqa: E402
from ef import core as C  # noqa: E402
from ef import slices as SL  # noqa: E402

DATA = EF / "data"
CA_DATA = CA / "data"
SLICE_AFTER = 7 * C.DAY + C.HOUR


def log(step: str, info: dict) -> None:
    path = DATA / "steps.json"
    d = json.loads(path.read_text()) if path.exists() else {}
    d[step] = info
    path.write_text(json.dumps(d, indent=1, default=str))
    print(json.dumps({step: info}, indent=1, default=str))


def spot_symbol(perp: str) -> str:
    """<BASE>USDT by name: BASE = perp symbol without the 'USDT' / 'USDTSETTLED' suffix."""
    base = perp[: -len("USDTSETTLED")] if perp.endswith("USDTSETTLED") else perp[: -len("USDT")]
    return base + "USDT"


# ------------------------------------------------------------------ candidates
def load_funding(sym: str) -> pd.DataFrame:
    df = pd.read_parquet(DATA / "funding" / f"{sym}.parquet")[["ts", "rate", "interval_h_archive"]]
    rest = CA_DATA / "funding_rest" / f"{sym}.parquet"
    if rest.exists():
        r = pd.read_parquet(rest)[["ts", "rate"]].assign(interval_h_archive=np.nan)
        df = pd.concat([df, r], ignore_index=True)
    return df.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)


def candidates() -> None:
    t0 = time.time()
    rows = []
    for p in sorted((DATA / "funding").glob("*.parquet")):
        sym = p.stem
        df = load_funding(sym)
        if df.empty:
            continue
        ft = C.funding_table(df[["ts", "rate"]]).merge(df[["ts", "interval_h_archive"]], on="ts", how="left")
        ft["symbol"] = sym
        ft["segment"] = [P.segment_of(P.ms_to_date(int(t))) for t in ft["ts"]]
        rows.append(ft[ft["segment"].isin(["dev", "verdict"])])
    allf = pd.concat(rows, ignore_index=True).rename(columns={"ts": "S", "rate": "f_S"})
    allf.to_parquet(DATA / "settlements.parquet", index=False)
    ev = allf[allf["h_S"] >= C.H_ENTRY]
    ev.to_parquet(DATA / "candidates.parquet", index=False)
    info = {}
    for seg in ("dev", "verdict"):
        a, e = allf[allf["segment"] == seg], ev[ev["segment"] == seg]
        arch = a.dropna(subset=["interval_h_archive"])
        info[seg] = {"settlements": len(a), "symbols": int(a["symbol"].nunique()),
                     "status_counts_all": a["status"].value_counts().to_dict(),
                     "h_ge_threshold": len(e), "h_ge_threshold_by_status": e["status"].value_counts().to_dict(),
                     "events_ok": int((e["status"] == "ok").sum()), "event_symbols_ok": int(e.loc[e["status"] == "ok", "symbol"].nunique()),
                     "interval_change_skips_h_ge_threshold": int((e["status"] == "interval_change").sum()),
                     "I_S_vs_archive_interval_mismatch": int((arch["I_S"] != arch["interval_h_archive"]).sum()),
                     "I_S_values": a["I_S"].value_counts().head(8).to_dict()}
    info["seconds"] = round(time.time() - t0)
    log("candidates", info)


# ------------------------------------------------------------------ DEV filters
def universe(seg: str) -> dict:
    u = json.loads((CA_DATA / seg / "universe.json").read_text())
    return {dt.date.fromisoformat(k): set(v) for k, v in u.items()}


_PERP_CACHE: dict = {}


def perp_minutes(fetch, sym: str, days: list[dt.date]) -> pd.DataFrame:
    """Perp 1m for the given days: crash-absorption DEV parquet where it has the day, else the daily archive file."""
    if sym not in _PERP_CACHE:
        p = CA_DATA / "klines" / "1m" / f"{sym}.parquet"
        _PERP_CACHE[sym] = pd.read_parquet(p) if p.exists() else pd.DataFrame(columns=["open_time", "close", "quote_volume"])
    base = _PERP_CACHE[sym]
    have = set(int(x) for x in np.unique(base["open_time"].to_numpy(np.int64) // P.DAY_MS)) if len(base) else set()
    parts = []
    for d in days:
        k = (d - dt.date(1970, 1, 1)).days
        if k in have:
            parts.append(base[(base["open_time"] // P.DAY_MS) == k])
        else:
            x = SL.get_klines(fetch, DATA / "perp1m", "perp", sym, d)
            if x is not None:
                parts.append(x)
    return pd.concat(parts, ignore_index=True).sort_values("open_time") if parts else pd.DataFrame(columns=["open_time", "close", "quote_volume"])


def spot_minutes(fetch, sym: str, days) -> pd.DataFrame:
    parts = [x for d in days if (x := SL.get_klines(fetch, DATA / "spot1m", "spot", sym, d)) is not None]
    return pd.concat(parts, ignore_index=True).sort_values("open_time") if parts else pd.DataFrame(columns=["open_time", "close", "quote_volume"])


def spot_listing(fetch, spot_syms) -> dict[str, set]:
    """Days with a spot 1m daily file, by date-bounded listing (2023-12-01 .. 2026-03-13)."""
    def one(s):
        keys = [k for pre in A.daily_prefixes(f"data/spot/daily/klines/{s}/1m", f"{s}-1m", dt.date(2023, 12, 1))
                for k, _ in A.list_zips(fetch, pre)]
        return s, {k[-14:-4] for k in keys}
    with cf.ThreadPoolExecutor(16) as ex:
        return dict(ex.map(one, sorted(spot_syms)))


def last_common_minute(spot: pd.DataFrame, perp: pd.DataFrame, a: int, b: int, traded_only: bool = False) -> int | None:
    """min(last spot bar, last perp bar) inside [a, b); None if both run to the end of the slice."""
    def last(df):
        d = df[(df["open_time"] >= a) & (df["open_time"] < b)]
        if traded_only:
            d = d[d["quote_volume"] > 0]
        return int(d["open_time"].max()) if len(d) else a - P.MINUTE_MS
    lc = min(last(spot), last(perp))
    return None if lc >= b - P.MINUTE_MS else lc


def filters() -> None:
    t0 = time.time()
    fetch = DL.HttpFetcher()
    ev = pd.read_parquet(DATA / "candidates.parquet")
    c = ev[(ev["segment"] == "dev") & (ev["status"] == "ok")].sort_values(["S", "symbol"]).reset_index(drop=True)
    drops = {"candidates_ok": len(c)}
    cut = C.segment_cutoff_ms("dev")
    drops["after_entry_cutoff"] = int((c["S"] > cut).sum())
    c = c[c["S"] <= cut]
    uni = universe("dev")
    inu = np.array([r.symbol in uni.get(P.ms_to_date(int(r.S)), set()) for r in c.itertuples()])
    drops["not_in_universe"] = int((~inu).sum())
    c = c[inu].copy()
    c["spot"] = c["symbol"].map(spot_symbol)
    lst = spot_listing(fetch, set(c["spot"]))
    has = np.array([bool({str(d) for d in SL.days_between(int(r.S) - C.DAY, int(r.S) - 1)} & lst[r.spot]) for r in c.itertuples()])
    drops["no_spot_pair_files_24h_before_S"] = int((~has).sum())
    c = c[has].copy()

    # spot liquidity and OI (data up to S only)
    def pre(r):
        S = int(r.S)
        sp = spot_minutes(fetch, r.spot, SL.days_between(S - C.DAY, S - 1))
        liq = C.spot_liquidity(sp, S)
        ms = [m for d in SL.days_between(S - C.OI_LAG_MS - C.DAY, S - C.OI_LAG_MS) if (m := SL.get_metrics(fetch, DATA / "metrics", r.symbol, d)) is not None]
        oi_now, oi_prev = C.oi_rise(pd.concat(ms).sort_values("ts"), S) if ms else (None, None)
        return {**liq, "oi_now": oi_now, "oi_prev": oi_prev}
    with cf.ThreadPoolExecutor(16) as ex:
        feats = list(ex.map(pre, c.itertuples()))
    c = pd.concat([c.reset_index(drop=True), pd.DataFrame(feats)], axis=1)
    sequential = [("spot_no_bars_24h", lambda d: d["bars"] == 0),
                  ("spot_qv24h_lt_5M", lambda d: d["qv_24h"] < C.SPOT_24H_QV_MIN),
                  ("spot_median_1m_qv_lt_50k", lambda d: d["median_1m_qv"] < C.SPOT_MED_1M_QV_MIN),
                  ("oi_missing", lambda d: d["oi_now"].isna() | d["oi_prev"].isna() | (d["oi_prev"] <= 0)),
                  ("oi_rise_lt_5pct", lambda d: d["oi_now"] < C.OI_RISE * d["oi_prev"])]
    for name, rule in sequential:  # each filter is evaluated on the rows that are still in
        bad = rule(c)
        drops[name] = int(bad.sum())
        c = c[~bad]
    drops["signals_after_entry_filters"] = len(c)
    c.to_parquet(DATA / "dev_signals.parquet", index=False)

    # slices S-24h .. S+7d+1h for the survivors: data ends (times only) for the delisting exit
    def ends(r):
        S = int(r.S)
        days = SL.days_between(S - C.DAY, S + SLICE_AFTER)
        sp, pp = spot_minutes(fetch, r.spot, days), perp_minutes(fetch, r.symbol, days)
        return (r.symbol, S), (last_common_minute(sp, pp, S, S + SLICE_AFTER),
                               last_common_minute(sp, pp, S, S + SLICE_AFTER, traded_only=True))
    with cf.ThreadPoolExecutor(8) as ex:
        data_end = dict(ex.map(ends, c.itertuples()))
    fts = {s: C.funding_table(load_funding(s)[["ts", "rate"]]) for s in set(c["symbol"])}
    beyond = []

    def exit_for(sym, S):
        try:
            t, why = C.exit_time(fts[sym], S, data_end[(sym, S)][0])
        except ValueError:  # no exit settlement and the data run to the slice end
            return S + SLICE_AFTER, "unresolved"
        if t > S + SLICE_AFTER:
            beyond.append((sym, S))
        return t, why
    trades, pdrops = C.simulate(c[["symbol", "S", "h_S"]], exit_for)
    for k in ("symbol_open", "cap"):
        drops[k] = int((pdrops["reason"] == k).sum())
    assert drops["signals_after_entry_filters"] == len(trades) + drops["symbol_open"] + drops["cap"]
    trades["entry_day"] = [str(P.ms_to_date(int(s))) for s in trades["S"]]
    trades["delisting_if_traded_bars_only"] = [data_end[(r.symbol, int(r.S))][1] is not None and data_end[(r.symbol, int(r.S))][1] < r.exit_ts
                                              for r in trades.itertuples()]
    trades.to_parquet(DATA / "dev_trades_times.parquet", index=False)
    log("filters_dev", {"drops_in_order": drops, "trades": len(trades), "exit_settlement_beyond_slice": len(beyond),
                        "seconds": round(time.time() - t0)})


# ------------------------------------------------------------------ report
def report() -> None:
    steps = json.loads((DATA / "steps.json").read_text())
    tr = pd.read_parquet(DATA / "dev_trades_times.parquet")
    hold = tr["hold_h"]
    n, syms, days = len(tr), int(tr["symbol"].nunique()), int(tr["entry_day"].nunique())
    scale = P.POWER_SCALE
    proj = {"trades": n * scale, "symbols": syms * scale, "entry_days": days * scale}
    out = {
        "dev": {"trades": n, "symbols": syms, "distinct_entry_days": days,
                "exit_reasons": tr["exit_reason"].value_counts().to_dict(),
                "delisting_exits_if_only_traded_bars_count": int(tr["delisting_if_traded_bars_only"].sum()),
                "hold_hours": {"min": float(hold.min()), "p10": float(hold.quantile(.1)), "median": float(hold.median()),
                               "p90": float(hold.quantile(.9)), "max": float(hold.max()), "mean": float(hold.mean())},
                "hold_hours_hist": {str(k): int(v) for k, v in pd.cut(hold, [0, 8, 24, 72, 168, 1e9], right=True).value_counts().sort_index().items()},
                "max_concurrent_positions": int(C.max_concurrent(tr)), "max_open_in_sim": int(tr["open_after_entry"].max()),
                "drops_in_order": steps["filters_dev"]["drops_in_order"]},
        "power_projection_verdict_x_200_602": proj,
        "power_minimums": {"trades": 60, "symbols": 15, "entry_days": 30},
        "power_meets": bool(proj["trades"] >= 60 and proj["symbols"] >= 15 and proj["entry_days"] >= 30),
        "candidates": steps["candidates"],
    }
    (EF / "results").mkdir(exist_ok=True)
    (EF / "results" / "EF1_FEASIBILITY.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    {"candidates": candidates, "filters": filters, "report": report}[sys.argv[1]]()
