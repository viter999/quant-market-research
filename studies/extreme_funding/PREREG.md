# PREREG — Extreme-funding carry, hedged (idea #5) — v0.3

Owner: Natthaphong (Shawn) Suebsri. 29 Oct 2026. Status: v0.2 revised after review round 1 (ChatGPT, Grok, Gemini); v0.3 = pre-outcome amendment below. No outcome computed.
Time cap: ≤ 7 calendar days from approval. A feasibility stop applies on day 3.

## Amendment v0.3 — 29 Oct 2026, before any outcome: power check failed at 37 DEV trades
- Why: the EF-1 DEV count under v0.2 gave 37 trades on 24 symbols and 30 entry days, projecting to 12.3 / 8.0 / 10.0 on VERDICT (× 200/602) against the required 60 / 15 / 30. No price, return or P&L had been computed on any segment. Decided by Shawn.
- §2: the cap is 10 open positions (was 5); same ordering by highest h_S at the same S.
- §4: the "top 80 by 7-day perp quote volume" universe is replaced by: perp 24h quote volume ≥ $20M at S, from its 1m bars in [S−24h, S). The frozen EXCLUSIONS and the spot rules (pair present; spot 24h quote volume ≥ $5M; median spot 1-min quote volume ≥ $50,000) are unchanged.
- §6: no change to the statistics, PASS items or seeds; the power check is re-run under the amended §2/§4.
- Everything else is unchanged: the threshold, OI +5 % in contracts, exits, execution, costs, splits, PASS items and seeds.

## 0. What is different from what already failed (read first)
- The carry study (Oct 2026) held coins UNHEDGED for weeks and died on price direction.
- The funding-unwind test (31 Aug) found that price drifts WITH the funding sign after settlement. We have both seen this; it is disclosed here.
- This test is HEDGED: long spot and short perp, in equal BASE quantity. Profit comes only from funding received plus any change in the perp-minus-spot gap, minus costs on 4 legs. It is not a directional indicator, so the 31 Aug stopping rule does not apply. Shawn confirms this reading at gate (a).
- All legs are taker. No maker fills are assumed, because archive data cannot model them honestly.

## 1. Hypothesis (one primary test)
H1: On Binance USDT-M perps that have a liquid Binance spot USDT pair, opening long-spot / short-perp right after a settlement with extreme positive funding and rising open interest earns a positive mean net return over the hold, after all costs.

## 2. Signal (everything known at settlement time S)
- f_S is the funding rate settled at S, exactly as in the archive. I_S is the interval in hours that ended at S (S minus the previous fundingTime). h_S = f_S / I_S is the funding earned per hour. No 8h extrapolation is used.
- Skip the event if I_S differs from the interval before it (an interval change at S is ambiguous), and count these skips.
- Entry condition, all required:
  - h_S ≥ 0.0125% per hour (equal to 0.10% per 8h);
  - OI in contracts (from metrics `sum_open_interest`, the last 5-min row timestamped ≤ S − 5 min) is ≥ 5% above the same field 24h earlier;
  - the symbol is in the universe (§4) at S;
  - fewer than 10 positions are open (cap; v0.3, was 5). If several signals arrive at the same S, take them in order of highest h_S;
  - no position is already open in that symbol.
- Positive funding only.

## 3. Execution, accounting and costs
- Prices are conservative worst-of-bar, using the first full 1m bar after S ([S+1m, S+2m)) for both legs:
  - spot BUY at max(open, close) of the spot bar;
  - perp SELL at min(open, close) of the perp bar.
- Exit: at the first later settlement S_k where h_{S_k} < 0.00375% per hour (equal to 0.03% per 8h), or the first settlement on or after entry + 7 days. Prices come from the bar [S_k+1m, S_k+2m): spot SELL at min(open, close) and perp BUY at max(open, close). S_k's funding is received, because the position is open at S_k.
- Quantity: Q = 500 / spot entry price, the same Q on both legs (exact base hedge, no rebalancing).
- P&L in USDT:
  - spot leg Q·(spot_exit − spot_entry);
  - plus perp leg Q·(perp_entry − perp_exit);
  - plus funding: the sum over settlements S_j in (entry, exit] of f_{S_j} · Q · perp_close at S_j (the perp 1m close used as the mark-price proxy);
  - minus fees: spot taker 10 bps on each spot trade, perp taker 5 bps on each perp trade, each charged on that trade's notional;
  - minus a slippage buffer of 5 bps per leg-trade on its notional at 1×, 10 at 2×, 25 at 5×.
