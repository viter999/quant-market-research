"""Convert Shawn's raw REST funding JSON (fetched in a browser with the logic of
fetch_funding_rest.py) into exactly the layout fetch_funding_rest.py writes:
<out>/funding_rest|funding_seam/<SYMBOL>.parquet + .coverage.json + funding_rest_manifest.json.
Refuses unless the raw file's sha256 equals the committed <raw>.sha256, its
spans equal SPANS, its symbols equal funding_rest_symbols.json, and every row
lies inside its span (max endTime = VERDICT end).
Usage: python -I scripts/convert_funding_raw.py <raw.json> <out_dir>"""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ffr", HERE / "fetch_funding_rest.py")
ffr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ffr)


def convert(raw: Path, out: Path) -> Path:
    want_sha = Path(str(raw) + ".sha256").read_text().split()[0]
    got = ffr.sha256(raw)
    if got != want_sha:
        raise SystemExit(f"REFUSED: raw sha256 {got} != committed {want_sha}")
    r = json.loads(raw.read_text())
    if {k: tuple(v) for k, v in r["meta"]["spans_ms"].items()} != ffr.SPANS:
        raise SystemExit(f"REFUSED: spans {r['meta']['spans_ms']} != {ffr.SPANS}")
    symbols = json.loads((ffr.STUDY / "funding_rest_symbols.json").read_text())["symbols"]
    if set(r["data"]) != set(symbols):
        raise SystemExit(f"REFUSED: symbol set differs from funding_rest_symbols.json")
    frames = {}
    for sym in symbols:
        for sub, (a, b) in ffr.SPANS.items():
            rows = r["data"][sym].get(sub, [])
            if any(x["symbol"] != sym for x in rows):
                raise SystemExit(f"REFUSED: {sym} {sub} contains rows of another symbol")
            ffr.guard({"startTime": a, "endTime": b})
            frames[(sym, sub)] = ffr.rows_to_frame(sym, rows, a, b)
    return ffr.write_outputs(out, frames)


if __name__ == "__main__":
    path = convert(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"manifest {path} sha256 {ffr.sha256(path)}")
