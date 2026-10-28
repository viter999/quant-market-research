# PREREG — Crash absorption with resting limit orders (idea #1) — v0.3 (final draft for approval)

Owner: Natthaphong (Shawn) Suebsri. 29 Oct 2026. Status: revised after two review rounds (round 1: ChatGPT, Gemini, Grok, DeepSeek, Perplexity; round 2: ChatGPT, Grok, Perplexity). Nothing run.
Scope note: this is a trade-level FILL-PROXY study. Without order-book replay, queue position is approximated conservatively (§5). A PASS therefore leads only to a live paper test that measures real fills; it is never treated as proof of a tradable edge.
Time cap: ≤ 14 calendar days from approval; any extension needs Shawn's OK.

## 0. Why this test, and the 31 Aug stopping rule
The 31 Aug rule (PREREG_basis_dislocation §0) closed the directional perp-microstructure family. This test is an explicit override by Shawn's decision of 29 Oct 2026, on one ground: the execution is different. Entry is a resting limit placed deep inside a crash; whether it fills is part of the outcome. The question is whether liquidity provision into forced selling is paid after realistic fills and exits. Background (7 Sep): limit entries on old signals saved ~2.5 bps and missed 48% of entries, so "same signal, maker entry" is NOT what is tested.

## 1. Hypothesis (one primary test)
H1: On Binance USDT-M perps, after a crash bar (§4), a buy limit at L = close × (1 − 0.5%), filled under the trade-level rule of §5, earns a positive mean return from fill to fill+15 min, net of realistic costs (§6), and more than matched placebo orders (§7).
Everything else (depths 0.25%/1.0%, 30/60-min exits, maker take-profit, pump mirror, regime splits, BTC-relative) is DESCRIPTIVE ONLY, labelled exploratory, no p-values.

