# Cross-coin Momentum on Binance USDT-M Perps — Pre-registration v0.2

Status: **Approved by the user in chat on 2026-10-23 and frozen; SHA-256 in HASHES.txt.** No signal-vs-future-return number had been computed when it was frozen. This file is never edited; changes go in v0.3 etc.

## 0. Changes from v0.1 (user rulings, 2026-10-23, before any signal-vs-return number)

- **Funding included** in returns (was [OPEN]).
- **Pre-2020 lookback:** 2019-09 to 2019-12 downloaded for lookbacks and listing dates only. Sample starts **2020-01-06**.
- **AMT period:** 2020-01 to 2022-12, same as the primary.
- **Portfolios:** top **third** vs bottom **third** (was 20%).
- **Volume floor:** **$2M** average daily (was $5M).
- **Breadth:** skip a week if fewer than **5** coins per side (was 3).
- **Power** recomputed for these changes (§11), using the coin counts in the data report.
- **Funding gaps** (new, from the data report): see §6.
- **From the data report (DATA_REPORT.md), no results involved:**
  - The archive has **no 2019 files**; USDT-M klines start 2020-01. The 3 coins listed earlier (BTC, ETH, BCH) take their listing date from exchangeInfo `onboardDate`. Lookbacks start 2020-01-01.
  - Days missing from monthly kline files are filled from the archive's daily files (§3).
  - The first 13 Mondays (2020-01-06 to 2020-03-30) fail the breadth rule, so the first used week is 2020-04-06 (142 weeks).
- Everything else is as approved in v0.1.

## 1. Question and hypotheses

Do coins with the highest past return keep beating coins with the lowest, over the next week?

- **H1 (primary):** the weekly long-top-third / short-bottom-third spread, net of costs and including funding, has a mean above 0.
- **H2 (secondary, AMT):** the value-area score S predicts next-day return with a positive sign, beyond the controls in §8. H2 has its own alpha and **cannot rescue a failed H1**.

## 2. Data

- Source: Binance public archive `data.binance.vision`, USDT-M futures. No API keys, no logins.
  - Daily klines: `futures/um/monthly/klines/<SYM>/1d/`, 2019-09 to 2022-12.
  - Funding: `futures/um/monthly/fundingRate/<SYM>/`, 2019-09 to 2022-12.
  - 5-minute klines (H2 only): `futures/um/monthly/klines/<SYM>/5m/`, 2020-01 to 2022-12. **Needs a new OK from the user before download.**
- Symbol list: every symbol with a monthly klines folder in the archive, **including symbols later delisted**.
- 2019-09 to 2019-12 was requested for lookbacks and listing dates, but the archive has no USDT-M files before 2020-01. Coins whose first archive file is 2020-01 and whose exchangeInfo `onboardDate` is earlier (BTCUSDT 2019-09-08, ETHUSDT 2019-11-27, BCHUSDT 2019-12-19) use `onboardDate` as the listing date. All other listing dates are the first trading day in the archive.
- **Holes:** a day with no row inside a symbol's monthly-file range is fetched once from the archive's daily files (`futures/um/daily/klines/<SYM>/1d/`); if absent, it stays a non-trading day. (268 filled, 5 absent.)

## 3. Cleaning rules (copied from carry-study PREREG_v0.2 §0, §3; carry-study not modified)

- **C1 Trading day.** A UTC day is a trading day for a symbol only if it has a daily kline with quote volume > 0. A zero-volume row counts as no kline.
- **C2 Funding on non-trading days is ignored.** Funding prints dated on a non-trading day (e.g. baseline-rate filler for delisted coins) are dropped.
- **C3 Listing-clock restart.** Trading again after **more than 7 consecutive non-trading days** = a new listing from the day trading resumes; the 60-day age clock restarts.
- **C4 Reused / renamed tickers = new coin.** Symbols are independent. A renamed or redenominated ticker (e.g. 1000x contracts) is a new listing; a reused ticker is caught by C3.
- **C5 Minimum age.** Coins less than 60 days into their current listing are skipped.
- **Housekeeping:** duplicate daily rows (same UTC day) keep the first; rows with a non-positive or missing price are dropped; funding timestamps are rounded to the minute and duplicates keep the first.
- **Exclusions:** delivery contracts; index contracts (DEFIUSDT, BTCDOMUSDT, ALLUSDT, FOOTBALLUSDT, BLUEBIRDUSDT, DOTECOUSDT); tokenised gold (PAXGUSDT, XAUTUSDT); stablecoins (USDC, BUSD, TUSD, USDP, DAI and any USD/EUR-pegged base); USTCUSDT; any non-COIN underlying in the 2026-10-21 exchangeInfo snapshot.

