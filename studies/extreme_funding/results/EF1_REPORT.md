# Extreme-funding carry — EF-1 feasibility (counts only)

No price, return or P&L was computed on any real data. Exit decisions used funding rates only. DEV only for filters and counts; VERDICT only for the funding-input candidate scan. HOLDOUT not read (guard max 2026-03-13).

## Power check (PREREG §6): **FAILS — stop and ask Shawn**
| | DEV (602 days) | Projected VERDICT (× 200/602) | Minimum |
|---|---|---|---|
| Trades | 37 | **12.3** | 60 |
| Symbols | 24 | **8.0** | 15 |
| Distinct entry days | 30 | **10.0** | 30 |

## DEV counts
Candidate scan (funding monthly 2023-12 → 2026-02, all 669 USDT-M perps incl. `…USDTSETTLED`; 1,526,554 settlements):
- DEV settlements 948,226 (533 symbols). Events with h_S ≥ 0.0125 %/h: 10,481; skipped for an interval change at S: **4**; skipped for no prior interval (first two settlements of a symbol): 45; candidates with status ok: **10,432** (390 symbols).

Entry filter, applied in this order (each count is of the rows still in):
| Step | Dropped | Remaining |
|---|---|---|
| Candidates (h_S ≥ threshold, interval ok) | — | 10,432 |
| Entry after the cutoff (segment end − 8 days) | 182 | 10,250 |
| Not in the point-in-time universe on S's day | 7,574 | 2,676 |
| No spot `<BASE>USDT` 1m file in the 24 h before S (by listing) | 1,617 | 1,059 |
| No spot bars in [S−24h, S) | 3 | 1,056 |
| Spot 24 h quote volume < $5M | 10 | 1,046 |
| Median spot 1-min quote volume < $50k | 721 | 325 |
| OI missing | 0 | 325 |
| OI rise < 5 % (24 h, last row ≤ S − 5 min) | 197 | 128 |
| Symbol already has an open position | 37 | 91 |
| Cap of 5 open positions | 54 | **37 trades** |

- Trades 37 on 24 symbols, 30 distinct entry days; entries cluster in 2024-02/03 (30 of 37). Top symbol: WIF (7 trades).
- Exit reasons: funding below 0.00375 %/h 34, 7-day max hold 3, delisting 0 (1 more would be a delisting exit if "data ends" meant the last *traded* bar).
- Hold length (hours): min 4, p10 8, median 48, mean 64, p90 152, max 168; histogram ≤8 h: 6, 8–24 h: 4, 24–72 h: 15, 72–168 h: 12.
- Max concurrent positions: 5 (the cap binds; 54 signals were dropped by it).
- VERDICT funding scan (inputs only, no filters run): 560,860 settlements; 10,470 events with status ok (209 symbols); 9 interval-change skips; 25 no-history skips. The filters and trade simulation were NOT run on VERDICT.

## Ambiguities in PREREG v0.2 (listed, not fixed; the implemented choice is in brackets)
1. **S has millisecond jitter** in the archive (e.g. 00:00:00.005). The bar [S+1m, S+2m) — [floor S to the minute, then +1m].
2. **I_S**: computed as S minus the previous fundingTime, or the archive's `funding_interval_hours` column? They disagree on 324 DEV / 187 VERDICT settlements. [computed, rounded to whole hours]
3. **First two settlements of a symbol** have no I_S or no previous interval. [skipped, counted as no_history: 45 DEV threshold events]
4. **Gaps in a symbol's funding history** (I_S of 504–4,500 h after a delisting/relisting) make the next settlement an "interval change". [skipped by the interval rule]
5. **"OI 24h earlier"**: the last row ≤ S − 5 min − 24 h, or the row exactly 24 h before the "now" row? [the former]
6. **"In the universe at S"**: the universe is daily. [the universe of S's UTC day]
7. **Spot pair by name only** (`<BASE>USDT`): renamed pairs (e.g. perp and spot names that differ) are counted as "no spot pair"; the 1,617 drops do not separate true absence from name mismatch.
8. **"Spot 1m klines in the 24h before S"**: any bar, or full coverage? [at least one daily file and one bar]
9. **Median 1-min spot quote volume**: missing minutes as 0, or only existing bars? [missing = 0]
10. **Exits and entries at the same settlement**: which comes first, and may a symbol re-enter at the settlement where it exits (7-day/delisting exit)? [exits first; re-entry allowed]
11. **Exit at an interval change**: h_{S_k} when I changes at S_k. [h computed with the new I_{S_k}]
12. **"Entry + 7 days"**: entry = S or the execution minute? With the execution minute, the max-hold exit can move to the next settlement (up to +8 h), beyond the S+7d+1h data slice. [S]
13. **Funding sum on (entry, exit]** with entry = S and exit = S_k (decision times). "perp close at S_j": the bar ending at S_j or starting at S_j? [close of the bar [S_j−1m, S_j)]
14. **"Data ends" for the delisting exit**: the archive continues flat, zero-volume bars after a delisting. Last bar present, or last traded bar? [last bar present; 1 DEV trade differs]
15. **Entry cutoff**: "7 days + 1 day before the segment end". [S ≤ last day 23:59:59.999 − 8 days → DEV last entry 2025-08-16]
16. **Filter order** for the drop counts (any order gives the same trades but different per-filter counts). [order of the table above]
17. **Dropped signals are not queued**: a signal blocked by the cap or an open position is lost, not retried at the next settlement. [not queued]
18. **VERDICT 2026-03-01…13 funding** comes from the REST import, which covers only the 177 universe members of those days; non-members have no March funding (irrelevant after the universe filter).
19. **Spot klines switched to microsecond timestamps on 2025-01-01** in the archive. [detected by magnitude and validated against the file's day]

## Reproducibility, disk, time
- Code: `ef/` (guardx, archive, core, slices, pnl [locked, synthetic tests only]), `scripts/ef1_funding.py`, `scripts/ef1_events.py`; 26 unit tests (interval-change skip, h_S, OI lookup ≤ S−5 min, spot liquidity, worst-of-bar prices, funding sum on (entry, exit], delisting exit, entry cutoff, cap ordering and tie-break, exits-before-entries, µs timestamps, data end, metrics time parsing, listing guard).
- Results: `results/EF1_FEASIBILITY.json`.
- Data (gitignored): funding 21 MB, spot 1m 56 MB, metrics 6.7 MB — 94 MB in total; 1,815 cached day files, 7 archive 404s. Perp 1m: all needed days were already in the crash-absorption DEV parquet.
- Run time: funding download 608 s; candidate scan 12 s; DEV filters 257 s (with downloads), 97 s re-run from cache after a counting fix (the first run's per-filter counts overlapped; trades were unchanged at 37).
