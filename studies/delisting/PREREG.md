# PREREG — Binance perp delisting drift — v0.2

Owner: Natthaphong (Shawn) Suebsri. 29 Oct 2026. Status: revised after review round 1 (ChatGPT, Grok; Gemini timed out). Nothing run. Shawn approved directing this test.
Time cap: ≤ 5 calendar days.

## 0. Why this test is allowed
- The 6 Sep §13 rule says any new direction test must name a participant with a CONTRACTUAL CLOCK (liquidation, settlement or delisting). This one does.
- After Binance announces a perp delisting, every holder must close by a fixed time. Binance settles all open positions at D, and no new orders are allowed from D − 1h.
- The direction is genuinely open. Forced selling by longs predicts a fall. Squeezes on thin books before settlement ("delisting pumps") predict a rise.

## 1. Events (public, collected 29 Oct 2026)
- Source: Binance announcements, Delisting catalog (161). Selected articles have titles matching "Futures Will Delist" or "Perpetual Contract". All titles and raw bodies are saved, with fetch time and sha256.
- Each event is (symbol, A, D, N):
  - A = the article release time (UTC);
  - D = the settlement time stated in the body;
  - N = the "no new orders" time stated in the body (D − 1h if not stated);
  - only USDT-margined perps.
- Episode: all symbols in one article form one episode.
- Exclude a symbol if:
  - there are no perp 1m klines on Binance in the 24h before A;
  - its perp 24h quote volume before A is < $5M (thin books);
  - D − A < 12h;
  - or the timestamp can't be verified: the largest 1m quote volume in [A−30m, A+30m] is less than 3× the median 1m volume of the 24h before A. This uses volume only, never price direction.
  Report every exclusion by reason.
- The full event list (all selected articles, parsed symbols, A, D, N, and any restriction text such as leverage or position limits) is committed BEFORE any price data is downloaded.

## 2. Trade (one primary rule)
- SHORT the perp, $500 notional.
- Entry: the bar [A+30m, A+31m), selling at min(open, close) of that bar. The 30-minute delay covers reading the news and placing the order.
- Exit: the bar [N−30m, N−29m), buying at max(open, close) of that bar, well before the no-new-orders time.
- Costs:
  - taker 5 bps per side;
  - slippage buffer 25 bps per side at 1×, 50 at 2×, 125 at 5× (these are thin coins);
  - funding is signed: a short receives positive rates and pays negative ones, summed over settlements in (entry, exit] from the archive fundingRate files.
- Net per event = (entry − exit)/entry − fees − buffer + funding received.
- Episode return = the mean of its events.
- BTC-relative version: subtract BTCUSDT's return over the same window (descriptive and PASS item 5).

## 3. Sample
- TEST: events with A from 2022-02-17 to 2026-03-13. There are no tunable parameters, so no development set is needed. No outcome on any delisting has been computed in earlier studies.
- HOLDOUT: events with A from 2026-03-15 to 2026-09-30. Prices are not downloaded until the TEST result is committed. It is run once after a PASS.

## 4. Verdict (fixed now)
- Unit: the episode. Bootstrap resamples episodes, 10,000 replicates, seed 20261103, percentile bounds.
- PASS on TEST only if ALL hold:
  1. ≥ 30 episodes and ≥ 40 symbol-events (otherwise NOT EVALUABLE);
  2. mean net per episode at 1× ≥ +100 bps, with the one-sided 99% lower bound > 0;
  3. mean net at 2× > 0;
  4. median episode net at 1× > 0;
  5. BTC-relative mean net at 1× > 0;
  6. still > 0 at 1× after removing the 3 best episodes.
- If the mean is significantly NEGATIVE (the 99% upper bound < 0), this is recorded as "the opposite direction (long) deserves its own prereg". It is NOT a pass.
- HOLDOUT confirm: mean net at 1× > 0 with a 90% lower bound > 0 (fewer events).
- Otherwise KILL. Published either way. No re-fit.

## 5. Descriptive only (EXPLORATORY)
- The immediate reaction A → A+15m (not tradeable).
- Entry at A+15m and A+60m.
- Bar-extreme pricing (short at the bar low, cover at the bar high) as a stress test.
- Articles that mention extra restrictions (leverage or position limits) vs the rest.
- Exit at D − 24h.
- The long-side mirror.
- Results by year.
- Spot-delisting vs futures-only cases.
- The funding share of P&L.
- Max adverse move during the hold (squeeze risk).

## 6. Known limits
- 1m bars are not fills; worst-of-bar prices plus a large buffer are the guard.
- Binance may also restrict leverage or position size near delisting; that is not modelled.
- Small sample: this test can only detect large effects.

## 7. Gates
Shawn has pre-approved directing this test. Changes to §1–§4 after any outcome is seen are forbidden.