## 4. Universe (rebuilt every rebalance Monday t)

A coin is eligible at t if:
1. It passes §3 (not excluded, ≥ 60 days into its current listing).
2. **Liquidity:** calendar average daily quote volume over days t−28 … t−1 (non-trading days = $0) is **≥ $2M**.
3. **Signal defined:** days t−30 and t−2 are trading days.
4. **Tradable at t:** day t is a trading day.
5. **Breadth:** n = floor(N/3) coins per side; if **n < 5** (N < 15), the week is skipped. Skipped weeks are counted and reported.

## 5. Signal and portfolio (H1)

- **Rebalance:** every Monday 00:00 UTC, non-overlapping 7-day holds.
- **Signal:** `MOM_i,t = Close_i(t−2) / Close_i(t−30) − 1` (Sunday t−1 skipped).
- **Ranking:** sort by MOM; ties broken alphabetically by symbol. Top n = long, bottom n = short (n = floor(N/3)); extra coins go to the middle.
- **Weights:** equal weight, +1/n per long, −1/n per short (gross 2, net 0).
- **BTC-neutral by construction:** BTC's return cancels exactly in `mean(r_long) − mean(r_short)`. Each leg's 60-day daily BTC beta is **reported**, not hedged.

## 6. Outcome and costs (H1)

- **Price return:** `r_i = Open_i(t+7) / Open_i(t) − 1` (daily-kline opens at 00:00 UTC).
- **Delisting during the hold:** if day t+7 is not a trading day, exit at the close of the last trading day in the hold. If none, return = 0 and the case is flagged.
- **Funding:** `F_i = Σ` funding rates of prints (on trading days, C2) with timestamp in (t, t+7d], on entry notional. Longs pay F_i, shorts receive F_i:
  `FUND_w = −mean_long(F) + mean_short(F)`.
  - **Funding gaps:** a coin-week with no funding print on a trading day gets F = 0 and is flagged; the count is reported. (The data report gives coverage.)
- **Gross spread:** `G_w = mean(r_long) − mean(r_short) + FUND_w`.
- **Costs:** 21 bps per side on actual turnover: `COST_w = 0.0021 × Σ_i |w_i,new − w_i,old|`, w_old = drifted weight at the end of the previous hold. From flat: 42 bps. Full replacement of both legs: 84 bps. Delisting exits are charged one side. Before a skipped week and at the end of the sample, positions are closed and the closing cost is charged to the last active week.
- **Net spread (primary outcome):** `NET_w = G_w − COST_w`.

## 7. Primary test (one look)

- **Sample:** rebalances **2020-01-06 to 2022-12-19** (last hold ends 2022-12-26): 155 Mondays. The breadth rule (§4.5) skips the first 13 (to 2020-03-30), so **142 weeks** are used, from 2020-04-06.
- **Test:** one-sided t-test of mean(NET_w) > 0, **Newey-West SE, 4 lags**, over non-skipped weeks.
- **Alpha 0.05.** **H1 PASS** if t_NW > 1.645. Otherwise **H1 FAIL**.

## 8. Secondary (H2): AMT value-area score

Own alpha 0.05. Cannot rescue a failed H1. Sample 2020-01 to 2022-12. Needs 5-minute klines (new user OK required).

**Daily profile (coin i, UTC day d):**
- The 288 five-minute bars of day d. Grid: 50 equal-width price bins from day low to day high.
- Each bar's quote volume is spread uniformly over the bins its [low, high] range touches.
- **POC** = bin with the most volume; **ties go lower**.
- **Value area (70%):** start at the POC; at each step add whichever adjacent bin (next above vs next below) has more volume; **ties go lower**; if one side is exhausted, add the other. Stop at ≥ 70% of the day's volume.
- **VAH** = top edge of the highest bin in the value area; **VAL** = bottom edge of the lowest.
- If the day has < 240 bars or zero volume, S is missing.

**Score S_i,d** (dH = VAH_d − VAH_{d−1}, dL = VAL_d − VAL_{d−1}):
- **+1** if dH > 0 and dL > 0 (higher value, overlapping higher).
- **−1** if dH < 0 and dL < 0 (lower value, overlapping lower).
- **0** otherwise (inside, outside, any equal edge).

