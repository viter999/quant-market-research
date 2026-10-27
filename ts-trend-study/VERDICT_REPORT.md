# Verdict report — time-series trend on Binance USDT-M perpetuals

Slice 2022-01-01 → 2023-12-31 (verdict). Run id verdict-20261027T155038Z-d779b9fe; prereg sha256 6e4bd3c48e5331a130076a0ac0672edac52ce70f1173ca64c014870ce207540a; code commit 764bac5d7220768f8435fb448d5ae7c53a76ee21.
Primary arm: long_short/atr, judged at 2x cost (20 bps per side). Every other arm, split and diagnostic is reported only.

## Verdict: **FAIL**

| gate | rule | value | pass |
|---|---|---|---|
| P0 | no liquidation event in the slice (either check) | 0 | PASS |
| P1 | net total return > 0 | -0.1853 | FAIL |
| P2 | net Sharpe >= B1 net Sharpe + 0.25 | -0.269 vs 0.084 | FAIL |
| P3 | net Sharpe >= B2 net Sharpe + 0.25 | -0.269 vs 0.545 | FAIL |
| P4 | net Sharpe >= B3 net Sharpe + 0.25 | -0.269 vs -0.142 | FAIL |
| P5 | calendar-2022 net return at 2x cost >= -15% | -0.0699 | PASS |

On FAIL the 1x-cost result is shown first, so the failure reads as either "no edge" or "edge below doubled costs".

## Primary arm by cost level

| cost | net_return | sharpe | max_drawdown | turnover | gross_exposure | flat_share | cap_bound_share | trades | hold_median | hold_mean | whipsaw_rate | liquidations | skipped_orders | missing_funding |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1x | -0.1469 | -0.1811 | 0.4939 | 47.6636 | 0.4480 | 0.0014 | 0.0000 | 445 | 8.0000 | 15.2000 | 0.2337 | 0 | 1920 | 0 |
| 2x | -0.1853 | -0.2692 | 0.5058 | 47.1141 | 0.4429 | 0.0014 | 0.0000 | 444 | 8.0000 | 14.9797 | 0.2365 | 0 | 1885 | 0 |
| 5x | -0.2914 | -0.5586 | 0.5474 | 46.1283 | 0.4498 | 0.0014 | 0.0000 | 442 | 8.0000 | 15.5475 | 0.2511 | 0 | 2193 | 0 |
| 21bps | -0.2134 | -0.3431 | 0.5118 | 47.1372 | 0.4447 | 0.0014 | 0.0000 | 444 | 8.0000 | 15.2568 | 0.2342 | 0 | 1993 | 0 |

## All arms by cost level

| arm | cost | net_return | sharpe | max_drawdown | turnover | trades | whipsaw_rate |
|---|---|---|---|---|---|---|---|
| long_short/atr | 1x | -0.1469 | -0.1811 | 0.4939 | 47.6636 | 445 | 0.2337 |
| long_short/atr | 2x | -0.1853 | -0.2692 | 0.5058 | 47.1141 | 444 | 0.2365 |
| long_short/atr | 5x | -0.2914 | -0.5586 | 0.5474 | 46.1283 | 442 | 0.2511 |
| long_short/atr | 21bps | -0.2134 | -0.3431 | 0.5118 | 47.1372 | 444 | 0.2342 |
| long_only/atr | 1x | -0.1446 | -0.2528 | 0.4003 | 22.4185 | 245 | 0.1878 |
| long_only/atr | 2x | -0.1545 | -0.2827 | 0.4027 | 22.3162 | 244 | 0.1967 |
| long_only/atr | 5x | -0.2126 | -0.4431 | 0.4393 | 22.2988 | 245 | 0.1959 |
| long_only/atr | 21bps | -0.1558 | -0.2860 | 0.4041 | 22.3424 | 244 | 0.1967 |
| long_short/equal | 1x | -0.3514 | -0.2331 | 0.7191 | 71.7954 | 447 | 0.2371 |
| long_short/equal | 2x | -0.3572 | -0.2469 | 0.7189 | 70.8897 | 444 | 0.2365 |
| long_short/equal | 5x | -0.4623 | -0.4455 | 0.7440 | 69.8170 | 434 | 0.2581 |
| long_short/equal | 21bps | -0.3638 | -0.2565 | 0.7227 | 71.1879 | 444 | 0.2365 |
| long_short/voltarget | 1x | -0.0883 | 0.0105 | 0.5215 | 61.2236 | 445 | 0.2315 |
| long_short/voltarget | 2x | -0.1414 | -0.0923 | 0.5210 | 60.3162 | 442 | 0.2353 |
| long_short/voltarget | 5x | -0.3766 | -0.5591 | 0.6369 | 60.0394 | 440 | 0.2432 |
| long_short/voltarget | 21bps | -0.1373 | -0.0732 | 0.5231 | 60.7352 | 441 | 0.2381 |

