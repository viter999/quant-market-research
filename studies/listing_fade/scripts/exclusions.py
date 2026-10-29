"""LF-1 step 3: PREREG §1 exclusions in the listed order, then the §2 data drops.
Inputs are timestamps, trade sides, quote notional (price x qty, for the $5M
volume rule only) and file/bar presence. No return, markout or PnL is computed.

  1 no_aggtrades_24h        no aggTrade in [L, L+24h)  (T0 undefined)
  2 vol_1h_lt_5M            sum(price*qty) of aggTrades in [T0, T0+1h) < $5M
  3 funding_record_missing  a settlement in the hold (T0+60m, T0+72h] has no record
  4 delisting_announced     a catalog-161 delisting title names the token, released in [A, T0+72h)
then (§2 drops, counted separately)
  no_entry_trades           no seller-initiated aggTrade in [T0+60m, T0+62m)
  no_exit_trades            no buyer-initiated aggTrade in [T0+72h, T0+72h+2m)
  btc_bar_missing           no BTCUSDT 1m bar at the entry or exit minute
Writes exclusions.csv and exclusions_summary.json in studies/listing_fade/."""
import csv
import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lf import events as E  # noqa: E402

DATA = E.ROOT / "data"
TOL = 5 * E.MIN


def key(e):
    return f"{e['symbol']}_{e['L_utc'][:10]}"


def funding_complete(f: pd.DataFrame | None, months_ok: bool, lo: int, hi: int) -> bool:
    """Every settlement in (lo, hi] has a record: the chain lo -> r1 -> ... -> rk -> hi
    has no gap longer than the funding interval (+5 min)."""
    if f is None or not months_ok:
        return False
    r = f[(f["ts"] > lo) & (f["ts"] <= hi)].sort_values("ts")
    if r.empty:
        return False
    ts, iv = r["ts"].tolist(), (r["funding_interval_hours"] * E.HOUR).tolist()
    if ts[0] - lo > iv[0] + TOL or hi - ts[-1] > iv[-1] + TOL:
        return False
    return all(b - a <= w + TOL for a, b, w in zip(ts, ts[1:], iv[1:]))


def delisting_hit(e: dict, t0: int, titles: list[dict]) -> str:
    s = e["symbol"]
    base = s[:-4]
    cands = {s, base} | ({base[4:]} if base.startswith("1000") else set())
    for x in titles:
        r = int(x["release"])
        if e["A_ms"] <= r < t0 + 72 * E.HOUR and re.search(r"Delist", x["title"]) and not x["title"].startswith(
                "Binance Margin") and any(re.search(r"(?<![0-9A-Za-z])" + re.escape(c) + r"(?![0-9A-Za-z])",
                                                    x["title"]) for c in cands):
            return x["title"][:120]
    return ""


def main() -> int:
    evs = E.universe(E.load_events())
    titles = json.loads((E.ROOT / "events_raw" / "delisting_catalog161_titles.json").read_text())["titles"]
    btc_t = set(pd.read_parquet(DATA / "klines_1m" / "BTCUSDT.parquet", columns=["open_time"])["open_time"].tolist())
    rows = []
    for e in evs:
        m = json.loads((DATA / "manifest" / f"{key(e)}.json").read_text())
        r = {"episode": e["episode"], "symbol": e["symbol"], "L_utc": e["L_utc"], "launch_day": e["launch_day"],
             "premarket_flag": e["premarket_flag"], "T0_minus_L_s": "", "vol_1h_usd": "", "reason": "", "drop": "",
             "missing_files": ";".join(m.get("agg_launch_missing_days", []) + m.get("agg_exit_missing_days", []) +
                                       m.get("kline_missing_days", []) + m.get("funding_missing", []))}
        t0 = m["T0_ms"]
        if t0 is None:
            r["reason"] = "no_aggtrades_24h"
            rows.append(r)
            continue
        a = pd.read_parquet(DATA / "aggtrades" / f"{key(e)}_launch.parquet", columns=["ts", "price", "qty", "ibm"])
        h = a[(a["ts"] >= t0) & (a["ts"] < t0 + E.HOUR)]
        vol = float((h["price"] * h["qty"]).sum())
        r.update({"T0_minus_L_s": round((t0 - e["L_ms"]) / 1000, 3), "vol_1h_usd": round(vol, 2)})
        fp = DATA / "funding" / f"{key(e)}.parquet"
        f = pd.read_parquet(fp, columns=["ts", "funding_interval_hours"]) if fp.exists() else None
        entry, exit_ = t0 + 60 * E.MIN, t0 + 72 * E.HOUR
        hit = delisting_hit(e, t0, titles)
        if vol < 5e6:
            r["reason"] = "vol_1h_lt_5M"
        elif not funding_complete(f, not m["funding_missing"], entry, exit_):
            r["reason"] = "funding_record_missing"
        elif hit:
            r["reason"] = "delisting_announced"
            r["drop"] = hit
        if not r["reason"]:
            x = pd.read_parquet(DATA / "aggtrades" / f"{key(e)}_exit.parquet", columns=["ts", "ibm"])
            drops = []
            if not ((a["ts"] >= entry) & (a["ts"] < entry + 2 * E.MIN) & a["ibm"]).any():
                drops.append("no_entry_trades")
            if not ((x["ts"] >= exit_) & (x["ts"] < exit_ + 2 * E.MIN) & ~x["ibm"]).any():
                drops.append("no_exit_trades")
            if E.floor_min(entry) not in btc_t or E.floor_min(exit_) not in btc_t:
                drops.append("btc_bar_missing")
            r["drop"] = ";".join(drops)
        rows.append(r)
    with open(E.ROOT / "exclusions.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    usable = [r for r in rows if not r["reason"] and not r["drop"]]
    kept = [r for r in rows if not r["reason"]]
    ep_day = {}
    for r in usable:
        ep_day[r["episode"]] = min(ep_day.get(r["episode"], r["L_utc"]), r["L_utc"])[:10]
    by = {}
    for r in rows:
        by[r["reason"] or "kept"] = by.get(r["reason"] or "kept", 0) + 1
    summ = {"universe_rows": len(rows), "universe_episodes": len({r["episode"] for r in rows}),
            "universe_launch_days": len({r["launch_day"] for r in rows}),
            "by_reason_first_failing": by,
            "kept_rows": len(kept), "kept_episodes": len({r["episode"] for r in kept}),
            "drops": {d: sum(1 for r in kept if d in r["drop"].split(";"))
                      for d in ("no_entry_trades", "no_exit_trades", "btc_bar_missing")},
            "usable_rows": len(usable), "usable_episodes": len(ep_day), "usable_launch_days": len(set(ep_day.values())),
            "premarket_usable_rows": sum(1 for r in usable if r["premarket_flag"] == "1")}
    summ["item1_met"] = summ["usable_episodes"] >= 120 and summ["usable_launch_days"] >= 70
    (E.ROOT / "exclusions_summary.json").write_text(json.dumps(summ, indent=1) + "\n")
    print(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
