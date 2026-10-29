# RESULT — Binance perp delisting drift: **NOT EVALUABLE** (sample)

PREREG v0.2 + CLARIFICATIONS v0.2.1 (approved). Closed on 29 Oct 2026 at the §4 item 1 check, before any outcome was computed.

## Question and answer
**Question.** After Binance announces a USDT-M perp delisting, does shorting the perp from A+30m to N−30m earn ≥ +100 bps per episode after costs?

**Answer.** The test can't be run. After the pre-registered exclusions, the TEST sample is **21 episodes / 34 symbol-events**; PREREG §4 item 1 needs ≥ 30 episodes and ≥ 40 symbol-events. Under PREREG §4, that makes the result NOT EVALUABLE. No return, PnL, markout or funding sum was computed on real data.

## Sample (TEST: A from 2022-02-17 to 2026-03-13)
| Step | Episodes | Symbol-events |
|---|---|---|
| TEST articles with USDT-M perps (of the 77 selected) | 38 | 78 |
| − window past the 2026-03-13 data limit (article 2026-03-13 14:14: VFY, 1000WHY, BDXN) | −1 | −3 |
| − D − A < 12h (LUNA, ANC, PORT3, AIA) | −4 | −4 |
| − perp 24h quote volume before A < $5M | −11 | −35 |
| − no 1m klines in the 24h before A | 0 | 0 |
| − timestamp not verified (max 1m volume in A±30m < 3× median) | 0 | 0 |
| **Kept by §1** | **22** | **36** |
| − data missing: no 2022-06 fundingRate archive file for ICPUSDT and TLMUSDT (same episode) | −1 | −2 |
| **Usable (item 1)** | **21** | **34** |

- Each excluded event is counted once, under the first §1 rule it fails, in PREREG order. MINAUSDT, a trading suspension, fails the volume rule first; it would also fail D − A < 12h.
- The volume rule drives the result. Most 2025–26 delistings are of very thin perps: 35 of 78 symbol-events had less than $5M in the 24h before A, the largest of them $4.97M (CVXUSDT).
- Usable events by year: 2022: 10, 2024: 15, 2025: 9, 2026: 0.

## Why this is final
- The event list was committed before any price data, and the exclusions use volume and bar presence only.
- Loosening the volume floor or adding COIN-M/BUSD contracts or the FTT article would change §1 after the volume counts are known. That is not allowed under the PREREG.
- A future version would need more events (more time: HOLDOUT-period and later delistings) under a new pre-registration.

## Reproducibility
| Item | Value |
|---|---|
| PREREG v0.2 | `5848ed9` |
| Raw announcements | v1 `binance_futures_delistings_2022-2026.json` sha256 `81750bb0…2eff` (23 bodies failed); v2 `binance_futures_delistings_v2.json` sha256 `0691a0d1…bfd03` (all 77 bodies, used) |
| Event list | `events.csv` sha256 `ed29ffc1…ed64`, commit `918a55e` (before any price data); `articles.csv`, `unselected.csv` (FTT, excluded by the title filter) |
| Decisions | OMGUSDT uses its original D/N; 2026-03-13 article excluded; FTT excluded (CLARIFICATIONS v0.2.1, approved `dcfc121`) |
| Exclusions | `exclusions.csv` sha256 `786da808…10bd`, `exclusions_summary.json` sha256 `3e449a47…c43e` |
| Data | data.binance.vision daily 1m klines (75 symbols + BTCUSDT) and monthly fundingRate, CHECKSUM-verified, all dated ≤ 2026-03-13 |
| Code | `scripts/parse_events.py`, `scripts/download_data.py`, `scripts/exclusions.py`; the VERDICT runner (`scripts/run_verdict.py`) was built and tested on synthetic data only, and was never run on real data |

**HOLDOUT (A from 2026-03-15) is untouched: no price data was downloaded for it.**
