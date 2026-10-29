"""The single VERDICT runner (PREREG §3–§8, CLARIFICATIONS v0.3.1–v0.3.4).

run() does, in order, and refuses to start unless every precondition holds:
  0. preconditions: (archive data) CA_RUN_VERDICT == clean HEAD; funding manifest
     sha256 == the expected value and every listed file matches its sha256;
     run-once lock not present; funding coverage for every universe member-day
  1. universe (1d quote volume, frozen exclusions)
  2. detection on VERDICT, episodes, placebo draws (seed 20261029)
  3. aggTrades stream for event and placebo windows (-5..+70 min)
  4. fills (primary + exploratory grid), exits, B2
  5. verdict.py (PASS / KILL / NOT EVALUABLE) + report with EXPLORATORY tables
The same code runs on synthetic data (origin=SYNTHETIC) for the dry run."""
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from ca import downloader as DL
from ca import params as P
from ca.events import detect_symbol_events, link_episodes, minute_features
from ca.exits import trade_outcome
from ca.fill import b2_entry, simulate_fill
from ca.lock import ARCHIVE, SYNTHETIC, _git, verdict_unlocked
from ca.placebo import candidate_bars, draw_from_matches, match
from ca.trades import Trades
from ca.universe import build_universe, check_reviewed, load_exclusions
from ca.verdict import evaluate_verdict

SEG = "verdict"
LIMIT_MS = P.date_to_ms(P.SEGMENTS[SEG][1] + dt.timedelta(days=1)) - 1  # 2026-03-13 23:59:59.999 (guard)
HOLDS = (15, 30, 60)
GRID = [(d, l, q) for d in P.DEPTHS for l in P.LATENCIES_S for q in P.QUEUE_MULTS]
PRIMARY = (P.PRIMARY_DEPTH, P.PRIMARY_LATENCY_S, P.PRIMARY_QUEUE_MULT)


class RefuseToRun(RuntimeError):
    pass


@dataclass
class Source:
    """Data in the study layout under data_dir (real or synthetic)."""
    data_dir: Path
    origin: str
    fetcher: object = None
    exclusions: dict | None = None          # None -> frozen EXCLUSIONS.json (+ review check)
    funding_symbols: list | None = None     # None -> funding_rest_symbols.json
    workers: int = 4
    extra: dict = field(default_factory=dict)

    @property
    def vdir(self) -> Path:
        return self.data_dir / "verdict"

    def daily(self) -> pd.DataFrame:
        from ca.pipeline import load_daily
        return load_daily(self.data_dir)

    def get_exclusions(self, daily: pd.DataFrame) -> dict:
        if self.exclusions is not None:
            return self.exclusions
        ex = load_exclusions(require_frozen=True)
        check_reviewed(daily["symbol"].unique(), ex)
        return ex

    def get_funding_symbols(self) -> list:
        if self.funding_symbols is not None:
            return self.funding_symbols
        return json.loads((P.STUDY_DIR / "funding_rest_symbols.json").read_text())["symbols"]

    def minute_path(self, s: str) -> Path:
        return self.vdir / "klines" / "1m" / f"{s}.parquet"


# ----------------------------------------------------------------- preconditions
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_funding_manifest(data_dir: Path, expected_sha: str | None, symbols: list) -> dict:
    man = data_dir / "funding_rest_manifest.json"
    if not man.exists():
        raise RefuseToRun(f"funding manifest missing: {man}")
    got = sha256_file(man)
    if not expected_sha or got != expected_sha:
        raise RefuseToRun(f"funding manifest sha256 {got} != expected {expected_sha!r} (CA_FUNDING_SHA256)")
    files = json.loads(man.read_text())["files"]
    for rel, sha in files.items():
        p = data_dir / rel
        if not p.exists() or sha256_file(p) != sha:
            raise RefuseToRun(f"funding file missing or sha256 mismatch: {rel}")
    for sub in ("funding_rest", "funding_seam"):
        missing = [s for s in symbols if f"{sub}/{s}.parquet" not in files]
        if missing:
            raise RefuseToRun(f"funding manifest lacks {sub} for {len(missing)} symbols, e.g. {missing[:5]}")
    return {"manifest_sha256": got, "files": len(files)}


