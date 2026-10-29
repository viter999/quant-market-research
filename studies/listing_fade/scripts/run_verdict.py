"""LF VERDICT runner (PREREG v0.2 §2/§4, CLARIFICATIONS v0.2.1).

  python3 -I scripts/run_verdict.py --dry-run     synthetic world, no real data read
  LF_RUN_VERDICT=<clean HEAD> python3 -I scripts/run_verdict.py   the one real run

Outputs go to data/results/ (gitignored) and are committed separately after the run."""
import argparse
import csv
import datetime as dt
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lf import events as E, verdict as V  # noqa: E402
from lf.guard import assert_event_allowed  # noqa: E402
from lf.lock import ARCHIVE, SYNTHETIC, OutcomeLocked, head_if_unlocked  # noqa: E402

DATA = E.ROOT / "data"


def key(e):
    return f"{e['symbol']}_{e['L_utc'][:10]}"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def select(events_csv: Path, excl_csv: Path) -> tuple[list[dict], list[dict]]:
    """(usable rows, rows excluded only for the $5M first-hour volume rule)."""
    ex = {(r["episode"], r["symbol"]): r for r in csv.DictReader(open(excl_csv))}
    use, thin = [], []
    for e in E.universe(E.load_events(events_csv)):
        r = ex[(e["episode"], e["symbol"])]
        if not r["reason"] and not r["drop"]:
            use.append(e)
        elif r["reason"] == "vol_1h_lt_5M":
            thin.append(e)
    return use, thin


def compute(evs: list[dict], d: Path, t0s: dict, origin: str) -> tuple[pd.DataFrame, np.ndarray, dict]:
    btc = V.load_parquet(d / "klines_1m" / "BTCUSDT.parquet", origin, ["open_time", "close"]).set_index("open_time")["close"]
    rows, rates, dropped = [], [], {}
    for e in evs:
        if origin != SYNTHETIC:
            assert_event_allowed(e)
        k, t0 = key(e), t0s[key(e)]
        la = V.load_parquet(d / "aggtrades" / f"{k}_launch.parquet", origin)
        xt = V.load_parquet(d / "aggtrades" / f"{k}_exit.parquet", origin)
        kl = V.load_parquet(d / "klines_1m" / f"{k}.parquet", origin, ["open_time", "open", "high", "low", "close"])
        fu = V.load_parquet(d / "funding" / f"{k}.parquet", origin, ["ts", "rate"])
        try:
            r = V.event_result(e, t0, la, xt, kl, fu, btc, origin)
        except V.Dropped as err:
            dropped[str(err)] = dropped.get(str(err), 0) + 1
            continue
        rows.append(r)
        rates += fu[(fu["ts"] > t0 + 60 * E.MIN) & (fu["ts"] <= t0 + 72 * E.HOUR + E.MIN)]["rate"].tolist()
    return pd.DataFrame(rows), np.array(rates, float), dropped


def descriptive(res: pd.DataFrame, rates: np.ndarray) -> dict:
    """PREREG §5, EXPLORATORY: episode means (1x) of each column and splits."""
    d = {}
    for c in [c for c in res.columns if c.startswith("x_")] + ["gross_bps", "funding_bps", "btc_ret_bps", "net_5x_bps"]:
        ep = res.groupby("episode")[c].mean().dropna()
        d[c] = {"episodes": int(len(ep)), "mean_bps": float(ep.mean()) if len(ep) else None,
                "median_bps": float(ep.median()) if len(ep) else None}
    adv = res.groupby("episode")["x_max_adverse_bps"].mean().dropna()
    d["x_max_adverse_p95_bps"] = float(np.percentile(adv, 95)) if len(adv) else None
    for name, col in (("by_year", res["L_utc"].str[:4]), ("by_premarket_flag", res["premarket_flag"].astype(str))):
        g = res.assign(g=col).groupby(["g", "episode"])["net_1x_bps"].mean()
        d[name] = {k: {"episodes": int(len(v)), "mean_bps": float(v.mean())} for k, v in g.groupby(level=0)}
    g, f = res["gross_bps"].abs().sum(), res["funding_bps"].abs().sum()
    d["funding_share_of_abs_pnl"] = float(f / (g + f)) if g + f else None
    d["funding_path"] = {"settlements": int(len(rates)), "rate_p1": float(np.percentile(rates, 1)) if len(rates) else None,
                         "rate_p50": float(np.median(rates)) if len(rates) else None,
                         "rate_p99": float(np.percentile(rates, 99)) if len(rates) else None}
    d["funding_stress"] = V.funding_stress(res, rates)
    d["fallbacks"] = {"entry": int(res["entry_fallback"].sum()), "exit": int(res["exit_fallback"].sum())}
    d["spot_pair_at_L"] = "not computed: no spot-listing data in the event list"
    return d


