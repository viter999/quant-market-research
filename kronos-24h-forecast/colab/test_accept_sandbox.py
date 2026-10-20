"""Sandbox test of accept_colab.py. Touches nothing real: fake root under tmp, fake CPU runner, fake CPU file, synthetic
(non-model) Colab forecasts whose c0 comes from the frozen input data. Never reads results/forecasts.csv.
Deletes all its synthetic files at the end, so none can be mistaken for a real Colab download.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import kt_common as kt
import kt_binance as kb
from run_forecasts import COLS

import numpy as np
import pandas as pd

BOX = os.path.join(ROOT, "tmp", "accept_sandbox")
ACCEPT = os.path.join(HERE, "accept_colab.py")
PY = sys.executable
HOUR = pd.Timedelta(hours=1)
MARKER = "SANDBOX_CPU_RUNNER_" + uuid.uuid4().hex[:8]
CPU_DUMMY = b"SANDBOX CPU PARTIAL FILE - stands in for the real one\n"
SCRIPT_SHA = kt.sha256_file(os.path.join(HERE, "colab_forecasts.py"))
BUNDLE_SHA = kt.sha256_file(os.path.join(HERE, "kronos_colab_bundle.zip"))


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def session(sid, **over):
    s = {"session": sid, "device": "cuda", "gpu": "Tesla T4 (sandbox)", "cuda": "12.4", "torch": "2.x+cu124",
         "einops": "0.8.1", "safetensors": "0.6.2", "huggingface_hub": "0.33.1",
         "script_sha256": SCRIPT_SHA, "bundle_sha256": BUNDLE_SHA}
    s.update(over)
    return s


def synthetic_download(folder, mutate=None):
    """A complete, internally consistent 13,710-row file in the frozen layout. Not model output."""
    os.makedirs(os.path.join(folder, "run"), exist_ok=True)
    syms = kt.universe()
    days = pd.date_range(kt.FULL_FIRST_DAY, kt.FULL_LAST_DAY, freq="D")
    rows = []
    for i, s in enumerate(syms):
        close = kb.load_1h_bars(s, *kt.DATA_MONTHS)["close"]
        for d in days:
            c0 = float(close[d - HOUR])
            p24 = c0 * (1.001 if (i + d.day) % 2 else 0.999)
            r = {"day": d.strftime("%Y-%m-%d"), "coin_index": i, "symbol": s, "seed": kt.seed_for(d, i),
                 "ctx_first_open": str(d - 512 * HOUR), "ctx_last_open": str(d - HOUR), "ctx_rows": 512,
                 "ctx_cols": 6, "out_rows": 24, "out_cols": 6, "c0": repr(c0), "p24": repr(p24),
                 "signal": int(np.sign(p24 - c0)), "seconds": "1.00", "finished_utc": "2026-10-19T00:00:00Z"}
            r.update({f"pred_close_{h:02d}": repr(c0 + (p24 - c0) * h / 24) for h in range(1, 24)})
            r["pred_close_24"] = repr(p24)
            rows.append(r)
    fc = pd.DataFrame(rows)[COLS].sort_values(["day", "coin_index"])
    if mutate == "extra_row":
        fc = pd.concat([fc, fc.iloc[[0]]])
    csv_path = os.path.join(folder, "run", "forecasts.csv")
    fc.to_csv(csv_path, index=False, lineterminator="\n")
    sessions = [session("s1"), session("s2")]
    if mutate == "mixed_script":
        sessions[0]["script_sha256"] = "0" * 64
    if mutate == "no_pins":
        sessions[1]["huggingface_hub"] = "1.0.0"
    man = {"complete": True, "rows": 13710, "forecasts_csv_sha256": sha(csv_path),
           "freeze_digest": kt.sha256_file(kt.FREEZE), "kronos_commit": kt.KRONOS_COMMIT,
           "script_sha256": SCRIPT_SHA, "last_session": sessions[-1]}
    json.dump(man, open(os.path.join(folder, "run", "colab_manifest.json"), "w"))
    with open(os.path.join(folder, "run", "colab_sessions.log"), "w") as f:
        f.writelines(json.dumps(s) + "\n" for s in sessions)
    if mutate == "tamper":
        with open(csv_path, "r+b") as f:
            f.seek(-5, 2)
            f.write(b"9")
    zpath = folder + ".zip"
    with zipfile.ZipFile(zpath, "w") as z:
        for n in ("forecasts.csv", "colab_manifest.json", "colab_sessions.log"):
            z.write(os.path.join(folder, "run", n), f"run/{n}")
    return zpath


def fresh_root(progress_done=500, report=False, attempts=False, analysis_json=False):
    root = os.path.join(BOX, "root")
    if os.path.exists(root):
        shutil.rmtree(root)
    for d in ("results", "logs"):
        os.makedirs(os.path.join(root, d))
    shutil.copyfile(kt.FREEZE, os.path.join(root, "FREEZE_kronos.sha256"))
    open(os.path.join(root, "results", "forecasts.csv"), "wb").write(CPU_DUMMY)
    open(os.path.join(root, "results", "progress.txt"), "w").write(f"forecasts_done   {progress_done} / 13710\n")
    open(os.path.join(root, "START_OR_RESUME_FULL_RUN.cmd"), "w").write("rem sandbox\n")
    open(os.path.join(root, "AMENDMENTS_kronos.md"), "w").write("# sandbox\n")
    open(os.path.join(root, "logs", "run_full.log"), "w").write("sandbox start\n")
    if report:
        open(os.path.join(root, "results", "REPORT_kronos.md"), "w").write("earlier look\n")
    if attempts:
        open(os.path.join(root, "logs", "analysis_attempts.log"), "w").write("2026 analyze.py started\n")
    if analysis_json:
        open(os.path.join(root, "results", "analysis.json"), "w").write("{}")
    return root


def fake_runner(root):
    lock = os.path.join(root, "results", "run.lock")
    code = (f"import msvcrt,time; f=open(r'{lock}','a+'); f.seek(0); "
            f"msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1); time.sleep(300)")
    # the base interpreter, so the fake runner is ONE process (the venv's python.exe is a launcher plus a child)
    base = getattr(sys, "_base_executable", PY)
    p = subprocess.Popen([base, "-I", "-c", code, MARKER])
    time.sleep(2)
    assert p.poll() is None, "fake runner did not start"
    return p


def run(download, root, *extra, marker=MARKER):
    cmd = [PY, "-I", ACCEPT, "--sandbox", root, "--sandbox-marker", marker, *extra]
    if download:
        cmd[3:3] = ["--download", download]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def untouched(root):
    res = os.path.join(root, "results")
    return (open(os.path.join(res, "forecasts.csv"), "rb").read() == CPU_DUMMY
            and os.path.exists(os.path.join(root, "START_OR_RESUME_FULL_RUN.cmd"))
            and not os.path.exists(os.path.join(res, "retired_cpu_run")))


def expect(name, cond, out=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}", flush=True)
    if not cond:
        print(out)
        sys.exit(1)


def refuse_case(name, good, phrase, **root_kw):
    root = fresh_root(**root_kw)
    p = fake_runner(root)
    rc, out = run(good, root)
    alive = p.poll() is None
    p.kill()
    p.wait()
    expect(name, rc != 0 and phrase in out and alive and untouched(root), out)


def main():
    kt.below_normal_priority()   # children inherit it
    if os.path.exists(BOX):
        shutil.rmtree(BOX)
    os.makedirs(BOX)
    good = synthetic_download(os.path.join(BOX, "dl_good"))
    bad = {m: synthetic_download(os.path.join(BOX, f"dl_{m}"), m)
           for m in ("tamper", "extra_row", "mixed_script", "no_pins")}
    rehearsal = os.path.join(ROOT, "tmp", "colab_test", "out")

    # guards on the sandbox switch itself (a path that does not exist, so a broken guard could harm nothing)
    rc, out = run(good, r"C:\kronos-test_no_such_root", "--check-only")
    expect("--sandbox outside tmp refused", rc != 0 and "must be a folder under" in out, out)
    root = fresh_root()
    rc, out = run(good, root, "--check-only", marker="x")
    expect("short sandbox marker refused", rc != 0 and "sandbox-marker" in out, out)

    # verification
    rc, out = run(rehearsal, root, "--check-only")
    expect("rehearsal output (2 rows) rejected", rc != 0, out)
    rc, out = run(bad["tamper"], root, "--check-only")
    expect("tampered forecasts.csv rejected (hash)", rc != 0 and "SHA-256 does not match" in out, out)
    rc, out = run(bad["extra_row"], root, "--check-only")
    expect("extra duplicated row rejected (frozen validator)", rc != 0 and "expected 13710" in out, out)
    rc, out = run(bad["mixed_script"], root, "--check-only")
    expect("session from another script version rejected", rc != 0 and "different colab_forecasts.py" in out, out)
    rc, out = run(bad["no_pins"], root, "--check-only")
    expect("session without pinned packages rejected", rc != 0 and "pinned helper packages" in out, out)
    rc, out = run(good, root, "--check-only")
    expect("good file passes --check-only and changes nothing", rc == 0 and "Colab files pass" in out and untouched(root), out)
    p = fake_runner(root)
    rc, out = run(None, root, "--preflight")
    p.kill()
    p.wait()
    expect("preflight finds the runner, changes nothing",
           rc == 0 and f"[{p.pid}]" in out and "be allowed" in out and untouched(root), out)

    # refusals before anything changes
    refuse_case("REPORT exists -> refuse, nothing changed", good, "one look has been taken", report=True)
    refuse_case("analysis already started (attempts log) -> refuse", good, "already started once", attempts=True)
    refuse_case("analysis outputs exist -> refuse", good, "already started once", analysis_json=True)
    refuse_case("CPU at 13,710 -> CPU counts, refuse", good, "CPU run counts", progress_done=13710)
    refuse_case("CPU at 13,705 -> owner decides, refuse", good, "owner decides", progress_done=13705)

    # happy path
    root = fresh_root()
    p = fake_runner(root)
    rc, out = run(good, root)
    p.wait(timeout=30)
    res = os.path.join(root, "results")
    retired = os.path.join(res, "retired_cpu_run")
    with zipfile.ZipFile(good) as z:
        colab_sha = hashlib.sha256(z.read("run/forecasts.csv")).hexdigest()
    expect("happy path exits 0", rc == 0, out)
    expect("fake CPU runner killed", p.poll() is not None, out)
    expect("launcher renamed", not os.path.exists(os.path.join(root, "START_OR_RESUME_FULL_RUN.cmd"))
           and os.path.exists(os.path.join(root, "START_OR_RESUME_FULL_RUN.cmd.retired")))
    expect("CPU file retired byte-for-byte", open(os.path.join(retired, "forecasts.csv"), "rb").read() == CPU_DUMMY)
    expect("hash recorded before the move", hashlib.sha256(CPU_DUMMY).hexdigest() in open(os.path.join(retired, "RETIRED.txt")).read())
    expect("Colab file installed, no .part left", sha(os.path.join(res, "forecasts.csv")) == colab_sha
           and not os.path.exists(os.path.join(res, "forecasts.csv.colab.part")))
    expect("analysis ran once (REPORT written)", os.path.exists(os.path.join(res, "REPORT_kronos.md")))
    amend = open(os.path.join(root, "AMENDMENTS_kronos.md"), encoding="utf-8").read()
    expect("acceptance and analysis logged", "ACCEPTANCE" in amend and "analyze.py exited 0" in amend, amend)
    rc, out = run(good, root)
    expect("second acceptance refused (one look taken)", rc != 0 and "one look has been taken" in out, out)

    # crash half-way: CPU file already retired, launcher renamed, a stale .part left, no runner -> re-run finishes
    root = fresh_root()
    res = os.path.join(root, "results")
    os.makedirs(os.path.join(res, "retired_cpu_run"))
    os.replace(os.path.join(res, "forecasts.csv"), os.path.join(res, "retired_cpu_run", "forecasts.csv"))
    os.replace(os.path.join(root, "START_OR_RESUME_FULL_RUN.cmd"), os.path.join(root, "START_OR_RESUME_FULL_RUN.cmd.retired"))
    open(os.path.join(res, "forecasts.csv.colab.part"), "w").write("half a copy")
    rc, out = run(good, root)
    expect("re-run after a half-way crash completes", rc == 0 and sha(os.path.join(res, "forecasts.csv")) == colab_sha
           and open(os.path.join(res, "retired_cpu_run", "forecasts.csv"), "rb").read() == CPU_DUMMY
           and os.path.exists(os.path.join(res, "REPORT_kronos.md")), out)

    # a sandbox fixture must never pass in real mode (read-only check, folder input so nothing is extracted)
    r = subprocess.run([PY, "-I", ACCEPT, "--download", os.path.join(BOX, "dl_good"), "--check-only"],
                       capture_output=True, text=True)
    out = r.stdout + r.stderr
    expect("synthetic fixture rejected in real mode", r.returncode != 0 and
           ("laptop sandbox fixture" in out or "FREEZE_colab.sha256 missing" in out), out)
    print("   (real-mode rejection reason: " + ("sandbox fixture" if "laptop sandbox fixture" in out else "Colab freeze not written yet") + ")")

    shutil.rmtree(BOX)
    expect("synthetic files deleted", not os.path.exists(BOX))
    print("ALL ACCEPTANCE SANDBOX TESTS PASSED")


if __name__ == "__main__":
    main()
