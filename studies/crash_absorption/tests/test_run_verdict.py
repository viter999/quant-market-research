"""VERDICT runner: end-to-end dry run on SYNTHETIC data and every refusal path."""
import json
import shutil

import pandas as pd
import pytest

from ca import synthetic_verdict as SV
from ca.lock import ARCHIVE, SYNTHETIC
from ca.verdict_run import RefuseToRun, Source, preconditions, run


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    root = tmp_path_factory.mktemp("synthetic_world")
    w = SV.build(root / "data")
    return root, w


def _src(root, w, origin=SYNTHETIC):
    return Source(root / "data", origin, fetcher=w["fetcher"], exclusions=w["exclusions"],
                  funding_symbols=w["symbols"], workers=1)


def test_dry_run_end_to_end(world, tmp_path):
    root, w = world
    res = run(_src(root, w), tmp_path / "results", w["expected_funding_sha"])
    v = res["verdict"]
    assert v["verdict"] in ("PASS", "KILL", "NOT EVALUABLE")
    assert set(v["items"]) == {"1_sample_size", "2_mean_net_1x", "3_mean_net_2x", "4_beats_placebo"}
    assert res["counts"]["events"] > 0 and res["counts"]["primary_fills"] > 0
    i4 = v["items"]["4_beats_placebo"]
    assert i4["events_compared"] + i4["events_without_placebo"] == res["counts"]["events"]
    rep = (tmp_path / "results" / "VERDICT_REPORT.md").read_text()
    assert "Item 4 event side: n = " in rep and "excluded (0 placebos)" in rep
    assert rep.count("(EXPLORATORY)") == len(res["exploratory"])
    for k in ("E1_grid_depth_latency_queue_15min_1x", "E2_primary_hold_x_buffer", "E4_B2_taker_at_close"):
        assert k in res["exploratory"]
    assert len(res["exploratory"]["E1_grid_depth_latency_queue_15min_1x"]) == 27
    assert res["seam"]["symbols_compared"] == len(w["symbols"]) and res["seam"]["max_abs_drate"] == 0.0
    assert (tmp_path / "results" / "VERDICT_RUN_STARTED.json").exists()
    oc = pd.read_parquet(tmp_path / "results" / "outcomes.parquet")
    assert set(oc["config"]) >= {"grid", "B2"}
    # the run-once lock refuses a second run in the same results directory
    with pytest.raises(RefuseToRun, match="runs once"):
        run(_src(root, w), tmp_path / "results", w["expected_funding_sha"])


def test_refuses_archive_without_unlock(world, tmp_path, monkeypatch):
    root, w = world
    monkeypatch.delenv("CA_RUN_VERDICT", raising=False)
    with pytest.raises(RefuseToRun, match="CA_RUN_VERDICT"):
        run(_src(root, w, ARCHIVE), tmp_path, w["expected_funding_sha"])
    monkeypatch.setenv("CA_RUN_VERDICT", "0" * 40)
    with pytest.raises(RefuseToRun, match="CA_RUN_VERDICT"):
        preconditions(_src(root, w, ARCHIVE), tmp_path, w["expected_funding_sha"])
    assert not (tmp_path / "VERDICT_RUN_STARTED.json").exists()


@pytest.mark.parametrize("sha", [None, "", "f" * 64])
def test_refuses_wrong_or_missing_funding_sha(world, tmp_path, sha):
    root, w = world
    with pytest.raises(RefuseToRun, match="sha256"):
        preconditions(_src(root, w), tmp_path, sha)


def _copy(root, tmp_path):
    shutil.copytree(root / "data", tmp_path / "data")
    return tmp_path


def test_refuses_tampered_funding_file(world, tmp_path):
    root, w = world
    r = _copy(root, tmp_path)
    p = r / "data" / "funding_rest" / f"{w['symbols'][0]}.parquet"
    df = pd.read_parquet(p)
    df.loc[0, "rate"] = 0.5
    df.to_parquet(p, index=False)
    with pytest.raises(RefuseToRun, match="mismatch"):
        preconditions(_src(r, w), tmp_path / "out", w["expected_funding_sha"])


