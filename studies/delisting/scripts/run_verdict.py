"""DL VERDICT runner (PREREG v0.2 §2/§4, CLARIFICATIONS v0.2.1).

  python3 -I scripts/run_verdict.py --dry-run     synthetic world, no real data read
  DL_RUN_VERDICT=<clean HEAD> python3 -I scripts/run_verdict.py   the one real run

Real-data outcomes need DL_RUN_VERDICT == clean git HEAD (dl/lock.py). Outputs go
to data/results/ (gitignored) and are committed separately after the run."""
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
from dl import events as E, verdict as V  # noqa: E402
from dl.guard import assert_event_allowed  # noqa: E402
from dl.lock import ARCHIVE, SYNTHETIC, OutcomeLocked, head_if_unlocked  # noqa: E402

DATA = E.ROOT / "data"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def usable_events(events_csv: Path, excl_csv: Path) -> list[dict]:
    ex = {(r["episode"], r["symbol"]): r for r in csv.DictReader(open(excl_csv))}
    out = []
    for e in E.load_events(events_csv):
        if e["segment"] != "TEST":
            continue
        r = ex[(e["episode"], e["symbol"])]
        if not r["reason"] and not r["data_missing"]:
            out.append(e)
    return out


def run(evs: list[dict], kl_dir: Path, fund_dir: Path, origin: str) -> tuple[pd.DataFrame, dict]:
    btc = V.load_prices(kl_dir / "BTCUSDT.parquet", origin)
    rows = []
    for e in evs:
        if origin != SYNTHETIC:
            assert_event_allowed(e)
        k = V.load_prices(kl_dir / f"{e['symbol']}.parquet", origin)
        f = V.load_funding(fund_dir / f"{e['symbol']}.parquet", origin)
        rows.append(V.event_result(e, k, btc, f, origin))
    res = pd.DataFrame(rows)
    return res, {"verdict": V.verdict(res), "descriptive": descriptive(res)}


def descriptive(res: pd.DataFrame) -> dict:
    """PREREG §5, EXPLORATORY: episode means of each column and splits."""
    d = {}
    for c in [c for c in res.columns if c.startswith("x_")] + ["gross_bps", "funding_bps", "btc_ret_bps",
                                                                 "net_5x_bps"]:
        ep = res.groupby("episode")[c].mean().dropna()
        d[c] = {"episodes": int(len(ep)), "mean_bps": float(ep.mean()) if len(ep) else None,
                "median_bps": float(ep.median()) if len(ep) else None}
    yr = res.assign(year=res["A_utc"].str[:4]).groupby(["year", "episode"])["net_1x_bps"].mean()
    d["by_year_net_1x"] = {y: {"episodes": int(len(g)), "mean_bps": float(g.mean())} for y, g in yr.groupby(level=0)}
    rs = res.groupby("restriction_flag")["net_1x_bps"]
    d["by_restriction_flag_net_1x_per_event"] = {str(k): {"events": int(len(g)), "mean_bps": float(g.mean())}
                                                 for k, g in rs}
    g, f = res["gross_bps"].abs().sum(), res["funding_bps"].abs().sum()
    d["funding_share_of_abs_pnl"] = float(f / (g + f)) if g + f else None
    d["spot_vs_futures_only"] = "not computed: events.csv carries no spot-delisting field"
    return d


# ------------------------------------------------------------------ dry run
def synthetic_world(td: Path, n_ep: int = 34, seed: int = 1) -> tuple[list[dict], Path, Path]:
    rng = np.random.default_rng(seed)
    kl, fd = td / "klines_1m", td / "funding"
    kl.mkdir()
    fd.mkdir()
    evs, t0 = [], int(dt.datetime(2024, 1, 3, tzinfo=dt.timezone.utc).timestamp() * 1000)
    btc_parts = []
    for i in range(n_ep):
        a = t0 + i * 10 * E.DAY + int(rng.integers(0, 3600_000))
        d = E.floor_min(a) + int(rng.integers(2, 6)) * E.DAY
        for j in range(int(rng.integers(1, 4))):
            s = f"SYN{i}X{j}USDT"
            evs.append({"episode": f"ep{i}", "A_ms": a, "A_utc": pd.Timestamp(a, unit="ms").strftime("%Y-%m-%d %H:%M:%S"),
                        "symbol": s, "D_ms": d, "N_ms": d - 30 * E.MIN, "segment": "TEST", "restriction_flag": j % 2})
            lo, hi = E.floor_min(a) - E.DAY - E.HOUR, d + E.HOUR
            t = np.arange(lo, hi, E.MIN)
            p = 100 * np.cumprod(1 + rng.normal(0.0, 1e-3, len(t)))
            o = np.r_[p[0], p[:-1]]
            pd.DataFrame({"open_time": t, "open": o, "high": np.maximum(o, p) * 1.001, "low": np.minimum(o, p) * 0.999,
                          "close": p}).to_parquet(kl / f"{s}.parquet", index=False)
            ts = np.arange(lo - lo % (8 * E.HOUR) + 8 * E.HOUR, hi, 8 * E.HOUR)
            pd.DataFrame({"ts": ts, "rate": rng.normal(1e-4, 2e-4, len(ts))}).to_parquet(fd / f"{s}.parquet", index=False)
            btc_parts.append(t)
    t = np.unique(np.concatenate(btc_parts))
    p = 30000 * np.cumprod(1 + rng.normal(0, 5e-4, len(t)))
    pd.DataFrame({"open_time": t, "open": p, "high": p, "low": p, "close": p}).to_parquet(kl / "BTCUSDT.parquet",
                                                                                          index=False)
    return evs, kl, fd


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.dry_run:
        with tempfile.TemporaryDirectory() as td:
            evs, kl, fd = synthetic_world(Path(td))
            res, out = run(evs, kl, fd, SYNTHETIC)
        print(json.dumps({"dry_run": True, "symbol_events": len(res), **out["verdict"]}, indent=1, default=float))
        return 0
    head = head_if_unlocked()
    if head is None:
        raise OutcomeLocked("DL_RUN_VERDICT must equal the clean git HEAD ('run VERDICT' not given)")
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    evs = usable_events(E.ROOT / "events.csv", E.ROOT / "exclusions.csv")
    res, out = run(evs, DATA / "klines_1m", DATA / "funding", ARCHIVE)
    used = sorted({e["symbol"] for e in evs} | {"BTCUSDT"})
    manifest = {s: sha256(DATA / "klines_1m" / f"{s}.parquet") for s in used}
    manifest.update({f"funding/{s}": sha256(DATA / "funding" / f"{s}.parquet") for s in used if s != "BTCUSDT"})
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
