# Preregistration — Perp–Spot Basis Dislocation
**Status: written before any data was pulled. Commit and push before the first download.
Shown to the operator before running; data is pulled only on his go.**
Version 2, 2026-08-31. Supersedes v1 (not run). Change listed at the end.

---

## 0. What is different about this question — and the stopping rule it carries

Every hypothesis killed this month asked whether a feature of the perp predicts the perp.
This one asks whether a *disagreement between two prices of the same asset* is
information. The counterparty story is at least structural: leveraged flow pushes the
perp away from spot, and someone carries that inventory back.

### Binding stopping rule
> **If the validation set yields ≥ 1,000 qualifying dislocations under the frozen rule
> and the gross event-weighted mean signed perp return is below 58 bps, the operator
> stops searching for a directional indicator in this family — perp-microstructure
> features predicting perp direction — entirely. This is the last hypothesis of that
> type.** This clause is binding, is restated in the findings file whichever way the
> result goes, and any future preregistration in this family must quote it and state
> why it is being overridden. If fewer than 1,000 dislocations qualify, the rule does
> not trigger and that is stated rather than treated as escape.

### Prior expectation
Null expected. Basis arbitrage is the most industrialised trade on these venues;
dislocations that survive to a 5-minute close are what the arb desks left behind.

---

## 1. Two hypotheses, same data, separate verdicts

**PRIMARY — direction.** When the perp is unusually rich or cheap against spot, does
the *perp itself* move predictably back? `direction = −sign(deviation)`: rich → SHORT
perp, cheap → LONG perp. This is the tradeable claim — the operator can hold one leg.

**SECONDARY — convergence (diagnostic only, never tradeable).** Does |basis| shrink
over the same window, regardless of which leg moves?

**Declared reading, fixed now:** if SECONDARY passes and PRIMARY fails, the gap closes
through the SPOT leg. Capturing that needs both legs, which the operator cannot hold.
**That outcome is a NULL for him and must not be written up as a positive finding.**
The reverse (PRIMARY passes, SECONDARY fails) would mean the perp trends without the
gap closing — reportable as what it is: momentum, not convergence.

---

## 2. Data and the basis definition

Both legs from archived monthly 5m klines on `data.binance.vision` (no REST):
- Perp: `data/futures/um/monthly/klines/<SYM>/5m/`
- Spot: `data/spot/monthly/klines/<SYM>/5m/`

**Timestamp alignment — the rule, stated because misalignment manufactures basis:**
both feeds key bars by `openTime` on the same UTC 5-minute grid. Basis at bar *t* pairs
the perp bar and the spot bar with **the identical `openTime`**, and both closes are
prices at the same instant *t*+5m. `openTime` is normalised by magnitude before any
comparison (spot dumps switched to microseconds in 2025; futures are milliseconds — a
raw equality would silently pair nothing). A basis observation exists only where **both**
bars are present and **both** are non-stale (`volume > 0` and `trade_count > 0`) — a
stale leg repeats its previous close and manufactures basis from the other leg's move.

```
basis_t = (perp_close_t − spot_close_t) / spot_close_t
```

### Pair eligibility
- Perp candidates: USDT-quoted PERPETUALs from exchangeInfo ∪ the vision directory
  listing (delisted included), as in the funding-unwind run.
- **Identity-name pairs only:** the spot symbol must equal the perp symbol exactly.
- **The multiplier family (`1000...`, `1000000...`, `1M...` prefixes) is EXCLUDED,
  counted, and named as an exclusion.** Pairing them needs a per-symbol multiplier
  convention, and one wrong multiplier manufactures a permanent fake dislocation —
  exactly the artefact class this file exists to keep out. Cost: some volatile symbols;
  accepted.
- Excluded and counted: perps with no identity-name spot listing; pairs with fewer than
  **10,000 valid basis observations in the definition set** (threshold not estimable).

---

## 3. Three-way date split — new discipline, declared exactly

| Set | UTC dates (inclusive → exclusive) | Days | Share | Role |
|---|---|---|---|---|
| DEFINE | 2026-01-01 → 2026-05-27 | 146 | 60.1% | thresholds ONLY |
| VALIDATE | 2026-05-27 → 2026-07-15 | 49 | 20.2% | **the verdict** |
| HOLDOUT | 2026-07-15 → 2026-09-01 | 48 | 19.8% | untouched until the end |

- On DEFINE, per pair: `median_basis` and the empirical distribution of
  `deviation = basis − median_basis`. **No outcome statistic is ever computed on
  DEFINE** — it exists to set thresholds, and computing returns on it would invite
  peeking.
- Thresholds are **frozen as absolute numbers per pair** after DEFINE and never
  re-estimated.
