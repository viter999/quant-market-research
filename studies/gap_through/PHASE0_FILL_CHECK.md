# Gap-through — Phase 0: fill-model check (no outcomes)

Status: frozen before running. 29 Oct 2026. Approved by Shawn (chat, 29 Oct 2026).
Why: three reviewers (ChatGPT, Grok, Gemini) independently said a trade-tape fill model can't show whether an IOC buy at L would really fill, or at what price. Binance's archive has real best bid/ask (um/daily/bookTicker) only up to 2024-03-30. That covers the first ~90 days of DEV, and DEV outcomes have never been computed.

## Sample
All crash-absorption events (frozen detector, universe and exclusions) whose bar t closes between 2024-01-01 00:00 and 2024-03-30 23:30 UTC, and whose symbol has a bookTicker file for that day. Report how many events are dropped for lack of a bookTicker file.

## Measured per event (latency 2 s primary; 5 s and 10 s reported too)
τ = bar close + latency; L = close × (1 − 0.5%); order qty = 500 / L.
1. REAL fill (quote-based): the best ask in force at τ (the last bookTicker update at or before τ) is ≤ L, and its best-ask qty is ≥ the order qty. Real entry = that best ask. Also report fills where the ask is ≤ L but the qty is too small (partial).
2. PROXY fill (PREREG v0.1 §1): the first buyer-initiated aggTrade in [τ, τ+1 s] has price ≤ L. Proxy entry = price × 1.0005.
3. OLD rule (the crash-absorption gap case): the first aggTrade of either side at or after τ is ≤ L. Old entry = min(price × 1.0005, L).
4. Exit-price proxy check: at T = (real fill time τ) + 15 min, compare the exit proxy (the lower of the seller-initiated VWAP in [T, T+10 s] and the last seller-initiated trade ≤ T within 60 s) with the real best bid in force at T. Report only the difference in bps. Never pair it with an entry price.

## Reported (prices and agreement only, no returns, no PnL, no markouts)
- A confusion matrix of REAL vs PROXY fill and REAL vs OLD fill: counts, precision, recall.
- Entry bias in bps, on events where both fill: (proxy entry − real entry) and (old entry − real entry). Report mean, median, p10, p90 and n.
- Exit bias in bps: (exit proxy − real bid at T). Report mean, median, p10, p90 and n.
- The spread at τ (ask − bid, in bps) on REAL-fill events.

## Decision rule (fixed now)
The PROXY model is ACCEPTED for Phase B only if ALL of these hold at 2 s:
- (a) at least 30 REAL fills;
- (b) PROXY precision ≥ 0.85 and recall ≥ 0.85 against REAL;
- (c) the mean entry bias (proxy − real) is ≥ −5 bps, i.e. the proxy is not more than 5 bps cheaper than the real ask on average;
- (d) the mean exit bias (exit proxy − real bid) is ≤ +5 bps.
If ACCEPTED: Phase B uses the PROXY model plus an extra cost equal to |mean entry bias| + |mean exit bias| (if either is adverse), and these 90 days are excluded from DEV in Phase B.
If NOT ACCEPTED: the idea is closed as untestable with archive data. The option of recording live quotes is noted.
If (a) fails (fewer than 30 real fills): report NOT ENOUGH DATA; Shawn decides.
