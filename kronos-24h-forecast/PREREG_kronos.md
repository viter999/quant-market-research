# PREREG — Kronos-small next-24h direction on Binance USDT-M perps

Status: **DRAFT, awaiting owner OK.** Nothing has been computed on the test window. No forecast has
been run on market data and no test-window price, volume or return has been read (the universe
completeness check below read the timestamp column only).

Written 2026-10-18. One look. After the owner's OK this file is frozen with SHA-256 (see §9).

---

## 1. Question

Does Kronos-small's next-24h direction forecast on Binance USDT-M perpetuals beat random after fees?

## 2. Pinned software and weights

| Item | Pin | Evidence |
|---|---|---|
| Kronos code | `shiyu-coder/Kronos` commit `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (master HEAD, 2026-04-13T12:38:49Z) | GitHub API; archive SHA-256 `5ef8e3d0…7b07b9d` (see `INSTALL_LOG.md`) |
| Model | HF `NeoQuasar/Kronos-small` revision `901c26c1332695a2a8f243eb2f37243a37bea320` | `model.safetensors` SHA-256 `b082dfcbd8e8c142a725c8bbb99781802f38fec81210e13479effb32b3c3e020` |
| Tokenizer | HF `NeoQuasar/Kronos-Tokenizer-base` revision `0e0117387f39004a9016484a186a908917e22426` | `model.safetensors` SHA-256 `59d85f6af76a2c3b8240ea06cb21db4213b4eeca053f246b23e29cf832fc6bee` |
| Runtime | Python 3.11.9, torch 2.14.1+cpu, numpy 2.4.6, pandas 2.2.2, scipy 1.17.1 | `logs\pip_freeze.txt` |
| Hardware | AMD Ryzen 5 5625U (6C/12T), 7.4 GB RAM, CPU only, `torch.set_num_threads(6)` | — |

## 3. Dates and test window (cite it or drop it)

**(a) Kronos-small weights published on Hugging Face: 2025-06-30T16:44:37Z.**
Source: HF commit history of `NeoQuasar/Kronos-small` (https://huggingface.co/api/models/NeoQuasar/Kronos-small/commits/main).
`model.safetensors` first appears in commit `ac5c409a313c4eadd1ca78201322f5cadb9c34ab` ("add model", 2025-06-30T16:44:37Z).
I checked the file at every later commit (`23958ab`, `ce3ddfa`, `12b7990`, `901c26c`): same LFS hash `b082dfcb…`, so the weights
never changed; the later commits only edit the README. The tokenizer weights were added the same day
(commit `9ef143b98ee3c2488eebd85404e0c215c112b46a`, 2025-06-30T17:04:10Z) and also never changed.

**(b) Training-data end date: June 2024.**
Source: Shi et al., *Kronos: A Foundation Model for the Language of Financial Markets*, arXiv:2508.02739v1
(submitted 2025-08-02), Appendix D "Task Implementation Details", "Forecasting Task Setup":
"The pre-training data for Kronos extends up to June 2024." (checked word for word in the arXiv HTML;
saved copy `downloads\paper\arxiv_2508.02739v1.html`, SHA-256 `5140e49f…251889feb`).
The HF model cards at the pinned revisions state no training-data date. No start date is given anywhere.

**Test window.** The later date is (a), 2025-06-30 16:44 UTC. The first 00:00 UTC day after it is
**2025-07-01**. Forecast days D = **2025-07-01 … 2026-09-30 inclusive = 457 days.** The last forecast
(D = 2026-09-30 00:00) is settled with the bar that opens 2026-09-30 23:00 and closes 2026-10-01 00:00,
so every price used lies inside the window.

## 4. Universe (frozen)

**Rule.** Rank every Binance USDT-margined perpetual (symbol ends in `USDT`, no `_` delivery suffix)
by total quote volume (kline column `quote_asset_volume`) over the 30 days before the test window,
**2025-06-01 00:00 → 2025-06-30 23:59 UTC**, from public 1d monthly klines
(`data/futures/um/monthly/klines/<SYM>/1d/<SYM>-1d-2025-06.zip`). The symbol list comes from the
data.binance.vision bucket listing, so coins delisted since are included in the ranking (900 USDT
perp folders, 484 with June 2025 data).
Exclude stablecoin bases (USDC, FDUSD, TUSD, BUSD, USDP, DAI, USDE, USD1, RLUSD, PYUSD, USDS, EURI,
AEUR, FRAX, LUSD, GUSD, USDD, SUSD, BFUSD, XUSD) and metals (XAU, XAUT, XAG, PAXG). Walk down the
ranking and keep the first 30 symbols whose 1h klines are complete, with no gaps or duplicates, from
**2025-06-09 16:00 UTC** (512 bars of warm-up before 2025-07-01 00:00) to **2026-09-30 23:00 UTC**,
i.e. 11,480 consecutive hourly bars. The completeness check read only the `open_time` column.

**Result.** Rejected while filling: RESOLVUSDT (rank 25, listed in June 2025, 21 warm-up bars missing)
and SAHARAUSDT (rank 29, listed late June 2025, 404 bars missing). No candidate was rejected for a
delisting or a data gap. The excluded pairs ranked far below the cut (PAXG 87th, USDC 294th).

| # | Symbol | June-2025 rank | June-2025 quote volume (USDT m) |
|---|---|---|---|
| 1 | BTCUSDT | 1 | 472,261 |
| 2 | ETHUSDT | 2 | 448,075 |
| 3 | SOLUSDT | 3 | 97,538 |
| 4 | 1000PEPEUSDT | 4 | 36,643 |
| 5 | XRPUSDT | 5 | 36,479 |
| 6 | DOGEUSDT | 6 | 27,801 |
| 7 | SUIUSDT | 7 | 19,473 |
| 8 | FARTCOINUSDT | 8 | 17,656 |
| 9 | WIFUSDT | 9 | 11,010 |
| 10 | AAVEUSDT | 10 | 10,743 |
| 11 | HYPEUSDT | 11 | 10,724 |
| 12 | ADAUSDT | 12 | 10,511 |
| 13 | FUNUSDT | 13 | 10,312 |
| 14 | UNIUSDT | 14 | 9,893 |
| 15 | ENAUSDT | 15 | 9,102 |
| 16 | TRUMPUSDT | 16 | 8,885 |
| 17 | BNBUSDT | 17 | 8,374 |
| 18 | LINKUSDT | 18 | 7,618 |
| 19 | MASKUSDT | 19 | 7,447 |
| 20 | BCHUSDT | 20 | 7,157 |
| 21 | AVAXUSDT | 21 | 7,055 |
| 22 | VIRTUALUSDT | 22 | 6,287 |
| 23 | RVNUSDT | 23 | 6,285 |
| 24 | LPTUSDT | 24 | 6,194 |
| 25 | SEIUSDT | 26 | 5,647 |
| 26 | TRBUSDT | 27 | 5,441 |
| 27 | ANIMEUSDT | 28 | 5,250 |
| 28 | OPUSDT | 30 | 4,610 |
| 29 | LTCUSDT | 31 | 4,528 |
| 30 | MOODENGUSDT | 32 | 4,509 |

Machine-readable copies: `data\universe\universe_frozen.json` (SHA-256 `30404eaeaabf7798aa4465835b9c1d438aacac4f6f5bd6f44e0d4ad56ced6d0a`),
full ranking `data\universe\ranking_2025-06_quote_volume.csv` (SHA-256 `d2319cae76b10f43a6fd4e9bb9c0a96930fcfff6c79e7dfc7fc4cb03bde3c02c`).
Coin index `i` = 0…29 in the order above (BTCUSDT = 0).

## 5. Data

Binance public 1h klines, USDT-M futures, monthly files
`https://data.binance.vision/data/futures/um/monthly/klines/<SYM>/1h/<SYM>-1h-<YYYY-MM>.zip`, 2025-06 … 2026-09.
Every zip is checked against Binance's `.CHECKSUM` (SHA-256); a mismatch stops the run. No API keys,
no login. Timestamps are kline `open_time` in UTC. Bar with open_time t covers [t, t+1h).
Kronos inputs: `open, high, low, close, volume` (base volume) and `amount` = quote asset volume.

