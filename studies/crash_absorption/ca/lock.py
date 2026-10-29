"""Outcome lock (standing rule): no exit price, return or other outcome may be
computed on real data, and the detector may not run on VERDICT, until the
director says "run VERDICT". Unlocking requires CA_RUN_VERDICT to equal the
current, clean git HEAD, so the frozen code commit is recorded by construction."""
import os
import subprocess

from ca.params import STUDY_DIR

SYNTHETIC = "synthetic"
ARCHIVE = "archive"
SESSION_PREFIX = "archive@"  # archive data inside a VERDICT run whose unlock was verified once at start

_SESSION_HEAD: str | None = None  # set by the VERDICT runner (and its worker initializer) only


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


def head_if_unlocked() -> str | None:
    """The clean HEAD if CA_RUN_VERDICT equals it (one rev-parse + one status), else None."""
    return os.environ.get("CA_RUN_VERDICT") if verdict_unlocked() else None


def start_session(head: str) -> str:
    """Called by the VERDICT runner after head_if_unlocked() succeeded, and in each
    worker with the HEAD handed over by the parent. Returns the session origin."""
    global _SESSION_HEAD
    _SESSION_HEAD = head
    return SESSION_PREFIX + head


def _session_ok(origin: str) -> bool:
    """No git call: the origin must carry the session HEAD, which must also equal CA_RUN_VERDICT."""
    return (_SESSION_HEAD is not None and origin == SESSION_PREFIX + _SESSION_HEAD
            and os.environ.get("CA_RUN_VERDICT") == _SESSION_HEAD)


def require_outcome_permission(origin: str) -> None:
    if origin == SYNTHETIC:
        return
    if origin.startswith(SESSION_PREFIX):
        if _session_ok(origin):
            return
        raise OutcomeLocked(f"VERDICT session origin {origin!r} does not match the verified HEAD")
    if not verdict_unlocked():
        raise OutcomeLocked(f"outcome computation on {origin!r} data is locked until 'run VERDICT'")


def require_segment_permission(segment: str, origin: str) -> None:
    if origin == SYNTHETIC or segment == "dev":
        return
    if segment == "verdict" and origin.startswith(SESSION_PREFIX) and _session_ok(origin):
        return
    if segment == "verdict" and not origin.startswith(SESSION_PREFIX) and verdict_unlocked():
        return
    raise OutcomeLocked(f"detection on {segment!r} ({origin}) is locked (gate (b) / HOLDOUT)")
