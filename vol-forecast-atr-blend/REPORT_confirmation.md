# P03 — confirmation, one look (PREREG_v0.1 b97646e9…)

Run 2026-10-22 16:05 UTC. Primary loss QLIKE; DM clustered by date, Newey–West lag 6; one-sided bar z ≥ 2.33.

**Verdict: CONFIRMED**

Discovery WINNER C vs runner-up B: z = 6.47; lowest confirmation mean QLIKE: C.

MALE ranks the candidates the same way as QLIKE (reported only; the verdict stays with QLIKE).

## Candidates

| candidate | mean QLIKE | mean MALE | bias mean(RV/F) | MZ a (SE) | MZ b (SE) | Spearman (SE) |
|---|---|---|---|---|---|---|
| A | 0.0755 | 0.2926 | 1.061 | -0.841 (0.051) | 0.648 (0.021) | 0.601 (0.014) |
| B | 0.0847 | 0.3238 | 1.004 | -0.507 (0.088) | 0.804 (0.036) | 0.547 (0.016) |
| C | 0.0663 | 0.2818 | 1.004 | -0.435 (0.059) | 0.836 (0.025) | 0.626 (0.015) |

## Pairwise DM (positive favours the first named)

| pair | loss | mean diff | SE | z | one-sided 95% lower | dates |
|---|---|---|---|---|---|---|
| C VS A | QLIKE | 0.00917 | 0.00267 | 3.43 | 0.00477 | 847 |
| C VS B | QLIKE | 0.01839 | 0.00284 | 6.47 | 0.01372 | 847 |
| A VS B | QLIKE | 0.00922 | 0.00522 | 1.77 | 0.00063 | 847 |
| C VS A | MALE | 0.01076 | 0.00675 | 1.60 | -0.00033 | 847 |
| C VS B | MALE | 0.04193 | 0.00666 | 6.30 | 0.03098 | 847 |
| A VS B | MALE | 0.03116 | 0.01262 | 2.47 | 0.01040 | 847 |

## Counts (§9)

- Symbols loaded: 154; eligible (coin, date) observations: 68284; used: 67689.
- Dropped, incomplete target window: 595 (of which running past the coin's last valid day: 66).
- Dropped, RV or a forecast not positive: 0.
- Forecast dates used: 847; coins per date min 3, median 85, max 132.

## Sensitivities (reported, never verdict-changing)

| config | obs | dates | lowest QLIKE | z C vs A | z C vs B | z A vs B | lowest MALE |
|---|---|---|---|---|---|---|---|
| S1 | 67689 | 847 | C | 3.28 | 5.42 | 1.58 | C |
| S2 | 9628 | 121 | C | 3.95 | 4.76 | 0.95 | C |
| S3 | 68060 | 847 | C | 3.45 | 6.48 | 1.76 | C |
| S4 | 41280 | 847 | C | 2.55 | 6.78 | 2.39 | C |
| S5-first | 17914 | 424 | C | 1.90 | 5.60 | 2.07 | C |
| S5-second | 49775 | 423 | C | 3.19 | 3.59 | 0.17 | C |
| S6 | 67689 | 847 | A | -4.14 | 8.46 | 7.66 | A |

One look. No re-tuning. Full numbers in the results JSON; hashes in `RESULTS.sha256`.
