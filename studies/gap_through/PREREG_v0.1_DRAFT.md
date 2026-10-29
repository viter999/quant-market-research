# PREREG — Gap-through after a crash bar (IOC buy) — v0.1 DRAFT

Owner: Natthaphong (Shawn) Suebsri. 29 Oct 2026. Status: draft for review. Nothing run on DEV or HOLDOUT outcomes.
Origin: exploratory finding in the crash-absorption VERDICT (commit d3b4b03, E3): orders that filled because the first trade after going live was already at or below L (667 "gap" fills) had a net of +67.7 bps per fill, while maker fills lost money. That number is POST-HOC and comes from one 200-day window. This prereg tests it on data whose outcomes nobody has seen.
Time cap: ≤ 7 calendar days from approval.

## 0. Data roles (all three segments come from the crash-absorption SPLITS.json)
- VERDICT (2025-08-26 → 2026-03-13): outcomes ALREADY SEEN. Used only for development (Phase A) and never as evidence.
- DEV (2024-01-01 → 2025-08-24): outcomes NEVER computed. Confirmation set 1.
- HOLDOUT (2026-03-15 → 2026-09-30): never downloaded. Confirmation set 2.
- The 31 Aug rule override from 29 Oct 2026 covers this study as a direct follow-up in the same family. It is not a new family.

## 1. Strategy (one primary rule)
- Same crash-bar detector, universe, exclusions and episodes as crash-absorption (PREREG §2 and §4 plus CLARIFICATIONS v0.3.1–v0.3.5), unchanged.
- At decision time τ = bar close + 2 s, send an IOC (immediate-or-cancel) limit BUY at L = close × (1 − 0.5%), $500.
- Fill model (realistic ask side): the order fills only if the first BUYER-initiated aggTrade (is_buyer_maker = false, i.e. at the ask) with timestamp in [τ, τ + 1 s] has price ≤ L. Entry = that price × (1 + 5 bps). If there is no buyer-initiated trade in that window, or it is above L, there is no fill. Nothing rests in the book.
- Why this changed from the exploratory rule: the old gap rule priced the entry at the first trade of either side. A seller-initiated print is at the bid, which a buyer cannot get, so it may have flattered the entry by half the spread.
- Exit: unchanged from crash-absorption §6. Taker sell at T = fill + 15 min, at the lower of (a) the seller-initiated VWAP in [T, T+10 s] and (b) the last seller-initiated trade at or before T within 60 s; drop and count if neither exists.
- Costs: taker entry 5 bps, taker exit 5 bps, buffer 5/10/25 bps at 1×/2×/5×, and signed funding if a settlement falls in (fill, exit].

## 2. Phase A — development on VERDICT (already seen, so not evidence)
- Compute the §1 rule on VERDICT and report fills, gross, net at 1×/2×/5×, and the old-rule vs new-rule comparison on the same events.
- No parameter search. The only things that may change after Phase A are bugs and data handling, and every change gets its own commit with a reason.
- Stop rule: if the VERDICT net per fill at 1× under the §1 rule is ≤ +10 bps, STOP. DEV and HOLDOUT are not touched, and the idea is closed as a bid-print artifact.

## 3. Phase B — confirmation (run once, frozen code, after Shawn's approval)
- Run §1 on DEV and on HOLDOUT. Each segment is evaluated on its own.
- Day-block bootstrap (resample days with ≥1 fill), 10,000 replicates, seed 20261101, percentile bounds; sensitivity with 7-day blocks.
- PASS only if ALL of the following hold in BOTH DEV and HOLDOUT:
  1. ≥ 150 fills, ≥ 60 episodes and ≥ 30 distinct days. If this fails: NOT EVALUABLE for that segment.
  2. Mean net per fill at 1× ≥ +20 bps, with the one-sided 99.5% lower bound > 0 under both 1-day and 7-day blocks.
  3. Mean net per fill at 2× ≥ +10 bps.
  4. Latency robustness: the mean net per fill at 1× with τ = close + 5 s is > 0.
  5. Concentration: the mean net per fill at 1× stays > 0 after removing the 3 days with the largest total PnL.
- Otherwise KILL. Published either way. No re-fit after any Phase B outcome.
- Power check before Phase B: count DEV fills under §1 using fill data only (no exit prices). If the projected fills are below 150 in either segment, stop and ask Shawn.

## 4. Descriptive only (labelled EXPLORATORY, no p-values)
- Depths 0.25% and 1.0%; holds of 5, 30 and 60 minutes; latency 10 s; the [τ, τ+2 s] fill window; the old-rule entry on the same events; results by month and by symbol volume rank; the share of PnL from the top 5 days.

## 5. Data and guard
- New study folder studies/gap_through/, with its own SPLITS guard: DEV and VERDICT are allowed now. HOLDOUT downloads are refused until Shawn approves Phase B, then allowed only through 2026-09-30.
- HOLDOUT needs: 1m klines for universe symbol-months, aggTrades for event symbol-days (window −5…+25 min), and the archive's monthly fundingRate (2026-03…09). No REST needed.

## 6. Gates (Shawn)
(a) this plan; (b) Phase B run including the HOLDOUT download; (c) any change to §1–§3.

## 7. What a PASS would and would not mean
- A PASS supports a small, live paper test of the IOC rule (real orders, measuring real fill rate and slippage). It is not a trading green light.
- Capacity is tiny by design: $500 per order, and the rule needs 1-second reaction.
