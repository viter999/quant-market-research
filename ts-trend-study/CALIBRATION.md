# Fake-data calibration of the pass rule (PREREG §11; BUILD_PLAN Step 9)

Run 2026-10-27 13:15 UTC on sign-flipped DEFINE data only. Every number below comes from a synthetic market; no statistic of the real data was computed.

**Calibration passes: 5 of 200 fake datasets pass the full rule** (limit 10 of 200, §11). Per §11 decision sequence 1 the study may proceed to freeze.

## Setup

- Synthetic slice: 2020-08-03 -> 2021-12-31 (516 days), the whole DEFINE slice from the Step 7 sample start; real bars before it are lookback inputs only.
- Seeds: `seeds/calibration.txt` (sha256 f43d55dc731cbac77151255f999e64dff614f9f1c3f996012d0d783f102a3d75), committed in b858999 before the first run; one seed per dataset in file order; eps from `numpy.random.default_rng(seed).integers(0, 2)` as the file header states.
- Fake market (§11): each day one sign shared by every coin; bars mirrored recursively from each coin's own fake previous close; volume unchanged; every funding settlement multiplied by the sign of its day.
- Pipeline: universe, Donchian ensemble, ATR-blend sizing (r = 0.5%), K = 10, 2x gross cap, turnover brake, costs at 2x (20 bps per side), funding, liquidation checks, delisting rule with announcement dates (ruling 2026-10-27); primary arm long-short ATR sizing; baselines B1-B3 on the same fake market.
- Starting equity $500 (PREREG v0.8). Pass rule §8 with margin +0.25 and floor -15%; P5 on the first 12 months of the synthetic slice (§11).
- Delisting paths on this slice: announcement day close 3, last-available close 0 (BTCSTUSDT announcement exit 2021-03-11; BZRXUSDT announcement exit 2021-12-16; LENDUSDT announcement exit 2020-10-03) (the dates are calendar facts, identical in every fake dataset).
- Code commit b858999 + uncommitted Step 9 code; workers 1; Below-normal priority; wall time 67 min.

## Pass count by gate

| gate | rule | datasets passing |
|---|---|---|
| P0 | no liquidation event (either check) | 200 of 200 |
| P1 | net total return > 0 | 65 of 200 |
| P2 | net Sharpe >= B1 net Sharpe + 0.25 | 40 of 200 |
| P3 | net Sharpe >= B2 net Sharpe + 0.25 | 58 of 200 |
| P4 | net Sharpe >= B3 net Sharpe + 0.25 | 16 of 200 |
| P5 | first 12 months (2020-08-03..2021-08-02) net return >= -15% | 127 of 200 |
| ALL | P0-P5 together | **5 of 200** |

## Distribution of each P-statistic over the fake datasets

| statistic | min | 5% | 25% | median | 75% | 95% | max | mean |
|---|---|---|---|---|---|---|---|---|
| P0_liquidations | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P1_net_return | -46.62% | -40.39% | -25.50% | -12.85% | 8.89% | 60.26% | 144.79% | -4.03% |
| P2_sharpe_minus_B1 | -3.292 | -2.004 | -1.232 | -0.652 | 0.084 | 0.932 | 2.330 | -0.575 |
| P3_sharpe_minus_B2 | -2.281 | -1.487 | -0.739 | -0.207 | 0.377 | 1.225 | 3.741 | -0.160 |
| P4_sharpe_minus_B3 | -3.289 | -2.137 | -1.685 | -1.066 | -0.515 | 0.501 | 3.705 | -1.028 |
| P5_first12m_return | -47.74% | -35.39% | -21.76% | -7.12% | 11.76% | 48.73% | 173.87% | -1.26% |

- P0: datasets with at least one liquidation event: 0 of 200; B3 liquidations in 2 datasets.
- Primary arm per dataset, medians: 246 trades, 2280 skipped orders, 0 missing funding settlements (applied as 0).
- Up days per dataset: median 258 of 516.

## Datasets that pass the full rule

| dataset | seed | P0_liquidations | P1_net_return | P2_sharpe_minus_B1 | P3_sharpe_minus_B2 | P4_sharpe_minus_B3 | P5_first12m_return |
|---|---|---|---|---|---|---|---|
| 77 | 3661496223 | 0 | 22.37% | 0.453 | 1.555 | 0.598 | 11.88% |
| 122 | 501260545 | 0 | 5.32% | 0.794 | 0.419 | 0.423 | 8.91% |
| 190 | 2410424680 | 0 | 71.28% | 1.013 | 1.182 | 0.866 | 44.31% |
| 195 | 580409163 | 0 | 63.50% | 1.624 | 0.370 | 1.040 | 23.77% |
| 196 | 3466373192 | 0 | 19.25% | 0.673 | 0.392 | 0.351 | 42.25% |

## Fake-data unit test (run before the calibration runs)

```
tests/test_fake_data.py::test_close_log_return_is_eps_times_r_every_day_and_the_path_is_continuous PASSED [  8%]
tests/test_fake_data.py::test_bar_ordering_holds_and_log_ranges_are_preserved PASSED [ 16%]
tests/test_fake_data.py::test_all_plus_one_reproduces_the_real_bars_and_all_minus_one_inverts_them PASSED [ 25%]
tests/test_fake_data.py::test_volume_columns_are_unchanged_and_bad_signs_are_refused PASSED [ 33%]
tests/test_calibrate.py::test_committed_seed_sets_have_200_distinct_seeds_each_and_share_none PASSED [ 41%]
tests/test_calibrate.py::test_daily_signs_follow_the_rule_in_the_seed_header PASSED [ 50%]
tests/test_calibrate.py::test_fake_klines_mirror_slice_rows_with_the_shared_daily_sign_and_keep_the_rest PASSED [ 58%]
tests/test_calibrate.py::test_fake_funding_multiplies_each_settlement_by_the_sign_of_its_snapped_day PASSED [ 66%]
tests/test_calibrate.py::test_fake_coin_refuses_rows_beyond_the_slice_and_non_positive_prices PASSED [ 75%]
tests/test_calibrate.py::test_gates_apply_the_section_8_rule_with_p5_on_the_first_12_months PASSED [ 83%]
tests/test_calibrate.py::test_run_dataset_matches_the_pipeline_run_by_hand_on_a_fake_market PASSED [ 91%]
tests/test_calibrate.py::test_summarize_counts_passes_and_halts_above_ten PASSED [100%]
============================= 12 passed in 20.73s =============================
```

Per-dataset rows: `reports/calibration_runs.csv`. Validation seeds (`seeds/validation.txt`) were not used.
