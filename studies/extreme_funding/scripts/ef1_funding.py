"""EF-1 step 2a: fundingRate monthly for all USDT-M perps (incl. ...USDTSETTLED), 2023-12..2026-02
(guard on: listings are date-bounded, downloads guarded + CHECKSUM). March 2026-03-01..13 comes
from the REST files already converted for crash-absorption (177 universe members)."""
import concurrent.futures as cf
import datetime as dt
import json
import sys
import time
from pathlib import Path

import pandas as pd

EF = Path(__file__).resolve().parents[1]
CA = EF.parent / "crash_absorption"
sys.path.insert(0, str(EF))
sys.path.insert(0, str(CA))
from ca import downloader as DL  # noqa: E402
from ef import archive as A  # noqa: E402

DATA = EF / "data"


def main():
    t0 = time.time()
    inv = json.loads((CA / "data" / "inventory_klines.json").read_text())["files"]
    syms = sorted(s for s, d in inv.items() if d["1m"] and "_" not in s and (s.endswith("USDT") or s.endswith("USDTSETTLED")))
    fetch, out_dir = DL.HttpFetcher(), DATA / "funding"
    out_dir.mkdir(parents=True, exist_ok=True)

    def one(s):
        p = out_dir / f"{s}.parquet"
        if p.exists():
            return s, len(pd.read_parquet(p)), None
        try:
            keys = [k for pre in A.monthly_prefixes(f"data/futures/um/monthly/fundingRate/{s}", f"{s}-fundingRate", dt.date(2023, 12, 1))
                    for k, _ in A.list_zips(fetch, pre)]
            parts = [A.parse_funding(A.fetch_csv(fetch, k, A.FUNDING_COLS), k[-11:-4]) for k in sorted(keys)]
            df = pd.concat(parts).sort_values("ts").drop_duplicates("ts") if parts else pd.DataFrame(columns=["ts", "interval_h_archive", "rate"])
            df["months"] = ",".join(k[-11:-4] for k in sorted(keys))
            df.to_parquet(p, index=False)
            return s, len(df), None
        except Exception as e:
            return s, 0, f"{type(e).__name__}: {e}"

    rows, errors = 0, {}
    with cf.ThreadPoolExecutor(16) as ex:
        for s, n, err in ex.map(one, syms):
            rows += n
            if err:
                errors[s] = err
    info = {"symbols": len(syms), "settlement_rows": rows, "errors": errors, "seconds": round(time.time() - t0)}
    (DATA / "steps.json").write_text(json.dumps({"funding": info}, indent=1))
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
