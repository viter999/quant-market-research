import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

spec = importlib.util.spec_from_file_location("ffr", Path(__file__).resolve().parents[1] / "scripts" / "fetch_funding_rest.py")
ffr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ffr)


def test_spans_and_limit():
    assert ffr.LIMIT_MS == 1773446399999  # 2026-03-13T23:59:59.999Z
    assert ffr.SPANS["funding_rest"] == (1772323200000, 1773446399999)
    assert ffr.SPANS["funding_seam"] == (1769904000000, 1772323199999)


@pytest.mark.parametrize("params", [{"symbol": "X", "startTime": 0}, {"symbol": "X", "endTime": 1},
                                    {"symbol": "X", "startTime": 2, "endTime": 1},
                                    {"symbol": "X", "startTime": 0, "endTime": 1773446400000}])
def test_guard_refuses(params):
    with pytest.raises(SystemExit):
        ffr.guard(params)


def test_main_writes_parquet_coverage_manifest(tmp_path, monkeypatch):
    urls = []

    class R:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return self.body

    def urlopen(url, timeout):
        urls.append(url)
        q = dict(p.split("=") for p in url.split("?")[1].split("&"))
        return R(json.dumps([{"fundingTime": int(q["startTime"]) + 1000, "fundingRate": "0.0001"}]).encode())

    monkeypatch.setattr(ffr.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(ffr.time, "sleep", lambda s: None)
    monkeypatch.setattr(ffr.json, "loads", json.loads)
    (tmp_path / "s").mkdir()
    monkeypatch.setattr(ffr, "STUDY", tmp_path / "s")
    (tmp_path / "s" / "funding_rest_symbols.json").write_text(json.dumps({"symbols": ["AUSDT", "BUSDT"]}))
    ffr.main(tmp_path / "out")
    m = json.loads((tmp_path / "out" / "funding_rest_manifest.json").read_text())
    assert len(m["files"]) == 8 and len(urls) == 4
    df = pd.read_parquet(tmp_path / "out" / "funding_rest" / "AUSDT.parquet")
    assert df["ts"].tolist() == [ffr.SPANS["funding_rest"][0] + 1000]
    assert all("endTime=" in u and "fapi.binance.com/fapi/v1/fundingRate" in u for u in urls)


def test_http_error_aborts(monkeypatch, tmp_path):
    def boom(url, timeout):
        raise OSError("HTTP Error 451")
    monkeypatch.setattr(ffr.urllib.request, "urlopen", boom)
    with pytest.raises(OSError):
        ffr.fetch("AUSDT", *ffr.SPANS["funding_rest"])
