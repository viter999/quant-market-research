"""Kronos-small forecasts on Google Colab GPU, per PREREG_kronos.md §6 and AMENDMENT 2.

Mirrors scripts/run_forecasts.py (same context, seed, model call and CSV columns); only the device and the
platform plumbing differ. Never computes outcomes and prints only counts.

  --self-test          2 pre-window forecasts, each twice: shapes, finite values, same-seed repeat. Writes work/selftest_ok.json
  --plumbing-check N   first N forecasts of pre-window day 2025-06-28 to work/plumbing_check.csv (laptop CPU comparison)
  (default)            full run, D = 2025-07-01 .. 2026-09-30, appended row by row to OUT/forecasts.csv, resumable

Before any forecast it checks: FREEZE_kronos.sha256 digest; SHA-256 of the universe file and the 480 data zips;
the Kronos code at the frozen commit; both model files at the pinned revisions; a SHA-256 of the parsed input bars.
"""
import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")   # deterministic cuBLAS; must precede CUDA init

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import platform
import socket
import sys
import time
import urllib.request
import uuid
import zipfile

import numpy as np
import pandas as pd

FREEZE_DIGEST = "a7b9ba2a38419443b4363a2b4d69689157dcebacb73704c1e4452269ed5fbee8"
KRONOS_COMMIT = "67b630e67f6a18c9e9be918d9b4337c960db1e9a"
HF_PINS = {  # local folder name -> (repo, revision)
    "Kronos-small@901c26c": ("NeoQuasar/Kronos-small", "901c26c1332695a2a8f243eb2f37243a37bea320"),
    "Kronos-Tokenizer-base@0e01173": ("NeoQuasar/Kronos-Tokenizer-base", "0e0117387f39004a9016484a186a908917e22426"),
}
# PREREG_kronos.md §6 (identical to scripts/kt_common.py)
CTX_BARS, PRED_BARS = 512, 24
TEMPERATURE, TOP_P, TOP_K, SAMPLE_COUNT = 1.0, 0.9, 0, 10
FULL_FIRST_DAY, FULL_LAST_DAY = "2025-07-01", "2026-09-30"
PLUMBING_DAY = "2025-06-28"
DATA_MONTHS = ("2025-06", "2026-09")
LOCK_STALE_SECONDS = 300
PINS = {"einops": "0.8.1", "safetensors": "0.6.2", "huggingface_hub": "0.33.1"}   # as on the laptop (clarification 4)

FEATURES = ["open", "high", "low", "close", "volume", "amount"]
COLS = (["day", "coin_index", "symbol", "seed", "ctx_first_open", "ctx_last_open", "ctx_rows", "ctx_cols",
         "out_rows", "out_cols", "c0", "p24", "signal"]
        + [f"pred_close_{h:02d}" for h in range(1, PRED_BARS + 1)]
        + ["seconds", "finished_utc"])
KLINE_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
              "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]
HOUR = pd.Timedelta(hours=1)
UA = {"User-Agent": "kronos-test-colab/1.0 (public data research)"}


