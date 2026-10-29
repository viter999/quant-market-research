import datetime as dt
import json

import pandas as pd
import pytest

from ca import universe as U

D0 = dt.date(2024, 3, 1)
EX = {"excluded_prefixes": ["1000", "1M"],
      "excluded_symbols": {"stablecoin": ["USDCUSDT"], "tokenized_metal": ["XAUUSDT"], "tokenized_equity": ["TSLAUSDT"]},
      "reviewed_symbols": ["BTCUSDT"]}


def _daily(rows):
    return pd.DataFrame(rows, columns=["symbol", "day", "quote_volume"])


def _span(sym, first, n, qv):
    return [(sym, first + dt.timedelta(days=i), qv(i) if callable(qv) else qv) for i in range(n)]


@pytest.mark.parametrize("sym,ok", [
    ("BTCUSDT", True), ("1000PEPEUSDT", False), ("1000000MOGUSDT", False), ("1MBABYDOGEUSDT", False),
    ("USDCUSDT", False), ("XAUUSDT", False), ("TSLAUSDT", False), ("BTCUSDT_240329", False), ("BTCUSDC", False),
])
def test_candidate_symbols(sym, ok):
    assert U.is_candidate_symbol(sym, EX) is ok


def test_top80_and_tie_break():
    rows = []
    for k in range(85):
        rows += _span(f"S{k:02d}USDT", D0, 20, 1000.0 - k)
    rows += _span("ZZUSDT", D0, 20, 1000.0 - 79)  # ties S79 at rank 80
    day = D0 + dt.timedelta(days=10)
    uni = U.build_universe(_daily(rows), EX, [day], D0)[day]
    assert len(uni) == 80 and "S79USDT" in uni and "ZZUSDT" not in uni and "S80USDT" not in uni


def test_needs_seven_full_days_listing_day_partial():
    rows = _span("BTCUSDT", D0, 30, 1.0) + _span("NEWUSDT", D0 + dt.timedelta(days=10), 20, 1e9)
    listed = D0 + dt.timedelta(days=10)
    days = [listed + dt.timedelta(days=k) for k in (7, 8)]
    uni = U.build_universe(_daily(rows), EX, days, D0)
    assert "NEWUSDT" not in uni[days[0]]  # D-7 is the listing day (partial) -> only 6 full days
    assert "NEWUSDT" in uni[days[1]]


def test_first_archive_day_counts_as_full():
    rows = _span("BTCUSDT", D0, 30, 1.0)
    assert "BTCUSDT" in U.build_universe(_daily(rows), EX, [D0 + dt.timedelta(days=7)], D0)[D0 + dt.timedelta(days=7)]


def test_missing_day_in_window_ineligible():
    rows = [r for r in _span("BTCUSDT", D0, 30, 1.0) if r[1] != D0 + dt.timedelta(days=12)]
    day = D0 + dt.timedelta(days=15)
    assert "BTCUSDT" not in U.build_universe(_daily(rows), EX, [day], D0)[day]
    assert "BTCUSDT" in U.build_universe(_daily(rows), EX, [day + dt.timedelta(days=5)], D0)[day + dt.timedelta(days=5)]


def test_ranking_uses_previous_days_only(monkeypatch):
    monkeypatch.setattr(U.P, "UNIVERSE_SIZE", 1)
    rows = _span("AUSDT", D0, 20, 10.0) + _span("BBUSDT", D0, 20, lambda i: 1e12 if i == 10 else 1.0)
    day = D0 + dt.timedelta(days=10)
    assert U.build_universe(_daily(rows), EX, [day], D0)[day] == {"AUSDT"}  # day-10 spike not used on day 10
    nxt = day + dt.timedelta(days=1)
    assert U.build_universe(_daily(rows), EX, [nxt], D0)[nxt] == {"BBUSDT"}


def test_draft_exclusions_refused_and_review_check(tmp_path, monkeypatch):
    draft = tmp_path / "EXCLUSIONS.json"
    draft.write_text(json.dumps(dict(EX, status="DRAFT")))
    monkeypatch.setattr(U, "EXCLUSIONS_PATH", draft)
    with pytest.raises(U.ExclusionsNotFrozen):
        U.load_exclusions(require_frozen=True)
    with pytest.raises(U.ExclusionsNotFrozen):
        U.check_reviewed(["BTCUSDT", "NEWUSDT"], EX)
    U.check_reviewed(["BTCUSDT"], EX)


def test_committed_exclusions_are_frozen():
    ex = U.load_exclusions(require_frozen=True)
    assert ex["status"] == "FROZEN" and "USDTSETTLED" in ex["perp_suffixes"]
    assert U.is_candidate_symbol("AERGOUSDTSETTLED", ex) and not U.is_candidate_symbol("ALLUSDT", ex)


def test_settled_suffix_and_excluded_days():
    ex = dict(EX, perp_suffixes=["USDT", "USDTSETTLED"],
              excluded_days={"OLDUSDTSETTLED": [str(D0 + dt.timedelta(days=12))]})
    assert U.is_candidate_symbol("OLDUSDTSETTLED", ex) and not U.is_candidate_symbol("OLDUSDTSETTLED", EX)
    rows = _span("OLDUSDTSETTLED", D0, 30, 5.0)
    day = D0 + dt.timedelta(days=15)
    assert "OLDUSDTSETTLED" not in U.build_universe(_daily(rows), ex, [day], D0)[day]  # excluded day in its window
    later = D0 + dt.timedelta(days=21)
    assert "OLDUSDTSETTLED" in U.build_universe(_daily(rows), ex, [later], D0)[later]