## Baselines by cost level (same account code)

| arm | cost | net_return | sharpe | max_drawdown | turnover | trades |
|---|---|---|---|---|---|---|
| B1 | 1x | -0.1545 | 0.0856 | 0.6437 | 2.8792 | 1 |
| B1 | 2x | -0.1563 | 0.0842 | 0.6443 | 2.8835 | 1 |
| B1 | 5x | -0.1616 | 0.0799 | 0.6460 | 2.8966 | 1 |
| B1 | 21bps | -0.1565 | 0.0841 | 0.6443 | 2.8840 | 1 |
| B2 | 1x | 0.0313 | 0.5751 | 0.0225 | 1.7013 | 8 |
| B2 | 2x | 0.0296 | 0.5448 | 0.0231 | 1.7024 | 8 |
| B2 | 5x | 0.0245 | 0.4535 | 0.0257 | 1.7057 | 8 |
| B2 | 21bps | 0.0295 | 0.5418 | 0.0232 | 1.7025 | 8 |
| B3 | 1x | -0.8131 | -0.1387 | 0.9356 | 28.0806 | 86 |
| B3 | 2x | -0.8134 | -0.1425 | 0.9355 | 27.8318 | 86 |
| B3 | 5x | -0.8293 | -0.1545 | 0.9364 | 28.0495 | 80 |
| B3 | 21bps | -0.8138 | -0.1411 | 0.9357 | 27.8701 | 86 |

## Year by year (primary arm at 2x; baselines at 2x)

| year | days | primary_net_return | primary_sharpe | B1_sharpe | B2_sharpe | B3_sharpe |
|---|---|---|---|---|---|---|
| 2022 | 365 | -0.0699 | -0.1252 | -1.3877 | -1.1738 | -1.1107 |
| 2023 | 365 | -0.1241 | -0.4379 | 2.1312 | 1.1355 | 1.1798 |

## Calm vs wild days (BTC 30-day realised vol terciles; cut points 0.6119 / 0.7505, hard-coded from DEFINE)

| split | days | mean_daily_bps | net_return | sharpe |
|---|---|---|---|---|
| calm | 504 | -3.0646 | -0.1733 | -0.4921 |
| mid | 116 | 3.8876 | 0.0302 | 0.4505 |
| wild | 110 | -2.6692 | -0.0435 | -0.3070 |

## Net return by funding tercile (mean funding rate across the tradeable set; cut points -0.000039 / 0.000035 from this slice)

| split | days | mean_daily_bps | net_return | sharpe |
|---|---|---|---|---|
| low | 243 | -3.6137 | -0.1155 | -0.4058 |
| mid | 243 | -2.9705 | -0.0788 | -0.6271 |
| high | 244 | 0.8718 | -0.0002 | 0.1257 |

## Eligible coins per month

