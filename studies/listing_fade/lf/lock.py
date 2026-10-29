"""Outcome lock (standing rule): no price, return, PnL or other outcome may be
computed on real data until the director says "run VERDICT". Unlock requires
LF_RUN_VERDICT to equal the current git HEAD with a clean studies/listing_fade tree,
so the frozen code commit is recorded by construction."""
import os
import subprocess
from pathlib import Path

STUDY_DIR = Path(__file__).resolve().parents[1]
SYNTHETIC = "synthetic"
ARCHIVE = "archive"


class OutcomeLocked(RuntimeError):
    pass


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=STUDY_DIR, capture_output=True, text=True, check=True).stdout.strip()


def head_if_unlocked() -> str | None:
    token = os.environ.get("LF_RUN_VERDICT")
    if not token:
        return None
    try:
        head, dirty = _git("rev-parse", "HEAD"), _git("status", "--porcelain", "--", ".")
    except (OSError, subprocess.CalledProcessError):
        return None
    return head if token == head and not dirty else None


def require_outcome_permission(origin: str) -> None:
    if origin == SYNTHETIC:
        return
    if origin != ARCHIVE or head_if_unlocked() is None:
        raise OutcomeLocked(f"outcome computation on {origin!r} data is locked until 'run VERDICT'")
