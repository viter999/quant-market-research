# REPORT — Kronos-small next-24h direction (one look)

Generated 2026-10-20 19:01 UTC by `scripts/analyze.py`. Frozen spec: `PREREG_kronos.md`; `FREEZE_kronos.sha256` SHA-256 `a7b9ba2a38419443b4363a2b4d69689157dcebacb73704c1e4452269ed5fbee8`.
457 forecast days × 30 coins.

## Decision: **DROP**

| Test | Mean per day | Std | t | one-sided p | α = 0.05 |
|---|---|---|---|---|---|
| PRIMARY: mean_i(s·r − 0.10% if s ≠ 0) | -0.1081% | 1.928% | -1.199 | 0.8844 | fail |
| SECONDARY: mean_i≠BTC s·(r − r_BTC), gross | -0.0023% | 1.341% | -0.036 | 0.5144 | fail |

## Report only (not part of the decision)

- Hit rate: 50.53% of 13,508 coin-days with s ≠ 0 and r ≠ 0
- Always-long net: -0.1580% per day (t = -0.932)
- Random-sign null, 10,000 runs: PRIMARY share of runs ≥ Kronos 0.5768, 95th pct -0.0342%; SECONDARY share ≥ Kronos 0.5290, 95th pct 0.0537%
- Signals: long 6,455, short 7,255, zero 0

### Per month

| Month | Days | Mean PRIMARY | Mean SECONDARY | Hit rate | Mean always-long net |
|---|---|---|---|---|---|
| 2025-07 | 31 | -0.1509% | 0.0412% | 49.78% | 0.4330% |
| 2025-08 | 31 | 0.2021% | 0.1204% | 56.08% | 0.0034% |
| 2025-09 | 30 | 0.2073% | 0.2790% | 51.17% | -0.1367% |
| 2025-10 | 31 | -0.5941% | -0.4006% | 48.39% | -0.6892% |
| 2025-11 | 30 | -0.2276% | -0.0889% | 46.16% | -0.7578% |
| 2025-12 | 31 | -0.2917% | -0.1485% | 50.05% | -0.4506% |
| 2026-01 | 31 | 0.3580% | 0.4514% | 57.05% | -0.4951% |
| 2026-02 | 28 | 0.3809% | -0.0009% | 49.82% | -0.4865% |
| 2026-03 | 31 | -0.1038% | -0.0338% | 48.38% | -0.1819% |
| 2026-04 | 30 | 0.2947% | 0.2643% | 57.39% | 0.0385% |
| 2026-05 | 31 | -0.0360% | 0.0830% | 50.33% | -0.1877% |
| 2026-06 | 30 | -0.1604% | 0.0137% | 49.54% | -0.8120% |
| 2026-07 | 31 | -0.4249% | -0.1590% | 46.47% | -0.0347% |
| 2026-08 | 31 | -0.3983% | -0.0117% | 49.55% | 0.6817% |
| 2026-09 | 30 | -0.6291% | -0.4423% | 47.53% | 0.6673% |

Daily series: `results/daily_series.csv`. All numbers: `results/analysis.json`.
