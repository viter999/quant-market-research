# Funding and roadmap

---

## The problem

Independent crypto execution research is dominated by unfalsifiable claims.
Strategies are published without hurdles, execution cost is assumed rather
than measured, and negative results are not reported — so the public record
is systematically biased toward things that appear to work.

The consequence is that an independent researcher cannot build on anyone
else's findings, because almost none of them state what would have made them
wrong.

## What I built

- Venue connectors developed across seven exchanges, with a supervised,
  documented deep-collection package for Binance USDT-M and a never-prune
  history layer for research
- A resumable, manifest-verified acquisition pipeline for third-party
  archives, currently holding roughly 85 GB for a single study
- A blocking integrity-gate system with decimal-exact reconciliation
- Byte-level provenance tooling: generators, hashed artifacts, and corpus
  assertions that abort rather than return a vacuous result
- A preregistration practice with a substantial body of registered
  hypotheses, each tagged before running

## What I learned

Mostly that the candidate signals do not survive contact with cost.

- A statistically present effect can be **15x too small to trade**: +3.78 bps
  in validation against a 58 bps hurdle — and it weakened to +1.23 bps, with
  the interval touching zero, in a frozen historical holdout. Small in
  validation, weaker in holdout, economically untradeable in both.
- An effect can be statistically present and still fail its economic hurdle.
  The relevant modelled round-trip cost range was 9–40 bps — a **cost model**
  (fee-only on liquid instruments plus a spread and slippage proxy on thinner
  ones), not a direct measurement.
- **Execution cost dominates, and it was measured directly.** On 7,149 fills
  from January–July 2026 in one Binance USDT-M account: **42.4 bps all-in
  taker round trip** — +8.1 bps entry placement, +24.5 bps exit placement,
  9.9 bps commissions. **Exits cost roughly three times entries.** The
  limitation is part of the result: one account, January–July 2026.
- Sample size is the binding constraint. Months of data required scale as
  1/IC², implying on the order of 31 months for the effect sizes in
  question. That finding redirected effort from chasing thin results toward
  building infrastructure capable of eventually supporting a real one.
- Data integrity is not a formality. A full study failed its gates, and
  understanding why took substantially longer than running it.

## Current scientific uncertainty

**Whether execution state — not price — is predictable for large TWAP parent
orders.**

Deliberately narrower than a returns question, because it is answerable with
the data available, whereas a returns question at this sample size is not.

The protocol is frozen and tagged. No model has been fitted. No prospective
data exists.

## Next milestone

1. Implement the v2 integrity rules and pass an acceptance suite that
   includes planted defects proving each check can fire
2. Reprocess historical development data under the frozen rules
3. Fit on TRAIN, select and calibrate on VALIDATION, then freeze the model
4. Run a single 30-day prospective confirmation window
5. Read once, by the rule written before the data existed, and publish the
   result either way

The most likely outcome, on the base rate of this programme so far, is
another null. The protocol is built so that a null is publishable rather
than discardable.

## Use of funds

Categories, not amounts. The repository does not support specific figures and
inventing them would undermine the point of the rest of this document.

| category | what it covers | why it is the constraint |
|---|---|---|
| **Storage** | archive retention across venues and studies | one study alone is ~85 GB; multi-venue history grows continuously |
| **Data access** | requester-pays archive egress, venue data | acquisition costs scale with study scope |
| **Compute** | integrity reprocessing and forensic passes | currently multi-hour passes on a single laptop, memory-bound |
| **Reliability** | a small always-on collector host | collection currently depends on a personal machine staying awake; observed gaps trace directly to machine sleep |
| **Research time** | running frozen protocols to completion | a 30-day prospective window plus analysis is calendar-bound and cannot be compressed |
| **Research software** | acceptance suites, provenance tooling | this is what makes results auditable rather than merely asserted |

**Not requested: trading capital.** This programme does not need capital to
trade, and asking for it would change what the research is for.

## What a funder is actually backing

Not a strategy — there isn't one yet, and this document does not claim
otherwise.

What exists is infrastructure and method: the ability to ask a falsifiable
question about market microstructure, answer it under rules fixed in advance,
and report the answer honestly whichever way it comes out. On current
evidence that capability produces negative results at a steady rate. The bet
is that the same capability eventually produces a positive one that is
actually real — and that, in the meantime, the negative results are worth
having.