def member_spans(uni: dict, traded: set | None = None) -> dict[str, list[tuple[int, int]]]:
    """[day start, min(next day 02:00, VERDICT end)] per member day; with `traded`,
    only member days on which the symbol has 1d quote volume > 0 (no order can
    fill, and so no funding is needed, on a zero-volume day)."""
    spans: dict[str, list] = {}
    for day, syms in uni.items():
        a = P.date_to_ms(day)
        b = min(a + P.DAY_MS + 2 * 3600_000, LIMIT_MS)
        for s in syms:
            if traded is None or (s, day) in traded:
                spans.setdefault(s, []).append((a, b))
    return spans


def check_funding_coverage(src: Source, uni: dict, daily: pd.DataFrame) -> dict:
    traded = {(r.symbol, r.day) for r in daily.itertuples() if r.quote_volume > 0}
    gaps = {}
    for s, spans in member_spans(uni, traded).items():
        cover = DL.load_funding(s, src.data_dir).cover
        bad = [str(P.ms_to_date(a)) for a, b in spans if not any(ca <= a and b <= cb for ca, cb in cover)]
        if bad:
            gaps[s] = bad
    if gaps:
        raise RefuseToRun(f"funding coverage gaps for {len(gaps)} symbols: "
                          f"{dict(list(gaps.items())[:3])}")
    n_all = sum(len(v) for v in uni.values())
    return {"member_days": n_all, "zero_volume_member_days_skipped": n_all - sum(map(len, member_spans(uni, traded).values()))}


def preconditions(src: Source, out_dir: Path, expected_funding_sha: str | None) -> dict:
    info = {"origin": src.origin}
    if src.origin != SYNTHETIC:
        if not verdict_unlocked():
            raise RefuseToRun("CA_RUN_VERDICT must equal the current, clean git HEAD")
        info["code_head"] = _git("rev-parse", "HEAD")
    info["funding"] = check_funding_manifest(src.data_dir, expected_funding_sha, src.get_funding_symbols())
    lock = out_dir / "VERDICT_RUN_STARTED.json"
    if lock.exists():
        raise RefuseToRun(f"VERDICT already started ({lock}); it runs once")
    return info


# ----------------------------------------------------------------- detection
def _detect(args):
    s, path, uni = args
    f = minute_features(pd.read_parquet(path, columns=["open_time", "close", "quote_volume"]))
    ev = detect_symbol_events(s, f, uni, SEG, args_origin[0])
    if ev.empty:
        return s, ev, {}
    cands = candidate_bars(s, f, ev["close_ts"].to_numpy(), uni, SEG).sort_values("close_ts")
    return s, ev, {int(t): match(row, cands) for t, (_, row) in zip(ev["close_ts"], ev.iterrows())}


args_origin = [ARCHIVE]  # set per process via initializer


def _init(origin):
    args_origin[0] = origin


def _pool(src: Source):
    if src.workers > 1:
        return cf.ProcessPoolExecutor(src.workers, initializer=_init, initargs=(src.origin,))
    _init(src.origin)
    return cf.ThreadPoolExecutor(1)


def detect(src: Source, uni: dict):
    members = sorted(set().union(*uni.values()))
    missing = [s for s in members if not src.minute_path(s).exists()]
    if missing:
        raise RefuseToRun(f"VERDICT 1m klines missing for {missing[:5]}")
    evs, matches = [], {}
    with _pool(src) as ex:
        for s, ev, m in ex.map(_detect, [(s, src.minute_path(s), uni) for s in members]):
            if len(ev):
                evs.append(ev)
                matches.update({(s, t): v for t, v in m.items()})
    if not evs:
        return pd.DataFrame(), pd.DataFrame()
    ev = pd.concat(evs, ignore_index=True).sort_values(["close_ts", "symbol"], kind="stable").reset_index(drop=True)
    ev["event_id"] = np.arange(len(ev))
    ev["episode"] = link_episodes(ev)
    pl = draw_from_matches(ev, {r.event_id: matches[(r.symbol, int(r.close_ts))] for r in ev.itertuples()})
    return ev, pl


