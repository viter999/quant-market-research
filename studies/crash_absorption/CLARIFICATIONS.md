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

# CLARIFICATIONS v0.3.2 — answers to implementation questions (no outcome seen; PROPOSED, pending Shawn gate (d) together with v0.3.1)

§4 event rule
- Correction of v0.3.1 (arithmetic slip): all 242 bars t−241…t must exist (σ_t over r_{t−240}…r_{t−1} needs close_{t−241}); otherwise no event at t.
- Klines from 2023-12-01 are downloaded as lookback inputs only (σ, volume median, 7-day ranking). No event before 2024-01-01.

§2 universe / exclusions
- Also excluded: index contracts (BTCDOM, DEFI, FOOTBALL and any similar index), USTC, EUR and any other fiat pair.
- The exclusion list stays DRAFT until checked against the real archive symbol list, then it is frozen.

§6 funding
- VERDICT funding for 2026-03-01…2026-03-13 (the 2026-03 monthly archive file covers HOLDOUT dates) comes from fapi /fapi/v1/fundingRate with endTime ≤ 2026-03-13 23:59:59.999 UTC, cached to parquet. The guard checks endTime (a request without endTime is refused). If fapi is unreachable, raise; never assume zero funding.

§7 B2 baseline
- B2 entry = first aggTrade at or after bar close + 2 s, price × (1 + 5 bps), taker fee 5 bps; same exit and buffers as the primary.

§8 bootstrap
- Placebos count on their EVENT's day.
- Only days with ≥ 1 primary order (event) are resampled; 7-day blocks likewise contain ≥ 1 such day.

Data handling
- aggTrades window widened to bar close −5 min … +70 min so the 30/60-min descriptive exits can be computed.
- Network: symbol listing waits until Shawn allowlists data.binance.vision, the S3 listing host it uses, and fapi.binance.com. No other route is used.

Implementation choices accepted (from the Task 2a report)
- Event day = UTC day of the bar's open; the 23:30 cutoff uses the bar's close time and also applies to placebos.
- "Full day" = any 1d kline except the symbol's listing day.
- Cooldown: next event ≥ 30 min after the previous accepted event; out-of-universe/out-of-segment candidates do not start a cooldown.
- Episodes: a gap of exactly 30 min joins.
- Placebo hour of day: circular ±60 min on bar close time; ±3 days inclusive; σ and volume tolerances inclusive; event 60-min volume = bars t−60…t−1; draws without replacement within an event (two events may draw the same minute).
- 7-day blocks are non-overlapping and aligned to the segment's first day.
- Funding exposure ends at T; funding = rate × entry notional.
- A trade exactly at T counts for both exit sources; same-millisecond trades are ordered by agg_id; a missing CHECKSUM is an error.
- Gate (b) and "run VERDICT" use the same unlock.

# CLARIFICATIONS v0.3.3 — answers to the Task 2a/v0.3.2 open points (no outcome seen; PROPOSED, pending Shawn gate (d) together with v0.3.1 and v0.3.2)

§8 verdict inputs
- Dropped fills (no exit price) are excluded from per-fill means, per-order means and the item-1 fill count, and reported as a count. Additionally (descriptive) the per-order mean is reported with dropped fills counted as 0.
- Item 1 counts episodes and days that contain ≥ 1 fill.
- Item 4 uses the 1× buffer on both sides; its event side is restricted to events with ≥ 1 placebo (items 1–3 use all events).
- A bootstrap replicate with no rows makes the lower bound NaN, which fails "> 0"; the NaN count is reported.
- Every bootstrap uses seed 20261030.

§7 B2 baseline
- B2 is capped at 5 min after bar close: if no aggTrade occurs in [bar close + 2 s, bar close + 300 s], there is no B2 entry, and it is counted.

§6 funding
- Archive (calc_time, last_funding_rate) and REST (fundingTime, fundingRate) are treated as one settlement series. At the seam, 2026-02 is also fetched via REST and compared with the archive file; the maximum timestamp and rate differences are reported.

§2 exclusions
- Frozen only after the research director's review of the real archive list.

# CLARIFICATIONS v0.3.4 — exclusion review against the real archive list (no outcome seen; PROPOSED, pending Shawn gate (d) together with v0.3.1–v0.3.3)

§2 universe / exclusions (research director's review of EXCLUSIONS v0.3-draft, 2026-10-29)
1. All earlier exclusions are kept (prefixes 1000/1M; USDC, USTC; the 6 tokenized metals; the 8 tokenized equities; the 4 index contracts). Delivery contracts (_YYMMDD), BUSD/USDC quotes and ETHBTC stay out through the USDT-perp filter.
2. Pegged check, every USDT perp, 1d klines, DEV only (≤ 2025-08-24), computed only on traded days (quote volume > 0 on that day AND the previous day): exclude if the median |daily close-to-close return| < 0.5 % (stablecoin-like), or if daily-return correlation with BTCUSDT > 0.98 and median |ret − BTC ret| < 0.3 % (BTC-pegged). Reason: delisted contracts continue in the archive as flat zero-volume bars, which would otherwise read as "stablecoin-like".
   - FRAX, US, STABLE and STBL cannot be checked on DEV (no DEV data) and are excluded to be conservative. USUAL and PUMPBTC failed the pegged test and are kept as crypto.
3. Equity-ticker collisions (ON, T, ROBO, INX): excluded only if the symbol's first data is on or after the first tokenized-equity listing day in the archive; otherwise kept as crypto.
4. ALLUSDT is excluded as a possible index.
5. …USDTSETTLED contracts are included as separate USDT-margined perps. Where one overlaps in time with the same-base …USDT symbol and the 1m closes are identical during the overlap, only the …USDT name is kept for the overlap.
6. Non-ASCII memecoins are kept (URL-encoded).
- After these rules the list is FROZEN.

§6 funding
- fapi.binance.com answers HTTP 451 (restricted location) from the study container. The REST funding (2026-02 seam check and 2026-03-01…13, all universe members of those days) is fetched later by Shawn from an eligible location with scripts/fetch_funding_rest.py (guarded, writes parquet + sha256). Until then any hold that needs it raises.

# CLARIFICATIONS v0.3.5 — missing aggTrades handled symmetrically (independent code review; no outcome seen; PROPOSED, to Shawn for gate (d) together with gate (b))

§5/§8 data availability
- An order (event or placebo) whose aggTrades symbol-day file is missing is excluded from its arm and counted: event_orders_data_missing and placebo_orders_data_missing, both shown in the VERDICT report. An event excluded this way is not counted as unfilled (it is not a 0 per order).
- The placebos of an excluded event are also removed from the placebo arm (so both arms are built from the same set of events) and counted as placebos_removed_with_their_event.
- Unchanged (v0.3.3): dropped fills (no exit price) are excluded from both per-fill and per-order statistics, including item 4's per-order arm; the dropped-as-0 per-order mean is descriptive only.
