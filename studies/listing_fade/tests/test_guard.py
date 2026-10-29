import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lf import archive as AR, events as E, guard as G  # noqa: E402


class NoNet:
    def download(self, url, path):
        raise AssertionError(url)

    get = download


def ms(*a):
    return int(dt.datetime(*a, tzinfo=dt.timezone.utc).timestamp() * 1000)


def test_files_after_limit_refused_before_request():
    for url in (AR.agg_url("X", dt.date(2026, 3, 14)), AR.kline_url("X", dt.date(2026, 3, 14)),
                AR.funding_url("X", "2026-03")):
        with pytest.raises(G.HoldoutViolation):
            AR.fetch_zip(NoNet(), url, Path("."))
    G.assert_allowed(AR.agg_url("X", dt.date(2026, 3, 13)))


def test_only_test_launches():
    ok = {"symbol": "X", "segment": "TEST", "L_ms": ms(2026, 3, 5, 23)}
    G.assert_event_allowed(ok)
    for bad in ({**ok, "segment": "HOLDOUT"}, {**ok, "L_ms": ms(2026, 3, 6)}, {**ok, "L_ms": ms(2023, 12, 31)}):
        with pytest.raises(G.HoldoutViolation):
            G.assert_event_allowed(bad)
    with pytest.raises(G.HoldoutViolation):
        G.assert_ms_allowed(ms(2026, 3, 14))


def test_latest_test_launch_fits_the_guard():
    L = ms(2026, 3, 5, 23, 59)
    t0 = L + E.DAY - 1
    G.assert_ms_allowed(t0 + E.EXIT_HI)
    G.assert_ms_allowed(max(L, t0) + E.KLINE_SPAN)


def test_days_between():
    assert E.days_between(ms(2024, 1, 1, 23), ms(2024, 1, 3)) == [dt.date(2024, 1, 1), dt.date(2024, 1, 2)]
