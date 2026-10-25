# Forecasting next-week daily true range: a pre-registered comparison of ATR10, ATR100 and a 50/50 blend

**Result: confirmed under the pre-registered rule.** C had the lowest mean QLIKE in both samples. It passed the
registered discovery comparisons against both alternatives and the held-out confirmation test against the
discovery runner-up. (C is the 50/50 blend of ATR10 and ATR100; the held-out test gave z 6.47 against a bar of
2.33.) The held-out sample, 2020–2022, is earlier in time than the discovery sample; it is not a forward test.
This is a forecast of how large daily moves will be, not of which way they go.

## What was tested

- **Question:** for Binance USDT-M crypto perpetuals, which of three fixed forecasts best predicts the **average
  daily true range over the next 7 days**, so that positions can be sized to equal risk?
  - **A:** ATR10, the simple mean of the last 10 daily true ranges, each divided by the previous close.
  - **B:** ATR100, the same over 100 days.
  - **C:** 0.5 × A + 0.5 × B. The weights were fixed in advance, not fitted.
- **Target:** the mean of the daily true range (as a fraction of the previous close) over the 7 calendar days t
  to t+6. All 7 days must be valid trading days. Forecasts use data up to day t−1 only.
- **Universe:** crypto contracts only (index, gold and stablecoin contracts excluded), delisted coins included. A
  coin needs at least 120 days of listing, 100 valid days and $10M average daily volume over the last 30 days.
- **No look-ahead in the filters:** all three filters use only data up to day t−1 (prereg §5, checked in the
  frozen code). The 30-day volume and its trading-day count end at t−1, the listing age runs from the current
  listing-clock start to t−1, and the 100 valid days are counted before t. The only conditions that look at day t
  or later belong to the target: days t to t+6 must all be valid.
- **Reused or relisted symbols:** each symbol is its own series. More than 7 consecutive days without trading
  restarts the listing clock; lookbacks then use only days after the restart, and the coin must again reach 120
  days and 100 valid days (prereg §4.3 rule 3 and §5). The held-out audit found 7 such restarts (zero-volume runs
  longer than 7 days) and checked every one-day price jump above 3× or below 1/3 by date, volume and gap (5 jumps,
  none next to a zero-volume day or across a calendar gap). The held-out exclusion script flags a symbol as a
  reused ticker only when its contract today is a non-crypto type listed after the data end; none was flagged.
  A ticker reused for a different token after a pause of 7 days or less would not restart the clock. No separate
  audit of ticker reuse is recorded. For the discovery data an earlier study's audit was reused as-is; whether it
  checked ticker reuse is not recorded in this study's files.
- **Pre-registered:** `PREREG_v0.1.md`, frozen by sha256 `b97646e9…5dbde5ff` (full hash in `HASHES.txt`) before
  any forecast or loss was computed. The published copy is redacted; see the reading notes below.
  - **Freeze date: 2026-10-22.** No separate freeze log was recorded. The hash file is timestamped 15:04 UTC that
    day, and the first run report that cites the hash (the discovery data check) ran at 15:20 UTC. The time of
    the operator's approval in chat is not recorded in the study files.
  - A hash proves the file has not changed since it was hashed. It does not prove when it was hashed.
- **Losses**, with RV the realized target and F the forecast:
  - **QLIKE** (primary): L = RV/F − ln(RV/F) − 1. It is zero only when F = RV.
  - **MALE** (secondary, reported only): L = |ln RV − ln F|.
  - **Weighting:** on each date the loss is averaged over the eligible coins with equal weight, then those daily
    values are averaged with equal weight per date. Large and small coins count the same.
  - **Zero or invalid values:** an observation whose RV or any forecast is not above zero (missing values
    included) is dropped and counted (prereg §6). None occurred: 0 in each sample.
- **Test:** Diebold–Mariano on the loss differences, using the same per-date averages, with a Newey–West standard
  error at lag 6, because the 7-day targets overlap.
- **Two stages, one look each:**
  1. **Discovery,** 2023-03-01 to 2026-09-23: 1,303 forecast dates, 668 symbols, median 173 coins per date (min
     108, max 256). A winner needs the lowest mean QLIKE and z ≥ 2.5 (one-sided) against each of the other two.
  2. **Held-out historical sample,** 2020-05-01 to 2022-08-25: 847 forecast dates, 154 symbols, median 85 coins
     per date (min 3, max 132). It was downloaded only after the discovery verdict. **CONFIRMED** needs the winner
     to beat the discovery runner-up with z ≥ 2.33 (one-sided) and to have the lowest mean QLIKE of the three.
