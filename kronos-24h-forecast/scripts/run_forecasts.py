"""Kronos-small daily forecasts, exactly as PREREG_kronos.md §6 and §9.

  --mode plumbing   D = 2025-06-28 .. 2025-06-30 -> results/plumbing/forecasts.csv (pre-window, checks only)
  --mode full       D = 2025-07-01 .. 2026-09-30 -> results/forecasts.csv, then analyze.py once

Never computes outcomes. Each model call receives only the 512 bars with open_time < D.
Resumable: rows already in the CSV are skipped; every row is flushed and fsynced.
Runs at below-normal priority, asks Windows not to idle-sleep, pauses while on battery.
"""
import argparse
import csv
import datetime as dt
import io
import msvcrt
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kt_common as kt
import kt_binance as kb

import numpy as np
import pandas as pd

COLS = (["day", "coin_index", "symbol", "seed", "ctx_first_open", "ctx_last_open", "ctx_rows", "ctx_cols",
         "out_rows", "out_cols", "c0", "p24", "signal"]
        + [f"pred_close_{h:02d}" for h in range(1, kt.PRED_BARS + 1)]
        + ["seconds", "finished_utc"])
FEATURES = ["open", "high", "low", "close", "volume", "amount"]
HOUR = pd.Timedelta(hours=1)


