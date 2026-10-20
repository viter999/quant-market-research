"""Speed test on SYNTHETIC random-walk data only (no market data): one forecast with the prereg settings."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kt_common as kt

kt.below_normal_priority()

import numpy as np
import pandas as pd
import torch

predictor = kt.load_predictor(threads=int(sys.argv[1]) if len(sys.argv) > 1 else 6)

rng = np.random.default_rng(0)
close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 512)))
df = pd.DataFrame({
    "open": close * (1 + rng.normal(0, 0.001, 512)),
    "high": close * 1.005,
    "low": close * 0.995,
    "close": close,
    "volume": rng.uniform(1e3, 1e4, 512),
})
df["amount"] = df["volume"] * df["close"]
x_ts = pd.Series(pd.date_range("2020-01-01", periods=512, freq="h"))
y_ts = pd.Series(pd.date_range(x_ts.iloc[-1] + pd.Timedelta(hours=1), periods=24, freq="h"))

for run in range(2):
    torch.manual_seed(123)
    t0 = time.perf_counter()
    pred = predictor.predict(df=df, x_timestamp=x_ts, y_timestamp=y_ts, pred_len=24,
                             T=1.0, top_p=0.9, sample_count=10, verbose=False)
    dt = time.perf_counter() - t0
    print(f"run {run}: {dt:.1f}s  pred shape {pred.shape}  threads {torch.get_num_threads()}")

torch.manual_seed(123)
p1 = predictor.predict(df=df, x_timestamp=x_ts, y_timestamp=y_ts, pred_len=24, T=1.0, top_p=0.9, sample_count=10, verbose=False)
torch.manual_seed(123)
p2 = predictor.predict(df=df, x_timestamp=x_ts, y_timestamp=y_ts, pred_len=24, T=1.0, top_p=0.9, sample_count=10, verbose=False)
print("same seed -> identical output:", bool(np.array_equal(p1.values, p2.values)))