def test_refuses_missing_manifest_or_symbol(world, tmp_path):
    root, w = world
    r = _copy(root, tmp_path)
    src = Source(r / "data", SYNTHETIC, fetcher=w["fetcher"], exclusions=w["exclusions"],
                 funding_symbols=w["symbols"] + ["OTHERUSDT"], workers=1)
    with pytest.raises(RefuseToRun, match="lacks funding_rest"):
        preconditions(src, tmp_path / "out", w["expected_funding_sha"])
    (r / "data" / "funding_rest_manifest.json").unlink()
    with pytest.raises(RefuseToRun, match="manifest missing"):
        preconditions(_src(r, w), tmp_path / "out", w["expected_funding_sha"])


def test_refuses_funding_coverage_gap_before_detection(world, tmp_path):
    root, w = world
    r = _copy(root, tmp_path)
    cov = r / "data" / "funding" / f"{w['symbols'][1]}.coverage.json"
    a, b = json.loads(cov.read_text())[0]
    cov.write_text(json.dumps([[a, a + 20 * 86_400_000]]))  # archive coverage ends early
    with pytest.raises(RefuseToRun, match="coverage gaps"):
        run(_src(r, w), tmp_path / "out", w["expected_funding_sha"])
    assert not (tmp_path / "out" / "VERDICT_RUN_STARTED.json").exists()  # refused before the lock / detection


def test_clip_windows_and_beyond_end():
    from ca.verdict_run import LIMIT_MS, beyond_end, clip_windows
    import datetime as dt
    d13, d14 = dt.date(2026, 3, 13), dt.date(2026, 3, 14)
    w = {d13: [(LIMIT_MS - 3600_000, LIMIT_MS)], d14: [(LIMIT_MS + 1, LIMIT_MS + 1800_000)]}
    assert clip_windows(w) == {d13: [(LIMIT_MS - 3600_000, LIMIT_MS)]}
    last_fill = LIMIT_MS + 1 - (24 * 60 - (23 * 60 + 35)) * 60_000 + 10_000  # 23:35:10 on 2026-03-13
    assert not beyond_end(last_fill, 15)  # primary exit always inside VERDICT (23:30 cutoff)
    assert beyond_end(last_fill, 30) and beyond_end(last_fill, 60)


class FakeGit:
    """Stands in for git in ca.lock: counts calls; status turns dirty after `dirty_after` calls."""
    def __init__(self, head="a" * 40, dirty_after=None):
        self.head, self.dirty_after, self.calls = head, dirty_after, []

    def __call__(self, *args):
        self.calls.append(args)
        if args[0] == "rev-parse":
            return self.head
        return " M ca/fill.py" if self.dirty_after is not None and len(self.calls) > self.dirty_after else ""


def test_archive_origin_run_checks_unlock_once_at_start_and_once_at_end(world, tmp_path, monkeypatch):
    """origin=ARCHIVE through the whole runner: git is called only for the start
    check and the end check (2 + 2 calls), not per outcome row."""
    import ca.lock as L
    root, w = world
    fake = FakeGit()
    monkeypatch.setattr(L, "_git", fake)
    monkeypatch.setenv("CA_RUN_VERDICT", fake.head)
    res = run(_src(root, w, ARCHIVE), tmp_path / "run", w["expected_funding_sha"])
    assert res["meta"]["origin"] == ARCHIVE and res["meta"]["code_head"] == fake.head
    assert res["meta"]["end_check"] == "HEAD and tree verified unchanged"
    assert len(fake.calls) == 4, fake.calls
    assert res["counts"]["primary_fills"] > 0 and res["verdict"]["verdict"] in ("PASS", "KILL", "NOT EVALUABLE")


def test_tree_change_mid_run_blocks_result(world, tmp_path, monkeypatch):
    import ca.lock as L
    root, w = world
    fake = FakeGit(dirty_after=2)  # clean at the start check, dirty at the end check
    monkeypatch.setattr(L, "_git", fake)
    monkeypatch.setenv("CA_RUN_VERDICT", fake.head)
    with pytest.raises(RefuseToRun, match="changed during the VERDICT run"):
        run(_src(root, w, ARCHIVE), tmp_path / "run", w["expected_funding_sha"])
    assert (tmp_path / "run" / "VERDICT_RUN_STARTED.json").exists()
    assert not (tmp_path / "run" / "VERDICT_RESULT.json").exists() and not (tmp_path / "run" / "VERDICT_REPORT.md").exists()