**Regression:**
`r_i,d+1 = β·S_i,d + γ1·r_i,d + γ2·r7_i,d + γ3·CL_i,d + α_d + ε_i,d+1`
- r = close-to-close daily return; r7 = 7-day return to close of d; CL = (Close − Low)/(High − Low) of day d (0.5 if High = Low).
- Date fixed effects; SE two-way clustered by coin and date.
- **Test:** one-sided β > 0, alpha 0.05. **H2 PASS** if t > 1.645.
- **Universe (each day d):** coins passing §3 with day-d quote volume ≥ $3M; the top 120 by day-d quote volume.

## 9. Fake-data check (before the real look; must find nothing)

- Within each date, shuffle daily returns across coins in the universe; rebuild prices from the shuffled returns; run §4–§8 unchanged. Funding is shuffled with its coin's returns.
- 200 shuffles, fixed seed. **Pass** if the share of shuffles rejecting H1 on the **gross** spread is ≤ 9%, the mean gross spread across shuffles is within ±2 SE of 0, and the same holds for H2.
- If the check fails, the real look does not run; the bug is fixed and logged first.

## 10. Reporting rules

- Headline: **average profit per week** (mean NET_w), plus mean G_w, mean FUND_w, mean COST_w. Not win rate.
- Results **with and without the 2 best weeks** (by NET_w).
- Also: weeks used/skipped, coins per side, turnover, leg BTC betas, delisting exits, funding gaps.
- **Replication (descriptive only, NOT pass/fail):** the same rule on the 2023-2026 carry-study data (read-only copy), flagged **"already seen"**.

## 11. Power

From DATA_REPORT.md and `data/clean/power.json` (random-split spread; no signal used).

- **Weeks:** 142 used (13 skipped at the start).
- **Coins per side:** median 37; 10th percentile 8; minimum 5 (April 2020). By period: ~5–22 in 2020, 23–42 in 2021, 43–47 in 2022.
- **Weekly spread SD:** a random third-minus-third split gives σ ≈ **4.8%/week** (2020: 4.9%, 2021: 6.6%, 2022: 2.3%). A momentum sort picks the most extreme movers, so its σ is likely higher; 1.5× is used as the pessimistic case.
- **Smallest detectable mean weekly net spread** (80% power, one-sided 0.05, ×1.1 for Newey-West): 2.49 × σ × 1.1 / √142
  - σ = 4.8% → **≈ 1.1%/week**
  - σ = 7.2% → **≈ 1.7%/week**
- v0.1 (20% legs, $5M, ≥ 3 per side) was ≈ 1.8–2.7%/week, with 3–6 coins per side in 2020. The changes mainly cut noise per leg; the test is still only able to see a large effect. A FAIL does not mean momentum is zero.
- **H2:** ~120 coins × ~1,000 dates; with date FE and date clustering the effective sample is about the 1,000 dates. Detectable β roughly 10–20 bps per unit of S (rough; refined once 5m data is approved).
- **5m download size (H2, not downloaded):** 161 coins, ≈ 3,600 symbol-months in 2020–2022 × ~0.3–0.5 MB ≈ **1.1–1.8 GB zipped**. Exact size to be listed from archive file headers when the user approves the 5m step.

## 12. Process

- Order: data report → this prereg approved in chat → SHA-256 in HASHES.txt → fake-data check → one look.
- No git: each version is its own file, never overwritten; every change is a line in CHANGELOG.md.
- One look only. Anything after is exploratory and labelled so.
- Machine: below-normal priority; pause if free RAM < 0.8 GB.

---

## Appendix A — TRIALS_LEDGER entry (draft)

| # | Date | Study | Prereg | Sample | Result | Verdict |
|---|---|---|---|---|---|---|
| 2 | _(on look)_ | Cross-coin momentum, Binance USDT-M perps: top − bottom third by 28d return (skip 1d), weekly, incl. funding, net 21 bps/side × turnover | PREREG_v0.2.md, sha256 `<on freeze>` | 2020-04-06 to 2022-12-19 (first 13 Mondays skipped by breadth), `<T>` weeks, `<n>` median coins/side | Mean NET = `<x>` bps/wk, t_NW = `<t>`; without 2 best weeks `<y>` bps/wk | H1 `<PASS/FAIL>`; H2 `<PASS/FAIL>` (secondary) |

Trial #1 in the carry-study ledger (carry, H1 FAIL) is a prior trial by the same user on related data; listed so the total number of looks is visible.
