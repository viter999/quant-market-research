# Whale Lab

Execution-state prediction for large TWAP parent orders on Hyperliquid.

---

## The research question

A TWAP (time-weighted average price) parent order executes as a long series
of small child fills. Given that such a parent order is **still live** at
some landmark time *t*, the study asks three things:

1. **Which terminal state** will the program reach — completed, terminated
   early, or ended in error?
2. **When** will it reach it?
3. **How much additional size** will execute before it does?

This is a question about *execution state*, not about price. Market returns,
P&L and markouts are excluded by preregistration. The study cannot, by
construction, produce a trading signal — and that scoping was deliberate,
because execution-state questions are answerable with the data available
whereas return questions at this sample size are not.

## The data

Public venue data from a third-party archive of Hyperliquid node output:

- **fills** — individual child executions, with the parent identifier that
  links them
- **TWAP statuses** — parent-order lifecycle records

The acquisition covers 16,861 hourly archive objects, roughly 85 GB, over a
one-year study window. One object was proven permanently absent at source
after repeated probes; it was recorded as absent rather than substituted or
interpolated.

## The preregistration approach

The protocol is written, committed and fixed with an annotated git tag before
the study runs. Three versions exist, each a freeze boundary:

- the original protocol,
- an amendment clarifying source-partition semantics,
- and the current v2 protocol.

Each tag pins the document's exact bytes, so the rules a study ran under can
be recovered and verified later rather than taken on trust.

## The first attempt failed

The first confirmatory attempt ran the frozen integrity pipeline and **failed
its gates**. Four gates passed; four did not, including the two that matter
most for this question:

- **duplicate actor-fill identity** — the same registered fill identity
  appeared more than once
- **parent/child reconciliation** — the child fills summed to the parent's
  declared executed quantity for **953,381 of 1,011,705** comparable parents,
  a rate of **94.2351%** against a required floor of 99.9%

**The attempt is recorded as failed and stays failed.** No model was fitted.
The dataset was not deduplicated, repaired or re-scored to produce a usable
result, and the failure was not reframed as a partial success.

## What the forensic work established

The failure was worth understanding even though the study was over, because
the same data pipeline would be reused. Three things were established, all of
them **engineering findings about data integrity, not predictive results**:

**The duplicates originate upstream, not in my pipeline.** Every affected
source object was reconciled against the raw archive on exact multiset
equality of the full scientific record. The duplicates are present in the
source; none were created by processing.

**Most of the reconciliation failure is attributable to those duplicates.**
Counterfactually removing only the mechanically proven source duplicates —
multiplicity-safely, retaining each proven record exactly once — accounts for
**98.80%** of the failing parents. Importantly, the gate would **still fail**
even then, because several hundred single-parent hard failures remain. The
counterfactual is a diagnostic; it never replaced the official result.

**The residue is a source-side discrepancy, not a pipeline defect.** For the
702 parents still failing, the raw archive, the admitted rows and the
processed rows agree exactly — decimal for decimal. The missing quantity was
never in the archive. It concentrates into 11 time-localised episodes
affecting many unrelated accounts simultaneously.

**One thing is deliberately left unresolved.** Whether the archive omitted
executed fills, or the venue's own status records overstated what it
published, cannot be distinguished with the two sources available. Both
remain live. Neither is asserted. Settling it would need an independent
venue-side record that this study does not hold.

## Why the original result remains failed

Because the counterfactual is not the result. Removing duplicates that were
genuinely present in the data produces a *hypothetical* dataset that was
never the study's input. Reporting 99.93% as though it were the outcome would
be reporting a number from a dataset that does not exist.

The permanent record is the failure. The forensic work explains it; it does
not replace it.

## What the next prospective test will do

The v2 protocol is frozen and tagged. Its structure:

- **Historical data is demoted to development use only.** The historical test
  split is prohibited from any predictive or evaluative use.
- **Confirmation comes from a new 30-day prospective window** that did not
  exist when the protocol was frozen — so the protocol cannot have been
  tuned to it.
- **The base model is fitted on TRAIN only**, with VALIDATION reserved for
  selection and calibration and no refit on the combined set before the test.
- **One window, one read.** No extension for low sample size, no replacement
  window, no early stopping, no post-result retuning.
- **The integrity implementation must pass an acceptance suite first**,
  including deliberately planted defects proving each check can actually
  fire.

The window was shortened from an earlier 73-day draft to 30 days for
project-timeline reasons. That costs statistical power and market-regime
coverage — a 30-day window may sit entirely inside one regime — and the
limitation was accepted and disclosed before any outcome existed.

**Current state: no model fitted, no test data collected, no result exists.**
