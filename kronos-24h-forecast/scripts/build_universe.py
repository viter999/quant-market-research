"""Build the frozen universe from PRE-WINDOW data only.

Stage 'rank':  quote volume of every USDT-M perpetual over 2025-06-01 00:00 .. 2025-06-30 23:59 UTC
               (the 30 days before the test window), from public 1d monthly klines.
Stage 'check': walk down the ranking (after exclusions) and keep the first 30 symbols whose 1h
               klines are complete from 2025-06-09 16:00 (512 warm-up bars) to 2026-09-30 23:00 UTC.
               This stage reads ONLY the open_time column: no prices, volumes or returns from the
               test window are parsed.
"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kt_common as kt
import kt_binance as kb

import pandas as pd

RANK_MONTH = "2025-06"
RANK_START = pd.Timestamp("2025-06-01 00:00", tz="UTC")
RANK_END = pd.Timestamp("2025-07-01 00:00", tz="UTC")       # exclusive
WARMUP_START = pd.Timestamp("2025-06-09 16:00", tz="UTC")   # 512 bars before 2025-07-01 00:00
LAST_BAR = pd.Timestamp("2026-09-30 23:00", tz="UTC")       # last 1h bar used by the last forecast
N_UNIVERSE = 30

STABLECOINS = {"USDC", "FDUSD", "TUSD", "BUSD", "USDP", "DAI", "USDE", "USD1", "RLUSD", "PYUSD",
               "USDS", "EURI", "AEUR", "FRAX", "LUSD", "GUSD", "USDD", "SUSD", "BFUSD", "XUSD"}
METALS = {"XAU", "XAUT", "XAG", "PAXG"}

OUT = os.path.join(kt.DATA, "universe")
os.makedirs(OUT, exist_ok=True)


def is_usdt_perp(sym):
    return sym.endswith("USDT") and "_" not in sym


def rank():
    syms = [s for s in kb.list_um_kline_symbols() if is_usdt_perp(s)]
    print(f"USDT-M perpetual symbols with a monthly klines folder: {len(syms)}")

    def one(sym):
        path = kb.monthly_zip(sym, "1d", RANK_MONTH)
        if path is None:
            return None
        df = kb.read_klines(path)
        df = df[(df.open_time >= RANK_START) & (df.open_time < RANK_END)]
        if df.empty:
            return None
        return {"symbol": sym, "quote_volume_usdt": float(df.quote_volume.sum()), "days": int(len(df))}

    with ThreadPoolExecutor(max_workers=8) as ex:
        rows = [r for r in ex.map(one, syms) if r]
    tab = pd.DataFrame(rows).sort_values("quote_volume_usdt", ascending=False).reset_index(drop=True)
    tab.insert(0, "rank_all", tab.index + 1)
    base = tab.symbol.str[:-4]
    tab["excluded"] = ""
    tab.loc[base.isin(STABLECOINS), "excluded"] = "stablecoin"
    tab.loc[base.isin(METALS), "excluded"] = "metal"
    tab.to_csv(os.path.join(OUT, "ranking_2025-06_quote_volume.csv"), index=False)
    print(f"symbols with June 2025 data: {len(tab)}")
    with pd.option_context("display.width", 200, "display.max_rows", 200):
        print(tab.head(60).to_string(index=False, formatters={"quote_volume_usdt": "{:,.0f}".format}))


def check():
    tab = pd.read_csv(os.path.join(OUT, "ranking_2025-06_quote_volume.csv"), keep_default_na=False)
    expected = pd.date_range(WARMUP_START, LAST_BAR, freq="h")
    need_months = kb.months(WARMUP_START.strftime("%Y-%m"), LAST_BAR.strftime("%Y-%m"))
    kept, rejected = [], []
    for _, row in tab.iterrows():
        if len(kept) == N_UNIVERSE:
            break
        sym = row.symbol
        if row.excluded:
            rejected.append({"symbol": sym, "rank_all": int(row.rank_all), "reason": row.excluded})
            continue
        with ThreadPoolExecutor(max_workers=8) as ex:
            paths = list(ex.map(lambda m: kb.monthly_zip(sym, "1h", m), need_months))
        missing_months = [m for m, p in zip(need_months, paths) if p is None]
        if missing_months:
            rejected.append({"symbol": sym, "rank_all": int(row.rank_all),
                             "reason": f"no 1h file for {','.join(missing_months)}"})
            print(f"  reject {sym}: no 1h file for {missing_months}")
            continue
        ts = pd.concat([kb.read_klines(p, usecols=["open_time"]).open_time for p in paths])
        ts = ts[(ts >= WARMUP_START) & (ts <= LAST_BAR)]
        dupes = int(ts.duplicated().sum())
        gaps = expected.difference(pd.DatetimeIndex(ts))
        if dupes or len(gaps):
            rejected.append({"symbol": sym, "rank_all": int(row.rank_all),
                             "reason": f"{len(gaps)} missing 1h bars, {dupes} duplicates",
                             "first_missing": [str(g) for g in gaps[:5]]})
            print(f"  reject {sym}: {len(gaps)} missing bars, {dupes} dupes, first {list(gaps[:3])}")
            continue
        kept.append({"symbol": sym, "rank_all": int(row.rank_all),
                     "quote_volume_usdt_2025_06": float(row.quote_volume_usdt)})
        print(f"  keep {len(kept):2d}: {sym} (rank {row.rank_all})")
    result = {
        "ranking_period_utc": [str(RANK_START), str(RANK_END - pd.Timedelta(seconds=1))],
        "completeness_span_utc": [str(WARMUP_START), str(LAST_BAR)],
        "expected_1h_bars": len(expected),
        "universe": kept,
        "rejected_before_30_filled": rejected,
    }
    with open(os.path.join(OUT, "universe_frozen.json"), "w") as f:
        json.dump(result, f, indent=2)
    print(f"kept {len(kept)}; rejected {len(rejected)}")


if __name__ == "__main__":
    {"rank": rank, "check": check}[sys.argv[1]]()