- The verdict — every kill condition in §6 — is computed on VALIDATE alone.
- HOLDOUT is opened **only after the VALIDATE verdict is committed to git**, with the
  same frozen thresholds, reported in the same table, labelled confirmation-only.
  **Holdout agreement strengthens or weakens confidence; it cannot flip a DEAD verdict
  to alive, and a dead VALIDATE still gets its holdout opened so the record is
  complete.**

## 4. Event definition — one rule, no sweeping

- **Percentile: 99th / 1st of the pair's own DEFINE-set deviation distribution**,
  two-sided and symmetric. Named once, here. Not tested at any other value.
- **Event = ONSET:** the first bar whose deviation crosses from inside to outside the
  frozen threshold. Rich onset (≥ p99) → SHORT arm; cheap onset (≤ p1) → LONG arm.
- **Cooldown: 60 minutes per pair-side** after an onset; crossings inside cooldown are
  not events. A dislocation episode is one decision, not fifty bars of the same one.
- Event validity: both legs present and non-stale at the entry AND exit bars (below);
  failures excluded with counts, split by which leg failed.

## 5. Trade definition (PRIMARY) and convergence measure (SECONDARY)

Bars keyed by `openTime`; T₀ = the onset bar's openTime.

- **Entry price** = perp close of bar T₀ (the onset is observable at that close).
  Execution instant T₀+5m.
- **Exit price** = perp close of bar with `openTime = T₀+30m`. Execution instant
  T₀+35m. **Exposure: exactly 30 minutes.**
- *Why 30m, chosen now:* dislocation half-lives are expected short (the arb exists);
  30 minutes is long enough to survive one bar of noise and short enough to still be
  "the event," and it is declared blind to every horizon tested this month.

```
PRIMARY:   signed_bps = direction × ln(perp_exit / perp_entry) × 10^4     (gross)
SECONDARY: convergence_bps = (|basis at T₀+5m instant| − |basis at T₀+35m instant|) × 10^4
```

PRIMARY is the **raw perp return — the quantity a one-legged account actually
captures.** A BTC-relative version (same instants, BTCUSDT perp) is reported alongside
as one robustness line, not the test. No winsorization, trimming, or clipping.

## 6. Reporting and kill conditions

Reported for PRIMARY, overall and per arm (rich/cheap): **N, gross mean bps, net mean
bps (gross − 58), median bps, hit rate** (share of events with gross > 0), mean/median
ratio, realized per-event SD. A mean has been one or two trades three times this month;
the median is load-bearing, not decorative.

**PRIMARY kill conditions — all three must pass on VALIDATE:**
1. Gross mean signed perp return **< 58 bps** → not tradeable.
2. 90% cluster-bootstrap CI **includes zero** → not demonstrated.
3. **Median signed return ≤ 0 → dead**, unconditional.

**SECONDARY kill conditions (diagnostic verdict, separate):**
1. Median convergence ≤ 0 → basis does not converge.
2. 90% cluster-bootstrap CI on mean convergence includes zero → not demonstrated.

Any PRIMARY failure → **nothing is built** — no signal, no panel column, no alert, no
follow-up on this data — and the §0 stopping rule binds if its trigger is met.
SECONDARY passing alone is the declared spot-leg null of §1, written up as a null.

## 6b. Pre-declared branch — funding-settlement overlap

The settlement bar is a KNOWN basis-mover as of this morning's funding-unwind run
(−21.8 bps signed in the settlement bar, ~2× the following hour). If dislocation
onsets sit next to settlements, a positive PRIMARY would be partly settlement wearing a
costume. The branch is therefore declared now, before any data:

- **Before the verdict is read**, compute the share of VALIDATE onsets falling within
  **±15 minutes of a funding settlement on that pair.** Settlement times come from the
  already-committed `scripts/funding_unwind_20260831/funding_all.csv.gz` (read-only
  reuse of an existing artefact; covers the VALIDATE dates in full).
- **If the share exceeds 25%:** the PRIMARY verdict table is reported **twice** — the
  full sample, and the sample excluding those onsets — with the exclusion version
  labelled a **declared robustness check**, not a post-hoc rescue. **Both are stated in
  the findings regardless of which looks better.** The §6 kill conditions apply to the
  full sample; the excluded variant qualifies confidence, in either direction.
- **If the share is 25% or under:** the overlap remains exactly what §10 makes it — a
  post-verdict diagnostic behind the firewall, and no second table is produced.

## 7. Inference — clustering declared before measurement

