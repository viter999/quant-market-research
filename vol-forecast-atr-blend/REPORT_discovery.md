# P02 — discovery, one look (PREREG_v0.1 b97646e9…)

Run 2026-10-22 15:46 UTC. Primary loss QLIKE; DM clustered by date, Newey–West lag 6; one-sided bar z ≥ 2.5.

**Verdict: WINNER C**

Lowest mean QLIKE: C; runner-up: B; z of C against each other candidate: A 6.49, B 7.87.

MALE ranks the candidates DIFFERENTLY from QLIKE (reported only; the verdict stays with QLIKE).

## Candidates

| candidate | mean QLIKE | mean MALE | bias mean(RV/F) | MZ a (SE) | MZ b (SE) | Spearman (SE) |
|---|---|---|---|---|---|---|
| A | 0.0890 | 0.3051 | 1.047 | -0.802 (0.020) | 0.697 (0.010) | 0.686 (0.008) |
| B | 0.0888 | 0.3192 | 1.010 | -0.508 (0.032) | 0.827 (0.015) | 0.642 (0.009) |
| C | 0.0730 | 0.2855 | 0.997 | -0.424 (0.024) | 0.858 (0.012) | 0.712 (0.008) |

## Pairwise DM (positive favours the first named)

| pair | loss | mean diff | SE | z | one-sided 95% lower | dates |
|---|---|---|---|---|---|---|
| C VS A | QLIKE | 0.01597 | 0.00246 | 6.49 | 0.01192 | 1303 |
| C VS B | QLIKE | 0.01572 | 0.00200 | 7.87 | 0.01244 | 1303 |
| A VS B | QLIKE | -0.00025 | 0.00411 | -0.06 | -0.00701 | 1303 |
| C VS A | MALE | 0.01970 | 0.00428 | 4.60 | 0.01266 | 1303 |
| C VS B | MALE | 0.03370 | 0.00445 | 7.57 | 0.02638 | 1303 |
| A VS B | MALE | 0.01400 | 0.00811 | 1.73 | 0.00067 | 1303 |

## Counts (§9)

- Symbols loaded: 668; eligible (coin, date) observations: 229619; used: 229266.
- Dropped, incomplete target window: 353 (of which running past the coin's last valid day: 332).
- Dropped, RV or a forecast not positive: 0.
- Forecast dates used: 1303; coins per date min 108, median 173, max 256.

## Sensitivities (reported, never verdict-changing)

| config | obs | dates | lowest QLIKE | z C vs A | z C vs B | z A vs B | lowest MALE |
|---|---|---|---|---|---|---|---|
| S1 | 229266 | 1303 | C | 6.00 | 6.50 | -0.05 | C |
| S2 | 32579 | 186 | C | 5.14 | 4.93 | -0.94 | C |
| S3 | 229376 | 1303 | C | 6.48 | 7.90 | -0.03 | C |
| S4 | 89848 | 1303 | C | 7.87 | 8.24 | 0.21 | C |
| S5-first | 108897 | 652 | C | 3.40 | 5.58 | 1.01 | C |
| S5-second | 120369 | 651 | C | 5.91 | 5.87 | -1.34 | C |
| S6 | 229266 | 1303 | A | -3.93 | 13.73 | 10.85 | A |

One look. No re-tuning. Full numbers in the results JSON; hashes in `RESULTS.sha256`.
