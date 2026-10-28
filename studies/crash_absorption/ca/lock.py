"""Outcome lock (standing rule): no exit price, return or other outcome may be
computed on real data, and the detector may not run on VERDICT, until the
director says "run VERDICT". Unlocking requires CA_RUN_VERDICT to equal the
current, clean git HEAD, so the frozen code commit is recorded by construction."""
import os
import subprocess

from ca.params import STUDY_DIR

SYNTHETIC = "synthetic"
ARCHIVE = "archive"


class OutcomeLocked(RuntimeError):
    pass


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=STUDY_DIR, capture_output=True, text=True, check=True).stdout.strip()


def verdict_unlocked() -> bool:
    token = os.environ.get("CA_RUN_VERDICT")
    if not token:
        return False
    try:
        head = _git("rev-parse", "HEAD")
        dirty = _git("status", "--porcelain", "--", ".")
    except (OSError, subprocess.CalledProcessError):
        return False
    return token == head and not dirty


def require_outcome_permission(origin: str) -> None:
    if origin == SYNTHETIC:
        return
    if not verdict_unlocked():
        raise OutcomeLocked(f"outcome computation on {origin!r} data is locked until 'run VERDICT'")


def require_segment_permission(segment: str, origin: str) -> None:
    if origin == SYNTHETIC or segment == "dev":
        return
    if segment == "verdict" and verdict_unlocked():
        return
    raise OutcomeLocked(f"detection on {segment!r} ({origin}) is locked (gate (b) / HOLDOUT)")
