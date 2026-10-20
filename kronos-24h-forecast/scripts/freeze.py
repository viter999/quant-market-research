"""Write FREEZE_kronos.sha256: SHA-256 of the prereg, all scripts, the universe, Kronos code, weights and data.

  freeze.py                      first freeze (refuses if a freeze already exists)
  freeze.py --amend "reason"     re-freeze after a logged bug fix; keeps the old file as FREEZE_kronos.vN.sha256
"""
import argparse
import datetime as dt
import glob
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kt_common as kt
import kt_binance as kb


def files():
    rel = ["PREREG_kronos.md",
           os.path.join("data", "universe", "universe_frozen.json"),
           os.path.join("data", "universe", "ranking_2025-06_quote_volume.csv")]
    rel += sorted(os.path.relpath(p, kt.ROOT) for p in glob.glob(os.path.join(kt.ROOT, "scripts", "*.py")))
    rel += sorted(os.path.relpath(p, kt.ROOT) for p in glob.glob(os.path.join(kt.REPO, "model", "*.py")))
    for d in (kt.MODEL_DIR, kt.TOKENIZER_DIR):
        rel += [os.path.relpath(os.path.join(d, n), kt.ROOT) for n in ("config.json", "model.safetensors")]
    for sym in kt.universe():
        for m in kb.months(*kt.DATA_MONTHS):
            rel.append(os.path.relpath(kb.local_zip(sym, "1h", m), kt.ROOT))
    return rel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--amend", default="")
    args = ap.parse_args()
    if os.path.exists(kt.FREEZE):
        if not args.amend:
            raise SystemExit("already frozen; use --amend \"reason\" for a logged bug-fix re-freeze")
        n = len(glob.glob(os.path.join(kt.ROOT, "FREEZE_kronos.v*.sha256"))) + 1
        shutil.copy2(kt.FREEZE, os.path.join(kt.ROOT, f"FREEZE_kronos.v{n}.sha256"))
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rel = files()
    missing = [r for r in rel if not os.path.exists(os.path.join(kt.ROOT, r))]
    if missing:
        raise SystemExit(f"missing files: {missing[:5]}")
    head = [f"# Kronos test freeze, {now}. Owner OK given in chat on 2026-10-18 before any test-window computation.",
            "# Format: sha256, two spaces, path relative to C:\\kronos-test. Checked by every run script at start."]
    if args.amend:
        head.append(f"# AMENDED: {args.amend}")
    body = [f"{kt.sha256_file(os.path.join(kt.ROOT, r))}  {r}" for r in rel]
    with open(kt.FREEZE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(head + body) + "\n")
    if args.amend:
        with open(os.path.join(kt.ROOT, "AMENDMENTS_kronos.md"), "a", encoding="utf-8") as f:
            f.write(f"- {now}: {args.amend} (new FREEZE SHA-256 {kt.sha256_file(kt.FREEZE)})\n")
    print(f"{len(body)} files frozen; FREEZE_kronos.sha256 SHA-256 {kt.sha256_file(kt.FREEZE)}")


if __name__ == "__main__":
    main()
