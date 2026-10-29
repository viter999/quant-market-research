# RESULT — Gap-through after a crash bar: **closed (fill model NOT ACCEPTED)**

## What was checked
The crash-absorption VERDICT showed, as a post-hoc exploratory pattern, that "gap" fills looked profitable. Before testing that idea on untouched data, Phase 0 (`PHASE0_FILL_CHECK.md`, frozen before running) asked a narrower question: **can the trade tape tell us whether an immediate-or-cancel buy at L would really have filled, and at what price?**

The answer was measured against real best bid/ask quotes (Binance `bookTicker`, available in the archive only up to 2024-03-30) on all 4,117 crash-absorption events with bars closing 2024-01-01 → 2024-03-30 23:30 UTC. No event was dropped for missing data. Only prices and fill agreement were measured; **no return, markout or PnL was computed**, and DEV and HOLDOUT outcomes remain untouched.

## Decision (rules fixed before running, 2 s latency)
| Rule | Value | Pass |
|---|---|---|
| (a) at least 30 real (quote-based) fills | 36 | yes |
| (b) trade-print proxy precision and recall ≥ 0.85 vs real fills | precision **0.586**, recall 0.944 | **no** |
| (c) mean entry bias (proxy − real ask) ≥ −5 bps | +2.95 bps | yes |
| (d) mean exit bias (exit proxy − real bid) ≤ +5 bps | **+61.5 bps** | **no** |

**NOT ACCEPTED.** Under the frozen rule the gap-through idea is closed as untestable with archive data.

## Main reason: the trade tape overstates fills
The proxy said "filled" 58 times; only 34 of those were real fills. So **about 4 in 10 trade-print "fills" (24 of 58) would not have filled a $500 order.** In 21 of those 24 the price was right — the best ask was at or below L — but **the size at the best ask was too small for the order** (typically about a third of the size needed). The other 3 had the ask above L. A trade printing at L shows that *someone* traded there; it does not show that the order's size was available. The same pattern holds at 5 s and 10 s latency (precision about 0.55).

## Note on rule (d): stale quotes in the archive
The exit-bias failure comes from gaps in the archive's `bookTicker` stream, not from the exit rule itself. In six of the 36 checks the "real" best bid was minutes old (2 to 38 minutes); for example, CKBUSDT on 2024-02-28 has no quote update for 43 minutes while tens of thousands of trades printed. *Diagnostic only, not part of the decision:* using only bids no older than 1 second, the exit proxy is slightly conservative (−6.0 bps on average, n = 30). This does not change the outcome, because rule (b) fails on its own.

## The only honest next step (if Shawn ever wants it)
Archive data cannot settle this. The test would need **live `bookTicker` recording — best bid and best ask together with their sizes —** for the crash-absorption universe, then a new pre-registered study tested **forward** on data collected after the recording starts. The existing liquidation-stream side task (crash-absorption PREREG §9) could be extended to record it.

## Reproducibility
- Spec frozen at `c393e89`; code and tests at `a9714f8`; result at `e72e4c6` (`results/PHASE0_REPORT.md`, `PHASE0_RESULT.json`, `PHASE0_DIAGNOSTICS.json`).
- Events: the frozen crash-absorption detector, universe and exclusions; re-detection reproduced all 27,255 stored DEV events exactly.
- Quote in force at a moment t = the last `bookTicker` update with `transaction_time` ≤ t (same-millisecond ties: highest `update_id`); 2,500 symbol-days streamed, all checksums verified.
