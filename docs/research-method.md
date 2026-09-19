# Research method

The method is the contribution. The individual results are mostly negative;
what makes them worth publishing is that they were set up so a negative
result *could* be reported.

---

## 1. Preregistration precedes the data

Before the first API call or the first query against a stored archive, a
preregistration document is written and committed. It fixes:

- the **question**, stated so it can fail;
- the **stopping rule** — the condition under which the hypothesis is dead;
- the **reading rule** — how the resulting number will be interpreted,
  written before the number exists;
- the **hurdle** — the effect size that would have to be exceeded to matter
  economically, not merely statistically;
- the **eligibility rules** — which observations count, and why.

Preregistrations are committed and, for the larger studies, fixed with an
annotated git tag. The tag is the freeze boundary: the document's content is
cryptographically pinned before the study runs.

This is the discipline that most independent quant work skips. Without it,
a "result" is indistinguishable from the best of many unrecorded attempts.

## 2. The stopping rule is binding

When a stopping rule fires, the hypothesis family closes. It is not
reopened, re-specified with a different window, or quietly replaced with a
neighbouring variant.

One study closed an entire family — directional perp microstructure — on a
single fired stopping rule. That decision was costly and it was honoured.

## 3. Economic hurdles, not just statistical significance

A result can be statistically real and economically dead. One study found a
statistically persistent effect that still failed its economic hurdle; the
relevant modelled round-trip cost range was 9–40 bps. The effect was real.
It was also unusable, and was recorded as such.

That 9–40 bps figure is a **cost model**, not a direct measurement — fee-only
taker cost on liquid instruments plus a spread and slippage proxy on thinner
ones. It is labelled as a model wherever it is used, because a reviewer once
found the project quoting two different "floor" numbers without definitions,
and the resulting reconciliation note is now part of the record.

Execution cost is also measured directly rather than assumed, because in this
domain it usually dominates. **Measured on 7,149 fills from January–July 2026
in one Binance USDT-M account: 42.4 bps all-in taker round trip — +8.1 bps
entry placement, +24.5 bps exit placement, and 9.9 bps commissions. Exits
cost roughly three times entries.** That ratio is placement, not price drift:
both legs are benchmarked against their own minute's mid, so movement while
the position is open contributes to neither.

**The limitation is part of the finding: one account, January–July 2026.**
It is not a venue-wide or population estimate.

## 4. Integrity gates block the pipeline

Before any analysis, the data passes a fixed set of gates — schema era,
source-partition containment, identifier canonicalization, actor invariants,
duplicate identity, and parent/child quantity reconciliation.

**A failed gate stops the study.** The failure is recorded permanently and
the result is published as failed. Nothing is deduplicated, repaired or
re-scored to produce a usable dataset. The Whale Lab v1.1 attempt did exactly
this: it failed, and it stays failed.

## 5. Claims are written at the resolution of the instrument

A recurring failure mode — in my own work as much as anyone's — is a claim
that outruns what the measurement could establish. The discipline is to state
what the instrument could actually distinguish, and to name explicitly what
it could not.

Where two explanations remain consistent with the evidence, both are
recorded and neither is asserted. The Whale Lab forensic work ends with an
unresolved question that could have been papered over with a plausible story;
it is written down as unresolved instead.

## 6. Every check must be shown able to fail

A monitoring check that has never fired is not evidence of health — it may
simply be incapable of firing. In one case a health check searched log output
for a string the logger never wrote; it returned zero hits across more than
19,000 lines and had been silently inert.

Consequently, integrity checks that have never fired on real data are
required to be demonstrated against deliberately planted defects before they
are trusted.

## 7. Provenance is byte-level

Results that later support a decision carry:

- the **generator** — the exact script that produced them;
- the **result artifact** — the output itself;
- **SHA-256 hashes** of both;
- an asserted **input corpus identity**, which aborts the run if the expected
  object and row counts are not seen.

This exists because a scan once ran against an unset data root, saw zero
objects, and returned a vacuous result that looked like a valid answer. The
corpus assertion makes that failure loud.

Related discipline: a hash covers a specific byte sequence. Line-ending
normalization silently changes those bytes, so text files whose exact bytes
matter are pinned to prevent it.

## 8. Power is computed before, not after

Where a study is underpowered, that is stated in advance rather than
discovered afterwards. One power analysis established that months of data
required scale as 1/IC², implying roughly 31 months for the effect sizes in
question — which redirected effort from chasing a thin result toward building
infrastructure that could eventually support a real one.

Low power is reported as the result. It does not license extending a window,
collecting a replacement sample, or stopping early.

---

## What this method does not give you

It does not produce a profitable strategy, and it has not produced one here.
It produces *reliable knowledge about what does not work*, which is cheaper
to obtain honestly than expensively in the market — and it leaves an audit
trail that a reviewer can check rather than trust.
