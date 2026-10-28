# CLARIFICATIONS v0.3.1 — implementation rules for PREREG v0.3 (no outcome seen; pending Shawn gate (d))

§3 split
- Floor convention as in SPLITS.json is accepted (DEV 2024-01-01→2025-08-24, embargo 2025-08-25, VERDICT 2025-08-26→2026-03-13, embargo 2026-03-14, HOLDOUT 2026-03-15→2026-09-30).
- An event is used only if its bar t closes ≤ 23:30 UTC on the last day of its segment, so every fill/exit window ends inside the segment. Data guard stays as is (no reads past 2026-03-13).
- Placebo draws are confined to the same segment as their event.

§4 event rule
- r_t = close_t / close_{t-1} − 1. σ_t = sample std (ddof = 1) of r over bars t−240…t−1.
- All 241 bars t−240…t must exist (no missing minute); otherwise no event at t.
- Episodes: single linkage — an event joins an episode if it starts ≤ 30 min after the previous event in that episode (any symbol).

§2 universe
- Symbol = archive symbol name; a renamed/relisted contract is a different symbol. Symbols with < 7 full days of klines before the event day are not eligible.
- Excluded families: any symbol starting with "1000" (incl. 1000000…) or "1M"; stablecoin pairs; tokenized equities/metals. The exclusion list is hand-made from symbol names, committed BEFORE any detection run, and frozen.
- Ranking uses 1d klines quote volume (7 full days ending at the previous day's close).

§5 fill
- Order quantity = 500 / L (base units).
- "After going live" = aggTrades with timestamp ≥ live time (inclusive). Side of the first trade does not matter.
- Gap case entry price = min(first trade price × 1.0005, L) (a buy limit cannot pay above L).
- Maker fill time = timestamp of the aggTrade at which cumulative qty strictly below L reaches 20× order qty (crossing inside one aggTrade counts at that trade's time). Trades at exactly the cancel time (live + 300 s) are included.

§6 exit and costs
- If only one of (a) bid-VWAP in [T, T+10 s] and (b) last seller-initiated trade ≤ T exists, use that one; (b) counts only if within 60 s before T; if neither → drop and count.
- The 1×/2×/5× multiplier scales the slippage buffer only, not the fees.
- Funding is signed (a long pays positive rates, receives negative). A settlement at time s counts if fill < s ≤ exit.

§7 placebo
- "Pre-window σ" = the §4 240-bar σ at the placebo time; "60-min quote volume" = sum over the 60 bars before the placebo time.
- "No event within ±120 min" = no event on the same symbol.
- Candidate minutes are drawn without replacement; the symbol must be in the universe on the placebo day. If fewer than 5 candidates qualify, use those that do and report the count; events with 0 placebos are reported and excluded from the placebo comparison only.
- Seeds (frozen): placebo draws seed = 20261029; bootstrap seed = 20261030; sanity-check sample seed = 20261031. Draws are generated deterministically from the seed after detection.

§7 sanity check
- 50 DEV events drawn uniformly at random (seed 20261031) from all DEV events.

§8
- Power check scales DEV counts by 200/602 (the detector is NOT run on VERDICT before gate (b)).
- "Per fill" includes gap (taker) fills and maker fills; both are also reported separately.
- The placebo difference bootstrap is paired by day: each replicate resamples days and recomputes both the event and placebo means.

Data handling
- aggTrades are streamed: download zip → extract only the needed windows (event/placebo time −5 min … +25 min) to parquet → delete the zip. Klines kept as parquet.
