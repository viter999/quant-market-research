# Uniswap v3 in-range liquidity recovery after large ETH/USDC moves: a pre-registered pilot

**Result: H1 No, H2-Arbitrum No, H2-Base Null.** For the fee tier (H1) and for Arbitrum (H2) the data rule out
the pre-registered 1.5× faster recovery; for Base the test is inconclusive. "No" means a 1.5× effect in the
hypothesised direction is ruled out, not that there is no difference.

The full report is [`REPORT.md`](REPORT.md). The preregistration, the frozen pipeline code and the files needed to
reproduce the one look are in the study's own repository:
[github.com/viter999/uniswap-liquidity-recovery](https://github.com/viter999/uniswap-liquidity-recovery).

## What was tested

- **Question:** after a large, fast move in the ETH/USDC price, how quickly does the liquidity near the current
  price (in-range depth) return to its pre-shock level in Uniswap v3 pools, and does that speed differ
  - **H1** by fee tier: 0.05% vs 0.3% on the same chain, and
  - **H2** by chain: Arbitrum and Base vs Ethereum, same tier?
- **Hypothesised directions,** fixed before the data: 0.05% faster than 0.3%; L2 faster than Ethereum.
- **Pools:** ETH/USDC 0.05% and 0.3% on Ethereum, Arbitrum and Base (confirmatory); Unichain 0.3% (exploratory).
- **Window:** 2024-01-01 to 2026-10-01 UTC; calibration on 2023 Ethereum only.
- **Shocks:** a move of at least 5% (log) within 60 minutes on the Ethereum 0.05% pool's price starts an episode;
  triggers less than 48 h apart chain into one episode. 48 episodes, 288 confirmatory pool-episodes.
- **Metric:** USD depth within ±1% of the pool price, every minute, rebuilt from tick-level liquidity. Recovery time
  = time after the last trigger until depth stays at or above 90% of its pre-shock median for 15 minutes, censored
  at 72 h.
- **Tests:** one value per episode (log-ratio of recovery times), Wilcoxon signed-rank test, Holm correction for
  the two H2 tests. **Yes** needs p < 0.05 and a median ratio of at least 1.5; **No** if the 90% CI of the median
  ratio lies entirely below 1.5; **Null** otherwise. At least 20 episodes per test. Each test is two-sided at
  α = 0.05 with a directional requirement, so effectively one-sided at α = 0.025.
- **One look:** the analysis ran once, on 2026-10-20 UTC.

## Result

| Test | n | p | Holm p | Median ratio | 90% CI | Verdict |
|---|---|---|---|---|---|---|
| H1 (fee tier) | 33 | 0.304 | 0.304 | 0.679 | [0.533, 0.825] | **No** |
| H2-Arbitrum (chain) | 25 | 0.381 | 0.762 | 0.947 | [0.388, 1.414] | **No** |
| H2-Base (chain) | 23 | 0.560 | 0.762 | 0.661 | [0.253, 1.906] | **Null** |

A median ratio below 1 means the comparison pool (0.3% for H1; Ethereum for H2) had the shorter recovery time on
the median episode. That direction was not pre-registered and is not tested, so it is not a finding. Per-pool results, figures, sensitivity analyses, every deviation from the plan (D1–D23) and the
limitations are in [`REPORT.md`](REPORT.md).

## Files

| File | What it is |
|---|---|
| `REPORT.md` | The report, version 1.0. It is the reviewed draft v0.5 with only status lines changed, plus one corrected short hash (line 3 says so) |
| `figures/fig1_recovery_curves.svg` | Figure 1: depth-recovery curves per pool |
| `figures/fig2_log_ratios.svg` | Figure 2: per-episode log-ratios for the three tests |
| `figures/figures_data.json` | The data behind both figures |
| `HASHES.txt` | SHA-256 of every file in this folder |

The figure hashes match the report's Appendix G.2.

## How to reproduce

Everything below is in
[github.com/viter999/uniswap-liquidity-recovery](https://github.com/viter999/uniswap-liquidity-recovery); the full
detail is in the report's section 7 and Appendix G.

1. **Check the frozen code:** `python -I tools/freeze_hash.py --verify CODE_FREEZE_MANIFEST.md` should report
   "verified 35 files, 0 problems". The environment is in `requirements.lock` (Python 3.9.7, numpy 2.0.2,
   scipy 1.13.1, pytest 8.4.2).
2. **Re-run the one look from the published results:** with the release files in place (the wrappers, the override
   files, `decision.json`, the four `results_*.jsonl` and the four `checks_*.json`), run
   `tools/run_analysis_guarded.py` with its defaults. The analysis refuses to run unless every chain's checks
   passed. With the same inputs and the pinned scipy it is deterministic (bootstrap seed 20261017).
3. **Re-pull from the chains:** in the frozen order, (1) `python -m pipeline.price_only --go`; (2)
   `tools/run_depth.py --chain <chain> --go` for each chain, with Arbitrum via the pre-fetch wrapper and then the
   driver (report Appendix G.5); (3) `tools/coverage_check.py --chain ethereum,arbitrum`; (4)
   `tools/run_analysis_guarded.py`. The public RPC endpoints and their limits are described in the report's
   section 3; a fresh pull depends on those endpoints still serving the same data.

## Limitations

The main ones (see the report's section 6 for all):

- **Power:** the spread of the per-episode values was far larger than the preregistration assumed; a rough,
  not pre-registered approximation gives about 35%, 11% and 13% power. The verdicts rest on the bootstrap CIs.
- **Base checking:** Base has no full-replay route, so swaps are checked on the snapshot route for in-band swaps
  only; 58 of 7,089,162 Base window swaps were unchecked. Episode 46 is unusable on both Base pools (outage).
- **Unichain:** the 0.05% pool was excluded at the freeze; the 0.3% pool is exploratory, absent for episodes 1–20,
  and missing from the analysis run.
- **Not done or from a different source:** the reorg re-check across the pull cutoffs, the Unichain analysis, the
  replenishment share, and the completeness second sources on Arbitrum and Base.
- **Procedures changed after the freeze** (data routes, timestamp sources, process control), but no analysis
  parameter changed; every change is listed in the report's Appendix C.

Not financial advice, and not a trading signal.
