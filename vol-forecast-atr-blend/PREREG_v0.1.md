# PREREG v0.1 — Which ATR forecast best predicts next-7-day volatility? (Binance USDT-M perps, for equal-risk sizing)

**Status: DRAFT, not frozen, not hashed.** Written 2026-10-22. No price, range or volume value has
been loaded or computed for this study. No data has been downloaded. The only numbers in this file
are assumptions (power, §10), operator-approved parameters carried over from the breakout study
(§4–§5), and bars proposed for the operator's OK (§8, §13). Freezing needs the operator's OK in chat
on this exact text.

**Where it runs.** On the operator's [redacted: machine detail], in `[redacted: local path]`. Discovery data is read
**read-only** from `[redacted: local path]`. Confirmation data is a fresh download to
`[redacted: local path]`. Nothing is read from or written to [redacted: local path]. Heavy work runs at
Below normal priority and pauses if free RAM drops under 3 GB.

---

## 1. Question

For Binance USDT-M crypto perpetuals, which of three fixed forecasts, all computable at the start of
day t from data through day t−1, best predicts the realized volatility of days t … t+6, so that
positions can be sized to equal risk?

This is a **forecasting study of a risk rule**. It computes no trade, no return and no P&L.

## 2. Candidates (fixed in advance; no others)

| label | forecast F_t |
|---|---|
| **A** | ATR_10(t−1), normalised (§5) |
| **B** | ATR_100(t−1), normalised |
| **C** | 0.5 × A + 0.5 × B |

The blend weights are fixed at 0.5 / 0.5. They are not fitted and no other weight is tried.

## 3. Hypotheses and what counts as a winner

Losses are compared pairwise with Diebold–Mariano (DM) statistics (§7). There are three pairs:
C vs A, C vs B, A vs B.

- **H1 (primary, decides the discovery verdict).** One candidate has the lowest mean QLIKE on the
  discovery sample **and** beats each of the other two with DM z ≥ **2.5** (one-sided). That
  candidate is the **WINNER**. If no candidate does, the verdict is **NO WINNER** (the three are not
  separable at this bar).
- **H2 (confirmation, one test, fresh data).** On the 2020–2022 sample (§4), the WINNER beats the
  discovery **runner-up** (second-lowest discovery QLIKE, fixed before the confirmation data is
  opened) with DM z ≥ **2.33** (one-sided), **and** has the lowest mean QLIKE of the three on that
  sample (point estimate, no test). Then the result is **CONFIRMED**; otherwise **NOT CONFIRMED**.
- **Secondary loss (no verdict).** Mean absolute log error (MALE, §6) is reported for every
  comparison. If MALE ranks the candidates differently from QLIKE, that is stated; the verdict stays
  with QLIKE.

**Why these bars and not the ledger's 3.6.** The ledger's z ≥ 3.6 is for a return claim chosen
after ≥ 326 looks. This study makes no return claim and selects nothing after looking: the three
candidates, the loss, the test and the bar are fixed here, and the pick is checked once on data
nobody has opened. Three pairwise comparisons at family-wise 0.05 need z ≥ 2.13 (Bonferroni 0.05/3,
one-sided); 2.5 (p ≈ 0.006) leaves margin for the secondary loss and the sensitivities. The
confirmation is a single pre-registered test at α = 0.01 one-sided (z ≥ 2.33). Both bars are
proposed, see §13 D3.

## 4. Data

### 4.1 Discovery (reused, read-only)

- **Source:** `[redacted: local path]` (`DATA_ROOT_DISC`): Binance USDT-M daily klines from
  data.binance.vision, monthly zip files per symbol, 2022-09-01 to 2026-09-29 (UTC), 888 symbols on
  disk, delisted ones included. Funding files are present but **not used** here.
- **Integrity:** before anything else, every kline file read is checked against the sha256 recorded in
  `[redacted: local path]`. A mismatch stops the study. Nothing under `DATA_ROOT_DISC` is
  written, moved or renamed.
