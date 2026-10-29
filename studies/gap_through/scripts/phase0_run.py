"""Phase 0 fill-model check (PHASE0_FILL_CHECK.md). Prices and agreement only.
Steps (resumable): verify | download | measure | report
Usage: python -I scripts/phase0_run.py <step>"""
import concurrent.futures as cf
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

GT = Path(__file__).resolve().parents[1]
CA = GT.parent / "crash_absorption"
sys.path.insert(0, str(GT))
sys.path.insert(0, str(CA))
from ca import downloader as DL  # noqa: E402
from ca import params as P  # noqa: E402
from ca.events import detect_symbol_events, minute_features  # noqa: E402
from ca.lock import ARCHIVE  # noqa: E402
from ca.trades import Trades  # noqa: E402
from phase0 import core as C  # noqa: E402
from phase0.stream import stream_bookticker, windows_for  # noqa: E402

CA_DATA = CA / "data"
DATA = GT / "data"
OUT = GT / "results"
WIN_A = P.date_to_ms(dt.date(2024, 1, 1))
WIN_B = P.date_to_ms(dt.date(2024, 3, 30)) + (23 * 60 + 30) * P.MINUTE_MS  # bar t closes <= 2024-03-30 23:30


def log(step: str, info: dict) -> None:
    DATA.mkdir(exist_ok=True)
    path = DATA / "steps.json"
    d = json.loads(path.read_text()) if path.exists() else {}
    d[step] = info
    path.write_text(json.dumps(d, indent=1, default=str))
    print(json.dumps({step: info}, indent=1, default=str))


def sample_events() -> pd.DataFrame:
    ev = pd.read_parquet(CA_DATA / "dev" / "events.parquet")
    return ev[(ev["close_ts"] >= WIN_A) & (ev["close_ts"] <= WIN_B)].sort_values(["close_ts", "symbol"]).reset_index(drop=True)


# ------------------------------------------------------------------ verify
def _det(args):
    s, uni = args
    f = minute_features(pd.read_parquet(CA_DATA / "klines" / "1m" / f"{s}.parquet", columns=["open_time", "close", "quote_volume"]))
    return detect_symbol_events(s, f, uni, "dev", ARCHIVE)[["symbol", "close_ts"]]


def verify() -> None:
    """Re-run the frozen crash-absorption detector on DEV; the stored DEV events must match exactly."""
    uni = {dt.date.fromisoformat(k): frozenset(v) for k, v in json.loads((CA_DATA / "dev" / "universe.json").read_text()).items()}
    members = sorted(set().union(*uni.values()))
    with cf.ProcessPoolExecutor(4) as ex:
        new = pd.concat(list(ex.map(_det, [(s, uni) for s in members])), ignore_index=True)
    old = pd.read_parquet(CA_DATA / "dev" / "events.parquet")[["symbol", "close_ts"]]
    a, b = set(map(tuple, new.to_numpy())), set(map(tuple, old.to_numpy()))
    code = subprocess.run(["git", "log", "-1", "--format=%H", "--", "ca"], cwd=CA, capture_output=True, text=True).stdout.strip()
    log("verify", {"redetected": len(a), "stored": len(b), "identical": a == b, "only_new": len(a - b), "only_stored": len(b - a),
                   "ca_code_last_commit": code, "sample_events": len(sample_events())})


# ------------------------------------------------------------------ download
def refs(ev: pd.DataFrame) -> dict[str, list]:
    """Per symbol: tau windows [tau-5 s, tau+10 s] and T windows [T-60 s, T+10 s] for all latencies."""
    out: dict[str, list] = {}
    for r in ev.itertuples():
        for lat in C.LATENCIES_S:
            tau = int(r.close_ts) + lat * 1000
            T = tau + C.HOLD_MS
            out.setdefault(r.symbol, []).extend([(tau - 5000, tau + 10_000), (T - 60_000, T + 10_000)])
    return out


def _dl(job):
    s, day, win = job
    try:
        return job, ("ok" if stream_bookticker(s, day, win, DATA, DL.HttpFetcher()) else "404")
    except Exception as e:
        return job, f"{type(e).__name__}: {e}"