- **Default fixed in advance:** if the data could not separate the three, the prereg already named C as the
  forecast to use. The test was whether the data could pick one.
- **Sensitivities:** six pre-declared variations, reported only; none can change a verdict.

## Deviations from the prereg

All four were decided by the operator and logged before the result they could affect was read. None changed a
loss, a test, a bar or a candidate. Full text in `DEVIATIONS.md`.

- **DEV-1:** a memory guard was put around the analysis run. It pauses the run if free memory drops below 3 GB
  and calls the frozen analysis functions unchanged. Logged and hashed before the discovery look.
- **DEV-2:** the scripts that download and audit the held-out data, and build its exclusion list, were written
  after the code freeze, adapted from an earlier study's tools. Logged after the discovery look and before any
  held-out data was downloaded.
- **DEV-3:** one more index contract, DOTECOUSDT, was excluded from the held-out data under the same rule as
  similar index contracts (one configuration line changed). It has only 31 days of data and could never pass the
  120-day rule, so no number moved. The same ruling kept the 2022 archive gaps as the frozen rules treat them
  (see below).
- **DEV-4:** the universe filter was written down: USDT-margined perpetuals by name (symbols ending in `USDT`
  with no `_`, 900 of 1,056 archive folders). It is the filter the discovery data already used; the prereg named
  the universe but did not spell the filter out. No file or code changed.

**The 2022 archive gaps.** The held-out data audit found 100 calendar gaps on 50 symbols, 247 symbol-days in all.
97 of them are two holes in Binance's public archive: 48 symbols have no daily row for 2022-02-26 to 02-28 and 49
have none for 2022-04-01 to 04-02. The other 3 are single-symbol gaps of 1 to 3 days. These are missing data;
whether those coins traded on those days is not recorded. Under the frozen rules a missing day counts as a
non-trading day, and because no gap is longer than 7 days the listing clock does not restart. Effects:
- **Target window:** it is always the 7 calendar days t to t+6 and never stretches past them. Any forecast date
  whose window contains a missing day is dropped. How many drops this caused is not recorded separately; they are
  inside the 595 incomplete-window drops.
- **Forecasts:** ATR10 and ATR100 use the last 10 or 100 valid days, so a lookback that crosses a gap reaches back
  a few more calendar days. The first day after a gap measures its true range against the last close before the
  gap. The effect of these gaps on forecast inputs (ATR lookbacks) was not separately quantified.
- **Volume filter:** missing days count as $0 and not as trading days in the 30-day window (at least 25 of 30
  needed).

## Result

| candidate | discovery mean QLIKE | held-out mean QLIKE |
|---|---|---|
| A (ATR10) | 0.0890 | 0.0755 |
| B (ATR100) | 0.0888 | 0.0847 |
| C (50/50 blend) | **0.0730** | **0.0663** |

| test | z | bar | outcome |
|---|---|---|---|
| Discovery: C vs A | 6.49 | 2.5 | pass |
| Discovery: C vs B | 7.87 | 2.5 | pass |
| Held-out (confirmatory): C vs B, the discovery runner-up | 6.47 | 2.33 | pass |
| Held-out (exploratory): C vs A | 3.43 | none | not part of the confirmatory test |

- **Discovery verdict: WINNER C**, runner-up B. A and B were not separable (z −0.06).
- **Held-out verdict: CONFIRMED.** C also had the lowest mean QLIKE. C vs A is exploratory: the prereg's one
  confirmatory test is C against the discovery runner-up.
- **Bias, aggregate only:** the average ratio of realized range to forecast for C was 0.997 in discovery and 1.004
  in the held-out sample. This is one aggregate number per sample. It is not a check of calibration for
  individual coins, coin groups or market regimes, which was not reported.
- MALE also put C lowest in both samples. In discovery it ordered A and B the other way round from QLIKE.
- C had the lowest QLIKE in every sensitivity except S6 (see Limitations).

Per-candidate detail (bias, Mincer–Zarnowitz, rank correlation), counts and all sensitivities are in the two
reports.

## Practical rule

