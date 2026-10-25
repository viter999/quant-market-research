# Hyperliquid vs Binance funding gap: a pre-registered, one-look test

**Result: FAIL.** Pairs opened on a large funding gap lost 63.8 bps per pair on average after costs. They did
collect funding (+19.8 bps per pair), but far less than the 84 bps cost of the four fills.

## What was tested

- **Question:** when the realized 24h funding for the same coin differs a lot between Hyperliquid and Binance
  USDT-M perpetuals, does a delta-neutral pair (long the lower-funding venue, short the higher) earn a positive net
  PnL after costs?
- **Pre-registered:** `PREREG_v0.2.md`, frozen 2026-10-25 18:02 UTC, sha256 `f6f70e38…f7e62b7` (full hash in
  `HASHES.txt`). No rule changed after the freeze.
- **Sample:** 2024-07-13 to 2026-09-30 UTC. The first possible entry is 2024-08-12, because the 30-day look-back
  also starts on 2024-07-13.
- **Universe:** coins listed on both venues, including later-delisted ones.
  - Mapped by underlying asset, and accepted only if the daily closes of the two venues agree.
  - At least $5M daily volume on each venue over the previous 30 days.
  - Coin-days before the token had a real spot market are excluded.
  - 118 coins were eligible at some point.
- **Signal:** every hour, each venue's realized funding over the last 24h is summed. Enter when the gap is at least
  25 bps at two consecutive hourly checks, with the same venue higher both times.
- **Fills:** the open of the first 4h bar strictly after the decision, on both venues.
- **Exit:** the gap falls below 10 bps, the gap changes sign, or 7 days pass. One pair per coin at a time; 24h
  cooldown after an exit.
- **Net PnL per pair:** funding paid and received + price change of both legs − 84 bps costs (4 leg fills), in bps
  of one-leg notional.
- **Fake-data check first:** each coin's hourly gap series was shuffled in time 20 times (fixed seeds) and the full
  pipeline run on each. The real data would be looked at only if no shuffle reached z ≥ 3.0.
- **Test:** mean net PnL per pair > 0, one-sided, with a weekly block bootstrap (10,000 draws, fixed seed).
  - **PASS:** z ≥ 3.0. The bar is high because Binance funding for 2023–2026 had already been seen in an earlier
    study.
  - **NOT DEMONSTRATED:** mean > 0 but z < 3.0.
  - **FAIL:** mean ≤ 0.
- **One look:** the analysis ran once. The thresholds (25 / 10 bps, 7 days, 24h cooldown, $5M, 84 bps, 4h fills)
  were not re-tuned afterwards.

## Result

**Fake-data check: PASS.** None of the 20 shuffles reached z ≥ 3.0 (highest z −12.4). Shuffled pairs net about
−84 bps, i.e. just the costs, as expected.

| | pairs | weeks | mean net bps | z | 95% CI |
|---|---|---|---|---|---|
| All pairs | 165 | 59 | −63.8 | −11.0 | [−76.4, −53.7] |
| Without the 2 best pairs | 163 | 59 | −66.0 | −12.2 | [−78.1, −56.9] |

- 165 pairs on 64 coins.
- Mean per pair: funding +19.8 bps, price +0.4 bps, costs −84 bps. Median net −67.0 bps.
- 7% of pairs ended above zero.
- Each year and both directions (Hyperliquid higher, Binance higher) were negative on average. These splits are
  descriptive and were not tested; the tables are in `RESULTS_v1.0.md`.

## Why it failed

The gap does not last. Almost every pair was closed by the rule because the gap fell below 10 bps or flipped sign,
and pairs were held 31 hours on average (median 24 hours in the count check run before the look). In that time a
pair collected about 20 bps of funding, roughly a quarter of the 84 bps it costs to open and close.

## Files

| File | What it is |
|---|---|
| `PREREG_v0.2.md` | The preregistration, byte-identical to the frozen original |
| `RESULTS_v1.0.md` | The one-look results, byte-identical to the original |
| `HASHES.txt` | SHA-256 of the two files above |

Reading notes:
- The preregistration's header still says "DRAFT, not frozen" and section 5 says "NOT YET COMPUTED". It was
  frozen by hash exactly as written, so those lines were left as they are. The freeze record is the hash and
  timestamp in `HASHES.txt`.
- Both files mention a trials ledger (#37). It is the author's list of every test run, kept so the number of
  attempts is on record. It is not part of this repository.
- RESULTS_v1.0.md line 4 says the scripts were not hashed; they were hashed afterwards, unchanged since the run
  (recorded in the private study record).

**Not included:** the code and the data. All inputs were public: Hyperliquid's public `info` API and Binance's
data.binance.vision files.

## Limitations

- **Trade price, not mark price:** exchanges charge funding on mark price. The study used 4h trade-price bar opens
  instead, both for the fills and for the funding cash flows.
- **Flat costs:** a fixed 84 bps per pair. Real fees, spread and slippage were not modelled. How the result changes
  with lower costs was not pre-registered and was not run.
- **Tracked period only:** 2024-07-13 to 2026-09-30, the 4h history Hyperliquid's public API served at download
  time. One rule, one set of thresholds, two venues; the result says nothing about other periods, venues or rules.

Not financial advice, and not a trading signal.