| month | eligible | tradeable |
|---|---|---|
| 2022-01 | 120 | 30 |
| 2022-02 | 124 | 30 |
| 2022-03 | 126 | 30 |
| 2022-04 | 127 | 30 |
| 2022-05 | 130 | 30 |
| 2022-06 | 130 | 30 |
| 2022-07 | 125 | 30 |
| 2022-08 | 124 | 30 |
| 2022-09 | 130 | 30 |
| 2022-10 | 117 | 30 |
| 2022-11 | 105 | 30 |
| 2022-12 | 117 | 30 |
| 2023-01 | 86 | 30 |
| 2023-02 | 129 | 30 |
| 2023-03 | 137 | 30 |
| 2023-04 | 132 | 30 |
| 2023-05 | 133 | 30 |
| 2023-06 | 107 | 30 |
| 2023-07 | 127 | 30 |
| 2023-08 | 126 | 30 |
| 2023-09 | 123 | 30 |
| 2023-10 | 117 | 30 |
| 2023-11 | 123 | 30 |
| 2023-12 | 160 | 30 |

## Delisting events and the rule each used

- Paths (§3, ruling 2026-10-27): announcement day close 17; last-available close (fallback) 4.

| symbol | last_date | last_close | F | penalty_fraction | confirmed | rule | exit_date | announce_date | notice | fallback_reason |
|---|---|---|---|---|---|---|---|---|---|---|
| 1000BTTCUSDT | 2022-04-11 | 0.0019 | n/a | n/a | PASS | announcement | 2022-04-04 | 2022-04-04 | 4baf8d70485c46e38637bd063c58c4d8 |  |
| AKROUSDT | 2022-05-27 | 0.0033 | 0.1586 | 0.1586 | PASS | last_close | 2022-05-27 | NaT |  | ambiguous notice |
| ANCUSDT | 2022-05-13 | 0.0555 | n/a | n/a | PASS | announcement | 2022-05-13 | 2022-05-13 | 0bfb6cfd10aa4d26926260c0159ef58d |  |
| BTCSTUSDT | 2021-03-12 | 319.4080 | n/a | n/a | PASS | announcement | 2021-03-11 | 2021-03-11 | 2c08ba9e1a1b409fb6a4a2cb2f5ed58b |  |
| BTSUSDT | 2022-08-18 | 0.0125 | 0.1058 | 0.1058 | PASS | announcement | 2022-08-09 | 2022-08-09 | 90498d8e2fec42468ec3d659bdfbb78b |  |
| BTTUSDT | 2022-01-14 | 0.0026 | 0.0891 | 0.0891 | PASS | announcement | 2022-01-10 | 2022-01-10 | 2722e6da4f5141dd9b2fb07b5b1f3f75 |  |
| BZRXUSDT | 2021-12-19 | 0.2301 | 0.1371 | 0.1371 | PASS | announcement | 2021-12-16 | 2021-12-16 | dff27dc6bcbb432c902bcbea5e24ddfa |  |
| COCOSUSDT | 2023-05-25 | 1.4540 | n/a | n/a | PASS | last_close | 2023-05-25 | NaT |  | no notice |
| CVCUSDT | 2022-11-29 | 0.1020 | 0.0686 | 0.0686 | PASS | announcement | 2022-11-28 | 2022-11-28 | 3188e26f14a1464b91487abad452c04f |  |
| DODOUSDT | 2022-05-27 | 0.1410 | 0.1435 | 0.1435 | PASS | announcement | 2022-05-18 | 2022-05-18 | d1cb959677034c45b5149f1d998ae2b1 |  |
| FTTUSDT | 2022-11-14 | 1.5900 | 0.3034 | 0.3034 | PASS | last_close | 2022-11-14 | NaT |  | ambiguous notice |
| HNTUSDT | 2023-03-20 | 1.4330 | 0.1106 | 0.1106 | PASS | last_close | 2023-03-20 | NaT |  | ambiguous notice |
| KEEPUSDT | 2022-02-15 | 0.6018 | 0.1295 | 0.1295 | PASS | announcement | 2022-02-09 | 2022-02-09 | 96698a6a80f64cb1ae27f813032bfaa9 |  |
| LENDUSDT | 2020-10-09 | 0.4976 | n/a | n/a | PASS | announcement | 2020-10-03 | 2020-10-03 | 17595222999545348c8acdd5dc41c00a |  |
| LUNAUSDT | 2022-05-12 | 0.0080 | 0.2217 | 0.2217 | PASS | announcement | 2022-05-12 | 2022-05-12 | ef3ce76d5c2d45ee9b6dc3f281cde744 |  |
| NUUSDT | 2022-02-15 | 0.5265 | 0.0960 | 0.0960 | PASS | announcement | 2022-02-09 | 2022-02-09 | 96698a6a80f64cb1ae27f813032bfaa9 |  |
| RAYUSDT | 2022-11-15 | 0.2480 | 0.1755 | 0.1755 | PASS | announcement | 2022-11-14 | 2022-11-14 | 9a6676662bd5417c92267953f3819dd0 |  |
| SCUSDT | 2022-06-17 | 0.0037 | 0.1066 | 0.1066 | PASS | announcement | 2022-06-10 | 2022-06-10 | 6ce355dedc5d438abde7b5dc99b3a56d |  |
| SRMUSDT | 2022-11-15 | 0.2870 | 0.2352 | 0.2352 | PASS | announcement | 2022-11-14 | 2022-11-14 | 9a6676662bd5417c92267953f3819dd0 |  |
| TOMOUSDT | 2023-11-14 | 1.2792 | 0.0823 | 0.0823 | PASS | announcement | 2023-11-06 | 2023-11-06 | 034eee2293964e26b915b1ec5c42972a |  |
| YFIIUSDT | 2022-04-12 | 1869.9000 | 0.0840 | 0.0840 | PASS | announcement | 2022-04-04 | 2022-04-04 | 4baf8d70485c46e38637bd063c58c4d8 |  |

