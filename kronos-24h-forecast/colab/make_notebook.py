"""Write colab/kronos_colab.ipynb with the bundle's SHA-256 built in.

Every step runs through run(), which streams the output into the cell and raises (a red error that stops
Runtime > Run all) when a command fails, so a failure can never look like a normal finish.
"""
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLE = os.path.join(HERE, "kronos_colab_bundle.zip")
OUT = os.path.join(HERE, "kronos_colab.ipynb")


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def code(src):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": src.strip("\n").splitlines(keepends=True)}


def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src.strip("\n").splitlines(keepends=True)}


cells = [
    md("""
# Kronos test: Colab GPU run (AMENDMENT 2)

Runs the frozen Kronos-small forecasts on a GPU. It prints **only progress counts**, never forecasts or outcomes.

* Start or resume: menu **Runtime > Run all**. Finished forecasts are kept on Google Drive and skipped.
* Keep this tab open while it runs.
* If a cell shows a red error, stop and send Claude the message.
* When it says `COMPLETE`, download the three files from `My Drive/kronos_colab/run` (see the steps). Do not open them.
"""),
    code(f'''
# 1. Settings, GPU check, and a helper that stops everything on any failure
BUNDLE_SHA256 = "{sha256(BUNDLE)}"
DRIVE_FOLDER = "/content/drive/MyDrive/kronos_colab"
RUN_DIR = DRIVE_FOLDER + "/run"
SCRIPT = "/content/bundle/colab_forecasts.py"
import subprocess, sys

def run(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in p.stdout:
        print(line, end="", flush=True)
    if p.wait() != 0:
        raise RuntimeError("This step failed (exit code %d). Stop here and send Claude the messages above." % p.returncode)

r = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True)
if r.returncode != 0 or "GPU" not in r.stdout:
    raise RuntimeError("No GPU. Menu: Runtime > Change runtime type > T4 GPU > Save. Then Runtime > Run all.")
print(r.stdout.strip())
'''),
    code('''
# 2. Connect Google Drive (forecasts are saved there as they are made)
from google.colab import drive
drive.mount("/content/drive")
'''),
    code('''
# 3. Check and unpack the data bundle
import hashlib, os, zipfile
src = DRIVE_FOLDER + "/kronos_colab_bundle.zip"
if not os.path.exists(src):
    raise RuntimeError("kronos_colab_bundle.zip not found in My Drive/kronos_colab. Upload it there first.")
h = hashlib.sha256(open(src, "rb").read()).hexdigest()
if h != BUNDLE_SHA256:
    raise RuntimeError("kronos_colab_bundle.zip is not the expected file (SHA-256 mismatch). Upload the original.")
with zipfile.ZipFile(src) as z:
    for name in z.namelist():
        if name.startswith("/") or ".." in name.split("/"):
            raise RuntimeError("unsafe path in bundle: " + name)
    z.extractall("/content/bundle")
print("bundle ok, sha256", h)
'''),
    code('''
# 4. Pinned helper packages (as on the laptop). Lines about "dependency conflicts" from pip are expected.
run([sys.executable, "-m", "pip", "install", "-q", "einops==0.8.1", "safetensors==0.6.2", "huggingface_hub==0.33.1"])
print("packages ok")
'''),
    code('''
# 5. Self-test: checks every hash, 2 pre-window forecasts (shapes, finite values, same-seed repeat), Drive write speed
import os
if os.path.exists("/content/work/selftest_ok.json"):
    os.remove("/content/work/selftest_ok.json")
run([sys.executable, "-u", SCRIPT, "--bundle", "/content/bundle", "--work", "/content/work", "--out", RUN_DIR, "--self-test"])
if not os.path.exists("/content/work/selftest_ok.json"):
    raise RuntimeError("Self-test failed. Stop here and send Claude the messages above.")
'''),
    code('''
# 6. Full run: 13,710 forecasts, saved to Drive one by one, resumes where it stopped
import os
if "RUN_DIR" not in globals() or not os.path.exists("/content/work/selftest_ok.json"):
    raise RuntimeError("Cells 1-5 have not run in this session. Use Runtime > Run all.")
run([sys.executable, "-u", SCRIPT, "--bundle", "/content/bundle", "--work", "/content/work", "--out", RUN_DIR,
     "--bundle-sha", BUNDLE_SHA256])
'''),
    code('''
# 7. Final check: the saved file must match its manifest before you download anything
import hashlib, json, os
manifest = RUN_DIR + "/colab_manifest.json"
if not os.path.exists(manifest):
    raise RuntimeError("Not complete yet. Use Runtime > Run all to resume.")
m = json.load(open(manifest))
h = hashlib.sha256(open(RUN_DIR + "/forecasts.csv", "rb").read()).hexdigest()
if h != m["forecasts_csv_sha256"]:
    raise RuntimeError("forecasts.csv on Drive does not match its manifest. Use Runtime > Run all again.")
drive.flush_and_unmount()
print("COMPLETE:", m["rows"], "forecasts, sha256", h)
print("Saved to Google Drive. Now download forecasts.csv, colab_manifest.json and colab_sessions.log")
print("from My Drive/kronos_colab/run as described in the steps. Do not open them.")
'''),
]

nb = {"nbformat": 4, "nbformat_minor": 0, "cells": cells,
      "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "T4"},
                   "kernelspec": {"name": "python3", "display_name": "Python 3"},
                   "language_info": {"name": "python"}}}
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    json.dump(nb, f, indent=1)
print(f"{OUT}: sha256 {sha256(OUT)}")
