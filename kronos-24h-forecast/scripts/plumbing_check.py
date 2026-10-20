"""Plumbing check, PREREG_kronos.md §9.2. Pre-window days only; shapes and mechanics, NO outcome statistics.

1. run_forecasts.py --mode plumbing --stop-after 5   (forced stop)
2. run_forecasts.py --mode plumbing                  (resume to the end)
3. check rows, shapes, timestamps, NaN, seeds, duplicates; repeat the first forecast in this process and
   compare it bit for bit; timing. Writes results/plumbing/PLUMBING_REPORT.md.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kt_common as kt
import kt_binance as kb
import run_forecasts as rf

import numpy as np
import pandas as pd

HOUR = pd.Timedelta(hours=1)
OUT = os.path.join(kt.RESULTS, "plumbing")
CSV = os.path.join(OUT, "forecasts.csv")
RUN = [sys.executable, "-I", os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_forecasts.py"),
       "--mode", "plumbing"]


def main():
    kt.below_normal_priority()
    if os.path.exists(CSV):
        raise SystemExit(f"{CSV} exists; plumbing check must start fresh")
    checks = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    rc1 = subprocess.run(RUN + ["--stop-after", "5"]).returncode
    n1 = len(pd.read_csv(CSV, dtype=str))
    check("forced stop after 5 forecasts", rc1 == 0 and n1 == 5, f"exit {rc1}, {n1} rows")
    first_rows = pd.read_csv(CSV, dtype=str)

    rc2 = subprocess.run(RUN).returncode
    fc = pd.read_csv(CSV, dtype=str)
    syms = kt.universe()
    log_text = open(os.path.join(kt.LOGS, "run_plumbing.log"), encoding="utf-8").read()
    skipped = len(set(re.findall(r"plumbing: skip (\S+ \S+)", log_text)))   # both runs log the same skips
    expected = len(kt.PLUMBING_DAYS) * len(syms) - skipped
    check("resume ran to the end", rc2 == 0, f"exit {rc2}")
    check("row count", len(fc) == expected, f"{len(fc)} rows, {skipped} skipped for short pre-window history")
    check("no duplicate (day, symbol)", not fc.duplicated(["day", "symbol"]).any())
    check("rows from before the forced stop unchanged", fc.head(5).equals(first_rows))
    check("context shape (512, 6)", ((fc.ctx_rows == "512") & (fc.ctx_cols == "6")).all())
    check("output shape (24, 6)", ((fc.out_rows == "24") & (fc.out_cols == "6")).all())
    D = pd.to_datetime(fc.day)
    check("context = D-512h .. D-1h",
          ((pd.to_datetime(fc.ctx_first_open) == D - 512 * HOUR) & (pd.to_datetime(fc.ctx_last_open) == D - HOUR)).all())
    preds = fc[[f"pred_close_{h:02d}" for h in range(1, 25)]].astype(float).to_numpy()
    check("24 finite predicted closes per row", np.isfinite(preds).all() and preds.shape[1] == 24)
    check("p24 = 24th predicted close", np.array_equal(preds[:, -1], fc.p24.astype(float).to_numpy()))
    idx = fc.symbol.map({s: i for i, s in enumerate(syms)})
    seeds = np.array([kt.seed_for(pd.Timestamp(d), i) for d, i in zip(fc.day, idx)], dtype=np.int64)
    check("seed = YYYYMMDD*100 + coin index", (fc.seed.astype(np.int64).to_numpy() == seeds).all())
    check("signal = sign(p24 - c0), values in {-1,0,1}",
          (np.sign(fc.p24.astype(float) - fc.c0.astype(float)).astype(int) == fc.signal.astype(int)).all())

    # repeat the very first forecast (written by the first process) in this process
    row = fc.iloc[0]
    day = pd.Timestamp(row.day)
    bars = kb.load_1h_bars(row.symbol, *kt.DATA_MONTHS)
    ctx = rf.context(bars, day)
    check("c0 = close of bar D-1h", float(row.c0) == float(ctx["close"].iloc[-1]))
    predictor = kt.load_predictor(threads=kt.THREADS)
    again = rf.forecast(predictor, ctx, day, int(row.seed))["close"].to_numpy(dtype=float)
    check("same seed reproduces the stored forecast bit for bit",
          [repr(float(v)) for v in again] == [row[f"pred_close_{h:02d}"] for h in range(1, 25)],
          f"{row.symbol} {row.day}, across two processes")

    secs = fc.seconds.astype(float)
    timing = f"mean {secs.mean():.1f}s, median {secs.median():.1f}s, max {secs.max():.1f}s per forecast"
    full_n = len(pd.date_range(kt.FULL_FIRST_DAY, kt.FULL_LAST_DAY, freq="D")) * len(syms)
    eta = full_n * secs.mean() / 3600

    ok = all(c[1] for c in checks)
    lines = ["# Plumbing check (pre-window days, no outcome statistics)", "",
             f"Days: {', '.join(kt.PLUMBING_DAYS)}. Coins: {len(syms)}. Result: **{'ALL PASS' if ok else 'FAIL'}**", "",
             "| Check | Result | Detail |", "|---|---|---|"]
    lines += [f"| {n} | {'pass' if p else 'FAIL'} | {d} |" for n, p, d in checks]
    lines += ["", f"Timing: {timing}. Full run: {full_n:,} forecasts ≈ {eta:.0f} h ≈ {eta / 24:.1f} days.", ""]
    with open(os.path.join(OUT, "PLUMBING_REPORT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
