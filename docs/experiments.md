# Experiments

Five studies, chosen to show the process rather than to flatter the results.
Two are nulls, one is an integrity failure, one has not started, and one is
mid-development. **None is a validated trading edge.**

Labels: `NULL` · `FAILED INTEGRITY` · `PROSPECTIVE` · `DEVELOPMENT`

---

## 1. Perp-spot basis dislocation — `NULL`

**Question.** When the perpetual price dislocates from spot, does the perp
subsequently move to close the gap, by enough to trade?

**Method.** Preregistered with an economic hurdle and three kill conditions
fixed in advance. Event-weighted estimation with hour-clustered confidence
intervals, to avoid treating overlapping episodes as independent
observations. A separate holdout was specified and deliberately left unopened
at the verdict commit.

**Result.** A small directional effect appeared in validation — gross
event-weighted mean **+3.78 bps**, 90% CI [+2.69, +4.91], n = 82,619 — which
is roughly **15x too small** to survive the 58 bps round-trip hurdle. The
primary verdict was DEAD on the hurdle alone, with two of three kill
conditions also passing.

**The frozen holdout weakened it further.** Opened only after the validate
verdict was committed, with thresholds unchanged: **+1.23 bps**, 90% CI
**[−0.04, +2.50]**, n = 90,556. The interval touches zero. The effect is
therefore **not** described here as reliable, confirmed or validated
out of sample — it was small in validation, materially weaker in holdout, and
economically too small to trade in both.

**On the holdout's nature.** This is a **frozen historical holdout**, not a
prospective test. All three windows predate the preregistration commit; what
the split controls for is peeking and threshold-fitting, not hindsight in
choosing the period. That distinction is stated in the study's provenance
note rather than glossed.

**Status.** `NULL`. The stopping rule triggered, closing the **entire
directional perp-microstructure family**. This is the most expensive single
decision in the programme and it was honoured rather than renegotiated.

---

## 2. Post-settlement funding unwind — `NULL`

**Question.** After a funding settlement, do positions that paid funding
unwind in a direction that can be traded?

**Method.** Preregistered and pushed to the remote **before the first API
call**, with a 45 bps hurdle reflecting realistic round-trip cost.

**Result.** DEAD — kill conditions 1 and 3 each failed, either sufficient
alone. The verdict itself carried little information, because a 45 bps hurdle
on a publicly scheduled event was near-certain to fail by construction. The
informative part was the detectability question: **something is detectable at
settlement, and it points the opposite way** to the hypothesis.

**Status.** `NULL`. Recorded as a case where the interesting finding was not
the verdict.

---

## 3. Whale Lab E2 — first confirmatory attempt — `FAILED INTEGRITY`

**Question.** For a live Hyperliquid TWAP parent order: which terminal state,
when, and how much more size executes before it ends.

**Method.** Preregistered, then amended once before running. Full source
acquisition of 16,861 archive objects (~85 GB) through a resumable,
manifest-verified pipeline, followed by a frozen integrity pass over eight
gates.

**Result.** **The study failed its own gates.**

| gate | outcome |
|---|---|
| Identifier canonicalization | PASS |
| Actor invariants | PASS |
| Null-identifier check | PASS |
| Split firewall | PASS |
| Source-partition containment | FAIL |
| Source-integrity envelope | FAIL |
| **Duplicate actor-fill identity** | **FAIL** |
| **Parent/child reconciliation** | **FAIL — 94.2351%** |

Reconciliation succeeded for 953,381 of 1,011,705 comparable parent orders.

**Status.** `FAILED INTEGRITY`. The attempt is closed and the failure is
permanent. It was **not** repaired, deduplicated, re-scored or re-run to
produce a usable result. No model was fitted.

*(Forensic decomposition of this failure is summarised in
[whale-lab.md](whale-lab.md). It is an engineering explanation of a data
defect, not a predictive finding.)*

---

## 4. Whale Lab E2 v2 — `PROSPECTIVE`

**Question.** Unchanged from the first attempt.

**Method.** A new preregistration, frozen and fixed with an annotated tag
before any development work began. Historical data is demoted to
*development* use only; confirmation comes from a **new 30-day prospective
window** that did not exist when the protocol was frozen. The base model is
fitted on TRAIN only, with VALIDATION reserved for selection and calibration
and no refit on the combined set. Actor history for test rows is
left-truncated at the window start, so no development-era state leaks
forward.

**Result.** None. No model fitted, no data collected, no outcome exists.

**Status.** `PROSPECTIVE`. The window was reduced from an earlier 73-day
draft to 30 days for project-timeline reasons — a decision that costs
statistical power and market-regime coverage, taken and disclosed **before**
any outcome existed. The protocol forbids extending or replacing the window
based on what the results look like.

---

## 5. OFI Engine — `DEVELOPMENT`

**Question.** Can depth-normalized order-flow imbalance be measured reliably
enough on Binance USDT-M perpetuals to serve as a research input?

**Method.** A measurement-infrastructure project with explicit phase gates —
five successive gate-protocol versions — and golden test cases that must pass
before a phase closes. Deliberately scoped as measurement, not as a trading
system.

**Result.** Phase-1 measurement gate passed and live-verified.

**Status.** `DEVELOPMENT`. No predictive claim is attached to OFI here. It is
infrastructure a future preregistered study could consume.

---

## What is deliberately absent from this page

- Any study presented as a validated edge — there is none.
- Exact thresholds, scoring constants or alerting rules.
- Any study whose preregistration and reading rule I cannot point to.