def download() -> None:
    t0 = time.time()
    jobs = [(s, day, win) for s, sp in refs(sample_events()).items() for day, win in windows_for(sp).items()]
    res = {"ok": 0, "404": []}
    errors = {}
    with cf.ProcessPoolExecutor(4) as ex:
        for (s, day, _), r in ex.map(_dl, jobs):
            if r == "ok":
                res["ok"] += 1
            elif r == "404":
                res["404"].append(f"{s} {day}")
            else:
                errors[f"{s} {day}"] = r
    pq = sum(f.stat().st_size for f in (DATA / "bookticker").rglob("*.parquet"))
    log("download", {"symbol_days": len(jobs), **res, "errors": errors, "parquet_bytes": pq, "seconds": round(time.time() - t0)})


# ------------------------------------------------------------------ measure
def _load_days(base: Path, s: str, days) -> pd.DataFrame | None:
    parts = []
    for d in sorted(set(days)):
        p = base / s / f"{d.isoformat()}.parquet"
        if not p.exists():
            return None
        parts.append(pd.read_parquet(p))
    return pd.concat(parts, ignore_index=True)


def _measure_symbol(args):
    s, g = args
    entries, exits = [], []
    for r in g.itertuples():
        close_ts, close = int(r.close_ts), float(r.close)
        a, b = close_ts - P.WINDOW_PRE_MIN * P.MINUTE_MS, close_ts + P.WINDOW_POST_MIN * P.MINUTE_MS
        trd = _load_days(CA_DATA / "aggtrades", s, [P.ms_to_date(a), P.ms_to_date(b)])
        tr = Trades.from_frame(trd, ARCHIVE) if trd is not None else None
        limit = close * (1 - C.DEPTH)
        qty = P.NOTIONAL_USD / limit
        for lat in C.LATENCIES_S:
            tau = close_ts + lat * 1000
            T = tau + C.HOLD_MS
            bk = _load_days(DATA / "bookticker", s, [P.ms_to_date(tau - 5000), P.ms_to_date(tau)])
            row = {"event_id": int(r.event_id), "symbol": s, "latency_s": lat, "aggtrades_missing": tr is None,
                   "bookticker_missing": bk is None}
            if tr is None or bk is None:
                entries.append(row)
                continue
            book = C.Book.from_frame(bk)
            real = C.real_fill(book, tau, limit, qty)
            prox = C.proxy_fill(tr, tau, limit)
            old = C.old_fill(tr, close_ts, close, lat)
            row.update({"real": real["status"], "real_ask": real.get("ask"), "real_ask_qty": real.get("ask_qty"),
                        "real_bid": real.get("bid"), "quote_age_ms": real.get("quote_age_ms"), "order_qty": qty,
                        "proxy_filled": prox["filled"], "proxy_entry": prox.get("entry"),
                        "old_filled": old["filled"], "old_entry": old["entry"]})
            entries.append(row)
            if real["status"] == "full":  # exit check: price at T vs real bid at T; no entry field is carried
                bkT = _load_days(DATA / "bookticker", s, [P.ms_to_date(T - 60_000), P.ms_to_date(T)])
                xr = {"event_id": int(r.event_id), "symbol": s, "latency_s": lat}
                if bkT is None:
                    xr["status"] = "bookticker_missing"
                else:
                    bT = C.Book.from_frame(bkT)
                    j = C.quote_at(bT, T)
                    px = C.exit_proxy_price(tr, T)
                    if j < 0 or px is None:
                        xr["status"] = "no_quote" if j < 0 else "no_exit_proxy"
                    else:
                        xr.update({"status": "ok", "exit_bias_bps": C.bps(px, float(bT.bid[j])),
                                   "bid_quote_age_ms": int(T - bT.ts[j])})
                exits.append(xr)
    return entries, exits


def measure() -> None:
    t0 = time.time()
    ev = sample_events()
    E, X = [], []
    with cf.ProcessPoolExecutor(4) as ex:
        for e, x in ex.map(_measure_symbol, list(ev.groupby("symbol"))):
            E += e
            X += x
    DATA.mkdir(exist_ok=True)
    pd.DataFrame(E).to_parquet(DATA / "entries.parquet", index=False)
    pd.DataFrame(X).to_parquet(DATA / "exit_check.parquet", index=False)
    log("measure", {"entry_rows": len(E), "exit_rows": len(X), "seconds": round(time.time() - t0)})