# ----------------------------------------------------------------- aggTrades
def clip_windows(windows: dict) -> dict:
    """Drop/clip trade windows past the VERDICT end (the guard refuses those files)."""
    out = {}
    for day, win in windows.items():
        kept = [(a, min(b, LIMIT_MS)) for a, b in win if a <= LIMIT_MS]
        if kept:
            out[day] = kept
    return out


def beyond_end(fill_ts: int, hold_min: float) -> bool:
    """Exit window [T, T+10 s] would reach past the VERDICT end (exploratory long holds only)."""
    return fill_ts + hold_min * P.MINUTE_MS + P.EXIT_VWAP_S * 1000 > LIMIT_MS


def fetch_trades(src: Source, orders: pd.DataFrame) -> dict:
    jobs = [(s, day, win) for s, g in orders.groupby("symbol")
            for day, win in clip_windows(DL.trade_windows(g["close_ts"].to_numpy())).items()]
    fetch = src.fetcher or DL.HttpFetcher()
    missing, errors = [], {}

    def one(job):
        s, day, win = job
        if (src.vdir / "aggtrades" / s / f"{day.isoformat()}.parquet").exists():
            return job, "ok"
        try:
            return job, "ok" if DL.stream_aggtrades(s, day, win, src.vdir, fetch) else "404"
        except Exception as e:
            return job, f"{type(e).__name__}: {e}"

    with cf.ThreadPoolExecutor(8) as ex:
        for (s, day, _), res in ex.map(one, jobs):
            if res == "404":
                missing.append(f"{s} {day}")
            elif res != "ok":
                errors[f"{s} {day}"] = res
    if errors:
        raise RuntimeError(f"aggTrades errors: {dict(list(errors.items())[:5])}")
    return {"symbol_days": len(jobs), "missing_404": missing}


def _trades(vdir: Path, s: str, ref: int, origin: str, cache: dict):
    a, b = ref - P.WINDOW_PRE_MIN * P.MINUTE_MS, min(ref + P.WINDOW_POST_MIN * P.MINUTE_MS, LIMIT_MS)
    days = tuple(sorted({P.ms_to_date(a), P.ms_to_date(b)}))
    if days not in cache:
        parts = [vdir / "aggtrades" / s / f"{d.isoformat()}.parquet" for d in days]
        cache[days] = None if not all(p.exists() for p in parts) else \
            Trades.from_frame(pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True), origin)
    return cache[days]


# ----------------------------------------------------------------- fills + exits
def _outcome_row(tr, fill, funding, hold, mult):
    if beyond_end(fill.fill_ts, hold):
        return {"dropped": True, "exit_source": "beyond_verdict_end", "gross": None, "net": None, "funding": None}
    out = trade_outcome(tr, fill, funding, buffer_mult=mult, hold_min=hold)
    return {"dropped": out["dropped"], "exit_source": out["exit_source"], "gross": out.get("gross"),
            "net": out.get("net"), "funding": out.get("funding")}


