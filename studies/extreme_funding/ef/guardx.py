"""Listing guard for this study: the frozen crash-absorption rule (every file name a
prefix can match must cover dates <= MAX_ALLOWED = 2026-03-13), extended to the spot
tree. File downloads still go through ca.guard.assert_allowed unchanged."""
from ca.guard import _FRAG, MAX_ALLOWED, HoldoutViolation, _completions

ALLOWED_ROOTS = ("data/futures/um/", "data/spot/")


def assert_file_listing_allowed(prefix: str) -> None:
    root = next((r for r in ALLOWED_ROOTS if prefix.startswith(r)), None)
    if root is None or "/" in prefix.rsplit("/", 1)[-1]:
        raise HoldoutViolation(f"listing {prefix!r} not allowed; refusing")
    freq = prefix[len(root):].split("/")[0]
    m = _FRAG.search(prefix.rsplit("/", 1)[-1])
    if freq not in ("monthly", "daily") or not m:
        raise HoldoutViolation(f"listing {prefix!r} has no date bound; refusing")
    ends = list(_completions(m.group(1), bool(m.group(2)), freq == "monthly"))
    if not ends or max(ends) > MAX_ALLOWED:
        raise HoldoutViolation(f"listing {prefix!r} can match dates after {MAX_ALLOWED}; refusing")
