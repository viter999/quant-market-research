"""Run VERDICT once (real archive data). Refuses unless:
  - CA_RUN_VERDICT equals the current, clean git HEAD (gate (b));
  - CA_FUNDING_SHA256 equals the sha256 of <data_dir>/funding_rest_manifest.json and
    every file listed there matches its sha256 (Shawn's REST funding);
  - funding covers every VERDICT universe member-day;
  - results/verdict/VERDICT_RUN_STARTED.json does not exist (runs once).
Usage: CA_RUN_VERDICT=<head> CA_FUNDING_SHA256=<sha> python -I scripts/run_verdict.py <data_dir>"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ca import params as P  # noqa: E402
from ca.lock import ARCHIVE  # noqa: E402
from ca.verdict_run import RefuseToRun, Source, run  # noqa: E402

if __name__ == "__main__":
    data_dir = Path(sys.argv[1])
    try:
        res = run(Source(data_dir, ARCHIVE), P.STUDY_DIR / "results" / "verdict", os.environ.get("CA_FUNDING_SHA256"))
    except RefuseToRun as e:
        raise SystemExit(f"REFUSED: {e}")
    print(json.dumps({"verdict": res["verdict"]["verdict"], "seconds": res["meta"]["seconds"]}))
