"""Shared setup for every Kronos-test script: paths, pins, prereg constants, priority, keep-awake, freeze check."""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
import sys

ROOT = r"C:\kronos-test"
REPO = os.path.join(ROOT, "repo", "Kronos")
MODEL_DIR = os.path.join(ROOT, "models", "Kronos-small@901c26c")
TOKENIZER_DIR = os.path.join(ROOT, "models", "Kronos-Tokenizer-base@0e01173")
DATA = os.path.join(ROOT, "data")
RESULTS = os.path.join(ROOT, "results")
LOGS = os.path.join(ROOT, "logs")
UNIVERSE_JSON = os.path.join(DATA, "universe", "universe_frozen.json")
FREEZE = os.path.join(ROOT, "FREEZE_kronos.sha256")

KRONOS_COMMIT = "67b630e67f6a18c9e9be918d9b4337c960db1e9a"
MODEL_REV = "901c26c1332695a2a8f243eb2f37243a37bea320"
TOKENIZER_REV = "0e0117387f39004a9016484a186a908917e22426"

# PREREG_kronos.md §6-7
CTX_BARS = 512
PRED_BARS = 24
TEMPERATURE = 1.0
TOP_P = 0.9
TOP_K = 0
SAMPLE_COUNT = 10
THREADS = 6
FEE = 0.0010
FULL_FIRST_DAY, FULL_LAST_DAY = "2025-07-01", "2026-09-30"        # 457 forecast days
PLUMBING_DAYS = ["2025-06-28", "2025-06-29", "2025-06-30"]
DATA_MONTHS = ("2025-06", "2026-09")
NULL_RUNS = 10_000
NULL_SEED = 20250701
ALPHA = 0.05

BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def seed_for(day, coin_index):
    """Prereg §6: s = int(D as YYYYMMDD) * 100 + i."""
    return int(day.strftime("%Y%m%d")) * 100 + coin_index


def universe():
    with open(UNIVERSE_JSON) as f:
        return [c["symbol"] for c in json.load(f)["universe"]]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_freeze():
    """Stop unless every file listed in FREEZE_kronos.sha256 still has its frozen hash."""
    if not os.path.exists(FREEZE):
        raise SystemExit("FREEZE_kronos.sha256 missing: freeze before running")
    bad, n = [], 0
    with open(FREEZE, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            digest, rel = line.split("  ", 1)
            path = os.path.join(ROOT, rel)
            n += 1
            if not os.path.exists(path) or sha256_file(path) != digest:
                bad.append(rel)
    if bad:
        raise SystemExit(f"FREEZE mismatch in {len(bad)} file(s), e.g. {bad[:5]}")
    return n


def on_battery():
    s = _PowerStatus()
    if not _k32.GetSystemPowerStatus(ctypes.byref(s)):
        raise OSError("GetSystemPowerStatus failed")
    return s.ACLineStatus == 0


class _PowerStatus(ctypes.Structure):
    _fields_ = [("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte),
                ("BatteryLifePercent", ctypes.c_ubyte), ("SystemStatusFlag", ctypes.c_ubyte),
                ("BatteryLifeTime", wintypes.DWORD), ("BatteryFullLifeTime", wintypes.DWORD)]


# Declared types matter: without them ctypes passes the 64-bit process pseudo-handle as a 32-bit int.
_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.GetCurrentProcess.restype = wintypes.HANDLE
_k32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_k32.SetPriorityClass.restype = wintypes.BOOL
_k32.GetPriorityClass.argtypes = [wintypes.HANDLE]
_k32.GetPriorityClass.restype = wintypes.DWORD
_k32.SetThreadExecutionState.argtypes = [wintypes.DWORD]
_k32.SetThreadExecutionState.restype = wintypes.DWORD
_k32.GetSystemPowerStatus.argtypes = [ctypes.POINTER(_PowerStatus)]
_k32.GetSystemPowerStatus.restype = wintypes.BOOL


def below_normal_priority():
    """Drop this process (and children it spawns) to below-normal CPU priority; raise if Windows refuses."""
    h = _k32.GetCurrentProcess()
    if not _k32.SetPriorityClass(h, BELOW_NORMAL_PRIORITY_CLASS):
        raise OSError(ctypes.get_last_error(), "SetPriorityClass failed")
    if _k32.GetPriorityClass(h) != BELOW_NORMAL_PRIORITY_CLASS:
        raise OSError("below-normal priority was not applied")


def keep_awake(on=True):
    """Ask Windows not to idle-sleep while this process runs. Per-process, no settings changed."""
    flags = ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0)
    if _k32.SetThreadExecutionState(flags) == 0:
        raise OSError("SetThreadExecutionState failed")


def import_kronos():
    if REPO not in sys.path:
        sys.path.insert(0, REPO)
    from model import Kronos, KronosTokenizer, KronosPredictor
    return Kronos, KronosTokenizer, KronosPredictor


def load_predictor(threads=THREADS):
    import torch
    torch.set_num_threads(threads)
    Kronos, KronosTokenizer, KronosPredictor = import_kronos()
    tokenizer = KronosTokenizer.from_pretrained(TOKENIZER_DIR)
    model = Kronos.from_pretrained(MODEL_DIR)
    tokenizer.eval()
    model.eval()
    return KronosPredictor(model, tokenizer, device="cpu", max_context=512)