def _symbol_outcomes(args):
    vdir, data_dir, s, orders, origin = args
    _init(origin)
    funding = DL.load_funding(s, data_dir)
    rows, cache = [], {}
    for _, o in orders.iterrows():
        ref, close = int(o["close_ts"]), float(o["close"])
        tr = _trades(vdir, s, ref, origin, cache)
        base = {"order_kind": o["kind"], "event_id": int(o["event_id"]), "symbol": s, "close_ts": ref}
        if tr is None:
            rows.append({**base, "config": "data_missing"})
            continue
        configs = GRID if o["kind"] == "event" else [PRIMARY]
        for d, lat, q in configs:
            f = simulate_fill(tr, ref, close, d, lat, q)
            r = {**base, "config": "grid", "depth": d, "latency_s": lat, "queue": q, "filled": f.filled,
                 "fill_kind": f.kind, "fill_ts": f.fill_ts}
            is_primary = (d, lat, q) == PRIMARY
            combos = [(h, m) for h in HOLDS for m in P.BUFFER_MULTS] if is_primary and o["kind"] == "event" \
                else ([(15, 1), (15, 2)] if is_primary else [(15, 1)])
            if not f.filled:
                for h, m in combos:
                    rows.append({**r, "hold": h, "mult": m})
                continue
            for h, m in combos:
                rows.append({**r, "hold": h, "mult": m, **_outcome_row(tr, f, funding, h, m)})
        if o["kind"] == "event":
            b2 = b2_entry(tr, ref, close)
            for m in P.BUFFER_MULTS:
                r = {**base, "config": "B2", "hold": 15, "mult": m, "filled": b2.filled, "fill_kind": "b2" if b2.filled else None,
                     "fill_ts": b2.fill_ts}
                rows.append({**r, **_outcome_row(tr, b2, funding, 15, m)} if b2.filled else r)
    return rows


def outcomes(src: Source, ev: pd.DataFrame, pl: pd.DataFrame) -> pd.DataFrame:
    orders = pd.concat([ev[["event_id", "symbol", "close_ts", "close"]].assign(kind="event"),
                        pl[["event_id", "symbol", "close_ts", "close"]].assign(kind="placebo")], ignore_index=True)
    jobs = [(src.vdir, src.data_dir, s, g.sort_values("close_ts"), src.origin) for s, g in orders.groupby("symbol")]
    rows = []
    with _pool(src) as ex:
        for r in ex.map(_symbol_outcomes, jobs):
            rows += r
    return pd.DataFrame(rows)


# ----------------------------------------------------------------- verdict inputs + report
def _primary(df: pd.DataFrame, kind: str, mult: int, hold: int = 15) -> pd.DataFrame:
    d, l, q = PRIMARY
    m = (df["order_kind"] == kind) & (df["config"] == "grid") & (df["depth"] == d) & (df["latency_s"] == l) \
        & (df["queue"] == q) & (df["hold"] == hold) & (df["mult"] == mult)
    return df[m].set_index("event_id" if kind == "event" else df[m].index)


def verdict_inputs(ev: pd.DataFrame, pl: pd.DataFrame, oc: pd.DataFrame):
    e1 = _primary(oc, "event", 1)
    e2 = _primary(oc, "event", 2)
    orders = ev[["event_id", "day", "episode"]].set_index("event_id").copy()
    orders["filled"] = e1["filled"].reindex(orders.index).fillna(False).astype(bool)
    orders["dropped"] = e1["dropped"].reindex(orders.index).fillna(False).astype(bool)
    orders["net_1x"] = e1["net"].reindex(orders.index).astype(float)
    orders["net_2x"] = e2["net"].reindex(orders.index).astype(float)
    orders["kind"] = e1["fill_kind"].reindex(orders.index)
    missing = oc[(oc["order_kind"] == "event") & (oc["config"] == "data_missing")]["event_id"]
    orders["data_missing"] = orders.index.isin(missing)
    p1 = oc[(oc["order_kind"] == "placebo") & (oc["config"] == "grid") & (oc["hold"] == 15) & (oc["mult"] == 1)]
    pl_key = pl.reset_index(drop=True)
    p1 = p1.merge(pl_key[["event_id", "close_ts", "event_day"]], on=["event_id", "close_ts"], how="left")
    placebos = pd.DataFrame({"event_id": p1["event_id"], "event_day": p1["event_day"], "filled": p1["filled"].astype(bool),
                             "dropped": p1["dropped"].fillna(False).astype(bool), "net_1x": p1["net"].astype(float)})
    return orders.reset_index(), placebos


def _summ(g: pd.DataFrame) -> dict:
    fl = g[g["filled"].astype(bool)]
    ok = fl[~fl["dropped"].fillna(False).astype(bool)]
    return {"orders": len(g), "fills": len(fl), "fill_rate": len(fl) / len(g) if len(g) else None,
            "dropped": int(fl["dropped"].fillna(False).astype(bool).sum()),
            "mean_gross_per_fill": float(ok["gross"].mean()) if len(ok) else None,
            "mean_net_per_fill": float(ok["net"].mean()) if len(ok) else None,
            "mean_net_per_order": float(np.where(g["filled"].astype(bool) & ~g["dropped"].fillna(False).astype(bool),
                                                 g["net"].fillna(0.0), 0.0).mean()) if len(g) else None}


