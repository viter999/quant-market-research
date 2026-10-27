# Study 1 result: time-series trend on Binance alt perpetuals — FAIL

**In one line:** a fixed Donchian trend rule, traded long and short on the 30 most liquid Binance
USDT-M perpetuals with volatility-scaled sizing, lost money over 2022–2023 even at base cost and did
not beat simple baselines. The pre-registered verdict is **FAIL**.

Trials ledger #38. Verdict run verdict-20261027T155038Z-d779b9fe (2026-10-27), one execution.
Pre-registration PREREG.md sha256 6e4bd3c4…540a (tag prereg-v1.0); code commit 764bac5 (tag
code-freeze-v1). Full numbers: VERDICT_REPORT.md.

## Question

On Binance USDT-M crypto perpetuals, daily bars, does a fixed Donchian breakout ensemble, traded long
and short with equal-risk sizing from a volatility forecast, beat simple baselines after realistic
costs and funding?

## Design (written down and frozen before any verdict data was read)

1. Universe: each month, the 30 most liquid eligible crypto perpetuals (listed ≥ 120 days, 30-day median volume ≥ $10M), point-in-time, delisted coins included.
2. Signal: the mean of three breakout votes (20, 50 and 100-day channels, exits at half length), long and short; at most 10 positions.
3. Sizing: 0.5% of equity per forecast daily range (ATR10/ATR100 blend), 2x gross cap, 20% turnover brake, Binance lot and minimum-order rules, $500 start.
4. Costs: 10 bps per side base, judged at 2x (20 bps per side); signal on the daily close, fill at the next open; actual Binance funding.
5. Data: Binance public archive. Mechanics built on 2020–21 with no outcome statistic; verdict on 2022-01-01 → 2023-12-31, one look; 2024 onward is a holdout opened only after a PASS.
6. Pass rule: all of P0–P5. Baselines: B1 BTC buy-and-hold, B2 the same rule on BTC alone, B3 always long the same 30 coins with the same sizing. The rule was checked on 200 fake markets before the freeze (CALIBRATION.md).

## Verdict (primary arm: long/short, ATR sizing, 2x cost)

| gate | rule | value | result |
|---|---|---|---|
| P0 | no liquidation event | 0 | PASS |
| P1 | net total return > 0 | −18.53% | FAIL |
| P2 | net Sharpe ≥ B1 + 0.25 | −0.269 vs 0.084 | FAIL |
| P3 | net Sharpe ≥ B2 + 0.25 | −0.269 vs 0.545 | FAIL |
| P4 | net Sharpe ≥ B3 + 0.25 | −0.269 vs −0.142 | FAIL |
| P5 | calendar-2022 net return ≥ −15% | −6.99% | PASS |

## First: the result at base cost (1x)

At 10 bps per side the primary arm still lost: **net return −14.69%, Sharpe −0.18**, max drawdown
49.4%, 445 trades. At 2x it lost 18.53% and at 5x 29.14%. This is **no edge**, not an edge eaten by
costs.

## Sensitivities (primary arm at 2x, reported only)

- $10,000 start: −18.59%, Sharpe −0.20, 491 trades, 6 orders skipped under the minimum.
- $100 start: −14.04%, Sharpe −0.38, 134 trades, 7,074 orders skipped under the $5 minimum.
- Delisting slippage penalty at 0x and 3x the forecast range: −18.53% and −18.58%.

## Diagnostics (reported only, never deciding)

- **R1, time-shifted null:** the real strategy beat a time-shifted replay of its own positions in
  49% of 200 paired comparisons; median paired Sharpe difference −0.02. The timing did no better
  than the same positions moved in time.
- **R2, two largest trades removed:** they were a LUNA short (May 2022, +$39.86) and a SOL long
  (Oct–Dec 2023, +$34.67). Without them: −33.44%, Sharpe −0.62.
- **Year split:** 2022 −6.99% (Sharpe −0.13); 2023 −12.41% (Sharpe −0.44). The baselines' Sharpes
  were lower in 2022 (B1 −1.39, B2 −1.17, B3 −1.11) and far higher in 2023 (2.13, 1.14, 1.18).
- **Calm vs wild days** (BTC 30-day volatility terciles, cut points fixed on 2020–21): calm 504 days
  −17.33%; mid 116 days +3.02%; wild 110 days −4.35%.
- Net Sharpe 95% block-bootstrap interval: [−1.84, 1.21].

## What was disclosed

- **Added after the freeze (decision 8):** `scripts/verdict_run.py`, which runs the frozen pipeline
  once and commits VERDICT.json, and `FREEZE.json`, a machine-readable copy of HASHES.txt. Neither
  holds trading logic. Every frozen file was checked against its code-freeze version before any
  verdict date was read.
- **Contract filters (decision 9):** lot steps and minimum orders come from a 2021-12-31 snapshot,
  so coins listed later, or missing from it, take the $5 default and no lot step: 120 and 26 of the
  260 slice coins; 17 and 7 of the 94 coins that were ever tradeable.
- **Delistings:** 21 events; 17 exited at the announcement-day close and 4 (AKRO, COCOS, FTT, HNT)
  at the last available close, because their notice was missing or ambiguous.
- **Standing disclosures:** the sizing model was chosen on overlapping data; the verdict years were
  chosen knowing their regimes; the 10 bps base cost is an assumption; next-open fills are
  optimistic; the null is a weight-path replay. The hourly-fill sensitivity was not computed (no
  hourly data).

**Consequence (PREREG §8, §12):** the "time-series trend on daily bars" family is closed until
2027-10-27, including a BTC-only version; no lookback, exit, size, cost or universe is re-tuned; there is no second look; the 2024+ holdout stays
locked for good.

## What this does NOT say

This is one market (Binance USDT-M perpetuals, top 30 by volume), one two-year period (2022–23, a
bear year then a recovery) and one fixed rule family (Donchian 20/50/100 with volatility sizing). It
does not show that trend following fails in other markets, other periods or with other rules, and
it tests no rule that was not frozen in advance. B2, the same rule on BTC alone, was positive
(+2.96%, Sharpe 0.54 at 2x), but it is a reported baseline, not a finding: it was not the
hypothesis, carries no significance test, and would need its own pre-registration and fresh data
before anyone treated it as an edge, and, under the family closure, not before 2027-10-27.
