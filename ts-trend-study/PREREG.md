# Time-series trend on Binance USDT-M perpetuals with volatility-forecast sizing

## DRAFT v0.9 — FREEZE CANDIDATE — NOT FROZEN — NO REAL-DATA OUTCOME COMPUTED

27 Oct 2026, 20:40. v0.9 changes text only in the four [TODO] lines and the Gate 2 proposal, recording operator rulings made 27 Oct 2026 (delisting announcement dates: yes; Gate 2: adopted as written; trials ledger #38; both seed sets committed in b858999) and the fake-data calibration result (5 of 200 pass, decision 1: proceed to freeze). No other number, rule or wording changed. v0.8 superseded v0.7 with one operator ruling from the Step 7 mechanics checks: starting equity $500 (at $100 every order fell under Binance's $5 minimum because the 2020–21 median forecast range is 11.1%, not the 4% used as an example). Mechanics checks (counts only) have been run on the DEFINE slice; no outcome statistic exists. v0.7 superseded v0.6: adds one reported-only arm (25% portfolio-volatility target, chosen by 4 of 6 reviewers over r = 1% and a 200-day regime filter), a pre-set live-sizing option, the delisting-announcement feasibility finding, and a Gate 2 proposal for ruling. v0.6 resolved the compression-breakout status, maintenance rate and Gate 1 drawdown definition. v0.5 filled in equity, drawdown cap and demo use; v0.4 followed four reviews of the §2/§7/§11 rebuilds. Nothing here is
binding until §15 step 6 is executed. No outcome statistic has been computed on real data.

Operator rulings (all stated in chat, 27 Oct 2026):
- Primary arm long/short; long-only reported. Main sizing ATR10/ATR100 blend; equal-weight reported.
- Split by calendar year. Pass rule relative to baselines, margins +0.25.
- Base cost 10 bps per side; verdict judged at 2× (20 bps/side, 40 bps round trip).
- Time-shifted null and top-2-trades check are reported, not vetoes.
- Bear floor: calendar-2022 net return at 2× cost ≥ −15%.
- Compression-breakout study: the ruling (frozen → finish first; unhashed → drop) was adopted, then
  made moot by the read-only audit of 27 Oct: the study is CLOSED (see §0).
- Liquidation check: daily close AND the conservative intraday check (§5). **Adopted.**
- Starting equity **$500** (ruled 27 Oct 2026 after Step 7 showed that at $100 a full-vote order is $4.51 at the slice-median forecast range of 11.1%, under the $5 minimum, so nothing trades; $500 is the smallest size at which the designed portfolio exists: full vote ~$22, two-thirds ~$15, one-third ~$7.5). Sensitivities **$100** (expected to show near-total skipping) and **$10,000**.
- Gate 1 drawdown cap **20%**. Gate 1 uses the Binance Futures testnet for operations and a mainnet-price paper harness for the numbers (§11).

What v0.4 fixes (from the v0.3 reviews):
1. §2 lock: run-scoped token acquired at launch (v0.3's token refused the run that created it);
   code identity checked against the blobs at the frozen commit, not HEAD (v0.3's HEAD test could
   never pass); token checked in git HISTORY so deleting the file does nothing; the verdict file must
   have exactly one commit and match a content hash in the ledger, so a FAIL→PASS edit is detectable.
2. §0/§15 ordering: the freeze is the LAST design step; only after it may the compression study's
   results be read; after that the design is immutable.
3. §13: crash-retry of the holdout named as a disclosed exception next to the bug procedure.
4. §7: untradeable shifted targets, null liquidation, and cost on fraction changes specified;
   "weight-path replay, not order replay" stated so the turnover claim cannot drift back.
5. §9: report how often the close check vs the intraday check triggers.

All four [TODO] items and the Gate 2 proposal were ruled on 27 Oct 2026 (§15 step 2, done). Decided tonight on sizing (27 Oct): r = 0.5% stays for the research test (crash-day arithmetic: 10 positions × 3 ranges × 0.5% = −15% in one day); the 2× gross cap stays; no leverage above it is contemplated at any stage.

---

## §0 Scope and family

- Family: **"time-series trend on daily bars"**. New family. Holding periods are days to weeks and
  no microstructure feature is used, so this study is declared OUTSIDE the "directional
  perp-microstructure" family closed by the basis-dislocation stopping rule (31 Aug 2026). It does
  not override that rule.
- One verdict only: the long/short arm, ATR-blend sizing, judged at 2× base cost, on the verdict
  slice. Every other arm, split, sensitivity and diagnostic is reported only and can never become the
  verdict. A reported-only arm that looks better is a NEW hypothesis: new pre-registration, fresh
  confirmation data (the historical holdout is never "fresh" for a promoted arm). It is never
  promoted after the fact.
- Compression-breakout study: **CLOSED, audited read-only on 27 Oct 2026.** PREREG_v0.1 was frozen on
  22 Oct 2026 (sha256 aae534a1…, verified; code freeze verified; 26 tests passed), ran its
  pre-registered count-only power gate P01 and stopped as NOT POWERED (MDE 344 bps vs a 250 bps
  gate; 0 outcome looks; ledger row #33). Nothing to finish, nothing to drop, nothing to fold in.
  Its lesson is recorded here: a rare-event design cannot reach z ≥ 3.6 on four years of daily
  data, which is one reason this study's pass rule is economic (§8, §10). Its cleaned base is reused
  where it fits (§2): the download scripts, the crypto-only exclusion list built from Binance
  contract metadata (`exclusions_v2.txt`, DEV-1 rulings) and the `exchangeInfo` snapshot.
  General ordering rule kept for any future sibling study: THIS design is frozen (§15 step 6) before
  any sibling's results are read; after that it is immutable except for the §11 bug procedure.
- Trials ledger: **#38** (operator ruling 27 Oct 2026), linked to the momentum study.

## §1 Question

Primary: On Binance USDT-M crypto perpetuals, daily bars, does a fixed Donchian breakout ensemble,
traded long and short, with equal-risk sizing from the ATR10/ATR100 blend, beat simple baselines
after realistic costs and funding?

Reported only (no verdict): long-only arm; equal-weight sizing arm; ATR14-sizing robustness arm on
the holdout; year-by-year, regime and funding splits; the diagnostics in §8–§9.

What this is NOT: not a claim of novelty (Donchian is a public recipe). The contribution is the
honest test: point-in-time universe with delisted coins, actual funding, small-account execution,
one look.

## §2 Data and split

- Source: Binance public archive (data.binance.vision), USDT-M perpetuals, daily klines (00:00 UTC
  bars) and 8-hour funding rates. Same download and cleaning pipeline as the momentum and
  vol-forecast studies. Delisted contracts included.
- Sample start: the first date on which ≥ 20 coins are eligible under §3. Expected mid-2020;
  **unverified until the §15 mechanics check**, which records the actual date. Sample end: the last
  complete UTC day before freeze.
- Split by calendar year:
  - **DEFINE**: sample start → 2021-12-31 (about 18 months; only one full calendar year). Mechanics
    only: universe reconstruction, delisting and relisting handling, funding alignment, lot and
    minimum-order simulation, margin accounting, count-only statistics (eligible coins, votes, ATR
    distribution, universe turnover), and the calm/wild cut points (§9). **No outcome statistic**
    (strategy return, Sharpe, hit rate, drawdown) may be computed on real DEFINE data. The fake-data
    calibration (§11) runs on sign-flipped DEFINE data only.
  - **VERDICT**: 2022-01-01 → 2023-12-31. One look, one script execution that produces the primary
    result, every reported arm, every baseline and the null comparisons at once.
  - **HOLDOUT**: 2024-01-01 → sample end. One look, one authorized execution, only after a PASS
    verdict is committed. Can confirm or weaken a PASS; can never turn a FAIL into a PASS.

- **Holdout lock (procedural, not data isolation).** The daily klines for 2024–2026 already exist
  on disk from the vol-forecast study. Nothing stops another script or a person from opening them;
  the access log records loader-mediated access only; a rewritten git history would be deliberate
  fraud, outside what a procedural lock can stop. What the lock enforces:

  1. **Separate script.** Holdout processing lives in `holdout_run.py`, the only code path whose
     loader can return dates ≥ 2024-01-01. The verdict script's loader refuses them unconditionally.
  2. **Verdict authenticity.** The loader requires `VERDICT.json` to satisfy all of:
     (a) `git log --format=%H -- VERDICT.json` returns exactly ONE commit, and
     `git status --porcelain VERDICT.json` is empty (no uncommitted edit);
     (b) the file's sha256 equals the content hash written into the trials-ledger entry in that same
     commit (so a FAIL→PASS edit shows as a second commit or a hash mismatch);
     (c) structured fields: `study` = this study's name, `primary_status` = `PASS`,
     `prereg_sha256` = the frozen prereg hash, `code_commit` = the freeze commit, `run_id`.
     (d) `prereg_sha256` equals the sha256 the loader recomputes from the committed prereg file.
  3. **Code identity (not HEAD).** A committed manifest lists every pipeline file. For each, the
     loader hashes the running file and compares it with the blob at `code_commit`
     (`git rev-parse <code_commit>:<path>` → blob id → `git cat-file -p` → sha256). Any mismatch
     refuses. HEAD may move freely (committing the verdict and the token moves it).
  4. **One authorized execution, run-scoped token.** At launch, BEFORE any holdout read,
     `holdout_run.py` checks that `git log --format=%H -- HOLDOUT_TOKEN.json` is EMPTY (the token has
     never existed in history) and that no working-tree token exists. If so it writes
     `HOLDOUT_TOKEN.json` = {run_id, timestamp, VERDICT sha256} and commits it immediately. Every
     read inside that process carries that run_id and is permitted. Any other execution finds the
     token in history and is refused, whether or not the working file still exists.
  5. **Crash.** The committed token means the holdout is consumed. A re-execution requires: an
     operator authorization recorded in the ledger; the crashed run's partial outputs deleted
     unread; a second token committed with `retry_of` = the crashed run_id; and the report disclosing
     a repeated execution of the same look. This is the §13 crash-retry exception.
  6. **After a FAIL** the verdict file says `FAIL`, check 2(c) fails forever, and the holdout stays
     locked for this study permanently.
  7. **No holdout number for ANY arm, baseline, sensitivity or diagnostic may exist before the
     holdout look.** The holdout execution produces everything at once.

- Disclosure 1: the sizing model (ATR blend) was selected in the vol-forecast study on 2023-03 →
  2026-09 data, which overlaps the verdict slice (2023) and the holdout. That was forecast
  selection, not return selection, and the blend weights were fixed in advance. Consequence: a
  holdout CONFIRMED means "consistent with prior selection", not an untouched confirmation. The
  holdout report includes an ATR14-sizing arm as a robustness comparison; it is not a selection-leak
  detector.
- Disclosure 2: the verdict years were chosen knowing 2022 was a bear year and 2023 a chop/recovery
  year. A regime-coverage choice made before any outcome; unavoidable with calendar splits. The
  holdout is likely a bull window, the hardest case for the short side.
- Disclosure 3: the compression-breakout study (closed, NOT POWERED) computed no returns, so nothing
  from it describes outcomes on this study's verdict or holdout dates. Its cleaned base is reused:
  cleaning rules, the crypto-only exclusion list and the metadata snapshot; its klines start 2022-09,
  so the 2020–21 data is a fresh download under the same rules.
- Boundary embargo (multi-week holds): each slice starts flat. A position open at a slice boundary
  is closed at the boundary close, with exit cost, in the earlier slice's accounting. Lookback
  windows (channels, ATR) may read prices from before the boundary: they are inputs known at
  decision time, not outcomes.

## §3 Universe (point-in-time, all filters use data to t−1 only)

- Crypto contracts only. Exclude stablecoin pairs, index contracts and tokenised gold/metals.
- Eligible on decision date t if: listed ≥ 120 days on its current listing clock; ≥ 100 valid
  trading days; 30-day median quote volume ≥ $10M. Same filters as the vol-forecast study.
- Relisting rule (vol-forecast §4.3): more than 7 consecutive days without trading restarts the
  listing clock, and the coin must re-qualify.
- Tradeable set: the top 30 eligible coins by 30-day median quote volume, fixed on the first day of
  each calendar month. Report the number of eligible coins per month.
- Disclosure 4: a volume filter is correlated with recent performance, so the universe is
  momentum-adjacent, not neutral. Disclosed; not changed.
- Delisting rule: exit at the coin's last available daily close (Binance settles delisted perps near
  the final mark, so this approximates settlement), plus a volatility-scaled slippage penalty of
  **1 × F_i** (the coin's forecast daily range, §5) at that date. Report sensitivities at 0 × F_i
  and 3 × F_i. **[RULED 27 Oct 2026: YES]** Binance delisting announcement dates are
  used: exit at the announcement day's close for every delisting with an unambiguous
  announcement timestamp, and use the last-available-close rule as the deterministic fallback for
  any without one; the report counts how many delistings took each path. Result (Step 8, 27 Oct): metadata/delisting_events.csv
  holds 178 Futures delisting events; all 3 delistings inside the DEFINE span (LENDUSDT, BTCSTUSDT,
  BZRXUSDT) have an unambiguous announcement; EOSUSDT and LITUSDT have none and take the
  last-close fallback. Feasibility (checked 27 Oct): Binance's "Delisting"
  announcement category renders server-side with publish dates (about 45 pages, ~900 notices;
  e.g. "Futures Will Delist PTBUSDT and MITOUSDT (2026-10-23)" published 2026-10-21), and a public
  JSON endpoint (`bapi/composite/v1/public/cms/article/list/query`, catalogId 161) serves the same
  list to scripts. Plan: build the event file (symbol, announcement date, delisting date) in the
  week-2 mechanics work; "multiple contracts" notices need the article body opened for symbols. If
  the endpoint blocks scripts, read the rendered pages through a browser; if neither works in the
  time box, the answer is "no" and the last-close rule applies to all.
- Coins with fewer than N+1 daily closes get a vote of 0 for that lookback N.

## §4 Signal (fixed forever at freeze; no tuning)

For each coin and each lookback N ∈ {20, 50, 100} days, on completed daily closes only:

- Long vote (+1) starts when close_t > max(close_{t−N} … close_{t−1}).
  It ends (vote → 0) when close_t < min(close over the prior N/2 days).
- Short vote (−1) starts when close_t < min(close_{t−N} … close_{t−1}).
  It ends (vote → 0) when close_t > max(close over the prior N/2 days).
- Exit channel = N/2 (10, 25, 50 days). Fixed in advance, so not tuning.
- Coin score s_t = mean of the three votes ∈ {−1, −2/3, −1/3, 0, +1/3, +2/3, +1}.
- **Primary arm (long/short):** direction = sign(s_t), size scales with |s_t|.
- **Secondary arm (long-only, reported):** s_t replaced by max(s_t, 0).
- No intraday data, no volume or OI feature, no regime filter in the signal.

## §5 Portfolio, sizing and account accounting

- Candidates each day: tradeable-set coins with s_t ≠ 0. If more than K = 10, keep the 10 with the
  highest 30-day median quote volume (liquidity, never signal strength; deterministic tie-break by
  symbol name).
- **Volatility forecast, defined exactly as in the confirmed study:** for each day,
  TR_t = max(high_t − low_t, |high_t − close_{t−1}|, |low_t − close_{t−1}|) and
  tr_t = TR_t / close_{t−1}. ATR10 = mean of tr over the last 10 days, ATR100 = mean over the last
  100 days, both using data to t−1. F_i = 0.5 × ATR10_i + 0.5 × ATR100_i. (The mean of normalised
  daily true ranges — NOT a price-unit ATR divided by one close.)
- **Main sizing (ATR blend):** daily-range exposure budget r = 0.5% of equity per one forecast
  daily range (exposure per forecast range, not stop-loss risk):
  notional_i = |s_i| × r × equity / F_i, direction sign(s_i).
  (Example: F = 4%, equity $1,000, full vote → notional $125 = 12.5% of equity.)
  r sets the absolute loss level that the bear floor (§8 P5) tests.
- Gross leverage cap: Σ|notional_i| over all long and short positions ≤ 2 × equity; scale all
  positions down proportionally if exceeded. Disclosure 5: with r = 0.5% the cap binds only when
  forecast ranges are small (roughly F ≤ 2.5% across ten full positions); a safety rail, not a
  design knob.
- Turnover brake: re-check daily, but only send an order when the sign changes, the vote goes to
  0, or the target notional differs from the current notional by more than 20%.
- **Executed position series:** the daily record, per coin, of the position actually held after the
  brake, lot rounding and skipped orders, stored as a fraction of that day's equity. This series is
  what §7's null replays.
- **Comparison sizing arm (equal weight, reported):** notional_i = |s_i| × 10% of equity, same cap
  and brake.
- **Portfolio-volatility-target arm (reported only, added v0.7):** the main arm's target notionals
  are all multiplied by one daily scale factor k_t = clip(25% / σ_{t−1}, 0.25, 2.0), where σ_{t−1} is
  the annualised realised volatility (√365 × standard deviation) of the UNSCALED main arm's own daily
  net returns over the trailing 60 trading days ending t−1 (point-in-time: it never uses day t).
  Startup: k = 1 until 60 days of unscaled history exist inside the slice. The 2× gross cap, the
  turnover brake, lot rounding and the minimum order apply after scaling. Nothing is fitted: 25%,
  60 days and the clip bounds are fixed here. It answers one question — does portfolio-level risk
  control add anything beyond per-coin range sizing — and carries no pass/fail.
- **Account realism:** cross-margin, daily mark-to-market. Equity_t = cash + unrealised PnL −
  cumulative funding − cumulative costs. Simulate Binance lot step sizes and the per-symbol minimum
  order notional (the $5 default; **verify per symbol from exchangeInfo MIN_NOTIONAL in the §15
  mechanics check**); orders below the minimum are skipped. Starting equity = **$500** (v0.8 ruling; the v0.7 text
  below records the superseded $100 arithmetic), with $100 and $10,000 reported as sensitivities. At $100 a
  full-vote position on a 4%-range coin is $12.50, a two-thirds vote $8.30, a one-third vote $4.20
  (skipped): the minimum-order rule is part of the strategy at this size, by design, and the report
  counts skipped orders. Disclosure 14. **Superseded by the $500 ruling (v0.8):** starting equity =
  **$500**; at the DEFINE-slice median forecast range of 11.1% a full vote is ~$22.5, two-thirds ~$15,
  one-third ~$7.5, all above the $5 minimum; the five contracts with a $20 minimum still skip
  one-third and two-thirds votes and are counted. Sensitivities $100 and $10,000.
- **Liquidation accounting (ruling adopted):** maintenance requirement = 5% of gross notional —
  **closed as a verified-conservative constant**: Binance's tier-1 maintenance rates at the simulated
  notionals run from ~0.4% (BTC) to ~2.5% for alts, so 5% is at or above every contract this
  universe can hold. It is also nearly immaterial under the 2× gross cap: maintenance = 5% × gross
  ≤ 10% of equity, so the check can only fire after a ~45% one-day adverse move on gross. The live
  table is still read once in the §15 mechanics check (through a browser) and recorded, in case a
  top-30 contract carries an unusual rate.
  Checked twice a day: at the daily close, and at a conservative intraday point where every long is
  marked at the day's low and every short at the day's high simultaneously — an over-estimate of the
  true intraday worst case that can fire when a real account would not have; daily bars allow
  nothing finer. If equity falls below the maintenance requirement at either check, every position
  is closed at that mark at a cost of 2 × (multiplier in force) × 10 bps per side, and the event is
  recorded with which check fired. A liquidation event inside the verdict slice is an automatic FAIL
  (§8 P0).

## §6 Execution and costs

- Signal from the completed 00:00 UTC daily bar; fill at the next daily open. Known to be
  optimistic (close and next open are adjacent); slippage is in the base cost. Optional reported
  sensitivity: fill at the close of the first hourly bar after the signal.
- **Base cost: 10 bps per side** on traded notional = 5 bps taker fee + 5 bps slippage. This is an
  ASSUMPTION for small market orders on top-30 coins. It is NOT measured: every fill record the
  operator owns (Blackbox manual fills, alert-bot fills) dates from 2026, inside the holdout period,
  so no pre-freeze measurement is allowed. Report at 1×, 2× and 5×.
  **The verdict is judged at 2× (20 bps per side, 40 bps round trip)**, about the ~42 bps round trip
  measured on the operator's fast altcoin trades. 5× (50 bps/side) is the stress case.
- Also report the old constant 21 bps/side (the momentum-study number, measured on fast taker
  trades with stop-outs) as a sensitivity, so the two cost worlds sit side by side.
- **On a FAIL, the report shows the 1× result prominently**, so the failure reads as either "no
  edge" or "edge below doubled costs", never silently one or the other.
- Funding: actual Binance 8-hour funding history, applied to every open position at each
  settlement, signed (longs pay when funding is positive, shorts receive).
- Delisting as in §3. Liquidation cost as in §5.

## §7 Baselines (same cost model, funding and account accounting)

- **B1** BTC buy-and-hold on the perpetual, 1× notional, funding included.
- **B2** BTC only, same signal, same sizing rule, same costs. (Does the altcoin universe add anything?)
- **B3** Always long every tradeable-set coin, same ATR-blend sizing, same caps. (Pure beta with the
  same sizing layer.)
- **B4 Time-shifted null (reported, §8 R1).** A time-displacement diagnostic, not a formal test. It
  is a **weight-path replay, not an order replay**: historical fractions applied to a new equity
  path change the dollar turnover, so it is never called "turnover-matched"; the achieved turnover
  of real and null runs is reported side by side.
  - Input: the primary arm's executed position series (§5), as fractions of equity per coin per day.
  - Lag: L is an integer drawn uniformly from [30, 365] inclusive, one L per run, the same for all
    coins; 200 runs; the seed is committed before first use. The shifted series on day d holds the
    real executed positions of day d − L; days before slice start + L are flat. No wrap-around.
  - Replay accounting (full): the null run starts flat with the same starting equity and computes
    its own equity daily. Each day it sets each coin's target notional = shifted fraction × its own
    equity, then applies lot rounding and the $5 minimum (the brake is not re-applied: the executed
    series already embodies it; the leverage cap is inherited because the fractions respected it).
    Cost is charged on the traded notional |n_t − n_{t−1}| at the verdict multiplier (20 bps per
    side). Funding is applied by date. The §5 liquidation accounting runs.
  - Untradeable shifted target: if the coin is not in that month's tradeable set, is not trading, or
    the order is below the minimum on that date, the target for that coin that day is 0. An open
    null position in a coin whose contract has ended is closed under the §3 delisting rule; an open
    null position in a coin that is merely untradeable that day is closed at the day's open with
    normal cost. The next day's target is applied fresh; nothing is carried.
  - Null liquidation: positions close under §5, the null's equity path continues flat (zero return)
    to the end of its window, its Sharpe is computed on the full window, and the event is counted.
  - Paired comparison: for each run, the real strategy is restarted flat on day slice start + L
    (entries charged, lookbacks may read earlier prices as inputs) and both are evaluated on the
    same window [slice start + L, slice end]. Shortest window = 365 days on the verdict slice.
  - Output: the fraction of the 200 paired comparisons in which the real net Sharpe exceeds the
    null's, the distribution of paired Sharpe differences, achieved turnover of both, and the count
    of null liquidations. There is no single real Sharpe to rank, so no percentile is reported.

## §8 Pass / fail — judged ONCE, on the VERDICT slice, primary arm, ATR sizing, 2× cost, funding on

Net annualised Sharpe (daily net return on equity, × √365) is the **sole comparative performance
statistic**. P0, P1 and P5 are **mandatory safety and return gates**, not comparisons.

**PASS requires ALL of:**
- P0 No liquidation event (§5, either check) in the verdict slice.
- P1 Net total return > 0 over the verdict slice.
- P2 Net Sharpe ≥ B1 net Sharpe + 0.25.
- P3 Net Sharpe ≥ B2 net Sharpe + 0.25.
- P4 Net Sharpe ≥ B3 net Sharpe + 0.25.
- P5 Bear floor: calendar-2022 net return at 2× cost ≥ −15%. Intent: "did not blow up in the bear
  year", on the same cost basis as the verdict.

The +0.25 margins are economic ("is the alt universe and the timing worth the extra complexity,
delisting risk and order count?"), not significance tests. P3 is expected to be the binding
condition in a bear/chop verdict window. Honest consequence of the rulings that made R1 and R2
reports: a PASS can be concentrated in a few trades and can sit inside the time-shifted null
distribution. The only false-positive evidence this study will have is the §11 calibration, which is
conditional on a synthetic null and is a noisy screen (10 of 200). A PASS is therefore never
described as statistically established.

**FAIL** otherwise. On FAIL: publish (with the 1× result shown, §6); the "time-series trend on
daily bars" family is closed for 12 months; no lookback, exit, K, r, cost or universe tuning; no
second look; the holdout stays locked.

**On PASS:** open the HOLDOUT, one authorized execution. **CONFIRMED (consistent with prior
selection)** requires: no liquidation event, net return > 0 at 2× cost, and net Sharpe ≥ B2 net
Sharpe. The holdout does not have to beat BTC buy-and-hold. PASS + failed holdout: publish, park the
family permanently.

A PASS or CONFIRMED means "worth a forward paper test" (§11). It is not statistical proof (§10) and
not a licence to trade live.

**Reported diagnostics attached to the verdict (never vetoes):**
- R1 Fraction of B4 paired comparisons won, and the distribution of paired differences (§7).
- R2 Net return and Sharpe with the 2 best trades removed. One algorithm: a trade is one coin's
  position from s ≠ 0 to s = 0 or a sign flip; rank trades by net dollar PnL including funding and
  costs; take the two largest; rebuild the equity path with those two trades' daily PnL, funding and
  costs set to zero while every other position keeps exactly the dollar notionals of the original
  run (sizing is NOT recomputed from the altered equity); report net return and Sharpe of that path.
  Trend following earns its year in a few large runs; concentration is disclosed, not punished.
- R3 Everything in §9.

## §9 Reports required (no verdict attached)

All arms (long/short, long-only; ATR blend, equal weight, 25% portfolio-vol target; on the holdout
also ATR14 sizing) at
1×/2×/5× cost and the 21 bps/side sensitivity; year by year; calm vs wild days — BTC 30-day realised
volatility terciles with cut points computed on the DEFINE slice and hard-coded into the committed
script before any 2022 data is processed; net return by funding tercile; number of trades; median
and mean holding period; whipsaw rate (trades closed at a loss within 5 days); max drawdown;
turnover (real and null); gross exposure; share of days flat; share of days the leverage cap bound;
number of eligible coins per month; delisting events, which rule each used, and their
sensitivities; liquidation checks: how many days the close check and the intraday check each came
within 2× of the maintenance requirement, and any events, by check; results with and without the
top 2 trades; cluster-robust (by date) and block-bootstrap (mean block 20 days) confidence intervals
on net Sharpe — reported, never deciding.

## §10 Power statement (arithmetic done before freeze, not after)

- For daily returns, t ≈ Sharpe × √years. Verdict slice = 2 years: true Sharpe 0.5 → t ≈ 0.7;
  1.0 → t ≈ 1.4; 1.5 → t ≈ 2.1. Holdout ≈ 2.8 years: 1.0 → t ≈ 1.7.
- The standard error of a single two-year Sharpe is about 0.7. The paired difference against a
  correlated baseline has a different, unknown standard error; the point is only that no slice can
  show "significantly above zero" unless the true Sharpe is above ~1.5. The pass rule is economic
  for that reason, and the null comparison is a report rather than a veto.
- Independent bets: ~10 positions with multi-week holds give perhaps 50–150 trades a year, but crypto
  trades share one market factor, so the effective number is far smaller. Confidence intervals are
  reported with that in mind.
- Realistic expectation from the outside reviews: net Sharpe 0.5–1.0 with long flat stretches.

## §11 Null calibration, bug exception and the live ladder

**Fake-data calibration (before freeze, on DEFINE data only; a screen, not matched calibration):**
- Synthetic slice = the whole DEFINE slice (about 18 months; shorter than the 2-year verdict, which is
  why this is labelled a screen). The bear-floor gate P5 is applied to the first 12 months of the
  synthetic slice (or the whole slice if shorter).
- 200 fake datasets. For each day t draw one sign ε_t ∈ {−1, +1}, the same for every coin that day
  (keeps cross-coin dependence). Build each coin's fake path RECURSIVELY from its own fake previous
  close q_{t−1} (q at the start = the real close before the slice), with p = the real previous close
  c_{t−1} and real fields O, H, L, C:
  - ε_t = +1: Õ = q·O/p, H̃ = q·H/p, L̃ = q·L/p, C̃ = q·C/p (same returns, re-anchored).
  - ε_t = −1: Õ = q·p/O, H̃ = q·p/L, L̃ = q·p/H, C̃ = q·p/C (log returns negated, high and low
    swapped and mirrored, re-anchored).
  Then q_t = C̃. The fake close-to-close log return is exactly ε_t·r_t on every day; the path is
  continuous; bar ordering holds (L̃ ≤ Õ, C̃ ≤ H̃). Log ranges are preserved; the price-unit
  normalised true range of §5 is NOT exactly preserved (second-order differences), so ATR and sizing
  are recomputed from the fake bars and no preservation is claimed. A unit test checks continuity,
  bar ordering and ε_t·r_t on every day before the runs.
- Volume is unchanged (it drives the universe). Each day's funding payments are multiplied by ε_t,
  so the fake market's funding sign follows its fake direction.
- Run the full pipeline (universe, signals, sizing, caps, costs at the verdict multiplier, funding,
  liquidation accounting, baselines B1–B3) and the full pass rule P0–P5 on each fake dataset. The
  rule may fire in at most 5% of runs (≤ 10 of 200).
- Seeds: two seed sets — calibration (200) and fresh validation (200) — are committed BEFORE the
  first calibration run. Seed sets cannot be discarded or replaced. Done: both committed in b858999
  (27 Oct 2026) before any run — seeds/calibration.txt sha256
  f43d55dc731cbac77151255f999e64dff614f9f1c3f996012d0d783f102a3d75, seeds/validation.txt sha256
  ff3d4cdb37b2384c1170a62d97a90e55cb6f3e09b97407d81ef6fa9e49bb2922. Calibration result (490695e,
  reports/CALIBRATION.md): 5 of 200 fake datasets pass P0–P5 → decision 1, proceed to freeze; the
  validation set stays unused.
- Decision sequence, fixed now:
  1. Calibration passes (≤ 10 of 200) → proceed to freeze. Results published.
  2. Calibration fails → HALT. No automatic tightening. Tightening any ruled number (+0.25 margin,
     −15% floor) requires an explicit operator ruling at that point, one time, recorded in the ledger
     and disclosed in the report; no new condition may be invented.
  3. If tightened: validate on the committed fresh seed set. Pass → freeze with the tightened rule.
  4. Fresh validation fails → no verdict run under this version. The study returns to design as a
     new version with a new outside review; the ledger records the failed calibration.

**Bug exception:** if an implementation bug is found after a look, it must be a demonstrable code
defect with a reproducible test case, shown as a diff and reviewed by an outside model. The original
and corrected runs are reported side by side; the ledger records both; the corrected run stands
whichever direction it moves the result; it counts as the SAME look and never as a fresh
confirmation.

**Live ladder (two gates, both set at freeze):**
- Gate 1, operations (feasibility, not evidence): ≥ 6 months forward run in two parts that run at
  the same time: (a) **plumbing on the Binance Futures testnet** — real order placement with demo
  USDT, lot rounding, minimum-notional handling, restart and reboot survival; its P&L is ignored
  because the testnet book is thin and its prices drift; (b) **numbers from a mainnet-price paper
  harness** — signals recorded and fills simulated at real market prices, as the alert bot's paper
  mode already does. Gate 1 passes when (a) ran clean (no missed days, no unexplained orders) and
  (b) shows net return > 0, net Sharpe ≥ B2 on the paper window, and max drawdown < **20%**,
  defined as the peak-to-trough fall of daily marked-to-market equity after costs and funding over
  the paper window. The 20% is fixed now, before any verdict exists, and is never derived from the
  verdict slice's simulated drawdown.
  Passing Gate 1 allows live trading at the intended stake of $500 — the smallest size at which
  the portfolio exists — and nothing larger. Live sizing option, to be ruled BEFORE the paper run starts and never
  after: two reviewers suggested r = 0.25% for live money as a risk constraint (crash day −7.5%
  instead of −15%). It does not change the research sizing and is not a Sharpe improvement; at $500 it
  also raises the order-skip rate, which the paper run would show. **[RULING at Gate 1 start]**
- Gate 2, evidence: the bar for adding capital beyond the $500 stake, set at freeze while no
  outcome exists. **Ruled 27 Oct 2026 (operator): adopted as written.** (i) at least 12 months of forward record, paper
  and live combined, with net return > 0 on real or simulated-at-real-price fills; (ii) max
  drawdown < 25% over that record; (iii) the forward record beats the BTC-only same-rule baseline
  (B2) on net Sharpe over the same window; (iv) capital is added in steps, at most ×2 per six clean
  months, never in one jump; (v) the estate's live bar (z ≥ 3.6 on new data) is reported next to
  the forward record every time, so no one forgets that 12 months of daily data cannot reach it.
  Do not lower it casually; six months of paper trading can be six months of luck; Gate 1 never
  substitutes for Gate 2.

## §12 Stopping rules

- Study level: FAIL → family closed 12 months (§8).
- Direction level: if this study FAILS and the token-unlock feasibility count also fails, no new
  research family is opened for 6 months; income only. The clock starts at the later of the two
  verdicts.

## §13 Not allowed after freeze

Changing N, exit channels, K, r, leverage cap, turnover brake, maintenance rate, cost base or
multiplier, universe filters, delisting rule, split dates, baselines, pass numbers or the primary
statistic. Any look at verdict outcomes before the fake-data calibration is passed and the prereg
hash is committed. Reading the holdout before a committed PASS, for any arm. Adding arms, splits or
moderators. Reinterpreting a reported-only arm or diagnostic as the verdict, or promoting one after
the fact. Re-rolling or replacing seeds. Changing the calm/wild cut points after they are committed.
Tightening or loosening the pass rule outside the §11 decision sequence. Making a new design version
after the compression study's results have been read (§0).

**The only permitted re-executions after a verdict** are (1) the §11 bug procedure (same look, side
by side, diff-reviewed) and (2) the §2 crash-retry of the holdout (operator-authorized, partial
outputs deleted unread, second token with `retry_of`, disclosed). Nothing else.

## §14 Disclosures (collected)

1. Sizing model selected on data overlapping the verdict and holdout (§2).
2. Verdict years chosen knowing their regimes (§2).
3. Compression-breakout results, if that study runs on holdout dates, are known before this
   holdout look (§2).
4. Volume-filtered universe is momentum-adjacent (§3).
5. The 2× leverage cap rarely binds (§5).
6. The 10 bps/side base cost is an assumption; no pre-2024 fill record exists to measure it (§6).
7. Close-to-next-open fills are optimistic; slippage is in the base cost (§6).
8. The signal is a public recipe; the contribution is the test, not the signal (§1).
9. The holdout is earlier-registered historical data, not a forward test; only the live ladder's
   paper run is forward (§11).
10. The holdout lock is procedural; the data exists on disk; it cannot stop deliberate history
    rewriting (§2).
11. The fake-data calibration is a screen on an 18-month synthetic slice, not matched calibration
    (§11).
12. The intraday liquidation check is a conservative proxy built from daily highs and lows and can
    fire when a real account would not have (§5).
13. The time-shifted null is a weight-path replay, not an order replay, and not turnover-matched (§7).
14. At $500 the designed portfolio exists; the $100 sensitivity arm is expected to skip almost every
    order (Step 7 mechanics: median forecast range 11.1% on 2020–21 alts). The simulated strategy is
    the $500 strategy, not an idealised one (§5). Funding settlement timestamps in the archive sit up
    to 1 s off the 8-hour grid and are snapped to it before the engine reads them (Step 8 fix).

## §15 Freeze procedure — the freeze is the LAST design step

1. (Done 27 Oct 2026.) Compression-breakout status audit: CLOSED, NOT POWERED. No sibling study is
   pending.
2. Resolve every **[TODO]** (four) and the Gate 2 ruling: delisting announcement dates yes/no
   (feasible; build in week 2); Gate 2 proposal ruled; ledger number; calibration seed set;
   fresh-validation seed set. (Starting equity $500, Gate 1 cap 20%, maintenance 5%, r = 0.5%,
   2× cap are set.) Record the vol-target arm's parameters (25%, 60 days, clip 0.25–2.0) as fixed.
3. DEFINE-slice mechanics checks (no outcome stats): actual sample-start date and DEFINE length;
   monthly top-30 universe reconstructable; delisted-coin klines complete; funding timestamps aligned
   to the daily bars; per-symbol minimum notional read from exchangeInfo; lot and minimum-order
   simulation behaves at $500; live Binance maintenance tiers read and recorded; margin
   accounting behaves at both checkpoints; calm/wild cut points computed and hard-coded; count-only
   statistics recorded; fake-data unit test (continuity, bar ordering, ε_t·r_t) passes; the §2 lock
   is tested end to end on a dummy study (first run allowed, second refused, deleted token refused,
   edited verdict refused, HEAD movement tolerated).
4. Commit both seed sets. Run the fake-data calibration (§11) and follow its decision sequence.
5. Commit the pipeline manifest (list of code and config files) and tag the code commit.
6. **FREEZE:** sha256 this file as final text, commit and tag; record the hash in HASHES.txt. After
   this step the design is immutable.
7. (No sibling results to read.)
8. Run the VERDICT slice once (one execution, everything at once). Commit VERDICT.json (with
   `primary_status`, `prereg_sha256`, `code_commit`, `run_id`) and the ledger line carrying its
   content hash in the same commit. Then, only on PASS, the holdout once via `holdout_run.py`.
9. Publish either way (quant-market-research, staging first), with the 1× result, the calibration
   results, the seeds, the manifest, the token and the access log.

## §16 Fit with the time budget

- Build and checks are Claude Code work; the operator's hours go to prompts, review and rulings.
- Three-week schedule (operator advanced the start before 30 Nov, ~7 h/week): week 1 audit, TODOs,
  archive cleanup; week 2 build and mechanics checks; week 3 calibration, freeze, verdict, report.
  Income work always pre-empts; a slip of a week is the correct outcome, not a failure.
