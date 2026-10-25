# PREREG v0.2 — Funding-gap study (Hyperliquid vs Binance USDT-M)

Status: DRAFT, not frozen. No PnL, funding received or price outcome has been computed.
v0.2 = v0.1 + operator rulings of 2026-10-24 (fills on 4h bars, sample from 2024-07-13, one
primary version; strict look-back; fill strictly after decision; funding on coin quantity x
latest price) and of 2026-10-26 (coin-level price check; pre-launch exclusion; verdict rules;
delayed settlements labelled by UTC hour).

## 1. Question
When the realized 24h funding on Hyperliquid and Binance differs by a lot for the same coin,
does a delta-neutral pair (long the lower-funding venue, short the higher) earn a positive net
PnL per pair after costs?

## 2. Data
- Sample: 2024-07-13 00:00 to 2026-09-30 23:59 UTC. Nothing before 2024-07-13 is used.
  This also applies to look-back windows (operator ruling): the 30-day volume window and the 24h
  funding window use only data from 2024-07-13, so the first possible entry day is 2024-08-12.
- Hyperliquid: `fundingHistory` (hourly realized rate), public `info` API, kept under 200 weight/min.
- Binance USDT-M: `fundingRate` monthly files from data.binance.vision (actual settlement time,
  interval in hours, rate), sha256-checked against each file's CHECKSUM.
- Prices: 4h bars on both venues, same open times (00/04/08/12/16/20 UTC): Hyperliquid 4h
  candles (public API serves the latest 5000, i.e. from 2024-07-13 at download time) and
  Binance 4h klines (data.binance.vision). Trade-price bars; the bar open is the fill price.
- Daily volume for the liquidity filter: Binance 1d klines (quote volume); Hyperliquid 1d candles
  (base volume x close).
- Hyperliquid's S3 archive is requester-pays (needs AWS keys) and is not used.
- Spot daily closes for the pre-launch check (section 3): Binance spot 1d files
  (data.binance.vision, sha256-checked), Bybit and Gate public candle APIs (no keys).

## 3. Universe
- Coins listed on both venues at the time, including later-delisted ones (Hyperliquid `meta`
  lists delisted perps; the Binance file listing includes delisted symbols).
- Mapping by underlying asset, not ticker. Unit multipliers: Hyperliquid `k` = 1000 units;
  Binance `1000` / `1000000` / `1M` prefixes. Alias: Hyperliquid JELLY = Binance JELLYJELLYUSDT.
- A mapping is accepted only if daily closes agree after unit adjustment (days from 2024-07-13):
  median ratio within 2% and at least 95% of overlap days within 3% (identity check, not a return).
  The check is per coin, over all overlap days (operator ruling 2026-10-26): a coin that fails is
  out for the whole sample. This excludes XPL, VINE and MEGA, the only failures that would have
  passed the liquidity filter.