def exploratory(ev: pd.DataFrame, oc: pd.DataFrame) -> dict:
    grid = oc[(oc["config"] == "grid") & (oc["order_kind"] == "event") & (oc["hold"] == 15) & (oc["mult"] == 1)]
    e1 = _primary(oc, "event", 1)
    out = {
        "E1_grid_depth_latency_queue_15min_1x": {f"d{d}_lat{l}s_q{q}x": _summ(g) for (d, l, q), g in
                                                 grid.groupby(["depth", "latency_s", "queue"])},
        "E2_primary_hold_x_buffer": {f"hold{h}_buf{m}x": _summ(_primary(oc, "event", m, h))
                                     for h in HOLDS for m in P.BUFFER_MULTS},
        "E3_primary_gap_vs_maker_1x": {k: _summ(g) for k, g in e1[e1["filled"].astype(bool)].groupby("fill_kind")},
        "E4_B2_taker_at_close": {f"buf{m}x": _summ(oc[(oc["config"] == "B2") & (oc["mult"] == m)]) for m in P.BUFFER_MULTS},
        "E5_placebo_primary_1x": _summ(oc[(oc["order_kind"] == "placebo") & (oc["config"] == "grid") & (oc["mult"] == 1)]),
        "E6_exit_source_primary": e1[e1["filled"].astype(bool)]["exit_source"].value_counts().to_dict(),
    }
    e1m = e1.join(ev.set_index("event_id")["day"])
    e1m["month"] = [f"{d:%Y-%m}" for d in e1m["day"]]
    out["E7_by_month_primary_1x"] = {m: _summ(g) for m, g in e1m.groupby("month")}
    out["not_implemented_no_spec"] = ["maker take-profit", "pump mirror", "regime splits", "BTC-relative"]
    return out


def seam_report(src: Source, symbols: list) -> dict:
    a, b = DL.seam_span()
    per, dts, drs = {}, [], []
    for s in symbols:
        pa_, pr = src.data_dir / "funding" / f"{s}.parquet", src.data_dir / "funding_seam" / f"{s}.parquet"
        if not (pa_.exists() and pr.exists()):
            continue
        arch = pd.read_parquet(pa_)
        arch = arch[(arch["ts"] >= a) & (arch["ts"] <= b)]
        r = DL.compare_funding_seam(arch, pd.read_parquet(pr))
        per[s] = r
        if r["max_abs_dts_ms"] is not None:
            dts.append(r["max_abs_dts_ms"])
            drs.append(r["max_abs_drate"])
    return {"symbols_compared": len(per), "max_abs_dts_ms": max(dts) if dts else None,
            "max_abs_drate": max(drs) if drs else None,
            "count_mismatch": {s: (v["archive_n"], v["rest_n"]) for s, v in per.items() if v["archive_n"] != v["rest_n"]}}


def _fmt(x):
    if isinstance(x, float):
        return "nan" if np.isnan(x) else f"{x:.6g}"
    return str(x)


