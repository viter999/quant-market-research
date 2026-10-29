# Gap-through — Phase 0 fill-model check: **NOT ACCEPTED**

Spec: `PHASE0_FILL_CHECK.md` (frozen at c393e89). Prices and agreement only — no return, markout or PnL was computed, and no entry was paired with an exit.

## Sample
- Crash-absorption DEV events (frozen detector, universe and exclusions; re-detection reproduced all 27,255 stored DEV events exactly) with bar t closing 2024-01-01 00:00 → 2024-03-30 23:30 UTC: **4,117 events, 179 symbols**.
- bookTicker files needed: 2,500 symbol-days — all present (**0 events dropped** for lack of a file), all CHECKSUMs verified; streamed, keeping only τ−5 s…τ+10 s and T−60 s…T+10 s (plus the last update before each window). DEV aggTrades windows reused: 0 missing.
- Quote in force at t = last bookTicker update with `transaction_time` ≤ t (ties: highest `update_id`).

## Decision at 2 s (rules fixed before running)
| Rule | Value | Pass |
|---|---|---|
| (a) ≥ 30 REAL fills | 36 | yes |
| (b) PROXY precision ≥ 0.85 and recall ≥ 0.85 | precision **0.586**, recall 0.944 | **no** |
| (c) mean entry bias (proxy − real) ≥ −5 bps | +2.95 bps | yes |
| (d) mean exit bias (exit proxy − real bid) ≤ +5 bps | **+61.5 bps** | **no** |

**NOT ACCEPTED.** Under the spec, the gap-through idea is closed as untestable with archive data; live quote recording remains the option.

## Results by latency (all 4,117 events evaluated at every latency)
| | 2 s (primary) | 5 s | 10 s |
|---|---|---|---|
| REAL full fills / REAL partial (ask ≤ L, size < order) | 36 / 22 | 116 / 80 | 238 / 177 |
| PROXY fills / OLD fills | 58 / 62 | 209 / 216 | 432 / 439 |
| REAL vs PROXY: TP / FP / FN / TN | 34 / 24 / 2 / 4,057 | 114 / 95 / 2 / 3,906 | 236 / 196 / 2 / 3,683 |
| … precision / recall | 0.586 / 0.944 | 0.545 / 0.983 | 0.546 / 0.992 |
| REAL vs OLD: TP / FP / FN / TN | 34 / 28 / 2 / 4,053 | 114 / 102 / 2 / 3,899 | 236 / 203 / 2 / 3,676 |
| … precision / recall | 0.548 / 0.944 | 0.528 / 0.983 | 0.538 / 0.992 |
| Entry bias, proxy − real (bps): mean / median / p10 / p90 (n) | +2.95 / +5.00 / −2.98 / +5.00 (34) | +2.88 / +5.00 / −0.39 / +5.00 (114) | +3.26 / +5.00 / −1.11 / +5.00 (236) |
| Entry bias, old − real (bps): mean / median / p10 / p90 (n) | −2.31 / +2.96 / −11.53 / +5.00 (34) | +1.41 / +3.52 / −3.06 / +5.00 (114) | +0.59 / +2.83 / −8.29 / +5.00 (236) |
| Exit bias, exit proxy − real bid (bps): mean / median / p10 / p90 (n) | +61.5 / −3.72 / −15.2 / +225.3 (36) | −49.5 / −2.61 / −148.4 / +3.15 (116) | +9.14 / −1.65 / −19.4 / +67.6 (238) |
| Spread at τ on REAL fills, (ask − bid)/mid (bps): mean / median / p10 / p90 | 13.0 / 6.65 / 0.87 / 38.6 | 8.26 / 4.36 / 1.10 / 18.1 | 9.09 / 4.48 / 1.38 / 19.8 |

Entry bias is a price difference at the same moment (the proxy's +5 bps median is its fixed slippage add-on); exit bias likewise.

## What drives the two failures (DESCRIPTIVE ONLY — not part of the decision; `PHASE0_DIAGNOSTICS.json`)
- **(b) Precision.** Of the 24 false PROXY fills at 2 s, **21 are REAL partials**: the best ask was at or below L, but the size shown at the best ask was smaller than the $500 order (median 0.36× the order size, p90 0.90×). Three had the ask above L. A trade print at ≤ L says the price traded there, not that the order's size was available; the tape cannot see the queue. The same pattern holds at 5 s and 10 s (precision ≈ 0.55).
- **(d) Exit bias** is driven by **gaps in the archive's bookTicker stream**, not by the exit rule. Six 2 s exit checks used a best bid that was 122 s to 2,274 s old; e.g. CKBUSDT's raw file for 2024-02-28 has no update from 17:32:22 to 18:15:20 (43 min) while aggTrades printed tens of thousands of trades. With bid quotes ≤ 1 s old, the exit bias is −5.97 bps mean (n = 30) at 2 s, −4.92 (n = 89) at 5 s — the exit proxy is slightly conservative. Stale quotes at τ are rare (5 events with quote age > 1 s at 2 s, 2 of them REAL fills).
- Neither observation changes the frozen decision: (b) fails on its own.

## Reproducibility
- Code: `phase0/core.py`, `phase0/stream.py`, `scripts/phase0_run.py` (steps verify → download → measure → report; diagnostics separate); 17 unit tests (quote lookup: last update at/before τ, exact-τ update, same-ms ties, missing quote; fill classes; proxy/old rules; exit proxy equals the frozen exit engine on synthetic data; stream carry-in; windows; confusion; decision).
- Results: `results/PHASE0_RESULT.json` (frozen-spec output), `results/PHASE0_DIAGNOSTICS.json` (descriptive). bookTicker windows kept under the gitignored `data/` (0.46 GB).
- No DEV outcome, no HOLDOUT data, no change to `main` or the crash-absorption branch.
