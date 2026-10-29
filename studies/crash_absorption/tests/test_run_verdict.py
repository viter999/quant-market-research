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