Dislocations cluster in time and across symbols: one volatility shock fires many pairs
at once. **Clustering unit: the UTC calendar hour of the onset bar.** Coarse enough to
hold a market-wide episode together, fine enough to keep power; declared here, before
anything is measured. Primary CI: resample hours with replacement, all events within a
drawn hour retained, 10,000 resamples, seed **20260831**, 90% percentile CI.
Robustness (reported, not a second test): the same bootstrap on **pairs** — one symbol
with a broken spot feed would correlate its own events in a way hour-clustering cannot
see. Arms with fewer than 100 events are labelled underpowered.

## 8. Power floor — fixed number, arithmetic shown

Assumptions, declared: per-event SD of 30-minute raw perp returns at disturbed moments
**σ = 250 bps** (this month's measured 15-minute SDs were 200–450); within-hour ICC
ρ = 0.3 with mean ~3 events/hour → design effect ≈ 1.6; MDE ≈ 2.49 × SE.

SE = σ·√(deff/N). At N = 400: SE = 250·√(1.6/400) ≈ 15.8 → **MDE ≈ 39 bps < 58 ✓.**
If realized σ were 400 bps: SE ≈ 25.3 → MDE ≈ 63 bps, marginally above — accepted and
stated, with realized σ > 500 reported as a caveat on the MDE (verdict rules unmoved).

> **Floor, both required on VALIDATE: N_events ≥ 400 AND N_hour-clusters ≥ 150.**

Below either → **NOT EVALUABLE.** The window is not widened, the percentile is not
moved, the split is not redrawn.

## 9. Positive controls — both must pass, else NOT EVALUABLE

1. **Synthetic injection (pipeline arithmetic):** for one pair-day, shift the spot leg
   by exactly +50 bps and re-run the basis computation; the pipeline must report the
   injected 50 ± 5 bps. Proves the code computes what the formula says.
2. **External instrument (alignment):** for 5 random pair-days (seed 20260831), the
   correlation between computed basis and Binance's own `premiumIndexKlines` close
   (perp vs multi-venue index — a related but independently produced series) must have
   **median ≥ +0.5**. Misaligned or mispaired feeds decorrelate this immediately. The
   index is not single-venue spot, so agreement is expected to be strong, not perfect —
   which is why the bar is 0.5, not 0.9.

A failed control voids the run before any verdict is read.

## 10. Diagnostics — after the VALIDATE verdict is committed; firewall as before

Descriptive only; nothing here alters a verdict.
- Response curve from entry: +5m, +15m, +30m, +60m, signed, per arm.
- **Funding-settlement overlap:** per §6b — a diagnostic here only when the share is
  ≤ 25%; above that it becomes the pre-declared dual-table reporting in §6b.
- Convergence decomposition: of the |basis| change, the share delivered by the perp leg
  vs the spot leg (the §1 declared-reading check, made visible).
- Fragility: each arm's mean recomputed without its single largest |return| event.

## 11. No sweeping

Frozen: 99/1 percentiles, DEFINE-set thresholds, 60m cooldown, 30m exposure, 58 bps
hurdle, hour clustering, the date split, floor 400/150. Not computed, not looked at:
other percentiles, other horizons, other cooldowns, per-regime splits, volatility
conditioning, threshold re-estimation on later data.

## 12. Order of operations
1. Commit and push this file. **Show it to the operator. Data is pulled only on his
   explicit go; corrections before the go become v2, superseding this file unrun.**
2. Enumerate pairs; report pair-eligibility counts (no spot listing, multiplier family,
   thin DEFINE data).
3. Download DEFINE + VALIDATE klines only — **holdout months are not downloaded until
   step 8.** Perp months already cached from the funding run are reused; reuse is
   read-only and does not constitute a data pull for this test.
4. Run both §9 controls. Fail → NOT EVALUABLE, stop.
5. Compute DEFINE thresholds; freeze; report per-pair threshold summary.
6. Detect VALIDATE events; apply exclusions with counts; check the §8 floor; below →
   NOT EVALUABLE, stop.
7. Compute PRIMARY and SECONDARY; apply §6; write the dated findings file with the
   VALIDATE verdict; commit and push.
8. Open HOLDOUT: download its months, apply the frozen rule, report the same table,
   append to the findings as confirmation-only; commit and push.
9. Diagnostics appendix, committed separately.

---
## Changes from v1
- **§6b added (operator amendment, before any data was pulled):** the funding-settlement
  overlap is computed before the verdict; if more than 25% of VALIDATE onsets sit within
  ±15 minutes of that pair's settlement, the PRIMARY table is reported twice (full
  sample and settlement-excluded) with the exclusion labelled a declared robustness
  check — both stated regardless of which looks better. At or under 25% it stays a
  post-verdict diagnostic. Settlement times reuse the committed funding-unwind artefact
  read-only. Nothing else changed; v1 was never run.
