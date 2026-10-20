"""Accept the Colab forecasts and run the ONE analysis (AMENDMENT 2, clarifications 1, 2 and 7).

  accept_colab.py --preflight                     report the CPU run's state (runner PIDs, task, launcher, count); change nothing
  accept_colab.py --download PATH --check-only    verify the Colab files; change nothing
  accept_colab.py --download PATH                 verify; stop the CPU runner and hold its lock; decide again under the
                                                  lock; only then disarm the CPU run, retire its file unopened, install
                                                  the Colab file and run the frozen analyze.py once

PATH is the folder, or the .zip Google Drive makes, holding forecasts.csv, colab_manifest.json, colab_sessions.log.
The CPU run's forecasts.csv is never read: it is only hashed and moved. Run it detached (its own window), so no
caller timeout can interrupt the analysis. Everything it says also goes to logs/accept_colab.log.
--sandbox DIR runs every step against a throwaway layout under C:\\kronos-test\\tmp (laptop test only).
"""
import argparse
import datetime as dt
import glob
import json
import msvcrt
import os
import shutil
import subprocess
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REAL_ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REAL_ROOT, "scripts"))
import kt_common as kt
import kt_binance as kb
import analyze
from run_forecasts import COLS

import numpy as np
import pandas as pd

TASK_NAME = "KronosTest-ResumeFullRun"
TOTAL = 13710
NEAR_END = 13700          # CPU this close to the end: refuse and leave the decision to the owner
PINS = {"einops": "0.8.1", "safetensors": "0.6.2", "huggingface_hub": "0.33.1"}
HOUR = pd.Timedelta(hours=1)
LOG_PATH = None


def utcnow():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def say(msg):
    line = f"{utcnow()} {msg}"
    print(line, flush=True)
    if LOG_PATH:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")


class Layout:
    def __init__(self, root):
        self.root = root
        self.results = os.path.join(root, "results")
        self.cpu_csv = os.path.join(self.results, "forecasts.csv")
        self.progress = os.path.join(self.results, "progress.txt")
        self.lock = os.path.join(self.results, "run.lock")
        self.report = os.path.join(self.results, "REPORT_kronos.md")
        self.analysis_json = os.path.join(self.results, "analysis.json")
        self.daily_csv = os.path.join(self.results, "daily_series.csv")
        self.retired = os.path.join(self.results, "retired_cpu_run")
        self.cmd = os.path.join(root, "START_OR_RESUME_FULL_RUN.cmd")
        self.amendments = os.path.join(root, "AMENDMENTS_kronos.md")
        self.incoming = os.path.join(root, "incoming")
        self.freeze = os.path.join(root, "FREEZE_kronos.sha256")
        self.logs = os.path.join(root, "logs")
        self.cpu_log = os.path.join(self.logs, "run_full.log")
        self.attempts = os.path.join(self.logs, "analysis_attempts.log")


# ---------------------------------------------------------------- expected Colab hashes

def expected_hashes(sandbox):
    """SHA-256 the Colab sessions must report: the shipped colab_forecasts.py and the bundle zip.

    Real mode also requires colab/FREEZE_colab.sha256 (whose digest is in AMENDMENTS_kronos.md) to match every file.
    """
    script = kt.sha256_file(os.path.join(HERE, "colab_forecasts.py"))
    bundle = kt.sha256_file(os.path.join(HERE, "kronos_colab_bundle.zip"))
    if not sandbox:
        path = os.path.join(HERE, "FREEZE_colab.sha256")
        if not os.path.exists(path):
            raise SystemExit("colab/FREEZE_colab.sha256 missing")
        table = {}
        for line in open(path, encoding="utf-8"):
            line = line.rstrip("\n")
            if line and not line.startswith("#"):
                digest, rel = line.split("  ", 1)
                table[rel] = digest
                if kt.sha256_file(os.path.join(REAL_ROOT, rel)) != digest:
                    raise SystemExit(f"{rel} changed since the Colab freeze")
        if table.get("colab/colab_forecasts.py") != script or table.get("colab/kronos_colab_bundle.zip") != bundle:
            raise SystemExit("FREEZE_colab.sha256 does not list the Colab script and bundle")
    return script, bundle


