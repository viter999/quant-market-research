"""DL-1 step 3: PREREG §1 exclusions, applied in the order listed there; volume
and bar presence only. Reads ONLY the open_time and quote_volume columns of the
1m klines (no price column is ever loaded). Writes exclusions.csv and
exclusions_summary.json in studies/delisting/."""
import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dl import events as E  # noqa: E402

DATA = E.ROOT / "data"
COLS = ["open_time", "quote_volume"]


def bars(sym: str) -> pd.DataFrame | None:
    p = DATA / "klines_1m" / f"{sym}.parquet"
    return pd.read_parquet(p, columns=COLS) if p.exists() else None


def funding_months_ok(sym: str, months: list[str]) -> bool:
    p = DATA / "funding" / f"{sym}.manifest.json"
    return p.exists() and set(months) <= set(json.loads(p.read_text())["present"])


def main() -> int:
    evs = [e for e in E.load_events() if e["segment"] == "TEST"]
    btc = bars("BTCUSDT")
    btc_t = set(btc["open_time"].tolist())
    rows = []
    for e in evs:
        w = E.windows(e)
        r = {"episode": e["episode"], "A_utc": e["A_utc"], "symbol": e["symbol"], "D_minus_A_h": e["D_minus_A_h"]}
        if e["excluded_by_time_rule"] == "window_past_data_limit":
            rows.append({**r, "reason": "window_past_data_limit"})
            continue
        k = bars(e["symbol"])
        t = k["open_time"].to_numpy() if k is not None else np.array([], dtype=np.int64)
        q = k["quote_volume"].to_numpy(float) if k is not None else np.array([])
        pre = (t >= w["pre_lo"]) & (t < w["pre_hi"])
        tsw = (t >= w["ts_lo"]) & (t <= w["ts_hi"])
        n_pre = int(pre.sum())
        vol24 = float(q[pre].sum()) if n_pre else 0.0
        med = float(np.median(q[pre])) if n_pre else float("nan")
        mx = float(q[tsw].max()) if tsw.any() else float("nan")
        r.update({"pre_bars": n_pre, "vol24_usd": round(vol24, 2), "median_1m_usd": round(med, 2),
                  "max_1m_A_pm30_usd": round(mx, 2), "ratio": round(mx / med, 3) if med > 0 else ""})
        if n_pre == 0:
            reason = "no_1m_klines_24h_before_A"
        elif vol24 < 5e6:
            reason = "vol24_lt_5M"
        elif e["D_ms"] - e["A_ms"] < 12 * E.HOUR:
            reason = "D_minus_A_lt_12h"
        elif not (mx >= 3 * med):
            reason = "timestamp_unverified"
        else:
            reason = ""
        ts_set = set(t.tolist())
        missing = [n for n, ok in (("entry_bar", w["entry"] in ts_set), ("exit_bar", w["exit"] in ts_set),
                                   ("btc_entry_bar", w["entry"] in btc_t), ("btc_exit_bar", w["exit"] in btc_t),
                                   ("funding_month", funding_months_ok(e["symbol"], E.months_needed(e)))) if not ok]
        r.update({"reason": reason, "data_missing": ";".join(missing) if not reason else ""})
        rows.append(r)
    fields = ["episode", "A_utc", "symbol", "D_minus_A_h", "pre_bars", "vol24_usd", "median_1m_usd",
              "max_1m_A_pm30_usd", "ratio", "reason", "data_missing"]
    with open(E.ROOT / "exclusions.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    kept = [r for r in rows if not r["reason"]]
    usable = [r for r in kept if not r["data_missing"]]
    by_reason = {}
    for r in rows:
        by_reason[r["reason"] or "kept"] = by_reason.get(r["reason"] or "kept", 0) + 1
    summ = {"test_symbol_events": len(rows), "test_episodes": len({r["episode"] for r in rows}),
            "by_reason_first_failing": by_reason,
            "kept_symbol_events": len(kept), "kept_episodes": len({r["episode"] for r in kept}),
            "kept_with_data_missing": sum(1 for r in kept if r["data_missing"]),
            "usable_symbol_events": len(usable), "usable_episodes": len({r["episode"] for r in usable}),
            "item1_met": len({r["episode"] for r in usable}) >= 30 and len(usable) >= 40}
    (E.ROOT / "exclusions_summary.json").write_text(json.dumps(summ, indent=1) + "\n")
    print(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
