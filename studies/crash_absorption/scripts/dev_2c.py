"""Task 2c (DEV only, no outcomes). Steps, each resumable:
  download1m  DEV 1m klines for universe symbol-months (+ previous month as lookback)
  detect      events, episodes, placebo draws (seed 20261029)
  aggtrades   stream aggTrades windows (-5..+70 min) for event and placebo symbol-days
  fills       FILL engine only + exit-DATA availability (timestamps/sides, no prices)
  report      counts, fill rates, sanity check vs kline low, power projection
Usage: python -I scripts/dev_2c.py <data_dir> <step>"""
import concurrent.futures as cf
import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ca import downloader as DL  # noqa: E402
from ca import inventory as I  # noqa: E402
from ca import params as P  # noqa: E402
from ca.availability import exit_data_available  # noqa: E402
from ca.events import detect_symbol_events, link_episodes, minute_features  # noqa: E402
from ca.fill import kline_touch, simulate_fill  # noqa: E402
from ca.lock import ARCHIVE  # noqa: E402
from ca.pipeline import load_daily, power_projection, segment_days  # noqa: E402
from ca.placebo import candidate_bars, draw_from_matches, match, sanity_sample  # noqa: E402
from ca.trades import Trades  # noqa: E402
from ca.universe import build_universe, check_reviewed, load_exclusions  # noqa: E402

SEG = "dev"


def _dev(d: Path) -> Path:
    out = d / "dev"
    out.mkdir(exist_ok=True)
    return out


def _log(d: Path, step: str, info: dict) -> None:
    path = _dev(d) / "steps.json"
    log = json.loads(path.read_text()) if path.exists() else {}
    log[step] = info
    path.write_text(json.dumps(log, indent=1, default=str, ensure_ascii=False))
    print(json.dumps({step: info}, indent=1, default=str, ensure_ascii=False))


def universe(d: Path) -> dict:
    path = _dev(d) / "universe.json"
    if path.exists():
        raw = json.loads(path.read_text())
        return {dt.date.fromisoformat(k): frozenset(v) for k, v in raw.items()}
    daily = load_daily(d)
    ex = load_exclusions(require_frozen=True)
    check_reviewed(daily["symbol"].unique(), ex)
    uni = build_universe(daily, ex, segment_days(SEG), DL.DOWNLOAD_START)
    path.write_text(json.dumps({str(k): sorted(v) for k, v in uni.items()}, ensure_ascii=False))
    return uni


# ------------------------------------------------------------------ download1m
def download1m(d: Path) -> None:
    t0 = time.time()
    uni = universe(d)
    need: dict[str, set] = {}
    for day, syms in uni.items():
        prev = day.replace(day=1) - dt.timedelta(days=1)
        for s in syms:
            need.setdefault(s, set()).update({f"{day:%Y-%m}", f"{prev:%Y-%m}"})
    inv = json.loads((d / "inventory_klines.json").read_text())["files"]
    plan, listed_bytes = {}, 0
    for s, months in need.items():
        have = {I.period_of(k)[1]: sz for k, sz in inv[s]["1m"] if I.period_of(k)[0] == "monthly"}
        plan[s] = sorted(m for m in months if m in have)
        listed_bytes += sum(have[m] for m in plan[s])
    fetch, errors = DL.HttpFetcher(), {}

    def one(s):
        if (d / "klines" / "1m" / f"{s}.parquet").exists():
            return s, None
        try:
            DL.download_klines(s, "1m", d, fetch, periods=[("monthly", m) for m in plan[s]],
                               columns=["open_time", "high", "low", "close", "quote_volume"])
            return s, None
        except Exception as e:
            return s, f"{type(e).__name__}: {e}"

    with cf.ThreadPoolExecutor(8) as ex:
        for s, err in ex.map(one, sorted(plan)):
            if err:
                errors[s] = err
    pq = sum(f.stat().st_size for f in (d / "klines" / "1m").glob("*.parquet"))
    _log(d, "download1m", {"symbols": len(plan), "symbol_months": sum(map(len, plan.values())),
                           "zip_bytes_listed": listed_bytes, "parquet_bytes": pq, "errors": errors,
                           "seconds": round(time.time() - t0)})


# ------------------------------------------------------------------ detect
def _detect_symbol(args):
    s, path, uni = args
    f = minute_features(pd.read_parquet(path, columns=["open_time", "close", "quote_volume"]))
    ev = detect_symbol_events(s, f, uni, SEG, ARCHIVE)
    if ev.empty:
        return s, ev, {}
    cands = candidate_bars(s, f, ev["close_ts"].to_numpy(), uni, SEG).sort_values("close_ts")
    return s, ev, {int(t): match(row, cands) for t, (_, row) in zip(ev["close_ts"], ev.iterrows())}