## Liquidation checks (primary arm at 2x): days within 2x of the maintenance requirement, and events

| close_within_2x | intraday_within_2x | events_close | events_intraday |
|---|---|---|---|
| 0 | 0 | 0 | 0 |

## R1 — time-shifted null (B4; weight-path replay, not order replay, not turnover-matched; reported only)

- Paired comparisons: 200; fraction won by the real strategy: 0.4900.
- Paired net-Sharpe differences (real − null), quantiles 5/25/50/75/95%: -1.4808, -0.6996, -0.0203, 0.5685, 1.2933.
- Achieved turnover, mean over runs: real 36.7092, null 27.7987.
- Null liquidations: 0.

## R2 — primary arm at 2x without its two largest trades (reported only)

| id | symbol | side | open_date | close_date | pnl |
|---|---|---|---|---|---|
| 96 | LUNAUSDT | -1 | 2022-05-08 | 2022-05-12 | 39.8632 |
| 421 | SOLUSDT | 1 | 2023-10-17 | 2023-12-31 | 34.6744 |

- With every trade: net return -0.1853, Sharpe -0.2692.
- Without the two largest (their daily PnL, funding and costs set to zero; every other notional unchanged): net return -0.3344, Sharpe -0.6224.

## Confidence intervals on net Sharpe (reported only, never deciding)

- Block bootstrap (stationary, mean block 20 days, 1000 resamples): [-1.8417, 1.2085].
- Cluster-robust by date (delta method, each date one cluster): [-1.6552, 1.1168].

## Missing funding settlements (counted as 0; operator ruling 2026-10-27)