# ---------------------------------------------------------------- 1. find and verify the Colab files (read-only)

def gather(download, lay):
    names = ("forecasts.csv", "colab_manifest.json", "colab_sessions.log")
    if os.path.isfile(download) and download.lower().endswith(".zip"):
        dest = os.path.join(lay.incoming, "colab_" + utcnow().replace(":", "").replace("-", ""))
        os.makedirs(dest)
        with zipfile.ZipFile(download) as z:
            for n in z.namelist():
                if n.startswith(("/", "\\")) or ".." in n.replace("\\", "/").split("/") or ":" in n:
                    raise SystemExit(f"unsafe path in the download zip: {n}")
            z.extractall(dest)
        base = dest
    elif os.path.isdir(download):
        base = download
    else:
        raise SystemExit(f"not a folder or .zip: {download}")
    found = {}
    for n in names:
        hits = glob.glob(os.path.join(base, "**", n), recursive=True)
        if len(hits) != 1:
            raise SystemExit(f"expected exactly one {n} in {download}, found {len(hits)}")
        found[n] = hits[0]
    return found


def verify(files, lay, exp_script, exp_bundle, sandbox):
    """All checks on the Colab output. Reads forecasts, inputs and hashes; never outcomes. Raises on any problem."""
    with open(files["colab_manifest.json"]) as f:
        man = json.load(f)
    problems = []
    if man.get("complete") is not True:
        problems.append("manifest does not say complete")
    if man.get("rows") != TOTAL:
        problems.append(f"manifest rows {man.get('rows')} != {TOTAL}")
    if man.get("freeze_digest") != kt.sha256_file(lay.freeze):
        problems.append("manifest freeze digest differs from FREEZE_kronos.sha256")
    if man.get("kronos_commit") != kt.KRONOS_COMMIT:
        problems.append("manifest Kronos commit differs")
    if man.get("script_sha256") != exp_script:
        problems.append("manifest script hash differs from the frozen colab_forecasts.py")
    if not isinstance(man.get("last_session"), dict):
        problems.append("manifest has no session record")
    digest = kt.sha256_file(files["forecasts.csv"])
    if man.get("forecasts_csv_sha256") != digest:
        problems.append("forecasts.csv SHA-256 does not match the manifest (incomplete or altered download)")
    sessions = [json.loads(line) for line in open(files["colab_sessions.log"]) if line.strip()]
    if not sessions:
        problems.append("no Colab session recorded")
    for s in sessions:
        sid = s.get("session", "?")
        if not str(s.get("device", "")).startswith("cuda") or not s.get("gpu") or not s.get("cuda") or not s.get("torch"):
            problems.append(f"session {sid} did not record a CUDA GPU run")
        if s.get("script_sha256") != exp_script:
            problems.append(f"session {sid} ran a different colab_forecasts.py")
        if s.get("bundle_sha256") != exp_bundle:
            problems.append(f"session {sid} used a different bundle")
        if any(s.get(k) != v for k, v in PINS.items()):
            problems.append(f"session {sid} did not have the pinned helper packages")
        if not sandbox and "sandbox" in str(s.get("gpu", "")).lower():
            problems.append(f"session {sid} is a laptop sandbox fixture, not a Colab run")
    if problems:
        raise SystemExit("REJECTED: " + "; ".join(sorted(set(problems))))

    fc = pd.read_csv(files["forecasts.csv"], dtype=str)
    if list(fc.columns) != COLS:
        raise SystemExit("REJECTED: column layout differs from the frozen runner")
    syms = kt.universe()
    days = list(pd.date_range(kt.FULL_FIRST_DAY, kt.FULL_LAST_DAY, freq="D"))
    analyze.validate(fc, syms, days)   # frozen checks: 13,710 rows, no duplicates, days, coins, seeds, signal rule
    D = pd.to_datetime(fc.day)
    preds = fc[[f"pred_close_{h:02d}" for h in range(1, 25)]].astype(float).to_numpy()
    shape_ok = ((fc.ctx_rows == "512") & (fc.ctx_cols == "6") & (fc.out_rows == "24") & (fc.out_cols == "6")).all()
    ctx_ok = ((pd.to_datetime(fc.ctx_first_open) == D - 512 * HOUR) & (pd.to_datetime(fc.ctx_last_open) == D - HOUR)).all()
    if not (shape_ok and ctx_ok and np.isfinite(preds).all()
            and np.array_equal(preds[:, -1], fc.p24.astype(float).to_numpy())):
        raise SystemExit("REJECTED: shapes, context window or predicted closes are inconsistent")
    for sym, g in fc.groupby("symbol"):
        close = kb.load_1h_bars(sym, *kt.DATA_MONTHS)["close"]
        if not np.array_equal(close.reindex(pd.to_datetime(g.day) - HOUR).to_numpy(), g.c0.astype(float).to_numpy()):
            raise SystemExit(f"REJECTED: c0 differs from the frozen input data for {sym}")
    gpus = sorted({s.get("gpu", "?") for s in sessions})
    say(f"Colab files pass: {TOTAL:,} rows, SHA-256 {digest}, {len(sessions)} session(s) on {', '.join(gpus)}")
    return digest, sessions