def test_missing_aggtrades_excluded_from_both_arms(world, tmp_path):
    """v0.3.5: an event day and a placebo-only day served as 404 -> those orders leave
    their arms (event not counted as an unfilled 0), and the excluded event's placebos go too."""
    root, w = world
    r = _copy(root, tmp_path)
    full = run(_src(r, w), tmp_path / "full", w["expected_funding_sha"])
    ev = pd.read_parquet(tmp_path / "full" / "events.parquet")
    pl = pd.read_parquet(tmp_path / "full" / "placebos.parquet")
    from ca import params as P
    e = ev.iloc[len(ev) // 2]
    ev_day = P.ms_to_date(int(e["close_ts"]))
    pl_days = {(s, P.ms_to_date(int(t))) for s, t in zip(pl["symbol"], pl["close_ts"])}
    ev_days = {(s, P.ms_to_date(int(t))) for s, t in zip(ev["symbol"], ev["close_ts"])}
    placebo_only = sorted(pl_days - ev_days)[0]
    r2 = _copy(root, tmp_path / "second")
    for s, d in [(e["symbol"], ev_day), placebo_only]:
        f = r2 / "data" / "verdict" / "aggtrades" / s / f"{d.isoformat()}.parquet"
        if f.exists():
            f.unlink()
        w["fetcher"].missing.add((s, d.isoformat()))
    try:
        res = run(_src(r2, w), tmp_path / "missing", w["expected_funding_sha"])
    finally:
        w["fetcher"].missing.clear()
    c = res["counts"]
    assert c["event_orders_data_missing"] >= 1 and c["placebo_orders_data_missing"] >= 1
    assert c["events_in_verdict_arms"] == c["events"] - c["event_orders_data_missing"]
    assert res["verdict"]["counts"]["orders"] == c["events_in_verdict_arms"]
    assert c["placebos_removed_with_their_event"] >= 0
    i4 = res["verdict"]["items"]["4_beats_placebo"]
    assert i4["placebo_orders"] == c["placebos"] - c["placebo_orders_data_missing"] - c["placebos_removed_with_their_event"] \
        - int((pd.read_parquet(tmp_path / "missing" / "outcomes.parquet").query("order_kind == 'placebo' and config == 'grid' and hold == 15 and mult == 1")
               .eval("filled & dropped")).sum())
    rep = (tmp_path / "missing" / "VERDICT_REPORT.md").read_text()
    assert "Missing aggTrades (v0.3.5, excluded from both arms): event orders = " in rep
    assert full["counts"]["event_orders_data_missing"] == 0


def test_coverage_check_skips_zero_volume_member_days(world, tmp_path):
    """A coverage gap on a member day with zero 1d quote volume (delisted, flat
    filler bars) is skipped; the same gap on a traded day refuses."""
    import datetime as dt
    from ca import params as P
    from ca.pipeline import segment_days
    from ca.universe import build_universe
    from ca.verdict_run import check_funding_coverage
    from ca import downloader as DL
    root, w = world
    r = _copy(root, tmp_path)
    s = w["symbols"][2]
    gap_day = dt.date(2025, 9, 10)
    cov = r / "data" / "funding" / f"{s}.coverage.json"
    a, b = json.loads(cov.read_text())[0]
    g0, g1 = P.date_to_ms(gap_day), P.date_to_ms(gap_day + dt.timedelta(days=2))
    cov.write_text(json.dumps([[a, g0 - 1], [g1, b]]))
    src = _src(r, w)
    daily = src.daily()
    uni = build_universe(daily, w["exclusions"], segment_days("verdict"), DL.DOWNLOAD_START)
    with pytest.raises(RefuseToRun, match="coverage gaps"):
        check_funding_coverage(src, uni, daily)
    flat = daily.copy()
    flat.loc[(flat["symbol"] == s) & flat["day"].isin([gap_day, gap_day - dt.timedelta(days=1), gap_day + dt.timedelta(days=1)]),
             "quote_volume"] = 0.0
    info = check_funding_coverage(src, uni, flat)
    assert info["zero_volume_member_days_skipped"] >= 1
