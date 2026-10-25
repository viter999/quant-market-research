# Results v1.0 — Funding-gap study (Hyperliquid vs Binance USDT-M), ledger #37

Date: 2026-10-26. One look under frozen PREREG_v0.2.md (sha256 f6f70e38fd66384657bce228683afe85c91ac2e2e62b08215cd2dba06f7e62b7).
Code: scripts/pnl_core_v1.py, p10_fake_check_v1.py, p11_one_look_v1.py (scripts kept unchanged; not hashed).

**Verdict: FAIL.** Mean net PnL per pair is -63.8 bps of one-leg notional (z -11.0, 95% CI -76.4 to -53.7).
The pairs do collect funding (+19.8 bps gross per pair on average), but that is far below the 84 bps cost.

## Fake-data check (run first)
- Engine check: the test pipeline reproduces count check v4 exactly (165 trades, same entries and exits).
- 20 shuffles of each coin's hourly gap series (seeds 1..20): 0 reached z >= 3.0; max z -12.4.
  Shuffled pairs earn about 0 bps funding and 0 bps price, so they net about -84 bps (the costs), as expected.
- Result: PASS, so the real-data look was run.

## Primary result
| | pairs | weeks | mean net bps | z | 95% CI |
|---|---|---|---|---|---|
| All pairs | 165 | 59 | -63.8 | -11.0 | -76.4 .. -53.7 |
| Without the 2 best pairs | 163 | 59 | -66.0 | -12.2 | -78.1 .. -56.9 |

- 64 coins. The 2 best pairs: kBONK 2024-11-11 (+147.2 bps), LAYER 2025-05-07 (+84.6 bps).
- Mean per pair: funding +19.8 bps, price +0.4 bps, costs -84 bps. Median net -67.0 bps.
- 7% of pairs end above zero; 11 of 165 have gross (funding + price) above 84 bps.

## Split by year (entry fill; descriptive, not tested)
| year | pairs | coins | mean net bps | mean funding bps | mean price bps |
|---|---|---|---|---|---|
| 2024 (from 08-12) | 40 | 24 | -39.4 | 36.2 | 8.4 |
| 2025 | 95 | 45 | -73.2 | 15.3 | -4.5 |
| 2026 (to 09-30) | 30 | 11 | -66.8 | 12.1 | 5.0 |

## Split by which venue was higher at entry (descriptive, not tested)
| higher venue | pairs | coins | mean net bps | mean funding bps | mean price bps |
|---|---|---|---|---|---|
| Hyperliquid (short HL, long Binance) | 135 | 58 | -69.1 | 18.8 | -3.9 |
| Binance (short Binance, long HL) | 30 | 20 | -40.2 | 24.5 | 19.3 |

## Capital tied up (descriptive)
- 5,112 pair-hours; mean hold 31 h.
- Mean open pairs over 2024-08-12..2026-09-30: 0.27; max 13 at once (26 legs of one-leg notional).

## Ledger line (#37, draft for TRIALS_LEDGER; not written to the ledger from here)
#37 funding-gap HL vs Binance USDT-M | prereg v0.2 f6f70e38 frozen 2026-10-26 | 1 variant (4h fills) | sample 2024-07-13..2026-09-30, entries from 2024-08-12 | 165 pairs / 64 coins / 59 weeks | mean net -63.8 bps/pair, z -11.0, 95% CI [-76.4, -53.7]; without 2 best -66.0, z -12.2 | gross funding +19.8 bps vs 84 bps costs | fake-data PASS (20 shuffles, max z -12.4) | bar z >= 3.0 (family) | FAIL

## Checked / not checked
- Checked: fake-data check first; engine reproduces the count check; one look only (the script refuses a rerun).
- Not checked: fills at mark price (trade-price 4h opens used); real fees/slippage (flat 84 bps as pre-registered);
  how the result moves with lower costs (not pre-registered, not run).
