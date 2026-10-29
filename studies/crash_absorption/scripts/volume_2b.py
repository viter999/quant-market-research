"""Task 2b step 5: measured volume estimate from listings (names + sizes only)
and 1d klines. Universe uses the DRAFT exclusion list (estimate only, not a
detection run). Usage: python -I scripts/volume_2b.py <data_dir>"""
import concurrent.futures as cf
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ca import downloader as DL  # noqa: E402
from ca import inventory as I  # noqa: E402
from ca import params as P  # noqa: E402
from ca.universe import build_universe, load_exclusions  # noqa: E402

GB = 1e9


def main(data_dir: Path):
    inv = json.loads((data_dir / "inventory_klines.json").read_text())["files"]
    rows = []
    for f in sorted((data_dir / "klines" / "1d").glob("*.parquet")):
        d = pd.read_parquet(f)
        rows.append(pd.DataFrame({"symbol": f.stem, "day": [P.ms_to_date(t) for t in d["open_time"]],
                                  "quote_volume": d["quote_volume"], "high": d["high"], "low": d["low"], "open": d["open"]}))
    daily = pd.concat(rows, ignore_index=True)
    days = [d for seg in ("dev", "verdict") for d in
            (P.SEGMENTS[seg][0] + dt.timedelta(days=i) for i in range((P.SEGMENTS[seg][1] - P.SEGMENTS[seg][0]).days + 1))]
    uni = build_universe(daily[["symbol", "day", "quote_volume"]], load_exclusions(require_frozen=False), days, DL.DOWNLOAD_START)
    members = sorted(set().union(*uni.values()))
    member_days = [(s, d) for d, ss in uni.items() for s in ss]

    # 1m klines
    all_1m = sum(sz for v in inv.values() for _, sz in v["1m"])
    need = set()
    for s, d in member_days:
        need.add((s, f"{d:%Y-%m}"))
        prev = d.replace(day=1) - dt.timedelta(days=1)
        need.add((s, f"{prev:%Y-%m}"))  # lookback
    mem_1m = 0
    for s in members:
        for k, sz in inv[s]["1m"]:
            freq, per = I.period_of(k)
            if (s, per[:7]) in need:
                mem_1m += sz
    one_1m = dict(inv["BTCUSDT"]["1m"])

    # aggTrades sizes for members (listing only)
    fetch = DL.HttpFetcher()

    def agg(sym):
        return sym, {I.period_of(k)[1]: sz for p in I.aggtrades_prefixes(sym, dt.date(2024, 1, 1))
                     for k, sz in I.list_files(fetch, p)}

    with cf.ThreadPoolExecutor(16) as ex:
        agg_sizes = dict(ex.map(agg, members))
    rng_map = {(r.symbol, r.day): (r.high - r.low) / r.open for r in daily.itertuples()}
    md = pd.DataFrame([{"symbol": s, "day": d, "size": agg_sizes[s].get(d.isoformat(), np.nan),
                        "range": rng_map.get((s, d), np.nan)} for s, d in member_days])
    missing = int(md["size"].isna().sum())
    md = md.dropna()
    hi = md[md["range"] >= md["range"].quantile(0.9)]
    out = {
        "symbols_listed_1d_downloaded": int(daily["symbol"].nunique()),
        "universe_members_ever": len(members), "member_days": len(member_days),
        "klines_1m_all_symbols_GB": all_1m / GB, "klines_1m_universe_members_GB": mem_1m / GB,
        "BTCUSDT_1m_2024-01_bytes": next((v for k, v in one_1m.items() if k.endswith("2024-01.zip")), None),
        "aggtrades_member_days_missing_file": missing,
        "aggtrades_member_day_MB": {"mean": md["size"].mean() / 1e6, "median": md["size"].median() / 1e6,
                                    "p90": md["size"].quantile(0.9) / 1e6, "max": md["size"].max() / 1e6},
        "aggtrades_top_decile_range_member_day_MB": {"mean": hi["size"].mean() / 1e6, "median": hi["size"].median() / 1e6},
        "aggtrades_1500_symbol_days_GB": {"at_mean": 1500 * md["size"].mean() / GB,
                                          "at_top_decile_range_mean": 1500 * hi["size"].mean() / GB},
        "aggtrades_all_member_days_GB": md["size"].sum() / GB,
    }
    (data_dir / "volume_2b.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
