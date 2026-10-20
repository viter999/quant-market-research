"""Laptop check: rows from colab_forecasts.py (CPU) must equal the frozen CPU runner's pre-window plumbing rows."""
import sys

import pandas as pd

new = pd.read_csv(sys.argv[1], dtype=str)
ref = pd.read_csv(sys.argv[2], dtype=str)
cols = [c for c in new.columns if c not in ("seconds", "finished_utc")]
assert list(new.columns) == list(ref.columns), "column layout differs"
merged = new.merge(ref, on=["day", "symbol"], suffixes=("_new", "_ref"))
assert len(merged) == len(new), "rows not found in the frozen plumbing file"
bad = [c for c in cols if c not in ("day", "symbol") and not (merged[c + "_new"] == merged[c + "_ref"]).all()]
print(f"compared {len(merged)} rows x {len(cols)} columns: " + ("IDENTICAL" if not bad else f"DIFFER in {bad}"))
sys.exit(1 if bad else 0)
