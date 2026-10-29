"""LF-1 step 2: data for every TEST launch in the universe (events.csv rows with
segment TEST and no family exclusion). HOLDOUT / out-of-range rows are never
requested. Per event:
  aggTrades  [L, L+25h10m]                  -> T0 = first aggTrade at or after L, within 24h
  aggTrades  [T0+72h-5m, T0+72h+10m]        (exit window; only if T0 exists)
  1m klines  [L, max(L, T0)+73h]
  fundingRate monthly files covering [L, max(L, T0)+73h]
plus BTCUSDT 1m klines on the same days. T0 is a timestamp only; no price is
looked at. Writes under studies/listing_fade/data/ (gitignored)."""
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lf import archive as AR, events as E  # noqa: E402
from lf.guard import assert_event_allowed, assert_ms_allowed  # noqa: E402

DATA = E.ROOT / "data"
LOCK = threading.Lock()


def key(e: dict) -> str:
    return f"{e['symbol']}_{e['L_utc'][:10]}"


def one(e: dict, fetch) -> dict:
    assert_event_allowed(e)
    s, L = e["symbol"], e["L_ms"]
    out = {"key": key(e), "symbol": s, "L_ms": L}
    man_p = DATA / "manifest" / f"{key(e)}.json"
    if man_p.exists():
        return json.loads(man_p.read_text())
    assert_ms_allowed(L + E.LAUNCH_SPAN)
    launch, miss = AR.agg_windows(s, E.days_between(L, L + E.LAUNCH_SPAN), L, L + E.LAUNCH_SPAN, fetch)
    (DATA / "aggtrades").mkdir(parents=True, exist_ok=True)
    launch.to_parquet(DATA / "aggtrades" / f"{key(e)}_launch.parquet", index=False)
    first = launch.loc[launch["ts"] < L + E.DAY, "ts"]
    t0 = int(first.iloc[0]) if len(first) else None
    out.update({"agg_launch_rows": int(len(launch)), "agg_launch_missing_days": miss, "T0_ms": t0})
    end = max(L, t0 or L) + E.KLINE_SPAN
    if t0 is not None:
        assert_ms_allowed(t0 + E.EXIT_HI)
        ex, miss2 = AR.agg_windows(s, E.days_between(t0 + E.EXIT_LO, t0 + E.EXIT_HI), t0 + E.EXIT_LO, t0 + E.EXIT_HI,
                                   fetch)
        ex.to_parquet(DATA / "aggtrades" / f"{key(e)}_exit.parquet", index=False)
        out.update({"agg_exit_rows": int(len(ex)), "agg_exit_missing_days": miss2})
    assert_ms_allowed(end)
    kl, kmiss = AR.klines(s, E.days_between(L, end), fetch)
    if kl is not None:
        (DATA / "klines_1m").mkdir(parents=True, exist_ok=True)
        kl.to_parquet(DATA / "klines_1m" / f"{key(e)}.parquet", index=False)
    fu, fpres, fmiss = AR.funding(s, E.months_between(L, end), fetch)
    if fu is not None:
        (DATA / "funding").mkdir(parents=True, exist_ok=True)
        fu.to_parquet(DATA / "funding" / f"{key(e)}.parquet", index=False)
    out.update({"kline_days": len(E.days_between(L, end)), "kline_missing_days": kmiss, "kline_end_ms": end,
                "funding_present": fpres, "funding_missing": fmiss})
    man_p.parent.mkdir(parents=True, exist_ok=True)
    man_p.write_text(json.dumps(out))
    with LOCK:
        print(f"{key(e)}: T0-L={'none' if t0 is None else round((t0 - L) / 1000, 3)}s launch_rows={len(launch)} "
              f"missing agg {miss} {out.get('agg_exit_missing_days', '')} kl {kmiss} funding {fmiss}", flush=True)
    return out


def main() -> int:
    evs = E.universe(E.load_events())
    for e in evs:
        assert_event_allowed(e)
    fetch = AR.HttpFetcher()
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda e: one(e, fetch), evs))
    days = sorted({d for r in res for d in E.days_between(r["L_ms"], r["kline_end_ms"])})
    btc, bmiss = AR.klines("BTCUSDT", days, fetch)
    btc.to_parquet(DATA / "klines_1m" / "BTCUSDT.parquet", index=False)
    print(f"BTCUSDT: {len(days)} days, missing {bmiss}", flush=True)
    (DATA / "download_report.json").write_text(json.dumps({"events": res, "btc_missing": bmiss}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
