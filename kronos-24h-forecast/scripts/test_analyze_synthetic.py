"""Test analyze.compute / write_report on SYNTHETIC prices only (no market data, nothing from the window).

1. Hand-computed 2-day x 3-coin case: P, S, hit rate and signal counts must match exactly.
2. Oracle signals on random walks: PRIMARY must pass.
3. Random signals: runs end to end; the null mean of PRIMARY must sit near -fee.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kt_common as kt
import analyze

import numpy as np
import pandas as pd

HOUR = pd.Timedelta(hours=1)
OUT = os.path.join(kt.ROOT, "tmp", "synthetic_test")
os.makedirs(OUT, exist_ok=True)


def frame(rows):
    return pd.DataFrame(rows, columns=["day", "symbol", "c0", "signal"]).astype(str)


# 1. hand-computed
syms = ["BTCUSDT", "AAAUSDT", "BBBUSDT"]
r = {("2025-01-01", "BTCUSDT"): 0.01, ("2025-01-01", "AAAUSDT"): 0.02, ("2025-01-01", "BBBUSDT"): -0.03,
     ("2025-01-02", "BTCUSDT"): -0.02, ("2025-01-02", "AAAUSDT"): 0.0, ("2025-01-02", "BBBUSDT"): 0.05}
s = {("2025-01-01", "BTCUSDT"): 1, ("2025-01-01", "AAAUSDT"): -1, ("2025-01-01", "BBBUSDT"): -1,
     ("2025-01-02", "BTCUSDT"): 0, ("2025-01-02", "AAAUSDT"): 1, ("2025-01-02", "BBBUSDT"): 1}
closes, c0s = {}, {}
for sym in syms:
    # day 2's c0 bar (open 2025-01-01 23:00) is day 1's settlement bar, as in real data
    p0 = 100.0
    p1 = p0 * (1 + r[("2025-01-01", sym)])
    p2 = p1 * (1 + r[("2025-01-02", sym)])
    closes[sym] = pd.Series({pd.Timestamp("2024-12-31 23:00"): p0, pd.Timestamp("2025-01-01 23:00"): p1,
                             pd.Timestamp("2025-01-02 23:00"): p2})
    c0s[("2025-01-01", sym)], c0s[("2025-01-02", sym)] = p0, p1
fc = frame([[d, sym, repr(c0s[(d, sym)]), s[(d, sym)]] for (d, sym) in r])
res = analyze.compute(fc, closes, syms)
P_exp = np.array([(0.009 - 0.021 + 0.029) / 3, (0 - 0.001 + 0.049) / 3])
S_exp = np.array([(-0.01 + 0.04) / 2, (0.02 + 0.07) / 2])
assert np.allclose(res["daily"].P.to_numpy(), P_exp, atol=1e-12), res["daily"].P
assert np.allclose(res["daily"].S.to_numpy(), S_exp, atol=1e-12), res["daily"].S
assert abs(res["primary"]["mean"] - P_exp.mean()) < 1e-12
assert res["report_only"]["hit_rate"] == 0.75 and res["report_only"]["hit_n"] == 4
assert (res["report_only"]["signals_long"], res["report_only"]["signals_short"],
        res["report_only"]["signals_zero"]) == (3, 2, 1)
print("1. hand-computed case: OK")

# 2 + 3. random walks, 30 coins, 120 days
rng = np.random.default_rng(7)
syms = ["BTCUSDT"] + [f"C{j:02d}USDT" for j in range(1, 30)]
hours = pd.date_range("2024-12-31 00:00", "2025-05-02 00:00", freq="h")
closes = {sym: pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(hours)))), index=hours) for sym in syms}
days = pd.date_range("2025-01-01", periods=120, freq="D")


def build(signal_fn):
    rows = []
    for D in days:
        for sym in syms:
            c0 = closes[sym][D - HOUR]
            r_true = closes[sym][D + 23 * HOUR] / c0 - 1
            rows.append([D.strftime("%Y-%m-%d"), sym, repr(float(c0)), signal_fn(r_true)])
    return frame(rows)


res = analyze.compute(build(lambda x: int(np.sign(x))), closes, syms)
assert res["primary"]["pass"] and res["primary"]["p_one_sided"] < 1e-6, res["primary"]
assert res["report_only"]["hit_rate"] == 1.0
print(f"2. oracle signals: PRIMARY mean {res['primary']['mean']:.4f}, p {res['primary']['p_one_sided']:.2e}: OK")

res = analyze.compute(build(lambda x: int(rng.choice([-1, 1]))), closes, syms)
analyze.save_outputs(res, OUT, os.path.join(OUT, "REPORT_synthetic.md"), "0" * 64)
assert os.path.exists(os.path.join(OUT, "analysis.json")) and os.path.exists(os.path.join(OUT, "daily_series.csv"))
ro = res["report_only"]
assert 0.0 <= ro["null_primary_share_ge"] <= 1.0 and 0.0 <= res["primary"]["p_one_sided"] <= 1.0
assert len(res["monthly"]) == 4 and int(res["monthly"].days.sum()) == 120
print(f"3. random signals: PRIMARY p {res['primary']['p_one_sided']:.3f}, null share>= {ro['null_primary_share_ge']:.3f}, "
      f"decision {res['decision']}: OK (report written to tmp)")

# 4. validate(): accepts a consistent file, rejects a wrong signal, a wrong seed and a missing row
syms4 = ["BTCUSDT", "AAAUSDT"]
days4 = list(pd.date_range("2025-01-01", periods=3, freq="D"))
fc4 = pd.DataFrame([{"day": d.strftime("%Y-%m-%d"), "coin_index": str(i), "symbol": sym,
                     "seed": str(kt.seed_for(d, i)), "c0": "100.0", "p24": "101.0", "signal": "1"}
                    for d in days4 for i, sym in enumerate(syms4)])
analyze.validate(fc4, syms4, days4)
for col, val in [("signal", "-1"), ("seed", "1")]:
    bad = fc4.copy()
    bad.loc[0, col] = val
    try:
        analyze.validate(bad, syms4, days4)
        raise AssertionError(f"validate accepted a bad {col}")
    except SystemExit:
        pass
try:
    analyze.validate(fc4.iloc[1:], syms4, days4)
    raise AssertionError("validate accepted a missing row")
except SystemExit:
    pass
print("4. validate(): OK")
print("ALL SYNTHETIC TESTS PASSED")