## 6. Forecast

For each forecast day D (00:00 UTC) and each coin i:

- Context: the 512 bars with open_time D−512h … D−1h (exactly 512 rows, no NaN, else the run stops).
  `x_timestamp` = their open_times; `y_timestamp` = D, D+1h, …, D+23h.
  The forecast code is never given any bar with open_time ≥ D.
- Last close `c0` = close of the bar with open_time D−1h (the price at D 00:00).
- Model call: `KronosPredictor(model, tokenizer, device="cpu", max_context=512).predict(...)` with
  `pred_len=24, T=1.0, top_p=0.9, top_k=0, sample_count=10, clip=5` (defaults otherwise).
  Kronos draws the 10 sample paths and returns their mean internally (`np.mean(preds, axis=1)` in
  `auto_regressive_inference`; the de-normalisation after it is linear, so this is the mean predicted
  path).
- Seed: immediately before each call, `torch.manual_seed(s)` and `np.random.seed(s % 2**32)` with
  `s = int(D as YYYYMMDD) * 100 + i` (e.g. 2025-07-01, ETHUSDT → 202507010001). One coin per call,
  so every forecast is reproducible on its own and a resumed run gives the same numbers.
  Verified on synthetic data: the same seed gives bit-identical output.
- Prediction `p24` = mean predicted close of the 24th predicted bar (open_time D+23h, i.e. the close at D+24h).
- **Signal `s = sign(p24 − c0)` ∈ {−1, 0, +1}. `s = 0` means no trade.**

## 7. Outcome and tests

