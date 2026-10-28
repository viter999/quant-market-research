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
