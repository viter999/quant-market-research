# Findings — Perp–Spot Basis Dislocation (PREREG_basis_dislocation.md v2 @ `cc0660a`)
**Date: 2026-08-31. VALIDATE verdict. HOLDOUT not yet opened at this commit — it follows
in a separate commit, per §3.**

**PRIMARY verdict: DEAD — on the hurdle alone. Kill 2 and kill 3 both PASS.**
**SECONDARY verdict: CONVERGES.**
**§0 stopping rule: TRIGGERED — the directional perp-microstructure family is closed.**

---

## The estimate and CI, first

> **Dislocations DO predict perp direction — reliably, typically, and 15× too small
> to trade.** Gross event-weighted mean **+3.78 bps**, 90% hour-cluster CI
> **[+2.69, +4.91]** — excludes zero on the predicted side. **Median +4.47 bps** —
> the typical event, not a tail. Hit rate 51.5% on n = **82,619**.

This is the first hypothesis this month where the *typical* event goes the predicted
way: the mean/median ratio is 0.85 — the median is *stronger* than the mean. Every
robustness line agrees:

| line | mean bps | 90% CI |
|---|---|---|
| primary (hour clusters, n=82,619, 1,176 hrs) | +3.78 | [+2.69, +4.91] |
| symbol bootstrap (352 pairs) | +3.78 | [+3.19, +4.41] |
| BTC-relative | +2.98 | [+2.22, +3.72] |
| rich arm → SHORT (n=56,387) | +3.73 | [+1.60, +5.89] |
| cheap arm → LONG (n=26,232) | +3.89 | [+0.73, +7.21] |

Both arms positive independently. One arm-level honesty note: the cheap/LONG arm's
**median is exactly 0.0** (hit rate 49.9%) — the typical cheap-side event does nothing;
the rich/SHORT arm carries the typical effect (median +5.63).

## §6 kill conditions (VALIDATE, full sample)

| # | condition | result | pass? |
|---|---|---|---|
| 1 | gross mean ≥ 58 bps | **+3.78** | **FAIL** |
| 2 | 90% CI excludes zero | [+2.69, +4.91] | pass |
| 3 | median > 0 | +4.47 | pass |

**DEAD as a trade** — net −54.2 bps per event after the 58 bps round trip. Nothing is
built. But unlike every other kill this month, conditions 2 and 3 passed: the mechanism
is demonstrated, in the operator's own tradeable leg, at a size only a maker-fee/HFT
cost structure could touch.

## SECONDARY — convergence

