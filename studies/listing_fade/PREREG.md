# PREREG — New Binance perp listing fade — v0.2

Owner: Natthaphong (Shawn) Suebsri. 29 Oct 2026. Status: revised after review round 1 (ChatGPT, Grok). Nothing run. Shawn approved directing this test.
Time cap: ≤ 7 calendar days.

## 0. Why this is allowed
- The 6 Sep §13 rule says a new direction test needs a participant with a contractual or scheduled clock.
- Here the clock is the scheduled launch time Binance announces. Early demand, airdrop and unlock holders, and market makers' inventory all meet at that fixed time.
- Proposed independently by ChatGPT, Gemini and Grok on 29 Oct 2026. Not in the log: earlier studies never looked at the first days of a new contract.

## 1. Events
- Source: Binance announcements, "New Cryptocurrency Listing" catalog (48). Titles matching "Futures Will Launch", with all raw bodies saved with sha256 BEFORE any price data.
- Each event is (symbol, A = announcement time, L = launch time stated in the body). T0 = the first actual aggTrade at or after L. All times below count from T0, not from L.
- USDT-margined perps only. Exclude anything in the frozen crash-absorption EXCLUSIONS families (stablecoins, metals, equities, indexes); 1000-prefix symbols are allowed, because returns don't depend on scale.
- Pre-market launches are flagged and kept.
- Several symbols launched in the same article = one episode. Inference is clustered by launch DAY (§4).
- The universe is built from the announcements FIRST. Every announced USDT-perp launch is a row; each exclusion is reported by reason, and the excluded rows are shown in a sensitivity table.
- Exclude:
  - no aggTrades within 24h of L (never traded);
  - perp quote volume in [T0, T0+1h] < $5M (too thin for fair fills);
  - a funding record missing for any settlement in the hold (unscorable, never treated as zero);
  - a delisting announced before T0+72h.

## 2. Trade (one primary rule)
- SHORT $500 notional.
- Entry: at T0+60m, sell as taker. Price = the VWAP of seller-initiated aggTrades (is_buyer_maker = true, i.e. at the bid) in [T0+60m, T0+61m). If there are none, use the next 1 minute; if still none, drop the event and count it.
- Exit: at T0+72h, buy as taker. Price = the VWAP of buyer-initiated aggTrades (at the ask) in [T0+72h, T0+72h+1m), with the same fallback.
- $500 is far below the launch leverage and position caps. Leverage ≤ 2× is assumed.
- Costs:
  - taker 5 bps per side;
  - slippage buffer 15 bps per side at 1×, 30 at 2×, 75 at 5×;
  - signed funding over settlements in (entry, exit] (a short receives positive rates, pays negative ones), from the archive fundingRate files;
  - funding on new contracts can be extreme, so the full funding path is reported, plus a stress run with every settlement set to its 95th-percentile adverse value (descriptive).
- No stop-loss in the primary rule. A stop on a 1m tape is not honestly fillable; the squeeze risk shows in the max adverse move, which is reported.
- BTC-relative net = net + BTC return over the same window.

## 3. Sample
- TEST: L from 2024-01-01 to 2026-03-05, so that L+73h ≤ 2026-03-13 (the archive guard).
- No tunable parameters, so no development set.
- HOLDOUT: L from 2026-03-15 to 2026-09-27. Prices are not downloaded until the TEST result is committed; it is run once after a PASS.

## 4. Verdict (fixed now)
- Unit: the episode (the mean of its symbols).
- Bootstrap: 10,000 replicates, seed 20261104, resampling 7-day blocks of launch days (primary, because catalysts cluster) and single launch days (also required).
- PASS on TEST only if ALL of these hold:
  1. ≥ 120 episodes on ≥ 70 distinct launch days (otherwise NOT EVALUABLE);
  2. mean net per episode at 1× ≥ +100 bps, with the one-sided 99% lower bound > 0 under 1-day AND 7-day blocks;
  3. mean net at 2× > 0;
  4. median episode net at 1× > 0;
  5. BTC-relative mean net at 1× > 0;
  6. still > 0 at 1× after removing the 5 best episodes.
- A significantly negative mean (99% upper bound < 0) is recorded as "the long side deserves its own prereg". It is NOT a pass.
- HOLDOUT confirm: mean net at 1× > 0 with a 95% lower bound > 0.
- Otherwise KILL. Published either way. No re-fit.

## 5. Descriptive only (EXPLORATORY)
- Entry at L+5m and L+24h.
- Holds of 4h, 24h and 7d.
- The long mirror.
- Pre-market vs regular launches.
- Results by year.
- The funding share of P&L.
- Max adverse move (squeeze risk).
- A 20% hard stop variant (fill at the first ask-side trade past the stop).
- All announced launches, including the liquidity exclusions (worst-case sensitivity).
- Whether the token already had a Binance spot pair at L.

## 6. Known limits
- 1m bars are not fills. Entry at L+60m avoids the launch-minute chaos; worst-of-bar pricing plus a buffer is the guard.
- Borrow and short limits on new contracts (Binance caps leverage and position size at launch) are not modelled; $500 is far below the caps.
- Survivorship: delisted contracts stay in the archive and are included.
- Airdrop and unlock timing can't be checked (no free unlock data). This limit is stated in the result.