# ------------------------------------------------------------------ dry run
def synthetic_world(td: Path, n_ep: int = 130, seed: int = 3) -> tuple[list[dict], dict]:
    rng = np.random.default_rng(seed)
    for sub in ("aggtrades", "klines_1m", "funding"):
        (td / sub).mkdir()
    evs, t0s, btc_t = [], {}, []
    base = int(dt.datetime(2024, 1, 2, tzinfo=dt.timezone.utc).timestamp() * 1000)
    for i in range(n_ep):
        L = base + i * 5 * E.DAY + int(rng.integers(0, 12)) * E.HOUR
        for j in range(int(rng.integers(1, 3))):
            s = f"SYN{i}X{j}USDT"
            e = {"episode": f"ep{i}", "symbol": s, "L_ms": L, "L_utc": pd.Timestamp(L, unit="ms").strftime("%Y-%m-%d %H:%M:%S"),
                 "segment": "TEST", "premarket_flag": j % 2}
            t0 = L + int(rng.integers(100, 60_000))
            t0s[key(e)] = t0
            t = np.sort(rng.integers(L, L + E.LAUNCH_SPAN, 40_000))
            p = 1.0 * np.cumprod(1 + rng.normal(0, 4e-4, len(t)))
            tr = pd.DataFrame({"ts": t, "price": p, "qty": rng.exponential(5000, len(t)), "ibm": rng.random(len(t)) < .5,
                               "agg_id": np.arange(len(t))})
            tr.to_parquet(td / "aggtrades" / f"{key(e)}_launch.parquet", index=False)
            tx = np.sort(rng.integers(t0 + E.EXIT_LO, t0 + E.EXIT_HI, 3000))
            px = p[-1] * np.cumprod(1 + rng.normal(0, 4e-4, len(tx)))
            pd.DataFrame({"ts": tx, "price": px, "qty": 1000.0, "ibm": rng.random(len(tx)) < .5,
                          "agg_id": np.arange(len(tx))}).to_parquet(td / "aggtrades" / f"{key(e)}_exit.parquet", index=False)
            m = np.arange(E.floor_min(L), E.floor_min(t0) + E.KLINE_SPAN, E.MIN)
            c = np.interp(m, np.r_[t, tx], np.r_[p, px])
            pd.DataFrame({"open_time": m, "open": c, "high": c * 1.002, "low": c * 0.998, "close": c}).to_parquet(
                td / "klines_1m" / f"{key(e)}.parquet", index=False)
            fts = np.arange(L - L % (4 * E.HOUR) + 4 * E.HOUR, t0 + 80 * E.HOUR, 4 * E.HOUR)
            pd.DataFrame({"ts": fts, "funding_interval_hours": 4, "rate": rng.normal(-1e-4, 3e-4, len(fts))}).to_parquet(
                td / "funding" / f"{key(e)}.parquet", index=False)
            btc_t.append(m)
            evs.append(e)
    m = np.unique(np.concatenate(btc_t))
    pd.DataFrame({"open_time": m, "close": 60000 * np.cumprod(1 + rng.normal(0, 3e-4, len(m)))}).to_parquet(
        td / "klines_1m" / "BTCUSDT.parquet", index=False)
    return evs, t0s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.dry_run:
        with tempfile.TemporaryDirectory() as td:
            evs, t0s = synthetic_world(Path(td))
            res, rates, dropped = compute(evs, Path(td), t0s, SYNTHETIC)
            out = {"verdict": V.verdict(res), "dropped": dropped, "descriptive": descriptive(res, rates)}
        print(json.dumps({"dry_run": True, "symbol_events": len(res), **out}, indent=1, default=float))
        return 0
    head = head_if_unlocked()
    if head is None:
        raise OutcomeLocked("LF_RUN_VERDICT must equal the clean git HEAD ('run VERDICT' not given)")
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    use, thin = select(E.ROOT / "events.csv", E.ROOT / "exclusions.csv")
    t0s = {json.loads(p.read_text())["key"]: json.loads(p.read_text())["T0_ms"] for p in (DATA / "manifest").glob("*.json")}
    res, rates, dropped = compute(use, DATA, t0s, ARCHIVE)
    out = {"verdict": V.verdict(res), "dropped": dropped, "descriptive": descriptive(res, rates)}
    sres, _, sdrop = compute(use + thin, DATA, t0s, ARCHIVE)
    sep = sres.groupby("episode")["net_1x_bps"].mean()
    out["descriptive"]["sensitivity_incl_thin"] = {"episodes": int(len(sep)), "mean_net_1x_bps": float(sep.mean()),
                                                   "median_net_1x_bps": float(sep.median()), "dropped": sdrop}
    files = sorted(p for sub in ("aggtrades", "klines_1m", "funding", "manifest") for p in (DATA / sub).glob("*"))
    manifest = {str(p.relative_to(DATA)): sha256(p) for p in files}
    meta = {"head": head, "started_utc": started, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "events_csv_sha256": sha256(E.ROOT / "events.csv"), "exclusions_csv_sha256": sha256(E.ROOT / "exclusions.csv"),
            "data_manifest_sha256": hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()}
    if head_if_unlocked() != head:
        raise OutcomeLocked("HEAD or tree changed during the run")
    o = DATA / "results"
    o.mkdir(parents=True, exist_ok=True)
    res.to_csv(o / "event_results.csv", index=False)
    (o / "data_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    (o / "VERDICT_RESULT.json").write_text(json.dumps({**meta, **out}, indent=1, default=float))
    print(json.dumps({**meta, "status": out["verdict"]["status"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