# ---------------------------------------------------------------- 2. CPU run state (counts and file names only)

def python_processes():
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine } | "
          "Select-Object ProcessId, CommandLine | ConvertTo-Json -Compress")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("could not list processes")
    out = r.stdout.strip()
    rows = json.loads(out) if out else []
    rows = rows if isinstance(rows, list) else [rows]
    mine = {os.getpid(), os.getppid()}   # never this script or its venv launcher
    return [r for r in rows if r["ProcessId"] not in mine and "accept_colab.py" not in r["CommandLine"].lower()]


def matching(procs, parts):
    return [r["ProcessId"] for r in procs if all(p.lower() in r["CommandLine"].lower() for p in parts)]


def cpu_state(lay, runner_parts):
    done = None
    if os.path.exists(lay.progress):
        for line in open(lay.progress):
            if line.startswith("forecasts_done"):
                done = int(line.split()[1])
    procs = python_processes()
    return {
        "done": done,
        "log_complete": os.path.exists(lay.cpu_log) and "all forecasts present" in open(lay.cpu_log, encoding="utf-8").read(),
        "report": os.path.exists(lay.report),
        "analysis_started": (os.path.exists(lay.attempts) and os.path.getsize(lay.attempts) > 0)
                            or os.path.exists(lay.analysis_json) or os.path.exists(lay.daily_csv),
        "analyze_procs": matching(procs, ["analyze.py"]),
        "runner_procs": matching(procs, runner_parts),
    }


def blockers(st):
    b = []
    if st["report"]:
        b.append("REPORT_kronos.md exists: the one look has been taken")
    if st["analysis_started"]:
        b.append("an analysis has already started once (attempts log or outputs exist): owner decision needed")
    if st["analyze_procs"]:
        b.append(f"an analyze.py process is running: {st['analyze_procs']}")
    if st["log_complete"] or (st["done"] is not None and st["done"] >= TOTAL):
        b.append("the CPU run reached 13,710 first, so the CPU run counts and Colab is retired unopened")
    elif st["done"] is not None and st["done"] >= NEAR_END:
        b.append(f"the CPU run is at {st['done']}, within {TOTAL - NEAR_END} of the end: owner decides")
    return b


def task_exists(task_name):
    return bool(task_name) and subprocess.run(["schtasks", "/Query", "/TN", task_name], capture_output=True).returncode == 0


def take_lock(lay, seconds=60):
    f = open(lay.lock, "a+")
    f.seek(0)
    t0 = time.time()
    while True:
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            return f
        except OSError:
            if time.time() - t0 > seconds:
                f.close()
                return None
            time.sleep(1)