- Total 0; per symbol: {'ETHUSDT': 0, 'SANDUSDT': 0, 'MANAUSDT': 0, 'LUNAUSDT': 0, 'XRPUSDT': 0, 'NEARUSDT': 0, 'MATICUSDT': 0, 'SOLUSDT': 0, '1000SHIBUSDT': 0, 'DOTUSDT': 0, 'FTMUSDT': 0, 'ATOMUSDT': 0, 'BNBUSDT': 0, 'ADAUSDT': 0, 'LINKUSDT': 0, 'DOGEUSDT': 0, 'GALAUSDT': 0, 'ALICEUSDT': 0, 'ETCUSDT': 0, 'RUNEUSDT': 0, 'WAVESUSDT': 0, 'KNCUSDT': 0, 'AVAXUSDT': 0, 'TRXUSDT': 0, 'BTCUSDT': 0, 'UNFIUSDT': 0, 'AAVEUSDT': 0, 'LTCUSDT': 0, 'APEUSDT': 0, 'GMTUSDT': 0, 'DYDXUSDT': 0, 'FILUSDT': 0, 'CHZUSDT': 0, 'EOSUSDT': 0, 'REEFUSDT': 0, 'SUSHIUSDT': 0, 'MASKUSDT': 0, 'OCEANUSDT': 0, 'AXSUSDT': 0, 'OPUSDT': 0, 'LDOUSDT': 0, 'APTUSDT': 0, 'INJUSDT': 0, 'SXPUSDT': 0, 'ARPAUSDT': 0, 'TOMOUSDT': 0, 'LINAUSDT': 0, 'CFXUSDT': 0, 'MKRUSDT': 0, 'COMPUSDT': 0, 'XLMUSDT': 0, 'BLZUSDT': 0, 'LPTUSDT': 0, 'SUIUSDT': 0, 'ARBUSDT': 0, 'STORJUSDT': 0, 'TRBUSDT': 0, 'BCHUSDT': 0, '1000PEPEUSDT': 0, 'BLURUSDT': 0}.
- Per trade: 0 of 444 trades had at least one missing settlement.

Disclosures: the sizing model was selected on overlapping data; the verdict years were chosen knowing their regimes; the 10 bps/side base cost is an assumption; fills at the next open are optimistic; the null is a weight-path replay (PREREG §14).

## Sensitivities (primary arm long_short/atr at 2x; reported only; same execution)

| sensitivity | value | net_return | sharpe | max_drawdown | trades | liquidations | skipped_orders |
|---|---|---|---|---|---|---|---|
| starting equity | $100 | -0.1404 | -0.3800 | 0.3057 | 134 | 0 | 7074 |
| starting equity | $10,000 | -0.1859 | -0.1985 | 0.5516 | 491 | 0 | 6 |
| delisting penalty | 0 x F | -0.1853 | -0.2692 | 0.5058 | 444 | 0 | 1885 |
| delisting penalty | 3 x F | -0.1858 | -0.2703 | 0.5060 | 444 | 0 | 1881 |

## Post-freeze additions (disclosed)

- `scripts/verdict_run.py` and `FREEZE.json` were added after the freeze (operator ruling 2026-10-27 21:50). Orchestration only: no trading, sizing, cost or pass-rule logic; every number above comes from the frozen pipeline at code_commit 764bac5d7220768f8435fb448d5ae7c53a76ee21 (MANIFEST.txt checked against its blobs before any verdict date was read).
- Orchestrator: scripts/verdict_run.py at commit 3a909b14026b72d8cd72aaa5db1863f25920d546, sha256 52b15c80de8c0d4a1ec92d62c2340c5df7effc148d689b72d5a81ae14d78f7f7.
- `FREEZE.json` is a machine-readable copy of HASHES.txt (the Step 2 loader contract).
- Contract filters (decision 9, accepted as frozen behaviour): universe.contract_filters reads the exchangeInfo snapshot as of 2021-12-31, so a coin whose snapshot contract onboarded after that date, or that is not in the snapshot, takes the $5 default minimum and no lot step. Verdict-slice coins: 260; default because onboarded after 2021-12-31: 120; default because not in the snapshot: 26. Coins ever in a verdict-month tradeable set: 94; onboarded after: 17; not in the snapshot: 7.
- The optional §6 sensitivity (fill at the close of the first hourly bar) is not computed: no hourly data.
