import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dl import archive, events as E, guard as G  # noqa: E402


class NoNet:
    def download(self, url, path):
        raise AssertionError(f"network touched: {url}")

    def get(self, url):
        raise AssertionError(f"network touched: {url}")


def test_files_after_limit_refused_before_any_request():
    for url in (archive.kline_url("X", dt.date(2026, 3, 14)), archive.funding_url("X", "2026-03")):
        with pytest.raises(G.HoldoutViolation):
            archive.fetch_zip(NoNet(), url, Path("."))
    G.assert_allowed(archive.kline_url("X", dt.date(2026, 3, 13)))
    G.assert_allowed(archive.funding_url("X", "2026-02"))


def test_only_test_events_inside_limit():
    ms = lambda d: int(dt.datetime(*d, tzinfo=dt.timezone.utc).timestamp() * 1000)  # noqa: E731
    ok = {"symbol": "X", "segment": "TEST", "A_ms": ms((2026, 2, 5, 7)), "D_ms": ms((2026, 2, 10, 9))}
    G.assert_event_allowed(ok)
    for bad in ({**ok, "segment": "HOLDOUT"}, {**ok, "A_ms": ms((2026, 3, 15)), "D_ms": ms((2026, 3, 16))},
                {**ok, "A_ms": ms((2026, 3, 13, 14)), "D_ms": ms((2026, 3, 17, 9))}):
        with pytest.raises(G.HoldoutViolation):
            G.assert_event_allowed(bad)


def test_windows():
    ev = {"A_ms": ms_(2024, 3, 19, 5, 5, 30), "N_ms": ms_(2024, 3, 26, 8, 30), "D_ms": ms_(2024, 3, 26, 9)}
    w = E.windows(ev)
    assert w["entry"] == ms_(2024, 3, 19, 5, 36) and w["exit"] == ms_(2024, 3, 26, 8, 0)
    assert w["pre_hi"] == ms_(2024, 3, 19, 5, 5) and w["pre_hi"] - w["pre_lo"] == E.DAY
    assert E.days_needed(ev)[0] == dt.date(2024, 3, 18) and E.days_needed(ev)[-1] == dt.date(2024, 3, 26)
    ev2 = {**ev, "A_ms": ms_(2024, 3, 19, 5, 5)}
    assert E.windows(ev2)["entry"] == ms_(2024, 3, 19, 5, 35)


def ms_(*a):
    return int(dt.datetime(*a, tzinfo=dt.timezone.utc).timestamp() * 1000)
