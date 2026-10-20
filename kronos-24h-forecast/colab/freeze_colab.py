"""Write colab/FREEZE_colab.sha256 (AMENDMENT 2, clarification 6): SHA-256 of every Colab file, before Colab runs.

accept_colab.py refuses real acceptance unless every file still matches this list. Its own digest goes into
AMENDMENTS_kronos.md. Refuses to overwrite an existing freeze.
"""
import datetime as dt
import hashlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "FREEZE_colab.sha256")
FILES = ["colab/colab_forecasts.py", "colab/kronos_colab_bundle.zip", "colab/kronos_colab.ipynb",
         "colab/accept_colab.py", "colab/make_bundle.py", "colab/make_notebook.py", "colab/compare_plumbing.py",
         "colab/test_accept_sandbox.py", "colab/freeze_colab.py", "colab/COLAB_STEPS.md"]


def sha(rel):
    with open(os.path.join(ROOT, *rel.split("/")), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


if os.path.exists(OUT):
    raise SystemExit("colab/FREEZE_colab.sha256 already exists; not overwriting")
now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
lines = [f"# Kronos test, AMENDMENT 2 Colab freeze, {now}. Written before Colab ran anything.",
         "# Format: sha256, two spaces, path relative to C:\\kronos-test."]
lines += [f"{sha(rel)}  {rel}" for rel in FILES]
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines) + "\n")
with open(OUT, "rb") as f:
    print(f"{len(FILES)} Colab files frozen; FREEZE_colab.sha256 SHA-256 {hashlib.sha256(f.read()).hexdigest()}")
