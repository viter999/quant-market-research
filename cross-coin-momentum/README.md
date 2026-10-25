# Cross-coin momentum on Binance perpetuals: a pre-registered, one-look test

**Result: FAIL.** No edge after costs.

## What was tested

**Question:** do coins with the highest past 28-day return keep beating the coins with the lowest over the next week, after costs?

- **Market:** Binance USDT-margined perpetual futures, public archive data (daily klines and funding). Delisted coins are included; stablecoins, index contracts and tokenised gold are excluded.
- **Signal:** the 28-day return, skipping the most recent day.
- **Portfolio:** every Monday, long the top third and short the bottom third of eligible coins, equal weight, held for 7 days. Coins need at least 60 days of listing and $2M average daily volume.
- **Returns:** price change plus funding paid or received, minus costs of 21 bps per side on actual turnover.
- **Sample:** 142 weeks, 2020-04-06 to 2022-12-19. This period had not been looked at before. The first 13 Mondays of 2020 were skipped because too few coins were eligible.
- **Pass rule:** the mean weekly net return must be above 0 with Newey-West t > 1.645 (one-sided, alpha 0.05).

**Process:**
1. Pre-registration written and frozen (SHA-256) before any signal-versus-return number was computed.
2. Fake-data check: 200 shuffled datasets in which momentum cannot work. It had to find nothing before the real data was used. It passed: 6% false rejections against a 9% limit, mean −1.3 bps per week.
3. One look at the real data. No re-runs.

## Result

| | Mean per week | Newey-West t |
|---|---|---|
| Net return, all 142 weeks | **−0.6 bps** | −0.01 |
| Net return, without the 2 best weeks | −30.1 bps | −0.57 |
| Gross return (price +28.0, funding +3.6) | +31.6 bps | |
| Costs | 32.2 bps | |

- Median 37 coins per side.
- The two best weeks (2021-03-08 and 2021-05-03) returned about +21% each.
- Both legs had similar BTC betas (long 1.10, short 1.14).

**Replication, 2023-01 to 2026-09 (descriptive only, not pass/fail).** This data had already been seen in an earlier study.

| | Mean per week | Newey-West t |
|---|---|---|
| Net return, 195 weeks | −24.3 bps | −0.95 |
| Gross return | +7.5 bps | |
| Costs | 31.9 bps | |

## Why it failed

- **Costs ate the edge.** Weekly rebalancing turned over about 1.5× the book each week. At 21 bps per side that cost about 32 bps per week, roughly the whole gross return.
- **The gross edge was not robust.** Two weeks in early 2021 produced more than all the other weeks combined. Without them, the net result is −30 bps per week.
- **The later sample is worse.** In 2023–2026 the gross return fell to +7.5 bps per week, far below costs.

## Files

| File | Content |
|---|---|
| `PREREG_v0.2.md` | The frozen pre-registration (exact copy) |
| `RESULT.md` | The one-look result (exact copy) |
| `HASHES.txt` | SHA-256 of the two files above |

Code, data and the other project files referred to in `RESULT.md` are not included. The study is recorded in a private trials ledger together with the other tests by the same author.

## Limitations

- **Low power.** With 142 weeks the test could only reliably detect large effects: about 1.1% per week or more (1.1–1.7% depending on volatility, from the pre-registered power calculation). A FAIL does not show that momentum is exactly zero, only that there is no edge after costs at a size this test can see.
- **The planned secondary test was dropped before any data was downloaded.** It was a value-area (AMT) score on 5-minute data. It was never run, and it is not part of this result.
- **Simple cost model.** A flat 21 bps per side, with no modelling of spread, slippage or market impact. Results use the exchange's trade prices.
- **Narrow scope.** One exchange, one signal definition, one rebalance frequency, one period.

Not financial advice, and not a trading signal.
