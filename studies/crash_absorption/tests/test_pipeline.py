import datetime as dt

import numpy as np
import pandas as pd
import pytest

from ca import params as P
from ca.events import minute_features
from ca.lock import SYNTHETIC
from ca.pipeline import detect, fill_table, power_projection, run_detection
from ca.universe import ExclusionsNotFrozen
from tests.synth import crash, klines, ms, trades, universe_all

D = dt.date(2024, 6, 10)


def test_end_to_end_synthetic():
    start = ms(D - dt.timedelta(days=3))
    kx = crash(klines(start, 7 * 1440, seed=1), ms(D, 12, 0), 0.02, 6)
    ky = crash(klines(start, 7 * 1440, seed=2), ms(D, 12, 20), 0.03, 8)
    feats = {"XUSDT": minute_features(kx), "YUSDT": minute_features(ky)}
    uni = universe_all(feats, D - dt.timedelta(days=3), 7)
    ev, cands = detect("dev", feats, uni, SYNTHETIC)
    assert list(ev["symbol"]) == ["XUSDT", "YUSDT"] and ev["episode"].tolist() == [0, 0]

    from ca.placebo import draw_placebos
    pl = draw_placebos(ev, cands)
    assert set(pl["event_id"]) == {0, 1} and pl.groupby("event_id").size().tolist() == [5, 5]

    def trades_for(sym, ref):
        close = float(ev.loc[(ev["symbol"] == sym) & (ev["close_ts"] == ref), "close"].iloc[0]) \
            if ((ev["symbol"] == sym) & (ev["close_ts"] == ref)).any() else None
        if close is None:
            return trades([(ref + 3000, 1e9, 1.0, False)])  # never fills
        return trades([(ref + 8000, close * 1.001, 1.0, False), (ref + 20_000, close * 0.99, 1e6, True)])

    ft = fill_table(ev, trades_for)
    assert len(ft) == 2 * 3 * 3
    assert ft.groupby("latency_s")["kind"].first().to_dict() == {2: "maker", 5: "maker", 10: "gap"}
    fp = fill_table(pl.reset_index(drop=True), trades_for, latencies=(2,), queues=(20,))
    assert not fp["filled"].any()

    pw = power_projection(ev, ft)
    assert pw["dev"] == {"fills": 2, "episodes": 1, "days": 1}
    assert pw["projected_verdict"]["fills"] == pytest.approx(2 * 200 / 602) and not pw["meets_minimum"]


def test_real_detection_refuses_draft_exclusions(tmp_path, monkeypatch):
    import json
    import ca.universe as U
    draft = tmp_path / "EXCLUSIONS.json"
    draft.write_text(json.dumps({"status": "DRAFT"}))
    monkeypatch.setattr(U, "EXCLUSIONS_PATH", draft)
    d = tmp_path / "klines" / "1d"
    d.mkdir(parents=True)
    pd.DataFrame({"open_time": [ms(D)], "quote_volume": [1.0]}).to_parquet(d / "BTCUSDT.parquet")
    with pytest.raises(ExclusionsNotFrozen):
        run_detection("dev", tmp_path, "archive")