def utcnow():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Log:
    def __init__(self, path):
        self.path = path

    def __call__(self, msg):
        line = f"{utcnow()} {msg}"
        print(line, flush=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def days_for(mode):
    if mode == "full":
        return list(pd.date_range(kt.FULL_FIRST_DAY, kt.FULL_LAST_DAY, freq="D"))
    return [pd.Timestamp(d) for d in kt.PLUMBING_DAYS]


def context(bars, day):
    """The 512 bars with open_time D-512h .. D-1h, or None if they are not all there."""
    expected = pd.date_range(day - kt.CTX_BARS * HOUR, periods=kt.CTX_BARS, freq="h")
    ctx = bars.loc[expected[0]:day - HOUR]
    if len(ctx) != kt.CTX_BARS or not ctx.index.equals(expected) or ctx[FEATURES].isna().any().any():
        return None
    assert ctx.index[-1] < day
    return ctx


def forecast(predictor, ctx, day, seed):
    import torch
    torch.manual_seed(seed)
    np.random.seed(seed % 2**32)
    x_ts = pd.Series(ctx.index)
    y_ts = pd.Series(pd.date_range(day, periods=kt.PRED_BARS, freq="h"))
    return predictor.predict(df=ctx[FEATURES].reset_index(drop=True), x_timestamp=x_ts, y_timestamp=y_ts,
                             pred_len=kt.PRED_BARS, T=kt.TEMPERATURE, top_k=kt.TOP_K, top_p=kt.TOP_P,
                             sample_count=kt.SAMPLE_COUNT, verbose=False)


def load_done(path):
    """(day, symbol) pairs already written; drops a partial last line left by a crash."""
    if not os.path.exists(path):
        return set()
    with open(path, "rb+") as f:
        data = f.read()
        if data and not data.endswith(b"\n"):
            f.truncate(data.rfind(b"\n") + 1)
    if os.path.getsize(path) == 0:
        os.remove(path)
        return set()
    df = pd.read_csv(path, dtype=str)
    if list(df.columns) != COLS:
        raise SystemExit(f"unexpected header in {path}")
    pairs = list(zip(df.day, df.symbol))
    if len(pairs) != len(set(pairs)):
        raise SystemExit(f"duplicate rows in {path}")
    return set(pairs)


def append_row(path, row):
    new = not os.path.exists(path)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    if new:
        w.writerow(COLS)
    w.writerow([row[c] for c in COLS])
    with open(path, "a", encoding="utf-8", newline="") as f:
        f.write(buf.getvalue())
        f.flush()
        os.fsync(f.fileno())


def write_progress(path, done, total, recent, on_batt):
    rate = float(np.mean(recent)) if recent else float("nan")
    eta_h = (total - done) * rate / 3600 if recent else float("nan")
    text = (f"updated_utc      {utcnow()}\n"
            f"forecasts_done   {done} / {total}\n"
            f"sec_per_forecast {rate:.1f} (last {len(recent)})\n"
            f"eta_hours        {eta_h:.1f}\n"
            f"on_battery       {on_batt}\n")
    with open(path + ".tmp", "w") as f:
        f.write(text)
    os.replace(path + ".tmp", path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["plumbing", "full"], required=True)
    ap.add_argument("--stop-after", type=int, default=0, help="exit after N new forecasts (plumbing resume test)")
    args = ap.parse_args()

    kt.below_normal_priority()
    kt.keep_awake(True)
    out_dir = kt.RESULTS if args.mode == "full" else os.path.join(kt.RESULTS, "plumbing")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(kt.LOGS, exist_ok=True)
    log = Log(os.path.join(kt.LOGS, f"run_{args.mode}.log"))

    lock = open(os.path.join(out_dir, "run.lock"), "a+")
    lock.seek(0)
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        log("another run already holds the lock; exiting")
        sys.exit(2)

    n_frozen = kt.verify_freeze()
    log(f"start mode={args.mode} pid={os.getpid()} freeze ok ({n_frozen} files)")

    syms = kt.universe()
    bars = {s: kb.load_1h_bars(s, *kt.DATA_MONTHS) for s in syms}
    days = days_for(args.mode)
    csv_path = os.path.join(out_dir, "forecasts.csv")
    done = load_done(csv_path)
    total = len(days) * len(syms)
    todo = [(d, i, s) for d in days for i, s in enumerate(syms) if (d.strftime("%Y-%m-%d"), s) not in done]
    log(f"{len(done)} rows already present, {len(todo)} to do, {total} in this mode")

    predictor = kt.load_predictor(threads=kt.THREADS)
    progress = os.path.join(out_dir, "progress.txt")
    recent, new, skipped = [], 0, 0
    for day, i, sym in todo:
        if kt.on_battery():
            log("on battery: pausing until AC power returns")
            write_progress(progress, len(done) + new, total, recent, True)
            while kt.on_battery():
                time.sleep(60)
            log("AC power back: resuming")
        ctx = context(bars[sym], day)
        if ctx is None:
            if args.mode == "full":
                raise SystemExit(f"incomplete context for {sym} on {day.date()}: run stopped")
            skipped += 1
            log(f"plumbing: skip {sym} {day.date()} (not 512 pre-window bars)")
            continue
        seed = kt.seed_for(day, i)
        t0 = time.perf_counter()
        pred = forecast(predictor, ctx, day, seed)
        secs = time.perf_counter() - t0
        closes = pred["close"].to_numpy(dtype=float)
        if pred.shape != (kt.PRED_BARS, len(FEATURES)) or not np.isfinite(pred.to_numpy(dtype=float)).all():
            raise SystemExit(f"bad model output for {sym} on {day.date()}: shape {pred.shape}")
        c0 = float(ctx["close"].iloc[-1])
        p24 = float(closes[-1])
        row = {"day": day.strftime("%Y-%m-%d"), "coin_index": i, "symbol": sym, "seed": seed,
               "ctx_first_open": str(ctx.index[0]), "ctx_last_open": str(ctx.index[-1]),
               "ctx_rows": ctx[FEATURES].shape[0], "ctx_cols": ctx[FEATURES].shape[1],
               "out_rows": pred.shape[0], "out_cols": pred.shape[1],
               "c0": repr(c0), "p24": repr(p24), "signal": int(np.sign(p24 - c0)),
               "seconds": f"{secs:.2f}", "finished_utc": utcnow()}
        row.update({f"pred_close_{h:02d}": repr(float(v)) for h, v in enumerate(closes, 1)})
        append_row(csv_path, row)
        new += 1
        recent = (recent + [secs])[-50:]
        write_progress(progress, len(done) + new, total, recent, False)
        if new % 30 == 0:
            log(f"{len(done) + new}/{total} done, {np.mean(recent):.1f}s per forecast")
        if args.stop_after and new >= args.stop_after:
            log(f"stop-after {args.stop_after} reached; exiting on purpose")
            return

    final = len(load_done(csv_path))
    log(f"loop finished: {final} rows, {skipped} skipped")
    if args.mode == "full":
        if final != total:
            raise SystemExit(f"only {final}/{total} rows; not starting the analysis")
        log("all forecasts present: running analyze.py (one look)")
        rc = subprocess.run([sys.executable, "-I", os.path.join(os.path.dirname(__file__), "analyze.py")]).returncode
        log(f"analyze.py exited {rc}")
    kt.keep_awake(False)


if __name__ == "__main__":
    main()
