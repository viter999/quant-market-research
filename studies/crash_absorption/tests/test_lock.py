import pytest

from ca import lock


def test_locked_without_token(monkeypatch):
    monkeypatch.delenv("CA_RUN_VERDICT", raising=False)
    assert not lock.verdict_unlocked()
    lock.require_outcome_permission(lock.SYNTHETIC)
    with pytest.raises(lock.OutcomeLocked):
        lock.require_outcome_permission(lock.ARCHIVE)


def test_unlock_requires_clean_head(monkeypatch):
    monkeypatch.setenv("CA_RUN_VERDICT", "abc123")
    monkeypatch.setattr(lock, "_git", lambda *a: "abc123" if a[0] == "rev-parse" else " M ca/fill.py")
    assert not lock.verdict_unlocked()  # dirty tree
    monkeypatch.setattr(lock, "_git", lambda *a: "abc123" if a[0] == "rev-parse" else "")
    assert lock.verdict_unlocked()
    lock.require_segment_permission("verdict", lock.ARCHIVE)
    with pytest.raises(lock.OutcomeLocked):
        lock.require_segment_permission("holdout", lock.ARCHIVE)  # HOLDOUT never via this lock
    monkeypatch.setenv("CA_RUN_VERDICT", "other")
    assert not lock.verdict_unlocked()


def test_session_origin_checked_without_git(monkeypatch):
    def no_git(*a):
        raise AssertionError("git must not be called for a session origin")
    monkeypatch.setattr(lock, "_git", no_git)
    head = "b" * 40
    monkeypatch.setenv("CA_RUN_VERDICT", head)
    origin = lock.start_session(head)
    try:
        for _ in range(1000):
            lock.require_outcome_permission(origin)
        lock.require_segment_permission("verdict", origin)
        with pytest.raises(lock.OutcomeLocked):
            lock.require_outcome_permission(lock.SESSION_PREFIX + "c" * 40)  # another HEAD
        with pytest.raises(lock.OutcomeLocked):
            lock.require_segment_permission("holdout", origin)
        monkeypatch.setenv("CA_RUN_VERDICT", "c" * 40)  # token changed under the session
        with pytest.raises(lock.OutcomeLocked):
            lock.require_outcome_permission(origin)
    finally:
        lock._SESSION_HEAD = None


def test_session_origin_refused_without_session(monkeypatch):
    lock._SESSION_HEAD = None
    monkeypatch.setenv("CA_RUN_VERDICT", "b" * 40)
    with pytest.raises(lock.OutcomeLocked):
        lock.require_outcome_permission(lock.SESSION_PREFIX + "b" * 40)


def test_plain_archive_still_checks_git_per_call(monkeypatch):
    calls = []
    monkeypatch.setattr(lock, "_git", lambda *a: calls.append(a) or ("d" * 40 if a[0] == "rev-parse" else ""))
    monkeypatch.setenv("CA_RUN_VERDICT", "d" * 40)
    for _ in range(3):
        lock.require_outcome_permission(lock.ARCHIVE)
    assert len(calls) == 6
    monkeypatch.delenv("CA_RUN_VERDICT")
    with pytest.raises(lock.OutcomeLocked):
        lock.require_outcome_permission(lock.ARCHIVE)
