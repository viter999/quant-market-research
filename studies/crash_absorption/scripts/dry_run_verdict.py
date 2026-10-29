"""Dry run of the VERDICT runner on SYNTHETIC data only (same code path as the
real run; origin=SYNTHETIC). Usage: python -I scripts/dry_run_verdict.py <empty_dir>"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ca import synthetic_verdict as SV  # noqa: E402
from ca.lock import SYNTHETIC  # noqa: E402
from ca.verdict_run import Source, run  # noqa: E402

if __name__ == "__main__":
    root = Path(sys.argv[1])
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"{root} must be empty")
    w = SV.build(root / "data")
    src = Source(root / "data", SYNTHETIC, fetcher=w["fetcher"], exclusions=w["exclusions"],
                 funding_symbols=w["symbols"], workers=1)
    res = run(src, root / "results", w["expected_funding_sha"])
    v = res["verdict"]
    print(json.dumps({"verdict": v["verdict"], "items": {k: it["pass"] for k, it in v["items"].items()},
                      "counts": res["counts"], "seconds": res["meta"]["seconds"]}, indent=1, default=str))
