"""Standalone REST funding fetch for the crash-absorption study (CLARIFICATIONS
v0.3.2/v0.3.3/v0.3.4). Run by Shawn from a location where fapi.binance.com is
available (the study container gets HTTP 451). Python stdlib + pandas/pyarrow,
no API keys.

Fetches /fapi/v1/fundingRate for every symbol in funding_rest_symbols.json:
  - seam:  2026-02-01 00:00:00.000 .. 2026-02-28 23:59:59.999 UTC -> <out>/funding_seam/
  - rest:  2026-03-01 00:00:00.000 .. 2026-03-13 23:59:59.999 UTC -> <out>/funding_rest/
Each symbol: <SYMBOL>.parquet (ts, rate) + <SYMBOL>.coverage.json; plus
<out>/funding_rest_manifest.json with the sha256 of every file written.

Guard: every request must carry startTime and endTime, start <= end, and endTime
must not pass the VERDICT end in SPLITS.json (2026-03-13); otherwise the script
refuses. Any HTTP/network error aborts the run (zero funding is never assumed).

Usage (from the repository root or anywhere):
  python studies/crash_absorption/scripts/fetch_funding_rest.py <out_dir>
Then send <out_dir> (or commit its manifest) back for verification.
"""
import datetime as dt
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

STUDY = Path(__file__).resolve().parents[1]
SPLITS = json.loads((STUDY / "SPLITS.json").read_text())
MAX_ALLOWED = dt.date.fromisoformat(SPLITS["download_guard"]["max_allowed_date"])
HOST, PATH = "fapi.binance.com", "/fapi/v1/fundingRate"
DAY_MS = 86_400_000


def ms(day: dt.date) -> int:
    return (day - dt.date(1970, 1, 1)).days * DAY_MS


LIMIT_MS = ms(MAX_ALLOWED + dt.timedelta(days=1)) - 1  # 2026-03-13 23:59:59.999
SPANS = {
    "funding_seam": (ms(dt.date(2026, 2, 1)), ms(dt.date(2026, 3, 1)) - 1),
    "funding_rest": (ms(dt.date(2026, 3, 1)), LIMIT_MS),
}


def guard(params: dict) -> None:
    if "startTime" not in params or "endTime" not in params:
        raise SystemExit(f"REFUSED: request without startTime/endTime: {params}")
    if params["startTime"] > params["endTime"]:
        raise SystemExit(f"REFUSED: startTime > endTime: {params}")
    if params["endTime"] > LIMIT_MS:
        raise SystemExit(f"REFUSED: endTime {params['endTime']} is after {MAX_ALLOWED} (HOLDOUT)")


def get(params: dict) -> list:
    guard(params)
    url = f"https://{HOST}{PATH}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=60) as r:  # any HTTP error raises and aborts
        page = json.loads(r.read())
    if not isinstance(page, list):
        raise SystemExit(f"ABORT: unexpected response for {params['symbol']}: {page!r:.300}")
    return page


def fetch(symbol: str, start: int, end: int) -> pd.DataFrame:
    rows, cur = [], start
    while True:
        page = get({"symbol": symbol, "startTime": cur, "endTime": end, "limit": 1000})
        rows += page
        time.sleep(0.5)  # stay well inside the request-weight limit
        if len(page) < 1000:
            break
        cur = int(page[-1]["fundingTime"]) + 1
    df = pd.DataFrame({"ts": [int(r["fundingTime"]) for r in rows],
                       "rate": [float(r["fundingRate"]) for r in rows]}, columns=["ts", "rate"])
    if len(df) and (df["ts"].min() < start or df["ts"].max() > end):
        raise SystemExit(f"ABORT: {symbol} rows outside the requested span")
    return df.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(out: Path) -> None:
    symbols = json.loads((STUDY / "funding_rest_symbols.json").read_text())["symbols"]
    manifest = {"spans_ms": SPANS, "symbols": len(symbols), "files": {}}
    for i, sym in enumerate(symbols, 1):
        for sub, (a, b) in SPANS.items():
            df = fetch(sym, a, b)
            d = out / sub
            d.mkdir(parents=True, exist_ok=True)
            pq, cov = d / f"{sym}.parquet", d / f"{sym}.coverage.json"
            df.to_parquet(pq, index=False)
            cov.write_text(json.dumps([[a, b]]))
            for f in (pq, cov):
                manifest["files"][f"{sub}/{f.name}"] = sha256(f)
            print(f"[{i}/{len(symbols)}] {sym} {sub}: {len(df)} settlements")
    (out / "funding_rest_manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
    print(f"done: {len(manifest['files'])} files, manifest {out / 'funding_rest_manifest.json'}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(Path(sys.argv[1]))