def log_amendment(lay, text):
    with open(lay.amendments, "a", encoding="utf-8") as f:
        f.write(text.rstrip("\n") + "\n")
        f.flush()
        os.fsync(f.fileno())


def append_fsync(path, text):
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())


# ---------------------------------------------------------------- 3. retire the CPU run and analyse once

def preflight(lay, runner_parts, task_name):
    st = cpu_state(lay, runner_parts)
    say(f"preflight: CPU runner processes {st['runner_procs']} (expect 2: launcher + child), "
        f"log-on task {'present' if task_exists(task_name) else 'absent'}, "
        f"launcher {'present' if os.path.exists(lay.cmd) else 'absent'}, CPU forecasts done {st['done']}")
    b = blockers(st)
    say("preflight: acceptance would " + ("be REFUSED: " + "; ".join(b) if b else "be allowed") + ". Nothing changed.")


def accept(files, digest, sessions, lay, runner_parts, analyze_cmd, task_name):
    # 1. decide before touching anything
    st = cpu_state(lay, runner_parts)
    b = blockers(st)
    if b:
        raise SystemExit("NOT ACCEPTED, nothing changed: " + "; ".join(b))

    # 2. stop the CPU runner and hold its lock; nothing is disarmed or moved yet
    pids = st["runner_procs"]
    for pid in pids:
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    lock = take_lock(lay)
    resume_hint = "Nothing disarmed or moved; double-click START_OR_RESUME_FULL_RUN.cmd to resume the CPU run."
    if lock is None:
        raise SystemExit(f"could not take the CPU runner's lock (killed {pids}). {resume_hint}")
    try:
        left = matching(python_processes(), runner_parts)
        if left:
            raise SystemExit(f"CPU runner processes still alive: {left}. {resume_hint}")
        say(f"CPU run stopped ({len(pids)} process(es)); holding its lock")

        # 3. decide again, now that the CPU run cannot move
        b = blockers(cpu_state(lay, runner_parts))
        if b:
            raise SystemExit("NOT ACCEPTED after stopping the CPU run: " + "; ".join(b) + ". " + resume_hint)
        say("accepted: retiring the CPU run (clarification 7)")

        # 4. switch off its automatic analysis: no log-on restart, no launcher
        if task_name:
            if task_exists(task_name):
                d = subprocess.run(["schtasks", "/Delete", "/TN", task_name, "/F"], capture_output=True, text=True)
                if d.returncode != 0:
                    raise SystemExit(f"could not delete task {task_name}: {d.stderr.strip()}")
            if task_exists(task_name):
                raise SystemExit(f"task {task_name} still exists")
            say(f"log-on task {task_name} removed")
        if os.path.exists(lay.cmd):
            os.replace(lay.cmd, lay.cmd + ".retired")
        say("launcher renamed to START_OR_RESUME_FULL_RUN.cmd.retired")

        # 5. retire the CPU files unopened: record hash and size first, then move
        os.makedirs(lay.retired, exist_ok=True)
        ledger = os.path.join(lay.retired, "RETIRED.txt")
        notes = []
        for src in (lay.cpu_csv, lay.progress):
            if not os.path.exists(src):
                continue
            sha, size = kt.sha256_file(src), os.path.getsize(src)
            if src == lay.cpu_csv and sha == digest:
                continue   # already the installed Colab copy from an earlier, interrupted acceptance
            dest = os.path.join(lay.retired, os.path.basename(src))
            if os.path.exists(dest):
                raise SystemExit(f"{dest} already exists; not overwriting a retired file")
            append_fsync(ledger, f"{utcnow()} retiring unopened (AMENDMENT 2, clarification 7): "
                                 f"{os.path.basename(src)} sha256 {sha} bytes {size}\n")
            os.replace(src, dest)
            notes.append(f"{os.path.basename(src)} sha256 {sha} bytes {size}")
        say("CPU files retired unopened: " + ("; ".join(notes) or "nothing new"))

        # 6. install the Colab file atomically
        part = lay.cpu_csv + ".colab.part"
        if os.path.exists(part):
            os.remove(part)
        shutil.copyfile(files["forecasts.csv"], part)
        if kt.sha256_file(part) != digest:
            raise SystemExit("copied Colab file does not match its hash")
        os.replace(part, lay.cpu_csv)
        if kt.sha256_file(lay.cpu_csv) != digest:
            raise SystemExit("installed Colab file does not match its hash")
        gpus = sorted({s.get("gpu", "?") for s in sessions})
        log_amendment(lay, f"""  - {utcnow()}: ACCEPTANCE (clarification 7). Colab forecasts accepted: {TOTAL:,} rows,
    SHA-256 {digest}, {len(sessions)} session(s) on {', '.join(gpus)}. CPU run stopped ({len(pids)} process(es)) and its
    lock held; log-on task removed; launcher renamed. Retired unopened: {'; '.join(notes) or 'nothing new'}.
    Colab file installed as results/forecasts.csv; running the frozen analyze.py once.""")

        # 7. the one analysis
        say("running the frozen analyze.py (one look)")
        rc = subprocess.run(analyze_cmd, cwd=lay.root).returncode
        log_amendment(lay, f"  - {utcnow()}: analyze.py exited {rc}; REPORT_kronos.md "
                           f"{'written' if os.path.exists(lay.report) else 'NOT written'}.")
        if rc != 0:
            raise SystemExit(f"analyze.py exited {rc}")
    finally:
        lock.close()