- **Exclusions:** `[redacted: local path]` (sha256
  `e98b2eb3393e280f94495e4206e1c877dadb80403d1053c91ce40e216a9ade9a`), i.e. **crypto only** (breakout
  DEV-1: every symbol whose Binance contract metadata is not `COIN`, plus PAXG, XAUT, USDC, BLUEBIRD,
  FOOTBALL). 668 symbols remain. The kept-with-note list (`exclusions_v2_kept_notes.txt`) applies as it
  stands, including MDTUSDT kept.
- **What has already been seen on this data:** the breakout study's P00 (dates), P00b (data audit:
  price ratios, gaps, zero-volume runs) and P01 (eligible-breakout counts per week). No volatility
  forecast, no forecast loss and no return has been computed on it in this folder. The carry study
  (ledger #32) computed 7-day returns over the same calendar period on its own copy of the data.
  Discovery is therefore **not blind to the period**, which is why the pick is confirmed on §4.2.
- **Fields used:** daily open, high, low, close, quote volume (USDT). Open is read only for the
  "valid day" check and the first-day true range.

### 4.2 Confirmation (new download, after freezing)

- **Source:** data.binance.vision, USDT-M futures daily klines (`futures/um/monthly/klines/<SYM>/1d`),
  **2020-01-01 to 2022-08-31** (UTC), every symbol the archive lists for that range, delisted ones
  included. Funding is not downloaded.
- **Saved to** `[redacted: local path]`. Never [redacted: local path].
- **Downloaded only after this file is frozen** (§11). No kline from this range is opened, by eye or
  by code, before its P00 manifest is written. The operator confirms in chat that no study on this
  [redacted: machine detail] has loaded 2020-01 … 2022-08 USDT-M klines before (§13 D4).
- **No overlap with discovery:** the confirmation data ends 2022-08-31; the discovery files start
  2022-09-01 and the first discovery forecast date is 2023-03-01.
- **Exclusions:** a new file `exclusions_confirm.txt`, built by the **same rule** as breakout DEV-1
  (crypto only, from symbol names plus `fapi/v1/exchangeInfo` metadata saved as
  `metadata/exchangeInfo_<date>.json`), written and hashed **before any price in the range is read**.
  Delisted symbols with no metadata are kept if crypto by name, and listed. Any judgement call is
  shown to the operator before P00c.

### 4.3 Cleaning (the breakout study's rules, unchanged)

1. A zero-volume day is **no trading**: its kline is treated as missing. It is not a trading day in any
   count and its prices are never used.
2. (Funding rule: not applicable, no funding used.)
3. More than 7 consecutive days without trading **restarts the listing clock**. Lookbacks use only days
   since the current clock start.
4. **30-day volume** = calendar average of daily quote volume over the 30 days ending t−1, zero-volume
   days as $0, and at least 25 trading days out of those 30.

"Valid day" = a day with a kline, volume > 0, quote volume > 0 and all four prices present (the
breakout code-freeze reading, IMPL 9). The cleaning code is **copied** from the frozen
`[redacted: local path]` into this study's `scripts/` with the source file's sha256
recorded, so the rules are byte-identical. The frozen file itself is not edited.

## 5. Fixed definitions

| item | definition |
|---|---|
| Day | UTC calendar day, as in the Binance daily kline |
| C_prev(d) | close of the previous **valid** day in the same clock segment |
| True range TR_d | max(H_d − L_d, \|H_d − C_prev\|, \|L_d − C_prev\|). On the **first valid day of a clock segment**, TR_d = H_d − L_d (breakout IMPL 1) |
| **Normalised true range NTR_d** | TR_d / C_prev(d) (on the first valid day of a segment, TR_d / O_d). A fraction of price, dimensionless |
| ATR_N(t−1), normalised | **simple** mean of NTR over the last N valid days ending on t−1 (if t−1 is not valid, the last N valid days before t in the same clock segment; breakout IMPL 2). Not Wilder smoothing |
| Forecast A, B, C | as in §2 |
| **Target RV_t** | mean of NTR_d over the 7 calendar days d = t … t+6, which must **all be valid days** in the same clock segment. If any is not, the (coin, t) observation is dropped and counted (§9) |
| Forecast date t | the forecast is usable at 00:00 UTC of day t; everything in A, B, C and the eligibility test uses data through t−1 |

**Why NTR and not ATR in price units divided by one close.** A 100-day mean of price-unit ranges
divided by today's close is distorted whenever price has moved a lot over the window, which in
crypto is often. That would handicap B for a reason unrelated to forecasting. Per-day normalisation
keeps A and B on the same footing. The price-unit version is reported as sensitivity S6. (Operator
choice, §13 D1.)

**Eligibility of a coin on forecast date t** (all measured through t−1, as in the breakout study):

- listing clock (rule 3) ≥ **120 days**, and at least **100 valid days** since the clock start (so
  ATR_100 exists on post-restart data only);
- 30-day volume (rule 4) ≥ **$10,000,000 per day**;
- not excluded (§4).

**Delisted coins.** Included. A coin's series ends at its last valid day. Forecast dates whose target
window t … t+6 runs past that day are dropped by the all-7-valid rule and counted under
`dropped_incomplete_target`. Nothing about delisting is known to the forecast at time t; this is as
it would be live. A coin that stops and restarts is handled by the clock restart (rule 3) and must
re-earn 120 days / 100 valid days. The number and share of drops that end at a coin's last valid day
are reported separately, because volatility before delisting is probably not typical and the drop
rule removes part of it from the sample (a limitation, §12).

**Forecast windows.**

| sample | forecast dates t (inclusive, UTC) | why |
|---|---|---|
| discovery | **2023-03-01 … 2026-09-23** | 120-day clock from 2022-11-01 at the latest; t+6 ≤ 2026-09-29 |
| confirmation | **2020-05-01 … 2022-08-25** | 120-day clock from the archive start 2020-01-01; t+6 ≤ 2022-08-31 |

For coins with history before 2020-01-01, the clock starts at their first archived kline (2020-01),
which is conservative.

## 6. Losses

For each eligible (coin i, date t) with RV > 0 and F > 0 (otherwise dropped and counted):

- **QLIKE** (primary): L(F, RV) = RV/F − ln(RV/F) − 1. Non-negative, zero only when F = RV. It is
  the standard loss for volatility forecasts because its minimiser is the conditional mean of the
  proxy whatever the noise in the proxy (Patton 2011), which is what equal-risk sizing needs.
- **MALE** (secondary): |ln RV − ln F|.

Both are computed on the same observations for all three candidates, so every comparison is on an
identical sample.

## 7. Test statistic (DM, clustered by date)

All coins share market moves, so losses on the same date are not independent, and 7-day targets on
neighbouring dates overlap. Both are handled by collapsing to one series per date:

1. For a pair (X, Y), the loss differential of observation (i, t) is d_{i,t} = L_Y − L_X. Positive
   favours X.
2. **Cluster by date:** d̄_t = equal-weighted mean of d_{i,t} over all eligible coins on date t.
3. **DM statistic:** z = mean_t(d̄_t) / SE, SE = Newey–West (Bartlett) standard error of the mean
   with **lag 6** (the target overlap is 6 days). T = number of forecast dates. No small-sample
   correction (T is in the hundreds).
4. Report for every pair: mean(d̄_t), SE, z, and the one-sided 95% lower bound of the mean.

**Also reported, no verdict:** per candidate, mean QLIKE and MALE; bias ratio mean(RV/F);
Mincer–Zarnowitz regression ln RV = a + b ln F (a, b with NW-lag-6 SE); and the mean over dates of
the cross-sectional Spearman correlation between F and RV (how well each candidate ranks coins by
risk within a day, which is what equal-risk sizing uses).

## 8. Verdicts

| verdict | rule |
|---|---|
| **NOT EVALUABLE (discovery)** | fewer than **800** discovery forecast dates with ≥ **30** eligible coins that have a complete target window (count-only gate P01, §10) |
| **WINNER X** | X has the lowest mean QLIKE and z ≥ 2.5 against each of the other two |
| **NO WINNER** | otherwise. The confirmation data is then **not opened**; it stays unseen for a future version |
| **NOT EVALUABLE (confirmation)** | fewer than **400** confirmation forecast dates with ≥ **10** eligible coins with a complete target window (counted at P01c, before any price is read) |
| **CONFIRMED** | z(WINNER vs runner-up) ≥ 2.33 on the confirmation sample and WINNER has the lowest confirmation mean QLIKE of the three |
| **NOT CONFIRMED** | otherwise |

One look per sample. No re-tuning after a look. No sensitivity, subgroup, coin or sub-period can
turn NO WINNER into a WINNER or NOT CONFIRMED into CONFIRMED.

**What the operator uses afterwards (policy, not a finding).** CONFIRMED → the WINNER is the
volatility forecast for equal-risk sizing. NO WINNER or NOT CONFIRMED → the pre-declared default is
**C** (the blend), on the grounds that when the data cannot separate them the hedge is the safe
choice. The default is set here, before any data, so it is not a data-driven pick (§13 D2).

## 9. Counts reported (every drop rule)

Per sample: symbols on disk, excluded, included; eligible (coin, date) observations; dropped for
incomplete target window (and how many of those end at a coin's last valid day); dropped for RV = 0
or F = 0; forecast dates used; eligible coins per date (min, median, max); observations per
candidate (identical by construction).

## 10. Power (assumptions, not data)

No data was used for this section.

**Model.** The DM test is on the daily series d̄_t. Let SD_d be the standard deviation of d̄_t and k
the Newey–West variance inflation from the 7-day overlap and volatility clustering (between 1 and 7
for a 6-lag overlap; assumed 3–7). SE ≈ SD_d × √(k / T). Minimum detectable mean differential at 80%
power: MDE = (z* + 0.84) × SE, z* = 2.5 (discovery) or 2.33 (confirmation).

**Assumed ranges.** Breakout P00 counted 150–651 listed symbols per day (median 313) before cleaning,
so 100–250 eligible coins per discovery date is assumed; the 2020–2022 archive is thinner (roughly
25 symbols in early 2020, 100–150 by 2021–22), so 20–150 per confirmation date. QLIKE levels: if the
log forecast error has SD 0.35–0.5, mean QLIKE is roughly 0.06–0.13. SD_d of the pairwise
differential: 0.05–0.20 (discovery), 0.10–0.30 (confirmation, fewer coins per date). T ≈ 1300
(discovery), ≈ 850 (confirmation).

| sample | T | SD_d | k | SE | MDE (QLIKE units) |
|---|---|---|---|---|---|
| discovery | 1300 | 0.05 | 5 | 0.0031 | 0.010 |
| discovery | 1300 | 0.10 | 5 | 0.0062 | 0.021 |
| discovery | 1300 | 0.10 | 7 | 0.0073 | 0.025 |
| discovery | 1300 | 0.20 | 5 | 0.0124 | 0.041 |
| discovery | 1300 | 0.20 | 7 | 0.0147 | 0.049 |
| confirmation | 850 | 0.10 | 5 | 0.0077 | 0.024 |
| confirmation | 850 | 0.20 | 5 | 0.0153 | 0.049 |
| confirmation | 850 | 0.20 | 7 | 0.0181 | 0.058 |
| confirmation | 850 | 0.30 | 7 | 0.0272 | 0.086 |

**Reading.** In the middle discovery case the test detects a QLIKE gap of about **0.02**, i.e. one
candidate's loss being roughly a sixth to a third lower than another's. Smaller gaps give NO WINNER.
The confirmation sample is about twice as blunt, so a WINNER with a modest discovery gap can come
back NOT CONFIRMED for power reasons alone; the report must say which case it is (the confirmation
point estimate and its bound are reported either way). No assumption is made about how far apart A
and B actually are.

**Count-only gates (P01, P01c).** Before any range is computed, the runner counts, per forecast date,
the eligible coins whose target window is complete (dates, volumes and valid-day flags only; no
high, low or close is read). The floors in §8 are applied. Counting is not an outcome look and adds
no ledger variant. There is no data-based power gate beyond the counts: the unknown here is SD_d,
and measuring it would be most of the look.

## 11. Run procedure

- **P00 (discovery manifest, no prices read):** list every discovery file used, with sha256, checked
  against `[redacted: local path]`; record `exclusions_v2.txt` and its hash, the copied
  cleaning code's hash and source hash, and Python and package versions. Coverage: klines from
  2022-11-01 at the latest through 2026-09-29. If anything mismatches, **stop and report**.
- **P00b (discovery audit): not repeated.** The breakout study's P00b report is reused as-is
  (read-only). Any cleaning change it would have implied was already settled there.
- **Code freeze:** analysis code written, unit-tested on synthetic data only, then hashed in
  `CODE_FREEZE.sha256` before P01. Choices the prereg leaves open are listed in `CODE_FREEZE.md` as
  `IMPL:` items, as in the breakout study.
- **Ledger:** the row in §13 is added to `TRIALS_LEDGER.md` **before** P02.
- **P01:** count-only gate on discovery (§8, §10).
- **P02 (discovery, one look):** writes `REPORT_discovery.md`, `results_discovery.json`, then
  `RESULTS.sha256`. The report heading reads the prereg version from this file's hash, not a
  hard-coded label. The WINNER and runner-up are written into `WINNER.txt` and hashed before P00c.
- **P00c (confirmation download, only if WINNER):** download §4.2 into `data_confirm`, Below normal
  priority, at most 4 workers, back off on HTTP 429/418, pause if free RAM < 3 GB. Build and hash
  `exclusions_confirm.txt` from names and metadata before any price is read. Manifest with sha256
  per file, first and last date per symbol from file names and date columns only. Coverage check:
  2020-01-01 … 2022-08-31; if shorter, stop and report. Do not move the window without a new prereg
  version.
- **P00d (confirmation data audit, no forecasts):** the breakout P00b checks (duplicates, gaps,
  zero-volume runs, one-day price jumps above 3× or below 1/3), each flagged jump checked by date,
  volume and gap only. A cleaning fix is a DEV-n shown to the operator before P01c. After P01c,
  cleaning can't change.
- **P01c:** count-only gate on confirmation (§8).
- **P03 (confirmation, one look):** `REPORT_confirmation.md`, `results_confirmation.json`, hashes
  appended to `RESULTS.sha256`.
- **Deviations:** any change after freezing is a DEV-n with the reason, logged before the result it
  affects is read. A bug found after a look is fixed as a DEV-n, both outputs are reported, and the
  verdict is the one the frozen rules give on the fixed code.
- **Machine:** Below normal priority throughout; pause and tell the operator if free RAM < 3 GB; no
  background task that only waits or polls; nothing on [redacted: local path].

**Sensitivities (pre-declared; reported, never verdict-changing).** Each changes one item from the
primary. Run on the discovery sample at P02 and, if P03 runs, on the confirmation sample too.

| # | change |
|---|---|
| S1 | Newey–West lag 13 instead of 6 |
| S2 | non-overlapping targets: forecast dates that are Mondays only, Newey–West lag 2 |
| S3 | target needs ≥ 5 of the 7 days valid (mean over the valid ones) instead of all 7 |
| S4 | liquidity floor $50,000,000 per day |
| S5 | first half of forecast dates vs second half, reported as two sets of numbers; counts as one sensitivity |
| S6 | forecasts in price units divided by one close: ATR_N(t−1) in price / C_{t−1}; target mean TR_d / C_{t−1} |

## 12. What this study does not claim

- **It is a risk rule, not a return signal.** A WINNER forecasts the size of moves, not their
  direction. Nothing here says that sizing positions by 1/F earns more, loses less, or improves any
  Sharpe ratio. Equal-risk sizing is the *use*; its effect on returns is untested and would be its
  own pre-registered study.
- **"Best" means lowest average QLIKE across coins and dates**, with every date weighted equally and
  every coin within a date weighted equally. It does not mean best for every coin, every regime, or
  the largest coins in particular.
- **The target is the mean daily true range**, a range-based proxy, not squared returns or intraday
  variance. A forecast that wins on this proxy is a forecast of expected daily range. Intraday paths,
  liquidation cascades and tail sizes within a day are not measured.
- **Daily bars, 7-day horizon, Binance USDT-M crypto perps with ≥ $10M/day volume.** No claim about
  other horizons, venues, spot, thin coins or TradFi contracts.
- **Fixed blend weights.** C is 0.5/0.5 by construction. The study does not say whether another
  weight, or a model fitted to the data, would do better; it was not asked.
- **Regime dependence.** 2020–2022 (few coins, one bull and one bear) differs from 2023–2026. A
  CONFIRMED result says the pick held in two periods; it does not say it will hold in the next.
- **Delisting.** Forecast dates whose 7-day window runs into a coin's last day are dropped, so the
  days just before delisting are under-represented. The count is reported; it is a limitation, not
  corrected.
- **Discovery is not blind to the period** (§4.1). Only the confirmation is.
- **NO WINNER is not "they are equal".** It means the data could not separate them at this bar and
  this power (§10).

## 13. Trials-ledger entry plan and open decisions for the operator

### 13.1 How the ledger should count this study

This is a forecasting study. It computes no return outcome and selects no trading strategy, so its
looks are not alpha variants in the sense the ledger's ≥ 326 total and z ≥ 3.6 bar were built for.
Proposed handling:

1. **One row, #34**, added to `TRIALS_LEDGER.md` **before P02**, in a **new section "G. Forecast /
   risk-rule studies"** (separate from A–D, which hold return claims), with the ledger's usual
   columns.
2. **Variants booked at discovery: 10** = 3 pairwise primary comparisons (the selection set: any of
   three candidates could be picked) + 1 secondary loss + 6 sensitivities. **Confirmation: 1** (the
   single pre-registered test). Total **11**, written in the row as "10 + 1".
3. **Not added to the alpha total (≥ 326)** and not changing the z ≥ 3.6 bar. Reason: the bar adjusts
   for picking a return claim after many looks; this study's output is a risk instrument, and if the
   WINNER ever feeds a return test, that test gets its own row judged against the alpha total.
4. **Proposed header line for the ledger** (needs the operator's OK, since ledger text is not edited
   without it): *"Section G lists forecast and risk-rule studies with their own variant counts; they
   are not in the alpha total."*
5. **Result column** is filled after P02 with WINNER/NO WINNER and the three z's, and after P03 with
   CONFIRMED/NOT CONFIRMED and the confirmation z. If P01 returns NOT EVALUABLE, the row reads
   "0 looks" like #33, and the booked variants are not counted.
6. **Source column:** this file's sha256 once frozen, `CODE_FREEZE.sha256`, `RESULTS.sha256`,
   `DEVIATIONS.md`.

Draft row (to be completed at each step):

> | 34 | Volatility forecast for equal-risk sizing (Binance USDT-M perps, crypto only): ATR_10 vs ATR_100 vs 0.5/0.5 blend, normalised true range, next-7-day mean NTR, QLIKE, DM clustered by date; discovery 2023-03…2026-09 on breakout data (read-only), one confirmation on a fresh 2020-01…2022-08 download | 2026-10-22 | PENDING (before P02) | 10 + 1 booked (3 pairwise primary + MALE + 6 sensitivities; 1 confirmation); forecast study, not in the alpha total | [repo] `[redacted: local path]` sha256 `<after freeze>` |

### 13.2 Decisions the operator must give in chat before this file is frozen

| # | decision | proposed |
|---|---|---|
| D0 | Study folder | `[redacted: local path]` (new; nothing on [redacted: local path]) |
| D1 | Normalisation | per-day NTR = TR_d / C_prev (price-unit version is S6) |
| D2 | Default forecast on NO WINNER or NOT CONFIRMED | C (the blend) |
| D3 | Bars | discovery z ≥ 2.5 one-sided against each other candidate; confirmation z ≥ 2.33 one-sided |
| D4 | Confirmation data is unseen | operator confirms no study on this [redacted: machine detail] has loaded 2020-01…2022-08 USDT-M klines |
| D5 | Ledger counting | 10 + 1 variants, new section G, not in the alpha total; header line in §13.1 item 4 |
| D6 | Count-gate floors | discovery 800 dates × ≥ 30 coins; confirmation 400 dates × ≥ 10 coins |
| D7 | NO WINNER leaves the confirmation data unopened | yes (kept for a future version) |

A "yes" to the whole table, or a ruling on each line, is needed before the hash. A ruling that
changes any rule makes this v0.2, not an edit of v0.1.