def utcnow():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def say(msg):
    print(f"{utcnow()} {msg}", flush=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def seed_for(day, coin_index):
    return int(day.strftime("%Y%m%d")) * 100 + coin_index


def months(start, end):
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


# ---------------------------------------------------------------- integrity checks

def read_freeze(bundle):
    path = os.path.join(bundle, "FREEZE_kronos.sha256")
    if sha256_file(path) != FREEZE_DIGEST:
        raise SystemExit("FREEZE_kronos.sha256 in the bundle is not the frozen one")
    table = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line and not line.startswith("#"):
                digest, rel = line.split("  ", 1)
                table[rel.replace("\\", "/")] = digest
    return table


def check(table, rel, path):
    if not os.path.exists(path) or sha256_file(path) != table[rel]:
        raise SystemExit(f"hash mismatch: {rel}")


def fetch(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r, open(dest + ".part", "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    os.replace(dest + ".part", dest)


def prepare(bundle, work):
    """Verify bundle data, fetch + verify Kronos code and weights. Returns (universe, kronos_dir, model_dirs)."""
    table = read_freeze(bundle)
    check(table, "data/universe/universe_frozen.json", os.path.join(bundle, "data", "universe", "universe_frozen.json"))
    with open(os.path.join(bundle, "data", "universe", "universe_frozen.json")) as f:
        syms = [c["symbol"] for c in json.load(f)["universe"]]
    n = 0
    for sym in syms:
        for m in months(*DATA_MONTHS):
            rel = f"data/raw/futures_um_monthly_klines/{sym}/1h/{sym}-1h-{m}.zip"
            check(table, rel, os.path.join(bundle, *rel.split("/")))
            n += 1
    say(f"bundle ok: FREEZE digest, universe, {n} data files")

    code_root = os.path.join(work, "Kronos")
    model_py = ["__init__.py", "kronos.py", "module.py"]
    if not all(os.path.exists(os.path.join(code_root, "model", p)) for p in model_py):
        zpath = os.path.join(work, f"Kronos-{KRONOS_COMMIT}.zip")
        fetch(f"https://codeload.github.com/shiyu-coder/Kronos/zip/{KRONOS_COMMIT}", zpath)
        prefix = f"Kronos-{KRONOS_COMMIT}/model/"
        with zipfile.ZipFile(zpath) as z:
            for p in model_py:
                os.makedirs(os.path.join(code_root, "model"), exist_ok=True)
                with open(os.path.join(code_root, "model", p), "wb") as f:
                    f.write(z.read(prefix + p))
    for p in model_py:
        check(table, f"repo/Kronos/model/{p}", os.path.join(code_root, "model", p))

    model_dirs = {}
    for folder, (repo, rev) in HF_PINS.items():
        d = os.path.join(work, "models", folder)
        for name in ("config.json", "model.safetensors"):
            dest = os.path.join(d, name)
            rel = f"models/{folder}/{name}"
            if not os.path.exists(dest) or sha256_file(dest) != table[rel]:
                fetch(f"https://huggingface.co/{repo}/resolve/{rev}/{name}", dest)
            check(table, rel, dest)
        model_dirs[folder] = d
    say(f"code ok: Kronos model/*.py at {KRONOS_COMMIT[:7]}; weights ok at the pinned revisions")
    return syms, code_root, model_dirs


# ---------------------------------------------------------------- data (same parsing as scripts/kt_binance.py)

def read_klines(path):
    with zipfile.ZipFile(path) as z:
        members = [m for m in z.namelist() if m.endswith(".csv")]
        if len(members) != 1 or "/" in members[0] or "\\" in members[0] or ".." in members[0]:
            raise RuntimeError(f"unexpected zip layout in {path}")
        raw = z.read(members[0])
    first = raw.split(b"\n", 1)[0]
    header = 0 if first[:1].isalpha() else None
    df = pd.read_csv(io.BytesIO(raw), header=header)
    df.columns = KLINE_COLS
    t = df["open_time"].astype("int64")
    unit = "us" if t.max() > 10**14 else "ms"
    df["open_time"] = pd.to_datetime(t, unit=unit, utc=True).dt.tz_localize(None).astype("datetime64[ns]")
    return df


def load_1h_bars(bundle, sym):
    parts = [read_klines(os.path.join(bundle, "data", "raw", "futures_um_monthly_klines", sym, "1h",
                                      f"{sym}-1h-{m}.zip")) for m in months(*DATA_MONTHS)]
    df = pd.concat(parts, ignore_index=True).set_index("open_time").sort_index()
    if not df.index.is_unique:
        raise RuntimeError(f"duplicate bars for {sym}")
    out = df[["open", "high", "low", "close", "volume"]].astype(float)
    out["amount"] = df["quote_volume"].astype(float)
    return out


def bars_digest(df):
    """SHA-256 of the parsed bars: open_time as int64 ns, then the six features as float64, row-major."""
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(df.index.values.astype("datetime64[ns]").view("int64")).tobytes())
    h.update(np.ascontiguousarray(df[FEATURES].to_numpy(dtype=np.float64)).tobytes())
    return h.hexdigest()


def load_and_check_bars(bundle, syms):
    with open(os.path.join(bundle, "expected_bars_sha256.json")) as f:
        expected = json.load(f)
    bars = {}
    for sym in syms:
        bars[sym] = load_1h_bars(bundle, sym)
        if bars_digest(bars[sym]) != expected[sym]:
            raise SystemExit(f"parsed input bars for {sym} differ from the laptop's frozen loader")
    say(f"parsed input bars identical to the laptop's for all {len(syms)} coins")
    return bars


# ---------------------------------------------------------------- model (same call as scripts/run_forecasts.py)

def load_predictor(code_root, model_dirs, device, threads):
    import torch
    if device.startswith("cuda"):
        if not torch.cuda.is_available():
            raise SystemExit("No GPU in this runtime. Runtime > Change runtime type > T4 GPU, then Runtime > Run all.")
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        torch.use_deterministic_algorithms(True, warn_only=True)
    else:
        torch.set_num_threads(threads)
    if code_root not in sys.path:
        sys.path.insert(0, code_root)
    from model import Kronos, KronosTokenizer, KronosPredictor
    tokenizer = KronosTokenizer.from_pretrained(model_dirs["Kronos-Tokenizer-base@0e01173"])
    model = Kronos.from_pretrained(model_dirs["Kronos-small@901c26c"])
    tokenizer.eval()
    model.eval()
    return KronosPredictor(model, tokenizer, device=device, max_context=512)


def context(bars, day):
    expected = pd.date_range(day - CTX_BARS * HOUR, periods=CTX_BARS, freq="h", unit="ns")
    ctx = bars.loc[expected[0]:day - HOUR]
    if len(ctx) != CTX_BARS or not ctx.index.equals(expected) or ctx[FEATURES].isna().any().any():
        return None
    assert ctx.index[-1] < day
    return ctx


def forecast(predictor, ctx, day, seed):
    import torch
    torch.manual_seed(seed)
    np.random.seed(seed % 2**32)
    x_ts = pd.Series(ctx.index)
    y_ts = pd.Series(pd.date_range(day, periods=PRED_BARS, freq="h", unit="ns"))
    return predictor.predict(df=ctx[FEATURES].reset_index(drop=True), x_timestamp=x_ts, y_timestamp=y_ts,
                             pred_len=PRED_BARS, T=TEMPERATURE, top_k=TOP_K, top_p=TOP_P,
                             sample_count=SAMPLE_COUNT, verbose=False)


def make_row(day, i, sym, seed, ctx, pred, secs):
    closes = pred["close"].to_numpy(dtype=float)
    if pred.shape != (PRED_BARS, len(FEATURES)) or not np.isfinite(pred.to_numpy(dtype=float)).all():
        raise SystemExit(f"bad model output for coin {i} on {day.date()}: shape {pred.shape}")
    c0 = float(ctx["close"].iloc[-1])
    p24 = float(closes[-1])
    row = {"day": day.strftime("%Y-%m-%d"), "coin_index": i, "symbol": sym, "seed": seed,
           "ctx_first_open": str(ctx.index[0]), "ctx_last_open": str(ctx.index[-1]),
           "ctx_rows": ctx[FEATURES].shape[0], "ctx_cols": ctx[FEATURES].shape[1],
           "out_rows": pred.shape[0], "out_cols": pred.shape[1],
           "c0": repr(c0), "p24": repr(p24), "signal": int(np.sign(p24 - c0)),
           "seconds": f"{secs:.2f}", "finished_utc": utcnow()}
    row.update({f"pred_close_{h:02d}": repr(float(v)) for h, v in enumerate(closes, 1)})
    return row


# ---------------------------------------------------------------- output file (same resume rules as the CPU runner)

def load_done(path):
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


def write_json(path, obj):
    with open(path + ".tmp", "w") as f:
        json.dump(obj, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(path + ".tmp", path)


def take_lock(out, session):
    """Refuse if another live session is writing to this Drive folder."""
    path = os.path.join(out, "run.lock.json")
    if os.path.exists(path):
        try:
            with open(path) as f:
                lk = json.load(f)
        except (OSError, ValueError):
            lk = {}
        age = time.time() - lk.get("heartbeat", 0)
        same_vm_dead = (lk.get("host") == socket.gethostname() and os.name == "posix"
                        and not os.path.exists(f"/proc/{lk.get('pid', -1)}"))
        if lk.get("session") != session and age < LOCK_STALE_SECONDS and not same_vm_dead:
            raise SystemExit(f"another session wrote here {int(age)} s ago. If none is running, wait "
                             f"{LOCK_STALE_SECONDS // 60} minutes and run again.")
    beat(out, session)


def release_lock(out, session):
    path = os.path.join(out, "run.lock.json")
    try:
        with open(path) as f:
            mine = json.load(f).get("session") == session
    except (OSError, ValueError):
        return
    if mine:   # removed after the file is closed (Windows cannot delete an open file)
        os.remove(path)


def beat(out, session):
    write_json(os.path.join(out, "run.lock.json"),
               {"session": session, "host": socket.gethostname(), "pid": os.getpid(), "heartbeat": time.time()})


def check_pins():
    found = {mod: __import__(mod).__version__ for mod in PINS}
    if found != PINS:
        raise SystemExit(f"pinned helper packages missing: need {PINS}, found {found}. Rerun the pip cell.")


def environment(device):
    import torch
    env = {"python": platform.python_version(), "torch": torch.__version__, "numpy": np.__version__,
           "pandas": pd.__version__, "device": device, "host": socket.gethostname()}
    if device.startswith("cuda"):
        env.update({"cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0)})
    for mod in PINS:
        env[mod] = __import__(mod).__version__
    return env


# ---------------------------------------------------------------- modes

def drive_probe(out, n=30):
    """Time n append+fsync writes of dummy text (not forecasts) in the Drive run folder, then delete the file."""
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "selftest_drive_probe.tmp")
    t0 = time.perf_counter()
    for k in range(n):
        with open(path, "a", encoding="utf-8", newline="") as f:
            f.write(f"probe line {k} " + "x" * 900 + "\n")
            f.flush()
            os.fsync(f.fileno())
    secs = (time.perf_counter() - t0) / n
    os.remove(path)
    return round(secs, 3)


def self_test(predictor, bars, syms, work, out=None):
    day = pd.Timestamp(PLUMBING_DAY)
    result = {"pre_window_day": PLUMBING_DAY, "checks": {}}
    secs = []
    for i in (0, 1):
        ctx = context(bars[syms[i]], day)
        if ctx is None:
            raise SystemExit("self-test: context incomplete")
        seed = seed_for(day, i)
        runs = []
        for _ in range(2):
            t0 = time.perf_counter()
            pred = forecast(predictor, ctx, day, seed)
            secs.append(time.perf_counter() - t0)
            make_row(day, i, syms[i], seed, ctx, pred, secs[-1])   # raises on bad shape or non-finite values
            runs.append(pred.to_numpy(dtype=float))
        result["checks"][f"coin_{i}_same_seed_bit_identical"] = bool(np.array_equal(runs[0], runs[1]))
    result["shapes_and_finite"] = True
    result["seconds_per_forecast_after_warmup"] = round(float(np.mean(secs[1:])), 2)
    result["drive_seconds_per_row_write"] = drive_probe(out) if out else None
    result["finished_utc"] = utcnow()
    write_json(os.path.join(work, "selftest_ok.json"), result)
    same = all(result["checks"].values())
    say(f"self-test passed: shapes (512,6)->(24,6), finite outputs; same-seed repeat "
        f"{'bit-identical' if same else 'NOT bit-identical on this GPU (recorded; run continues)'}; "
        f"{result['seconds_per_forecast_after_warmup']} s per forecast; "
        f"Drive write {result['drive_seconds_per_row_write']} s per row")


def plumbing_check(predictor, bars, syms, work, n):
    day = pd.Timestamp(PLUMBING_DAY)
    path = os.path.join(work, "plumbing_check.csv")
    if os.path.exists(path):
        os.remove(path)
    for i in range(n):
        ctx = context(bars[syms[i]], day)
        seed = seed_for(day, i)
        t0 = time.perf_counter()
        pred = forecast(predictor, ctx, day, seed)
        append_row(path, make_row(day, i, syms[i], seed, ctx, pred, time.perf_counter() - t0))
    say(f"plumbing check: {n} pre-window forecasts written to {path}")


def full_run(predictor, bars, syms, out, device, session, work, bundle_sha, rehearsal=False, max_new=0):
    """rehearsal=True: same code path on 1 pre-window day x 2 coins (laptop test only)."""
    os.makedirs(out, exist_ok=True)
    take_lock(out, session)
    env = environment(device)
    selftest = None
    if os.path.exists(os.path.join(work, "selftest_ok.json")):
        with open(os.path.join(work, "selftest_ok.json")) as f:
            selftest = json.load(f)
    line = {"session": session, "started_utc": utcnow(), **env, "bundle_sha256": bundle_sha,
            "script_sha256": sha256_file(os.path.abspath(__file__)), "selftest": selftest}
    with open(os.path.join(out, "colab_sessions.log"), "a") as f:
        f.write(json.dumps(line) + "\n")
        f.flush()
        os.fsync(f.fileno())
    csv_path = os.path.join(out, "forecasts.csv")
    if rehearsal:
        days, syms = [pd.Timestamp(PLUMBING_DAY)], syms[:2]
    else:
        days = list(pd.date_range(FULL_FIRST_DAY, FULL_LAST_DAY, freq="D"))
    total = len(days) * len(syms)
    done = load_done(csv_path)
    todo = [(d, i, s) for d in days for i, s in enumerate(syms) if (d.strftime("%Y-%m-%d"), s) not in done]
    say(f"session {session} on {env.get('gpu', device)}: {len(done)} done, {len(todo)} to do, {total} total")
    recent, new = [], 0
    for day, i, sym in todo:
        w0 = time.perf_counter()
        ctx = context(bars[sym], day)
        if ctx is None:
            raise SystemExit(f"incomplete context for coin {i} on {day.date()}: run stopped")
        seed = seed_for(day, i)
        t0 = time.perf_counter()
        pred = forecast(predictor, ctx, day, seed)
        secs = time.perf_counter() - t0
        append_row(csv_path, make_row(day, i, sym, seed, ctx, pred, secs))
        new += 1
        if new % 10 == 0:
            beat(out, session)
        recent = (recent + [time.perf_counter() - w0])[-100:]   # wall time incl. the Drive write, for the ETA
        n_done = len(done) + new
        if new % 30 == 0 or n_done == total:
            rate = float(np.mean(recent))
            write_json(os.path.join(out, "colab_status.json"),
                       {"updated_utc": utcnow(), "done": n_done, "total": total, "sec_per_forecast": round(rate, 2)})
            say(f"done {n_done}/{total}  ({rate:.2f} s per forecast, about {(total - n_done) * rate / 3600:.1f} h left)")
        if max_new and new >= max_new:
            say(f"stopped on purpose after {new} new forecasts")
            return
    final = load_done(csv_path)
    if len(final) != total:
        raise SystemExit(f"only {len(final)}/{total} rows; run the notebook again to resume")
    manifest = {"complete": True, "rows": total, "forecasts_csv_sha256": sha256_file(csv_path),
                "finished_utc": utcnow(), "freeze_digest": FREEZE_DIGEST, "kronos_commit": KRONOS_COMMIT,
                "script_sha256": sha256_file(os.path.abspath(__file__)), "last_session": env}
    write_json(os.path.join(out, "colab_manifest.json"), manifest)
    say(f"COMPLETE: {total}/{total} forecasts. Download forecasts.csv, colab_manifest.json and colab_sessions.log.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", help="Drive folder for the full run")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--threads", type=int, default=6, help="CPU threads (laptop comparison only)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--plumbing-check", type=int, default=0)
    ap.add_argument("--rehearsal", action="store_true", help="laptop test: full-run code path on 1 pre-window day x 2 coins")
    ap.add_argument("--max-new", type=int, default=0, help="laptop test: stop after N new forecasts")
    ap.add_argument("--bundle-sha", default="", help="SHA-256 of the bundle zip, as checked by the notebook")
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)

    check_pins()
    syms, code_root, model_dirs = prepare(args.bundle, args.work)
    bars = load_and_check_bars(args.bundle, syms)
    predictor = load_predictor(code_root, model_dirs, args.device, args.threads)
    if args.self_test:
        self_test(predictor, bars, syms, args.work, args.out)
    elif args.plumbing_check:
        plumbing_check(predictor, bars, syms, args.work, args.plumbing_check)
    else:
        if not args.out or not args.bundle_sha:
            raise SystemExit("--out and --bundle-sha are required for the full run")
        session = uuid.uuid4().hex[:12]
        try:
            full_run(predictor, bars, syms, args.out, args.device, session, args.work, args.bundle_sha,
                     rehearsal=args.rehearsal, max_new=args.max_new)
        finally:
            release_lock(args.out, session)


if __name__ == "__main__":
    main()