## 2. Data
- Detection: Binance public archive (data.binance.vision), USD-M 1-minute klines, all symbols including delisted.
- Fills and exits: aggTrades daily files, downloaded only for symbol-days that contain an event or a placebo order (every VERDICT event, not a sample).
- Universe, point-in-time: the 80 USDT perps with the highest mean daily quote volume over the 7 full days before the event day (computed from klines up to the previous day's close). Exclude stablecoin pairs, tokenized equities/metals, and the 1000-prefix family. Listing date and symbol identity taken from the archive; symbols that were renamed or relisted are treated as separate contracts.
- Funding: added to the trade if a funding settlement falls inside the holding window (rate from the archive).

## 3. Date split (holdout physically not downloaded)
- Period 2024-01-01 → 2026-09-30. DEV = first 60% of dates; VERDICT = next 20%; HOLDOUT = last 20%; 1-day embargo at each boundary.
- DEV: plumbing, event counts, fill rates and power projection only. No return or outcome statistic is computed on DEV.
- VERDICT: run once with frozen code (commit hash recorded before the run).
- HOLDOUT: not downloaded until the VERDICT result is committed; run once, only after a PASS and Shawn's approval.

## 4. Event rule (inputs known at bar close)
- Crash bar t on symbol s: 1-min return ≤ −max(4·σ_t, 1.0%), σ_t = std of the previous 240 one-minute returns (bar t excluded), AND bar quote volume ≥ 5× the median of the previous 240 bars.
- Cooldown: one event per symbol per 30 minutes.
- Episodes: events on any symbols that start within 30 minutes of each other form one episode.

## 5. Fill rule (trade level, all VERDICT events)
- Order size: $500 notional. Order goes live 2 seconds after the close of bar t (latency); cancelled 5 minutes after going live. Trades are replayed in timestamp order.
- Gap case: if the first trade after going live is at or below L, the order would have been marketable → TAKER fill, entry price = that trade's price × (1 + 5 bps), taker fee. Gap fills are also reported separately.
- Maker fill (primary, conservative queue proxy): otherwise filled at L only when the cumulative quantity traded at prices STRICTLY below L, after going live, reaches 20× the order quantity. Fill time = moment that threshold is reached. 5× and 10× are reported as descriptive sensitivities.
- Latency sensitivity (descriptive): 5 s and 10 s.
- Unfilled orders are recorded; fill rate is reported, and per-order results (non-fills count as 0) are reported alongside per-fill results.

## 6. Exit and costs
- Exit time T = fill time + 15 minutes, as a taker sell. Exit price = the LOWER of (a) the VWAP of seller-initiated trades (is_buyer_maker = true, i.e. at the bid) in [T, T+10 s] and (b) the last seller-initiated trade at or before T. If neither exists within 60 s before T, the event is dropped and counted (a high drop count is reported).
- Fees: maker entry 2.0 bps (taker 5.0 bps in the gap case); taker exit 5.0 bps. Extra slippage buffer applied once per round trip: 5 bps at 1×, 10 bps at 2×, 25 bps at 5×. Funding added when a settlement (Binance funding timestamps from the archive) falls inside the hold.
- Net return per fill = (exit − entry)/entry − fees − buffer − funding paid. Gross and net both reported.

## 7. Placebo control (B1) and other baselines
- For each event: 5 placebo orders on the same symbol, drawn within ±3 days of the event, at times with no event within ±120 minutes, same hour of day (±1 h), pre-window σ within ±25% and pre-window 60-min quote volume within ±50% of the event's, same depth relative to the then-current close, same fill and exit rules. Random seed and draws frozen in the prereg commit.
- B2 (descriptive): taker buy at the crash-bar close, same exit.
- Fill-rule sanity check: on 50 DEV events, the trade-level fill decision is compared against the kline low; disagreements listed (descriptive, no outcome).

## 8. Statistics and verdict (fixed now)
- Bootstrap: resample whole UTC days with replacement (block = 1 day), 10,000 replicates, percentile bounds, seed fixed. Sensitivity: 7-day blocks. Episodes (events within 30 min across symbols) are reported; rows are never counted as independent.
- Power check before VERDICT: from DEV fill rates only (no DEV outcomes), project VERDICT fills. If the projection is < 300 fills, < 100 episodes or < 40 days, stop and ask Shawn BEFORE any outcome is computed.
- PASS on VERDICT if ALL hold (primary: d = 0.5%, 20× queue, 2 s latency, 15-min exit):
  1. ≥ 300 fills in ≥ 100 episodes on ≥ 40 distinct days;
  2. mean net return per fill at 1× ≥ +15 bps, with the 99.9% one-sided lower bound > 0 under BOTH 1-day and 7-day blocks;
  3. mean net per fill at 2× ≥ +5 bps;
  4. beats placebo: per-fill mean net exceeds the placebo per-fill mean net by ≥ 10 bps AND per-order mean net exceeds the placebo per-order mean net, each with a 99% lower bound of the difference > 0 (1-day blocks).
- Otherwise KILL (or NOT EVALUABLE if item 1 fails). Written up and published either way. No re-fit after any outcome.
- HOLDOUT confirm (after a committed PASS and Shawn's approval): mean net per fill at 1× ≥ +8 bps and 95% lower bound > 0. Run once.
- A confirmed result is not a trading green light; it leads to a separate, approved live paper test that measures real fills and placement lag.

## 9. Side task (not part of the verdict)
Record Binance's live liquidation stream (!forceOrder@arr) on Shawn's laptop for a later real-liquidation study.

## 10. Timeline (≤ 14 days)
- Day 1: repo; this prereg committed (hash). Downloader for klines (DEV+VERDICT) and event-day aggTrades.
- Day 2–3 (feasibility phase): universe builder, event detector, fill/exit engine, unit tests on synthetic data; DEV counts, fill rates, drop counts, power projection. If data validation or execution realism cannot be done without shortcuts, stop and report instead of running.
- Day 4: code frozen; Shawn approves the VERDICT run.
- Day 5: VERDICT run once; result committed.
- Day 6–7: HOLDOUT (only if PASS and approved) or write-up. Days 8–14: buffer.

## 11. Approval gates
Shawn approves: (a) this plan, (b) the VERDICT run, (c) any HOLDOUT download, (d) any change to §4–§8.