Mean **+7.48 bps** of |basis| closed in 30 minutes, 90% CI [7.29, 7.68], median +5.65,
**64.2% of dislocations shrink**. Read against PRIMARY: the perp's directional move
(+3.78) is roughly **half** of the total convergence (+7.48) — the gap closes through
BOTH legs, not spot alone. The §1 declared reading ("converges but direction doesn't
predict → spot leg → null for the operator") therefore does **not** apply cleanly:
direction *did* demonstrate. What stands is its tradeability arm: at +3.78 bps gross,
one-legged capture is dead against any taker cost structure, so the practical outcome
for the operator is the same null. The exact per-leg decomposition is a §10 diagnostic.

## §0 stopping rule — TRIGGERED, binding

> The validate set produced **82,619** qualifying dislocations under the frozen rule —
> far beyond the 1,000 threshold — and the gross effect is **+3.78 bps < 58 bps**.
> **Per the preregistration, the operator stops searching for a directional indicator
> in the perp-microstructure family entirely. This was declared the last hypothesis of
> that type.** Any future preregistration in this family must quote this clause and
> state why it is being overridden.

The month's closing arithmetic makes the clause easy to obey: funding settlement
(−3.4 bps), pre-entry taker flow (±0), and basis dislocation (+3.8 bps) — the family's
best member pays a twentieth of the round trip.

## §6b branch — not applied

Settlement-overlap share of validate onsets: **11.7%**, under the 25% trigger. Per the
v2 amendment the overlap stays a post-verdict diagnostic; no second table is produced.

## Controls, floor, coverage

- **Control 1 (synthetic +50 bps injection): PASS** — recovered 49.55 bps (expect
  ~49.8, tolerance ±5).
- **Control 2 (premiumIndexKlines): PASS, narrowly** — per-day correlations 0.753,
  0.479, 0.307, 0.538, one n/a; median **0.509** against the declared 0.5 bar. Passed
  as declared, and reported as the near-thing it was rather than rounded up. The
  weaker days are thin pairs where the multi-venue index legitimately diverges from
  single-venue spot.
- **Floor: MET by two orders of magnitude** — 82,619 events (≥400), 1,176 hour
  clusters (≥150). Realized per-event SD **107 bps**, *below* the assumed 250 — the
  declared caveat does not fire; the realized MDE (~1.4 bps at this N) makes the test
  vastly overpowered for its question.
- Pairs: **373 eligible** of 466 identity-name candidates (93 thin/absent DEFINE data);
  excluded by rule: **multiplier family 16**, **no spot listing 352** — half the perp
  universe has no identity-name spot market, so this result describes the
  **spot-listed, more established half** of the universe, stated rather than implied
  away. 807 of 6,531 monthly files missing (late listings/delistings inside the split).
- Event validity exclusions: entry legs 0/0; exit perp 7; **exit spot 5,664** — thin
  spot books go stale within the 30-minute window; these events are excluded, not
  zero-filled, per the stale-leg rule.

## Honesty notes on the event class

- 82,619 onsets over 49 days across 373 pairs ≈ **4.5 per pair-day**: at p99 on 5m
  bars, "dislocation" is a *dense microstructure condition*, not a rare shock. The
  effect is a small persistent drift on a frequent state — which is exactly why the
  arb-desk prior ("what survives to a 5m close is what the desks left behind") and the
  +3.8 bps magnitude are the same fact.
- The onset rule requires the previous bar valid-and-inside, so feed gaps cannot
  manufacture onsets; July's monthly file spans the validate/holdout boundary and was
  masked to onset dates < Jul 15, with only the ≤25-minute exit spillover of
  Jul-14-late onsets read past it. No August file was downloaded for this verdict.

## Reproducibility

Prereg `cc0660a` (v2; v1 `e927b9e` superseded unrun). Artefacts:
`scripts/basis_dislocation_20260831/` — `run_validate.py`, `thresholds.csv` (per-pair
frozen thresholds), `events.csv` (82,619 rows), `results.json`, `run_log.txt`.
Seed 20260831; 10,000 resamples; kline archives only, no REST market data; perp months
and settlement times reused read-only from the funding-unwind artefacts.

---

## HOLDOUT (§3, confirmation-only)
Opened after commit `5ff8589`, frozen thresholds, no re-estimation. Window
Jul 15 00:00 → Aug 31 00:00 UTC — July from the cached monthly files, **August from
the DAILY archive** (monthly zips unpublished on the run date), with Aug 31 itself
unpublished: the declared Sep 1 boundary is short by one day, disclosed here. 21,638
daily files served, 772 missing (3.4%); exit-spot staleness excluded 8,474 events.

| | n | gross mean | median | hit rate | 90% CI |
|---|---|---|---|---|---|
| PRIMARY (holdout) | 90,556 | **+1.23** | +2.20 | 50.7% | **[−0.04, +2.50]** |
| PRIMARY (validate, for reference) | 82,619 | +3.78 | +4.47 | 51.5% | [+2.69, +4.91] |
| SECONDARY convergence (holdout) | 90,556 | +5.01 | +3.45 | 59.6% | [+4.87, +5.15] |

**Read honestly:** convergence **confirms cleanly**. The directional effect **does not
replicate at validate strength** — same sign, roughly a third of the size, and the
holdout CI grazes zero. Two candidate explanations, neither testable here without
sweeping: a quieter Jul–Aug regime, or mild adaptation of the DEFINE-set thresholds to
the adjacent validate period. Per §3 the holdout is confirmation-only and the verdict
is unchanged (it was DEAD regardless); what it qualifies is the mechanism claim — the
defensible statement is **"+1 to +4 bps of 30-minute perp reversion, sign stable,
magnitude regime-dependent,"** not "+3.8 bps." The stopping rule stands a fortiori:
the out-of-sample estimate is even further below 58.


## Appendix — §10 diagnostics
Run after commits `5ff8589` and `3f89556`. Descriptive only; verdicts unchanged.

**Response curve from entry (signed perp bps, VALIDATE):**

| | rich→SHORT mean / median | cheap→LONG mean / median |
|---|---|---|
| +5m | +2.99 / +3.22 | +3.38 / +2.60 |
| +15m | +3.58 / +4.46 | +3.96 / +3.03 |
| +30m (the test) | +3.73 / +5.63 | +3.89 / **0.00** |
| +60m | +4.94 / **+7.24** | +5.43 / **0.00** |

The rich arm's median grows monotonically through the hour; the cheap arm's typical
event flatlines at zero from +30m — the reversion that exists is, typically, the rich
perp coming down.

**Convergence decomposition at +30m — AND A CORRECTION.** Measured per leg, the pull-back
in the deviation splits: **perp +3.78 bps (17%), spot +18.13 bps (83%)**. The validate
section above says the perp delivers "roughly half of the total convergence" — that was
arithmetic on the wrong pair of numbers (3.78 vs the 7.48 |basis| change, which is not
the leg-sum: overshoot past the median makes |basis| shrink less than the deviation
pulls back). **The correct statement: the perp is a minority mover; five-sixths of the
reversion happens in the spot leg.** This substantially reinstates the §1 declared
reading — the gap closes mostly through spot, the leg the operator cannot hold — and it
is recorded here as a correction rather than edited into the section above.

**Settlement overlap detail:** near-settlement onsets (11.7%, n=9,628) average **+1.78**
vs +4.04 for the rest — the overlap *diluted* the result rather than inflating it. The
§6b worry ran the safe way.

**Fragility:** dropping each arm's single largest event moves the rich mean
+3.727 → +3.680 and the cheap mean +3.893 → +3.780; medians unchanged. For the first
time this month, an effect is **not** runner-driven.

