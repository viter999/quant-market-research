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


def test_funding_chain_rule():
    import pandas as pd
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import exclusions as X
    H = E.HOUR
    f = pd.DataFrame({"ts": [4 * H, 8 * H, 10 * H, 12 * H], "funding_interval_hours": [4, 2, 2, 2]})
    assert X.funding_complete(f, True, 3 * H, 13 * H)            # 4h -> 2h switch is fine
    assert not X.funding_complete(f.drop(index=2), True, 3 * H, 13 * H)   # 8h -> 12h gap at 2h interval
    assert not X.funding_complete(f, False, 3 * H, 13 * H)       # a monthly file missing
    assert not X.funding_complete(f, True, 3 * H, 15 * H)        # nothing after 12h but hold runs to 15h
    assert not X.funding_complete(None, True, 3 * H, 13 * H)


def test_funding_chain_anchored_on_outside_records():
    import pandas as pd
    import exclusions as X
    H = E.HOUR
    f = pd.DataFrame({"ts": [4 * H, 8 * H, 12 * H, 16 * H, 18 * H, 20 * H], "funding_interval_hours": [4, 4, 4, 2, 2, 2]})
    assert X.funding_complete(f, True, 12 * H + 6, 19 * H)     # AERGO case: 12h (4h) -> 16h (2h)
    assert not X.funding_complete(f.drop(index=3), True, 12 * H + 6, 19 * H)
