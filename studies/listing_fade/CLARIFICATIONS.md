# CLARIFICATIONS v0.2.1 — implementation rules for PREREG v0.2 (no outcome seen) — PROPOSED, pending review

Written before any return, markout, PnL or funding sum was computed. So far only timestamps, trade sides, first-hour quote notional and file/bar presence have been looked at (§1 exclusions and §2 drops).

## §1 events
1. **Source.** `events_raw/binance_futures_launches_2023-2026.json` (sha256 `0f82229c…e692`), 311 articles, all bodies present.
2. **L comes from the body's contract table.** Each article's table has a "Launch Time" cell for each symbol column; a single value covers all columns. Where a table omits "(UTC)" (some 2026 articles), the same time appears with "(UTC)" in the body text. Every table time in `events.csv` was found in its body as "T (UTC)" (`L_in_body_utc` = 1 for all 523 rows).
   - Five articles carry a "launch time updated" note (CROSS/AIN, XPIN, LIT, AIA, PREDICT). Their tables already show the updated time, which is used.
3. **USDT-margined perps only.** USDC-margined (e.g. BTCUSDC), USD1-quoted, COIN-M perpetual and COIN-M delivery contracts are dropped: 27 articles have none of the kept kind.
4. **Unparseable:** one article, "ALL Composite Index Perpetual Contract" (2025-08-05). It has no table and never names a symbol. It is an index, so it would be excluded anyway (ALLUSDT is in the frozen possible_index list).
5. **Families: the frozen crash-absorption `EXCLUSIONS.json` named lists, applied literally** (1000/1M prefixes allowed, as PREREG says).
   - This removes 17 TEST rows: 8 tokenized equities, 4 metals (PAXG, XAG, XPT, XPD), and 5 rows the list excludes for crash-absorption reasons although their bodies describe crypto tokens:
     - INXUSDT (Infinex) and ROBOUSDT (Fabric Protocol), listed as "equity_ticker_collision";
     - STBLUSDT, STABLEUSDT and USUSDT (Talus Network), listed as "not_checkable_on_dev".
   - **Open question for review:** keep the literal list (proposed; it is what "frozen" means), or keep those 5 crypto rows.
   - A body-based check (underlying equity / index / metal / FX) finds no non-crypto TEST row that the list misses.
6. **Pre-market flag** = "Pre-Market" in the title or body; the two always agree (29 articles).
7. **Episode = article.** Three TEST articles launch symbols on different days. An episode's launch day is the UTC day of its earliest usable L.
8. **Relaunches.** MAVIA, AERGO and AIA each launch twice in TEST; each launch is its own event (files keyed by symbol + L date).

## §1 exclusions (applied in the listed order; each row reported once, under the first rule it fails)
- **T0** = timestamp of the first aggTrade with ts ≥ L. "No aggTrades within 24h of L" = none in [L, L+24h).
- **First-hour volume** = Σ price × qty over aggTrades in [T0, T0+1h).
- **Funding record missing.** The hold is (entry, exit]. A record is missing if:
  - a monthly fundingRate file is missing, or would cover dates after 2026-03-13 (2026-03, never requested); or
  - any gap in this chain exceeds the larger stated `funding_interval_hours` of its two ends (+5 min tolerance): the last settlement at or before entry (else entry itself) → each settlement in the hold → the first settlement after exit (else exit itself).
  - The larger-interval rule handles interval changes, e.g. AERGOUSDT 2025-04-16 switching from 4h to 2h.
- **Data gaps found:**
  - **KATUSDT (L 2026-03-02):** its hold runs into March, and the 2026-03 archive file covers HOLDOUT dates, so it is excluded as funding_record_missing. REST funding for 2026-03-01…05, fetched by Shawn as in crash-absorption, would make it scorable. This is a decision for review; the exclusion is the default.
  - **AIAUSDT relaunch (L 2026-01-16):** the archive has no aggTrades files for 2026-01-16 and 01-17, although its 1m klines exist. Reported as `aggtrades_files_missing`, not as "never traded".
- **"A delisting announced before T0+72h"** = a Delisting-catalog (161) title released in [A, T0+72h) that contains "Delist", does not start with "Binance Margin", and names the symbol or its token as a whole word.
  - Titles are copied from the delisting study's v2 raw file into `events_raw/delisting_catalog161_titles.json`, with the source sha256 recorded.

## §2 trade
- **Entry:** VWAP of seller-initiated aggTrades (`is_buyer_maker` = true) in [T0+60m, T0+61m); if there are none, [T0+61m, T0+62m); otherwise the event is dropped and counted.
- **Exit:** VWAP of buyer-initiated aggTrades in [T0+72h, T0+72h+1m), with the same fallback.
- **Funding:** settlements with entry-window start < ts ≤ exit-window start (the windows actually used). Funding = Σ rate × entry notional; a short receives +rate.
- **Net** = (entry − exit)/entry − 2 × 5 bps − 2 × buffer (15 / 30 / 75 bps per side) + funding.
- **BTC-relative:** r_BTC = BTCUSDT 1m close of the exit-window minute / close of the entry-window minute − 1; BTC-relative net = net + r_BTC.
- **Funding stress (descriptive):** every settlement in a hold set to the 5th percentile of all settlement rates in the usable holds, pooled (the 95th-percentile adverse value for a short).

## §4 verdict
- Episode net = the mean of its usable rows.
- **Bootstrap:** 10,000 replicates, `numpy.random.default_rng(20261104)`.
  - Units: single launch days, and 7-day blocks of launch days aligned to 2024-01-01 (non-overlapping, only blocks containing an episode).
  - A replicate is the mean over all episodes in the drawn units.
  - The one-sided 99% lower bound is the 1st percentile; item 2 needs it > 0 under both block schemes.
- **"Significantly negative"** = the 99th percentile < 0 under 7-day blocks (primary).
- **Item 6** removes the 5 episodes with the highest 1× net.
- **Item 1** counts episodes with ≥ 1 usable row, and their distinct launch days.

## §5 descriptive (EXPLORATORY; computed in the same run, no claims; 1× costs)
- **Entry at L+5m and L+24h:** the same seller-VWAP rule at that time, and the same exit.
- **Holds:** 4h and 24h exits use buyer-VWAP at T0+4h / T0+24h where the stored aggTrades window [L, L+25h10m] reaches; otherwise NaN.
  - 7d is NOT computed: data past max(L, T0)+73h was not downloaded. It can be added if approved.
- **Long mirror:** buy at buyer-VWAP at T0+60m, sell at seller-VWAP at T0+72h; pays the short's funding.
- **Max adverse move:** highest 1m high over the hold / entry − 1.
- **20% stop:** uses 1m bars, because aggTrades over the full hold were not downloaded. The first bar after the entry minute whose high ≥ 1.2 × entry is filled at max(1.2 × entry, that bar's open), with funding up to that bar.
- **Also:** pre-market vs regular, by year, funding share, and the sensitivity run including the rows excluded only by the $5M rule.
- **Spot pair at L is NOT computed:** no spot-listing data.

## Data
- aggTrades are kept for [L, L+25h10m] (covers [L, L+24h], T0+62m for any T0 within 24h, and L+24h+2m) and for [T0+72h−5m, T0+72h+10m].
- 1m klines are kept for [L, max(L, T0)+73h], since T0 can be later than L.
- Only rows still in the universe after the family exclusions are downloaded; HOLDOUT never is.