- Pre-launch exclusion (operator ruling 2026-10-26): coin-days before the token had a real spot
  market (Hyperliquid pre-launch / hyperp periods) are not eligible. Hyperliquid's API has no
  history of hyperp status, so spot evidence is used: spot launch day S = the first UTC day
  (from 2024-07-13 and from the coin's first Hyperliquid day in sample) on which the token's USDT
  spot daily close on Binance (data.binance.vision), Bybit or Gate (public APIs) is within 5% of
  the Hyperliquid perp daily close (unit-adjusted). Matching on price stops a different token with
  the same ticker from counting. Days before S are not eligible; if no venue ever matches, none of
  the coin's days are eligible. OKX was not reachable from this network and is not used, so a
  token whose first spot was elsewhere may lose some early days (conservative). Code:
  scripts/p09_spot_launch_v2.py, scripts/p03_eligibility_v3.py.
- Liquidity: for decision day d, mean USD volume over days d-30..d-1 >= $5M on EACH venue.
  All 30 days must exist on both venues. Applies at entry only; an open pair is not closed
  because liquidity later drops.

## 4. Rule (the count check uses this code: scripts/p05_count_check_v4.py)
- Clock: signal checks at each UTC hour t.
- Settlement times are rounded to the nearest minute and labelled with their UTC hour. This
  includes delayed settlements (128 Hyperliquid events off the hour, e.g. 10:14); labelling them by
  UTC hour is approved (operator ruling 2026-10-26). The label is used for the signal window; the
  actual (minute-rounded) time is used for funding cash flows (section 5).
- Signal: F_v(t) = sum of venue v realized funding rates labelled t-24h .. t-1h (settled before t),
  in bps. gap(t) = F_HL(t) - F_BN(t).
- The window must be complete on both venues: the funding intervals in it sum to exactly 24h
  (24 Hyperliquid hourly events; 3/6/24 Binance events for 8h/4h/1h intervals). Otherwise no
  decision at that hour (no entry, no signal exit; the time stop still applies).
- Entry decision at t: coin passes the liquidity filter on day(t); checks t-1h and t are both
  complete with |gap| >= 25 bps and the same sign (same venue higher); no open pair on the coin;
  cooldown: check t-1h is at least 24h after the last exit fill on that coin.
- Position: long the lower-funding venue, short the higher, equal USD notional per leg.
- Entry fill: the first 4h bar open strictly after t, on both venues (delay 1-4h).
  "Strictly after" (operator ruling): a decision at 08:00 fills at 12:00, not at the 08:00 open.
  If that bar is missing on either venue the entry is skipped; a later check may still enter.
- Exit decision at each complete check t' >= T_e: |gap(t')| < 10 bps, or the sign of gap(t')
  differs from the entry sign (reversal). Exit fill: the first 4h bar open strictly after t',
  on both venues. If that bar is missing on either venue, the next bar present on both.
- Time stop: exit fill no later than T_e + 168h (7 days; a 4h boundary).
- Data end (either venue's data ends, delisting, or study end): forced exit at the last 4h bar
  present on both venues; counted and reported separately.
- One pair per coin at a time.

## 5. PnL per pair (bps of one-leg notional) — NOT YET COMPUTED
- Funding: each leg pays/receives every actual funding settlement of its own venue with
  settlement time s strictly after T_e and strictly before T_x (rounded to the minute; an event
  exactly at a fill bar open is not collected).
  Cash per event (operator ruling) = -side x Q x P_v(s) x rate, where side = +1 long / -1 short,
  Q = the leg's coin quantity = one-leg notional / P_e,v (entry fill price on venue v), and
  P_v(s) = the venue's latest available 4h-bar price at or before s: the open of the 4h bar with
  open time <= s < open time + 4h (the previous bar's close is at the same instant; the open is
  used). If that bar is missing, the close of the latest earlier bar on that venue.
  In bps of one-leg notional: -side x (P_v(s) / P_e,v) x rate x 1e4.
  (Exchanges charge funding on position size x mark price; trade-price bar opens stand in for
  mark price here.)
- Price: each leg on its own venue's 4h bar opens: long (P_x / P_e - 1), short -(P_x / P_e - 1).
  The cross-venue basis change is inside these two terms; no separate basis term (no double count).
- Costs: 84 bps per pair (4 leg fills), subtracted once.
- Net = funding + price - 84.

## 6. Tests
- Fake-data check FIRST: shuffle each coin's hourly gap series in time (random permutation,
  fixed seeds 1..20), keep real funding cash flows and prices, run the full pipeline. Pass only if
  none of the 20 shuffles reaches z >= 3.0. If it fails, stop and report; no real-data look.
- Primary: mean net PnL per pair > 0, one-sided. Weekly block bootstrap across all coins: pairs
  grouped by the UTC week (Monday 00:00) of entry fill; resample weeks with replacement,
  10,000 draws, seed 20261024; z = mean / bootstrap SE. Bar: z >= 3.0 (ledger family-level bar;
  Binance funding 2023-2026 was already seen in the carry study).
- Verdict (operator ruling 2026-10-26):
  - PASS: z >= 3.0.
  - NOT DEMONSTRATED: mean net PnL per pair > 0 but z < 3.0. This is not a pass.
  - FAIL: mean net PnL per pair <= 0.
- Always reported with the verdict: the 95% CI of the mean net PnL per pair (2.5th-97.5th
  percentiles of the same weekly block bootstrap draws), and the mean, z and 95% CI without the
  2 best pairs.
- One look. No re-tuning of thresholds (25 / 10 bps, 7 days, 24h cooldown, $5M, 84 bps, 4h fills)
  after the look.

## 7. Reporting
- Average net PnL per pair (not win rate); n pairs, n coins.
- Same without the 2 best pairs.
- Capital tied up (descriptive): pair-hours, mean and max concurrent open pairs, 2 legs each.
- Split by year and by which venue was higher (descriptive only; not tested).
- Ledger entry draft (TRIALS_LEDGER; next number #37 to be confirmed by the operator; the
  ledger lives in the research-plan repo and is not touched from this study).

## 8. Variants counted for the ledger
One primary variant (4h fills). No 1h or 8h version.

## 9. Phase 0 counts (count-only, no outcomes; reports/COUNT_CHECK_v0.1.md)
- Universe: 118 coins ever eligible (13-49 per day); 207 of 217 name matches pass the price check.
- Count check v3 (before pre-launch exclusion): 169 trades on 65 coins, 2024-08-12 .. 2026-09-30
  (~79 per year; 2024 40, 2025 95, 2026 34). Median hold 24 h (p10 4, p90 64); 1 trade hit the
  7-day cap; 2 forced exits at data end. Trades fall in 60 distinct entry weeks; busiest week 19.
- Count check v4 (pre-launch coin-days excluded, the rule tested): 165 trades on 64 coins (-4).
  The only coin losing eligible days is XMR (all 173): no Binance/Bybit/Gate USDT spot close
  matched in the sample, so the "no match -> not eligible" clause removes it.
- Price check: coin-level kept (operator ruling 2026-10-26); XPL, VINE, MEGA stay out.
