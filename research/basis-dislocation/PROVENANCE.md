# Provenance — perp–spot basis dislocation study

## Current interpretation — read this before the findings

The original findings document uses the word "reliably" for the validation
result. A subsequently opened frozen historical holdout showed a smaller
**+1.23 bps** effect with a 90% CI of **[−0.04, +2.50]**, spanning zero. I
therefore do not describe the effect as confirmed, prospective, or reliably
replicated.

| | n | gross mean | 90% CI |
|---|---|---|---|
| validation | 82,619 | +3.78 bps | [+2.69, +4.91] |
| frozen historical holdout | 90,556 | **+1.23 bps** | **[−0.04, +2.50]** |

- The holdout **is not prospective.** Its data already existed when the
  preregistration was written — every window in the study is historical.
- It was **untouched until after the validation verdict was frozen** and
  committed, with thresholds unchanged. That is what it controls for:
  peeking and threshold-fitting, not hindsight in choosing the period.
- **The holdout weakened the result.** The effect shrank and its interval
  came to include zero.
- **The economic verdict is dead regardless.** Both figures sit far below the
  58 bps round-trip hurdle; the validation estimate was already roughly
  fifteen times too small to trade.

The findings document is preserved byte-identical as a historical record. Its
wording is not amended — this note supersedes it as the current reading.

## What these two documents are

- `PREREG_basis_dislocation.md` — the preregistration: the hypothesis, the
  three-way date split, the frozen thresholds, the kill conditions and the
  economic hurdle, all fixed before any outcome was computed.
- `FINDINGS_basis_dislocation_20260831.md` — the result, read under exactly
  those rules. Primary verdict: **DEAD on the hurdle**.

## Published verbatim — no redactions

Unlike some material in this repository, these two files are **byte-identical
to the private originals**. A security scan found nothing requiring
redaction: no paths, usernames, addresses, credentials, account references,
database names or repository structure. Nothing was removed, softened or
reworded.

This is a property of the study, not of the sanitisation: it used **only
public market-data archives** — monthly 5-minute klines for perpetual and
spot legs — and touched no account, position or trading record at any point.

## The date split, and what kind of holdout this is

The preregistration declared a three-way temporal split before any outcome
statistic was computed:

| set | window (UTC) | days | role |
|---|---|---|---|
| DEFINE | 2026-01-01 → 2026-05-27 | 146 | thresholds only — no outcome ever computed |
| VALIDATE | 2026-05-27 → 2026-07-15 | 49 | the verdict |
| HOLDOUT | 2026-07-15 → 2026-09-01 | 48 | untouched until the verdict was committed |

**This is a frozen historical holdout, not a prospective test.** The
preregistration was committed on 2026-08-31, by which date the holdout window
had almost entirely elapsed. The data existed before the protocol was
written.

What the design does give is a genuine and auditable separation:

- thresholds were fitted on DEFINE only, frozen as absolute numbers per pair,
  and never re-estimated;
- **no outcome statistic was ever computed on DEFINE**, by rule, precisely to
  remove the temptation to peek;
- the verdict was computed on VALIDATE alone;
- HOLDOUT was opened **only after the VALIDATE verdict had been committed to
  git**, with the same frozen thresholds;
- the preregistration states in advance that holdout agreement "cannot flip a
  DEAD verdict to alive", and that a dead VALIDATE still gets its holdout
  opened "so the record is complete" — which is what happened.

Calling this prospective would be wrong, and the distinction matters: a
frozen historical holdout controls for peeking and threshold-fitting, but not
for the possibility that the whole period was selected with hindsight.

## The result, stated carefully

A small directional effect appeared in validation, **weakened materially in
the frozen holdout**, and remained far below estimated trading costs
throughout.

| set | n | gross mean | 90% CI |
|---|---|---|---|
| VALIDATE | 82,619 | +3.78 bps | [+2.69, +4.91] |
| HOLDOUT | 90,556 | **+1.23 bps** | **[−0.04, +2.50]** |

The holdout interval touches zero. The effect should therefore **not** be
described as reliable, confirmed, or validated out of sample. Against a
58 bps round-trip hurdle, the validate-set effect was already roughly
fifteen times too small to trade; the holdout figure is smaller still.

The study's own framing — that dislocations *do* move perp direction, just
far too little to matter — is a statement about the validate set. The holdout
weakens even that.

## The stopping rule fired

The preregistration carried a family-level stopping rule, and it triggered:

> Per the preregistration, the operator stops searching for a directional
> indicator in the perp-microstructure family entirely. This was declared the
> last hypothesis of that type. Any future preregistration in this family
> must quote this clause and state why it is being overridden.

That clause is the reason this study was chosen as the first public artifact.
It is a pre-committed rule closing an entire line of research, with an
override requirement that makes any future evasion visible in the record.

## Ordering, and what a public reader can check

The findings cite the preregistration at commit `cc0660a` (v2; v1 `e927b9e`
superseded before being run), and the holdout records being opened after
commit `5ff8589`.

**Can check:** that the split, thresholds, kill conditions and hurdle were
fixed in advance; that the findings report against exactly those conditions;
that the holdout is reported alongside validate rather than replacing it;
that the verdict follows from the stated rules; that the stopping rule's text
matches what the preregistration declared.

**Cannot check:** the commit ordering. The original repository is private, so
those hashes and their dates **cannot be independently verified by a public
reader**. They are offered as provenance, not as proof. This is not
cryptographically established and not publicly verifiable — a reader who
declines to take it on trust is being reasonable.

## Data

Archived monthly 5-minute klines from the exchange's own public data archive,
for both perpetual and spot legs. No REST API, no live feed, no account data.
The findings document records its own coverage limitations, including missing
archive files and the disclosed one-day shortfall at the declared boundary.

## Why publish a dead hypothesis

Because the negative result is the contribution, and because this one is
unusually instructive: the effect was *real* and still worthless. Separating
statistical reality from economic viability is the single most useful habit
in this domain, and this study is the clearest demonstration of it in the
programme.