def detect(d: Path) -> None:
    t0 = time.time()
    uni = universe(d)
    members = sorted(set().union(*uni.values()))
    jobs = [(s, d / "klines" / "1m" / f"{s}.parquet", uni) for s in members]
    missing = [s for s, p, _ in jobs if not p.exists()]
    if missing:
        raise SystemExit(f"1m klines missing for {missing[:5]}")
    evs, matches = [], {}
    with cf.ProcessPoolExecutor(4) as ex:
        for s, ev, m in ex.map(_detect_symbol, jobs, chunksize=4):
            if len(ev):
                evs.append(ev)
                matches.update({(s, t): v for t, v in m.items()})
    ev = pd.concat(evs, ignore_index=True).sort_values(["close_ts", "symbol"], kind="stable").reset_index(drop=True)
    ev["event_id"] = np.arange(len(ev))
    ev["episode"] = link_episodes(ev)
    pl = draw_from_matches(ev, {r.event_id: matches[(r.symbol, int(r.close_ts))] for r in ev.itertuples()})
    ev.to_parquet(_dev(d) / "events.parquet", index=False)
    pl.to_parquet(_dev(d) / "placebos.parquet", index=False)
    per_event = pl.groupby("event_id").size().reindex(ev["event_id"], fill_value=0)
    month = pd.Series([f"{x:%Y-%m}" for x in ev["day"]])
    _log(d, "detect", {
        "events": len(ev), "episodes": int(ev["episode"].nunique()), "distinct_days": int(ev["day"].nunique()),
        "symbols_with_events": int(ev["symbol"].nunique()), "universe_members": len(members),
        "per_month": month.value_counts().sort_index().to_dict(),
        "top10_symbols": ev["symbol"].value_counts().head(10).to_dict(),
        "placebos": len(pl), "events_with_5": int((per_event == 5).sum()),
        "events_with_1_4": int(((per_event >= 1) & (per_event <= 4)).sum()), "events_with_0": int((per_event == 0).sum()),
        "seconds": round(time.time() - t0)})


# ------------------------------------------------------------------ aggtrades
def _orders(d: Path) -> pd.DataFrame:
    ev = pd.read_parquet(_dev(d) / "events.parquet")
    pl = pd.read_parquet(_dev(d) / "placebos.parquet")
    a = ev[["event_id", "symbol", "close_ts", "close"]].assign(kind="event")
    b = pl[["event_id", "symbol", "close_ts", "close"]].assign(kind="placebo")
    return pd.concat([a, b], ignore_index=True)


def aggtrades(d: Path) -> None:
    t0 = time.time()
    orders = _orders(d)
    jobs = []
    for s, g in orders.groupby("symbol"):
        for day, win in DL.trade_windows(g["close_ts"].to_numpy()).items():
            jobs.append((s, day, win))
    fetch, errors, missing = DL.HttpFetcher(), {}, []

    def one(job):
        s, day, win = job
        if (d / "aggtrades" / s / f"{day.isoformat()}.parquet").exists():
            return job, "ok"
        try:
            return job, "ok" if DL.stream_aggtrades(s, day, win, d, fetch) else "404"
        except Exception as e:
            return job, f"{type(e).__name__}: {e}"

    with cf.ThreadPoolExecutor(8) as ex:
        for (s, day, _), res in ex.map(one, jobs):
            if res == "404":
                missing.append(f"{s} {day}")
            elif res != "ok":
                errors[f"{s} {day}"] = res
    pq = sum(f.stat().st_size for f in (d / "aggtrades").rglob("*.parquet"))
    _log(d, "aggtrades", {"symbol_days": len(jobs), "missing_files_404": missing, "errors": errors,
                          "parquet_bytes": pq, "seconds": round(time.time() - t0)})


# ------------------------------------------------------------------ fills
def _trades_for(d: Path, s: str, ref: int):
    a, b = ref - P.WINDOW_PRE_MIN * P.MINUTE_MS, ref + P.WINDOW_POST_MIN * P.MINUTE_MS
    parts = []
    for day in sorted({P.ms_to_date(a), P.ms_to_date(b)}):
        p = d / "aggtrades" / s / f"{day.isoformat()}.parquet"
        if not p.exists():
            return None
        parts.append(pd.read_parquet(p))
    return Trades.from_frame(pd.concat(parts, ignore_index=True), ARCHIVE)