- `r = close(bar D+23h) / c0 − 1` (close at D+24h over close at D).
- Fee `f = 0.0010` (0.10%) per coin-day with `s ≠ 0`: one round trip, opened at D 00:00 and closed at
  D+24h, charged every day even if the direction repeats. No fee when `s = 0`. Funding is not modelled.

**PRIMARY.** Daily series `P_D = (1/30) Σ_i ( s_i·r_i − f·|s_i| )` (coins with s = 0 count as 0 and stay in the denominator).
One-sided one-sample t-test, H1: mean(P) > 0, `scipy.stats.ttest_1samp(P, 0, alternative="greater")`, n = 457.
Passes iff p < 0.05.

**SECONDARY (must also pass).** BTC-relative, gross:
`S_D = (1/29) Σ_{i ≠ BTC} s_i·( r_i − r_BTC,D )`. Same one-sided t-test on S. Passes iff p < 0.05.

**REPORT ONLY (not part of the decision):**
- Hit rate: share of coin-days with s ≠ 0 and r ≠ 0 where sign(s) = sign(r), all 30 coins.
- Always-long net: daily mean across the 30 coins of `(r − f)`; mean, t-stat.
- Random-sign null, 10,000 runs: each run draws s ∈ {−1, +1} with p = ½, independently per coin-day,
  with `numpy.random.default_rng(20250701)`, and recomputes mean(P) and mean(S). Reported: the share
  of runs at or above the Kronos value, and the 95th percentile.
- Per-month table (calendar months, UTC): days, mean P, mean S, hit rate, mean always-long net.
- Counts of s = +1 / −1 / 0.

## 8. Decision

**PASS** only if PRIMARY and SECONDARY both pass. PASS means a written follow-up plan, never trading.
Otherwise **DROP** Kronos.

**ONE LOOK.** No reruns with another model size, temperature, top_p, sample count, horizon, fee,
universe, window or seed after seeing any result. The analysis runs once, after all 13,710 forecasts
(457 × 30) exist.

## 9. Execution protocol (Step 4, only after the owner's OK)

1. **Freeze.** Write `scripts\run_forecasts.py` and `scripts\analyze.py` to this spec, then record
   SHA-256 of this file, both scripts, `scripts\kt_common.py`, `scripts\kt_binance.py`, and the two
   universe files in `FREEZE_kronos.sha256`. Nothing on the test window runs before this.
2. **Plumbing check** on 3 pre-window days (D = 2025-06-28, 06-29, 06-30), all 30 coins, written to
   `results\plumbing\` (never mixed with test results). Checks only: context shape (512, 6), timestamps,
   no NaN, output shape (24, 6), seed reproducibility (one forecast repeated), resume after a forced
   stop gives no duplicates, seconds per forecast. No returns, no hit rates, no outcome statistics.
   Any coin without 512 pre-window bars on a plumbing day is skipped in the plumbing check only.
   If the check finds a bug, the fix is logged in `AMENDMENTS_kronos.md` with new hashes before the
   first test-window forecast. Bug fixes only; no design change.
3. **Full run.** `run_forecasts.py` writes one row per (D, coin) to `results\forecasts.csv`
   (D, symbol, seed, c0, p24, s, and the 24 predicted closes), flushed and fsynced after every row.
   On restart it skips rows already present, so a crash or sleep loses at most one forecast.
   The forecast script does not compute outcomes. It runs at below-normal Windows priority, asks
   Windows not to idle-sleep while it runs (per-process request, no settings changed), and pauses
   while the laptop is on battery. No restart is part of the run.
4. **One look.** `analyze.py` runs once on the complete file, writes `results\REPORT_kronos.md`,
   and the project stops.

**Run time.** Measured on synthetic data with these settings: about 52–55 s per forecast on 6 threads
(12 threads and multi-coin batching were not faster). 13,710 forecasts ≈ 200–210 hours ≈ **8½–9 days**
of uninterrupted compute, longer if the laptop is in use (below-normal priority yields to you).

## 10. Known limitations (stated before results)

1. **Survivor condition.** The universe rule needs full data through 2026-09-30, so a coin delisted in
   the window could not be chosen. In practice no candidate was rejected for that; only two were
   rejected for listing too late for the warm-up.
2. **Costs.** 0.10% per round trip only; no funding, no slippage, no spread beyond it.
3. **Serial correlation** in the daily series is not corrected (plain t-test, as specified). Coins
   are averaged within each day first, so cross-coin correlation does not inflate n.
4. **Bit-exact reproducibility** holds on this machine with 6 threads; other CPUs or thread counts may
   differ in the last digits and, rarely, flip a sign.
5. **Training data.** The paper gives only "up to June 2024" and no data list. The window starts after
   the weights were public, which bounds any overlap regardless.
6. **Context = max_context = 512**, so as Kronos generates, the oldest context tokens slide out of its
   window. That is how the pinned code works; it is not modified.
7. **Timestamp convention.** Kronos's time features are fed the bar open_time (UTC). Fixed here, not tuned.
