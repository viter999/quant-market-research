"""Build colab/kronos_colab_bundle.zip: the frozen input files, their hashes, and the Colab script.

expected_bars_sha256.json is computed with the FROZEN laptop loader (scripts/kt_binance.load_1h_bars), so the
Colab loader must reproduce the laptop's parsed numbers exactly. The zip uses fixed timestamps, so rebuilding
from the same files gives the same SHA-256.
"""
import hashlib
import json
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import kt_common as kt
import kt_binance as kb

import numpy as np

FEATURES = ["open", "high", "low", "close", "volume", "amount"]
OUT = os.path.join(HERE, "kronos_colab_bundle.zip")
FIXED_TIME = (2026, 10, 18, 0, 0, 0)


def bars_digest(df):   # identical to colab_forecasts.bars_digest
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(df.index.values.astype("datetime64[ns]").view("int64")).tobytes())
    h.update(np.ascontiguousarray(df[FEATURES].to_numpy(dtype=np.float64)).tobytes())
    return h.hexdigest()


def add(z, arcname, data, compress):
    info = zipfile.ZipInfo(arcname, FIXED_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    info.external_attr = 0o644 << 16
    z.writestr(info, data)


def main():
    kt.verify_freeze()
    syms = kt.universe()
    expected = {s: bars_digest(kb.load_1h_bars(s, *kt.DATA_MONTHS)) for s in syms}
    with zipfile.ZipFile(OUT + ".part", "w") as z:
        add(z, "FREEZE_kronos.sha256", open(kt.FREEZE, "rb").read(), True)
        add(z, "data/universe/universe_frozen.json", open(kt.UNIVERSE_JSON, "rb").read(), True)
        for s in syms:
            for m in kb.months(*kt.DATA_MONTHS):
                path = kb.local_zip(s, "1h", m)
                add(z, f"data/raw/futures_um_monthly_klines/{s}/1h/{os.path.basename(path)}", open(path, "rb").read(), False)
        add(z, "expected_bars_sha256.json", json.dumps(expected, indent=2).encode(), True)
        add(z, "colab_forecasts.py", open(os.path.join(HERE, "colab_forecasts.py"), "rb").read(), True)
    os.replace(OUT + ".part", OUT)
    print(f"{OUT}: {os.path.getsize(OUT):,} bytes, sha256 {kt.sha256_file(OUT)}")


if __name__ == "__main__":
    main()