- Return is reported in bps of the $500 spot notional (primary) and of the $1,000 of capital used.
- If spot or perp data ends before the exit (delisting), close both legs at the last common minute using worst-of-bar prices plus the 5× buffer, and count it.

## 4. Universe and data
- Universe (v0.3): at S the perp's 24h quote volume, summed from its 1m bars in [S−24h, S), is ≥ $20M (point-in-time, data before S only). The frozen crash-absorption EXCLUSIONS still apply (prefixes 1000/1M, stablecoins, tokenized metals and equities, index contracts, and the other v1.0 entries). The former "top 80 by 7-day perp quote volume" rule is dropped.
- In addition, at S: a Binance spot `<BASE>USDT` pair with 1m klines in the 24h before S; spot 24h quote volume ≥ $5M; and median spot 1-min quote volume over the prior 24h ≥ $50,000. Spot availability is judged only with data up to S.
- Pipeline:
  - Scan the fundingRate monthly files first (tiny) to list candidate (symbol, S) pairs.
  - Then fetch only the needed slices: perp and spot 1m klines from S−24h to S+7d+1h, and metrics for S−24h to S.
  - Perp 1m klines already downloaded for DEV/VERDICT are reused.

## 5. Date split (reuses crash-absorption SPLITS.json)
- DEV 2024-01-01 → 2025-08-24: plumbing, counts, the power check. No returns.
- VERDICT 2025-08-26 → 2026-03-13: run once.
- HOLDOUT 2026-03-15 → 2026-09-30: not downloaded until the VERDICT result is committed; run only after a PASS and Shawn's OK.
- A trade belongs to its entry's segment. Entries are allowed only up to 7 days + 1 day before the segment end, so a trade never reads data past its segment. Excluded entries are counted.

## 6. Statistics and verdict (fixed now)
- Unit: the trade.
- Bootstrap: resample entry days in 1-day blocks and 7-day blocks, 10,000 replicates, seed 20261102, percentile bounds.
- Report: the maximum concurrent positions, and the P&L split into funding / gap change / fees / buffer.
- Power check on DEV (counts only): if the projected VERDICT trades are < 60, or the symbols are < 15, stop and ask Shawn.
- PASS on VERDICT only if ALL of these hold:
  1. ≥ 60 trades on ≥ 15 symbols and ≥ 30 distinct entry days (otherwise NOT EVALUABLE);
  2. mean net per trade at 1× ≥ +25 bps (spot-notional basis), with the one-sided 99% lower bound > 0 under BOTH block sizes;
  3. mean net per trade at 2× > 0;
  4. median net per trade at 1× > 0;
  5. still > 0 at 1× after removing the 3 symbols with the largest total net P&L.
- HOLDOUT confirm: mean net at 1× ≥ +15 bps with the 95% lower bound > 0 (1-day blocks).
- Otherwise KILL. Published either way. No re-fit.

## 7. Descriptive only (EXPLORATORY)
- The funding-only rule without the OI condition (rule 8: beat the simple version).
- Fixed holds of 8h, 24h and 72h.
- Thresholds 0.05% and 0.20% per 8h-equivalent hour rate.
- No cap on concurrent positions.
- Close-price execution and high/low worst-case execution.
- The unhedged short-perp leg alone.
- Calm vs wild BTC; time in trade; max adverse gap move; skipped interval-change events.

## 8. Known limits
- 1m bars are not executions. Worst-of-bar pricing plus the buffer is the guard, and the high/low stress is reported.
- Wallet transfers, margin, borrowing and Binance funding caps are not modelled beyond what is in the data.
- A PASS leads only to a small live paper test; it is not a trading green light.

## 9. Gates (Shawn)
(a) this plan, including the 31 Aug reading; (b) the VERDICT run; (c) the HOLDOUT download; (d) any change to §2–§6.