def main():
    global LOG_PATH
    ap = argparse.ArgumentParser()
    ap.add_argument("--download")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--sandbox", help="laptop test: root of a throwaway layout under C:\\kronos-test\\tmp")
    ap.add_argument("--sandbox-marker", help="laptop test: command-line marker of the fake CPU runner")
    args = ap.parse_args()

    if args.sandbox:
        box = os.path.realpath(args.sandbox)
        tmp = os.path.realpath(os.path.join(REAL_ROOT, "tmp")) + os.sep
        if not box.startswith(tmp) or box == os.path.realpath(REAL_ROOT):
            raise SystemExit("--sandbox must be a folder under C:\\kronos-test\\tmp")
        if not args.sandbox_marker or not args.sandbox_marker.startswith("SANDBOX_") or len(args.sandbox_marker) < 16:
            raise SystemExit("--sandbox-marker must start with SANDBOX_ and be at least 16 characters")
        lay = Layout(box)
        runner_parts = [args.sandbox_marker]
        analyze_cmd = [sys.executable, "-I", "-c",
                       f"open(r'{os.path.join(box, 'results', 'REPORT_kronos.md')}', 'w').write('sandbox')"]
        task_name = None
    else:
        lay = Layout(REAL_ROOT)
        runner_parts = ["run_forecasts.py", "--mode full"]
        analyze_cmd = [os.path.join(REAL_ROOT, "venv", "Scripts", "python.exe"), "-I",
                       os.path.join(REAL_ROOT, "scripts", "analyze.py")]
        task_name = TASK_NAME
        kt.verify_freeze()
    os.makedirs(lay.logs, exist_ok=True)
    LOG_PATH = os.path.join(lay.logs, "accept_colab.log")
    say(f"accept_colab.py started: {' '.join(sys.argv[1:])}")

    if args.preflight:
        preflight(lay, runner_parts, task_name)
        return
    if not args.download:
        raise SystemExit("--download is required")
    exp_script, exp_bundle = expected_hashes(bool(args.sandbox))
    files = gather(args.download, lay)
    digest, sessions = verify(files, lay, exp_script, exp_bundle, bool(args.sandbox))
    if args.check_only:
        say("check only: nothing changed")
        return
    accept(files, digest, sessions, lay, runner_parts, analyze_cmd, task_name)
    say("done: the one analysis has run")


if __name__ == "__main__":
    main()