Expected average daily true range over the next week, as a fraction of price:

**forecast = 0.5 × ATR10% + 0.5 × ATR100%**

where ATR10% and ATR100% are the simple means of the last 10 and 100 daily true ranges, each day's range divided
by the close of the day before it. For equal-risk sizing, this is the number to scale positions by. Whether sizing
this way improves any trading result was not tested.

## Files

| File | What it is |
|---|---|
| `PREREG_v0.1.md` | The preregistration, redacted copy (see below) |
| `DEVIATIONS.md` | DEV-1 to DEV-4, redacted copy (see below) |
| `REPORT_discovery.md` | The discovery one-look report, byte-identical to the original |
| `REPORT_confirmation.md` | The held-out (confirmation) one-look report, byte-identical to the original |
| `HASHES.txt` | SHA-256 of the four files above, plus the hashes of the two private originals |

Reading notes:
- **Redacted copies.** `PREREG_v0.1.md` and `DEVIATIONS.md` have local folder paths and mentions of the machine
  replaced by `[redacted: local path]` or `[redacted: machine detail]`. Nothing else changed, so their hashes
  differ from the private originals. `HASHES.txt` lists both, including the frozen prereg hash `b97646e9…`.
- The preregistration's header still says "DRAFT, not frozen, not hashed". It was frozen by hash exactly as
  written, so that line was left as it is.
- The prereg and reports call the held-out sample the "confirmation" sample.
- The prereg refers to earlier breakout and carry studies and a trials ledger (#34). They are the author's own
  records and are not part of this repository.

**Not included:** the code, the data, the results JSON files and the data audits. All inputs were public
Binance daily klines from data.binance.vision.

## Limitations

- **Size, not direction.** The forecasts predict how large moves will be, not which way they go.
- **Not tested inside a trading strategy.** Nothing here says that sizing by this forecast earns more, loses
  less or improves any risk-adjusted return. That would be its own pre-registered study.
- **One exchange, one setup.** Binance USDT-M crypto perpetuals with at least $10M daily volume, daily bars,
  7-day horizon. No claim about other venues, spot, thinner coins, other horizons or other assets.
- **Sample periods.** Discovery (2023-03 to 2026-09) was not blind: the same period had been used in earlier
  studies. The held-out sample (2020-05 to 2022-08) was not used before, but it is earlier in time, thinner
  (median 85 coins per date, minimum 3) and covers one bull and one bear market. A result that held in two past
  periods may not hold in the next.
- **Normalisation matters (S6).** The two ways of putting the range on a price scale:

  | | primary (per-day %, then average) | S6 (average price range, then divide by one close) |
  |---|---|---|
  | ATR_N | mean over the last N valid days of TR_d / C_prev(d) | (mean over the last N valid days of TR_d) / C_prev(t) |
  | target | mean over t … t+6 of TR_d / C_prev(d) | (mean over t … t+6 of TR_d) / C_prev(t) |

  They can differ a lot when the price has moved over the lookback window, which over 100 days is common in
  crypto: old price-unit ranges are then out of scale with today's price. The prereg chose per-day normalisation
  for this reason. Under S6, A (ATR10) has the lowest QLIKE in both samples (z of C vs A −3.93 in discovery,
  −4.14 held-out). The result above holds only for the per-day-normalised range.
- **Serial dependence.** Newey–West at lag 6 matches the 6-day overlap of the 7-day targets. Volatility clusters
  (the prereg's power section assumes this), so dependence beyond 6 days could make the standard error too small
  and z somewhat too large. The pre-declared checks point the same way as the main result but are not a
  correction: at lag 13 (S1), C vs B is 6.50 in discovery and 5.42 held-out; with non-overlapping Monday-only
  targets (S2), 4.93 and 4.76.
- **Range proxy.** The target is the mean daily true range, not squared returns or intraday variance. Moves
  within a day and tail sizes are not measured.
- **Fixed weights.** C is 0.5/0.5 by construction. Other weights or a fitted model were not tried.
- **Delisting.** Coin-dates whose 7-day window runs past the coin's last trading day are dropped (332 coin-dates
  in discovery, 66 held-out; counted per coin and date, not per date), so the days just before a delisting are
  under-represented.
- **Not reproducible from this folder alone.** The code and data are not included. The inputs are public Binance
  files; the code is not published.

Not financial advice, and not a trading signal.
