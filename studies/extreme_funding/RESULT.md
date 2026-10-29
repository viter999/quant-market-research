# RESULT — Extreme-funding carry, hedged (idea #5): **NOT EVALUABLE (power)**

The study stopped at the pre-registered power check (PREREG §6), before any price, return or P&L was computed on any data. VERDICT was not run, and HOLDOUT was never read.

## What was checked
The plan was to open long spot / short perp (equal base quantity) right after a settlement with extreme positive funding (≥ 0.0125 % per hour) and rising open interest, and hold until funding normalises or 7 days pass. Before any outcome, the DEV period (2024-01-01 → 2025-08-24) was used only to count how many trades the rules would produce, then projected to VERDICT (× 200/602). The test needs at least 60 trades on 15 symbols and 30 entry days.

## Result of the count
| | DEV trades | symbols | entry days | Projected VERDICT trades / symbols / days |
|---|---|---|---|---|
| v0.2 (top-80 universe, cap 5) | 37 | 24 | 30 | 12.3 / 8.0 / 10.0 |
| v0.3 amendment (perp 24 h volume ≥ $20M, cap 10) | 58 | 38 | 41 | **19.3 / 12.6 / 13.6** |
| Required | | | | 60 / 15 / 30 |

Both versions fail on all three counts. The v0.3 amendment (29 Oct 2026, decided by Shawn before any outcome) widened the universe and the cap; it raised the count but not nearly enough.

## Why there are so few trades (v0.3, DEV)
Of 10,432 extreme-funding settlements, almost all are filtered out by the liquidity and hedging requirements:
| Step | Dropped | Remaining |
|---|---|---|
| Candidates (funding ≥ threshold, interval unchanged) | — | 10,432 |
| Entry too close to the segment end | 182 | 10,250 |
| Excluded symbol (frozen list) | 1,054 | 9,196 |
| Perp 24 h volume < $20M | 3,001 | 6,195 |
| No Binance spot pair | 3,518 | 2,677 |
| Spot liquidity (no bars / 24 h < $5M / median 1-min < $50k) | 9 / 55 / 2,248 | 365 |
| Open interest missing / rise < 5 % | 9 / 201 | 155 |
| Symbol already held / cap of 10 | 70 / 27 | **58 trades** |

In plain terms: extreme funding happens mostly on small or new perps that either have no Binance spot market to hedge with, or whose spot market is too thin. The trades that remain are also concentrated in time — 37 of the 58 entered in March 2024 — so even the 58 are closer to a handful of episodes than to 58 independent tests.

## Conclusion
With these rules the idea cannot be tested with enough trades on this data, so no verdict is possible: **NOT EVALUABLE (power)**. No P&L was ever computed, so nothing is known about whether the trade would have paid. Loosening the rules further (for example accepting thin spot hedges) would test a different, riskier strategy and would need its own pre-registration.

## Reproducibility
- PREREG v0.2 `8f1140e`; amendment v0.3 `30d5978`. Code and counts on branch `study/extreme-funding`; DEV counts in `results/EF1_FEASIBILITY.json` (v0.2) and `results/EF1_V03_FEASIBILITY.json` (v0.3); ambiguities and details in `results/EF1_REPORT.md`.
- Funding scan: all 669 USDT-M perps, 2023-12 → 2026-02 archive monthly files (1,526,554 settlements). Frozen crash-absorption EXCLUSIONS v1.0 and SPLITS; listing and download guard capped at 2026-03-13.
