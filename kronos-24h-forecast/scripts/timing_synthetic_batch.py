"""Speed test on SYNTHETIC data: predict_batch with N series at once vs one at a time."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kt_common as kt

kt.below_normal_priority()

import numpy as np
import pandas as pd
import torch

n = int(sys.argv[1])
predictor = kt.load_predictor(threads=6)
rng = np.random.default_rng(0)
x_ts = pd.Series(pd.date_range("2020-01-01", periods=512, freq="h"))
y_ts = pd.Series(pd.date_range(x_ts.iloc[-1] + pd.Timedelta(hours=1), periods=24, freq="h"))
dfs = []
for _ in range(n):
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 512)))
    df = pd.DataFrame({"open": close, "high": close * 1.005, "low": close * 0.995, "close": close,
                       "volume": rng.uniform(1e3, 1e4, 512)})
    df["amount"] = df["volume"] * df["close"]
    dfs.append(df)

torch.manual_seed(1)
t0 = time.perf_counter()
out = predictor.predict_batch(dfs, [x_ts] * n, [y_ts] * n, pred_len=24, T=1.0, top_p=0.9, sample_count=10, verbose=False)
dt = time.perf_counter() - t0
print(f"batch of {n}: {dt:.1f}s total, {dt / n:.1f}s per series, {len(out)} outputs of shape {out[0].shape}")