def write_report(out_dir: Path, result: dict) -> None:
    v = result["verdict"]
    lines = [f"# VERDICT — crash absorption ({result['meta']['origin']})", "",
             f"**{v['verdict']}**", "",
             f"- code HEAD: `{result['meta'].get('code_head', 'n/a (synthetic)')}`",
             f"- funding manifest sha256: `{result['meta']['funding']['manifest_sha256']}`",
             f"- started {result['meta']['started']}, finished {result['meta']['finished']}", "",
             "## Primary test (d = 0.5 %, 20x queue, 2 s latency, 15-min exit) — PREREG §8", "",
             "| item | values | pass |", "|---|---|---|"]
    for k, it in v["items"].items():
        vals = ", ".join(f"{a}={_fmt(b)}" for a, b in it.items() if a != "pass")
        lines.append(f"| {k} | {vals} | {it['pass']} |")
    i4 = v["items"]["4_beats_placebo"]
    n_ev = v["counts"]["orders"]
    lines += ["", f"Item 4 event side: n = {i4['events_compared']} events with >= 1 placebo; "
                  f"excluded (0 placebos) = {i4['events_without_placebo']} of {n_ev} "
                  f"({i4['events_without_placebo'] / n_ev:.1%})." if n_ev else "", "",
              "## Counts", "", "```", json.dumps(result["counts"], indent=1, default=str), "```", "",
              "## Funding seam (2026-02 archive vs REST)", "", "```", json.dumps(result["seam"], indent=1, default=str), "```", "",
              "## Descriptive (v0.3.3)", "", "```", json.dumps(v.get("descriptive", {}), indent=1, default=str), "```", "",
              "## EXPLORATORY — descriptive only, no p-values, not part of the verdict", ""]
    for k, tab in result["exploratory"].items():
        lines += [f"### {k} (EXPLORATORY)", "", "```", json.dumps(tab, indent=1, default=str), "```", ""]
    (out_dir / "VERDICT_REPORT.md").write_text("\n".join(lines))


def run(src: Source, out_dir: Path, expected_funding_sha: str | None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    meta = preconditions(src, out_dir, expected_funding_sha)
    daily = src.daily()
    from ca.pipeline import segment_days
    uni = build_universe(daily, src.get_exclusions(daily), segment_days(SEG), DL.DOWNLOAD_START)
    meta["funding_coverage"] = check_funding_coverage(src, uni, daily)
    meta["started"] = dt.datetime.now(dt.timezone.utc).isoformat()
    with open(out_dir / "VERDICT_RUN_STARTED.json", "x") as f:  # run-once lock, written before any VERDICT detection
        json.dump(meta, f, indent=1, default=str)
    ev, pl = detect(src, uni)
    if ev.empty:
        raise RuntimeError("no VERDICT events")
    orders = pd.concat([ev[["symbol", "close_ts"]], pl[["symbol", "close_ts"]]], ignore_index=True)
    trade_info = fetch_trades(src, orders)
    oc = outcomes(src, ev, pl)
    vin_orders, vin_pl = verdict_inputs(ev, pl, oc)
    v = evaluate_verdict(vin_orders, vin_pl, P.SEGMENTS[SEG][0], src.origin)
    e1 = _primary(oc, "event", 1)
    counts = {"events": len(ev), "episodes": int(ev["episode"].nunique()), "event_days": int(ev["day"].nunique()),
              "symbols_with_events": int(ev["symbol"].nunique()), "placebos": len(pl),
              "events_with_5_placebos": int((pl.groupby("event_id").size().reindex(ev["event_id"], fill_value=0) == 5).sum()),
              "events_with_0_placebos": v["items"]["4_beats_placebo"]["events_without_placebo"],
              "primary_fills": int(e1["filled"].astype(bool).sum()),
              "primary_gap_fills": int((e1["fill_kind"] == "gap").sum()),
              "primary_maker_fills": int((e1["fill_kind"] == "maker").sum()),
              "primary_dropped": v["counts"]["dropped"], "event_orders_data_missing": int(vin_orders["data_missing"].sum()),
              "aggtrades": trade_info}
    meta["finished"] = dt.datetime.now(dt.timezone.utc).isoformat()
    meta["seconds"] = round(time.time() - t0)
    result = {"meta": meta, "verdict": v, "counts": counts,
              "seam": seam_report(src, src.get_funding_symbols()), "exploratory": exploratory(ev, oc)}
    (out_dir / "VERDICT_RESULT.json").write_text(json.dumps(result, indent=1, default=str, ensure_ascii=False))
    ev.to_parquet(out_dir / "events.parquet", index=False)
    pl.to_parquet(out_dir / "placebos.parquet", index=False)
    oc.to_parquet(out_dir / "outcomes.parquet", index=False)
    write_report(out_dir, result)
    return result