def fills(d: Path) -> None:
    t0 = time.time()
    orders = _orders(d)
    rows = []
    for s, g in orders.groupby("symbol"):
        for i, o in g.iterrows():
            tr = _trades_for(d, s, int(o["close_ts"]))
            base = {"order": i, "kind_order": o["kind"], "event_id": o["event_id"], "symbol": s}
            if tr is None:
                rows.append({**base, "data_missing": True})
                continue
            for lat in P.LATENCIES_S:
                for q in P.QUEUE_MULTS:
                    f = simulate_fill(tr, int(o["close_ts"]), float(o["close"]), P.PRIMARY_DEPTH, lat, q)
                    r = {**base, "data_missing": False, "latency_s": lat, "queue": q, "filled": f.filled,
                         "fill_kind": f.kind, "fill_ts": f.fill_ts}
                    if f.filled:
                        r.update(exit_data_available(tr.ts, tr.is_buyer_maker, f.fill_ts))
                    rows.append(r)
    ft = pd.DataFrame(rows)
    ft.to_parquet(_dev(d) / "fills.parquet", index=False)
    _log(d, "fills", {"rows": len(ft), "seconds": round(time.time() - t0)})


# ------------------------------------------------------------------ report
def _rates(ft: pd.DataFrame) -> dict:
    out = {}
    ok = ft[~ft["data_missing"]]
    for (lat, q), g in ok.groupby(["latency_s", "queue"]):
        n = len(g)
        fl = g[g["filled"]]
        out[f"lat{int(lat)}s_q{int(q)}x"] = {
            "orders": n, "filled": len(fl), "fill_rate": len(fl) / n if n else None,
            "gap": int((fl["fill_kind"] == "gap").sum()), "maker": int((fl["fill_kind"] == "maker").sum()),
            "cancelled_unfilled": n - len(fl), "cancel_rate": (n - len(fl)) / n if n else None,
            "filled_no_exit_data": int((~fl["available"].astype(bool)).sum()),
            "filled_no_vwap_window_data": int((~fl["vwap_window"].astype(bool)).sum())}
    return out


def report(d: Path) -> None:
    ev = pd.read_parquet(_dev(d) / "events.parquet")
    ft = pd.read_parquet(_dev(d) / "fills.parquet")
    fe, fp = ft[ft["kind_order"] == "event"], ft[ft["kind_order"] == "placebo"]
    # sanity check: 50 DEV events vs the 1m kline low over [live, cancel] (primary spec)
    smp = sanity_sample(ev)
    prim = fe[(fe["latency_s"] == P.PRIMARY_LATENCY_S) & (fe["queue"] == P.PRIMARY_QUEUE_MULT)].set_index("event_id")
    rows = []
    for _, e in smp.iterrows():
        kl = pd.read_parquet(d / "klines" / "1m" / f"{e['symbol']}.parquet", columns=["open_time", "low"])
        L = e["close"] * (1 - P.PRIMARY_DEPTH)
        live = int(e["close_ts"]) + P.PRIMARY_LATENCY_S * 1000
        touch = kline_touch(kl["open_time"].to_numpy(), kl["low"].to_numpy(), live, live + P.CANCEL_AFTER_S * 1000, L)
        r = prim.loc[e["event_id"]] if e["event_id"] in prim.index else None
        filled = None if r is None or bool(r["data_missing"]) else bool(r["filled"])
        rows.append({"event_id": int(e["event_id"]), "symbol": e["symbol"], "close_ts": int(e["close_ts"]),
                     "trade_level_filled": filled, "fill_kind": None if r is None else r.get("fill_kind"),
                     "kline_low_below_L": touch})
    sc = pd.DataFrame(rows)
    disagree = sc[sc["trade_level_filled"] != sc["kline_low_below_L"]]
    # power projection from DEV fill counts (primary spec)
    ev_fills = fe[~fe["data_missing"]].rename(columns={"order": "order_row"}).copy()
    ev_fills["order"] = ev_fills["event_id"]
    ev_fills["depth"] = P.PRIMARY_DEPTH
    pw = power_projection(ev.set_index("event_id", drop=False), ev_fills)
    _log(d, "report", {
        "events_fill_rates": _rates(fe), "placebo_fill_rates": _rates(fp),
        "event_orders_data_missing": int(fe.drop_duplicates("order")["data_missing"].sum()),
        "placebo_orders_data_missing": int(fp.drop_duplicates("order")["data_missing"].sum()),
        "sanity_check": {"n": len(sc), "agree": int(len(sc) - len(disagree)),
                         "disagreements": disagree.to_dict("records")},
        "power_projection": pw})


if __name__ == "__main__":
    d = Path(sys.argv[1])
    {"download1m": download1m, "detect": detect, "aggtrades": aggtrades, "fills": fills,
     "report": report}[sys.argv[2]](d)
