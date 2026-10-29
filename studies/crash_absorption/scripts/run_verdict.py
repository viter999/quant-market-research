"""Run VERDICT once (real archive data). Refuses unless:
  - CA_RUN_VERDICT equals the current, clean git HEAD (gate (b));
  - CA_FUNDING_SHA256 equals the sha256 of <data_dir>/funding_rest_manifest.json and
    every file listed there matches its sha256 (Shawn's REST funding);
  - funding covers every VERDICT universe member-day;
  - <data_dir>/verdict/run/VERDICT_RUN_STARTED.json does not exist (runs once).
Outputs are written under the gitignored <data_dir>/verdict/run/ (so the tree stays
clean for the outcome lock during the run) and the report files are copied to
results/verdict/ afterwards, for commit.
Usage: CA_RUN_VERDICT=<head> CA_FUNDING_SHA256=<sha> python -I scripts/run_verdict.py <data_dir>"""
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ca import params as P  # noqa: E402
from ca.lock import ARCHIVE  # noqa: E402
from ca.verdict_run import RefuseToRun, Source, run  # noqa: E402

if __name__ == "__main__":
    data_dir = Path(sys.argv[1])
    run_dir = data_dir / "verdict" / "run"
    try:
        res = run(Source(data_dir, ARCHIVE), run_dir, os.environ.get("CA_FUNDING_SHA256"))
    except RefuseToRun as e:
        raise SystemExit(f"REFUSED: {e}")
    dest = P.STUDY_DIR / "results" / "verdict"
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("VERDICT_RUN_STARTED.json", "VERDICT_RESULT.json", "VERDICT_REPORT.md"):
        shutil.copy2(run_dir / name, dest / name)
    print(json.dumps({"verdict": res["verdict"]["verdict"], "seconds": res["meta"]["seconds"]}))
