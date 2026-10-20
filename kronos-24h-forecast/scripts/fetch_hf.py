"""Download the pinned Hugging Face snapshots into C:\\kronos-test\\models and print their hashes.

Plain-folder downloads (local_dir) instead of the symlinked HF cache, which needs admin rights
or Developer Mode on Windows.
"""
import hashlib
import os

from huggingface_hub import snapshot_download

MODELS_DIR = r"C:\kronos-test\models"
PINS = [
    ("NeoQuasar/Kronos-small", "901c26c1332695a2a8f243eb2f37243a37bea320"),
    ("NeoQuasar/Kronos-Tokenizer-base", "0e0117387f39004a9016484a186a908917e22426"),
]

for repo, rev in PINS:
    local_dir = os.path.join(MODELS_DIR, repo.split("/")[1] + "@" + rev[:7])
    path = snapshot_download(repo_id=repo, revision=rev, local_dir=local_dir)
    print(repo, rev, path)
    for name in sorted(os.listdir(path)):
        full = os.path.join(path, name)
        if os.path.isfile(full):
            with open(full, "rb") as f:
                print(f"  {name:20s} {os.path.getsize(full):>10d}  sha256 {hashlib.sha256(f.read()).hexdigest()}")
