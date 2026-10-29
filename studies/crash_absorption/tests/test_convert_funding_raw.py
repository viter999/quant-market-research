import hashlib
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location("cfr", HERE / "convert_funding_raw.py")
cfr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cfr)
SP = cfr.ffr.SPANS


def _raw(tmp_path, data, spans=None, sha=None):
    body = json.dumps({"meta": {"spans_ms": {k: list(v) for k, v in (spans or SP).items()}}, "data": data})
    p = tmp_path / "raw.json"
    p.write_text(body)
    Path(str(p) + ".sha256").write_text((sha or hashlib.sha256(body.encode()).hexdigest()) + "  raw.json\n")
    return p


def _setup(tmp_path, monkeypatch, symbols):
    st = tmp_path / "study"
    st.mkdir()
    (st / "funding_rest_symbols.json").write_text(json.dumps({"symbols": symbols}))
    monkeypatch.setattr(cfr.ffr, "STUDY", st)


def _row(s, t, r="0.0001"):
    return {"symbol": s, "fundingTime": t, "fundingRate": r, "markPrice": "1", "rateType": "Regular"}


def test_convert_layout_and_manifest(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, ["AUSDT", "BUSDT"])
    a, b = SP["funding_rest"]
    data = {"AUSDT": {"funding_rest": [_row("AUSDT", a + 5)], "funding_seam": []},
            "BUSDT": {"funding_rest": [], "funding_seam": [_row("BUSDT", SP["funding_seam"][0] + 1, "-0.0002")]}}
    man = cfr.convert(_raw(tmp_path, data), tmp_path / "out")
    m = json.loads(man.read_text())
    assert len(m["files"]) == 8 and m["symbols"] == 2
    assert pd.read_parquet(tmp_path / "out" / "funding_rest" / "AUSDT.parquet")["ts"].tolist() == [a + 5]
    assert pd.read_parquet(tmp_path / "out" / "funding_rest" / "BUSDT.parquet").empty
    assert json.loads((tmp_path / "out" / "funding_rest" / "AUSDT.coverage.json").read_text()) == [[a, b]]


def test_refuses_sha_spans_symbols_and_rows(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, ["AUSDT"])
    a, b = SP["funding_rest"]
    ok = {"AUSDT": {"funding_rest": [], "funding_seam": []}}
    with pytest.raises(SystemExit, match="sha256"):
        cfr.convert(_raw(tmp_path, ok, sha="0" * 64), tmp_path / "o1")
    with pytest.raises(SystemExit, match="spans"):
        cfr.convert(_raw(tmp_path, ok, spans={"funding_seam": SP["funding_seam"], "funding_rest": (a, b + 1)}), tmp_path / "o2")
    with pytest.raises(SystemExit, match="symbol set"):
        cfr.convert(_raw(tmp_path, {"XUSDT": ok["AUSDT"]}), tmp_path / "o3")
    with pytest.raises(SystemExit, match="another symbol"):
        cfr.convert(_raw(tmp_path, {"AUSDT": {"funding_rest": [_row("ZUSDT", a)], "funding_seam": []}}), tmp_path / "o4")
    with pytest.raises(SystemExit, match="outside"):
        cfr.convert(_raw(tmp_path, {"AUSDT": {"funding_rest": [_row("AUSDT", b + 1)], "funding_seam": []}}), tmp_path / "o5")


def test_committed_raw_file_sha():
    raw = Path(__file__).resolve().parents[1] / "funding_raw" / "funding_2026-02-01_03-13.json"
    assert cfr.ffr.sha256(raw) == Path(str(raw) + ".sha256").read_text().split()[0] == \
        "006e11f6c1e4cbcefa177e0722a978b98c9ad54f45c66a72915fce40aaddb3f2"