# ------------------------------------------------------------------ report
def summarize(E: pd.DataFrame, X: pd.DataFrame, lat: int) -> dict:
    e = E[E["latency_s"] == lat]
    ok = e[~e["aggtrades_missing"] & ~e["bookticker_missing"]]
    q = ok[ok["real"] != "no_quote"]
    real = (q["real"] == "full").to_numpy()
    both = q[(q["real"] == "full") & q["proxy_filled"]]
    both_old = q[(q["real"] == "full") & q["old_filled"]]
    rf = q[q["real"] == "full"]
    x = X[(X["latency_s"] == lat)]
    xok = x[x["status"] == "ok"]
    part = q[q["real"] == "partial"]
    return {
        "events": int(len(e)), "aggtrades_missing": int(e["aggtrades_missing"].sum()),
        "bookticker_missing": int(e["bookticker_missing"].sum()), "no_quote_at_tau": int((ok["real"] == "no_quote").sum()),
        "evaluated": int(len(q)), "real_full": int(real.sum()), "real_partial": int(len(part)),
        "real_partial_with_proxy_fill": int(part["proxy_filled"].sum()), "real_partial_with_old_fill": int(part["old_filled"].sum()),
        "proxy_fills": int(q["proxy_filled"].sum()), "old_fills": int(q["old_filled"].sum()),
        "confusion_real_vs_proxy": C.confusion(real, q["proxy_filled"].to_numpy()),
        "confusion_real_vs_old": C.confusion(real, q["old_filled"].to_numpy()),
        "entry_bias_bps_proxy_minus_real": C.stats(C.bps(p, a) for p, a in zip(both["proxy_entry"], both["real_ask"])),
        "entry_bias_bps_old_minus_real": C.stats(C.bps(p, a) for p, a in zip(both_old["old_entry"], both_old["real_ask"])),
        "exit_bias_bps_proxy_minus_real_bid": C.stats(xok["exit_bias_bps"]),
        "exit_check_status": x["status"].value_counts().to_dict(),
        "spread_bps_at_tau_on_real_fills": C.stats((a - b) / ((a + b) / 2) * 1e4 for a, b in zip(rf["real_ask"], rf["real_bid"])),
        "quote_age_ms_at_tau": C.stats(q["quote_age_ms"]),
    }


def report() -> None:
    E = pd.read_parquet(DATA / "entries.parquet")
    X = pd.read_parquet(DATA / "exit_check.parquet")
    by = {f"{lat}s": summarize(E, X, lat) for lat in C.LATENCIES_S}
    p = by[f"{C.PRIMARY_LATENCY_S}s"]
    dec = C.decision(p["real_full"], p["confusion_real_vs_proxy"], p["entry_bias_bps_proxy_minus_real"]["mean"],
                     p["exit_bias_bps_proxy_minus_real_bid"]["mean"])
    steps = json.loads((DATA / "steps.json").read_text())
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=GT, capture_output=True, text=True).stdout.strip()
    res = {"spec": "studies/gap_through/PHASE0_FILL_CHECK.md (frozen at c393e89)", "code_head": head,
           "sample": "crash-absorption DEV events with bar t closing 2024-01-01 00:00 .. 2024-03-30 23:30 UTC",
           "events_in_sample": int(E["event_id"].nunique()), "steps": steps, "decision_at_2s": dec, "by_latency": by,
           "notes": ["quote in force at t = last bookTicker update with transaction_time <= t (ties: highest update_id)",
                     "spread = (ask - bid) / mid", "bias values are price differences at the same moment, not returns",
                     "no return, markout or PnL computed; entry and exit tables are never joined"]}
    OUT.mkdir(exist_ok=True)
    (OUT / "PHASE0_RESULT.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({"decision_at_2s": dec, "primary": {k: p[k] for k in ("evaluated", "real_full", "proxy_fills")}}, indent=1))


if __name__ == "__main__":
    {"verify": verify, "download": download, "measure": measure, "report": report}[sys.argv[1]]()
