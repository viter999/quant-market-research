# CLARIFICATIONS v0.2.1 — implementation rules for PREREG v0.2 (no outcome seen; PROPOSED, pending Shawn)

Written before any price, return or funding sum was computed. Only volume and bar presence were looked at (§1 exclusions).

§1 events (decisions by Shawn, 29 Oct 2026)
- Raw source: `events_raw/binance_futures_delistings_v2.json` (sha256 `0691a0d1…bfd03`, all 77 bodies); v1 kept for the record. The parser reads `body_raw`; on v1 it reproduces the earlier output exactly.
- OMGUSDT: its delisting was postponed twice (notices 2024-12-14 and 2024-12-20, to 2025-01-31 09:00). The trade uses the ORIGINAL D and N of its own article (D 2024-12-16 09:00, N 08:30), which is what a trader knew at A. The postponement is noted in `events.csv`. Postponement notices are not episodes.
- The 2026-03-13 14:14 article (VFY, 1000WHY, BDXN; D 2026-03-17) is excluded: its window needs data after 2026-03-13. It is never downloaded.
- FTT (2022-11-13, "Binance Will Delist FTT Margin Pairs, USDⓈ-M Futures Contracts and Binance Flexible Products") fails the frozen title filter and is excluded by rule (`unselected.csv`).
- USDT-margined only: BUSD-quoted, USDC-quoted and COIN-M contracts are dropped. 2022 names ("AKRO USDT-Margined Contract") map to the archive symbol (AKROUSDT).
- MINAUSDT (2023-02-06) was a trading suspension, not a delisting. It is in the selection (its title matches) and drops out under D − A < 12h.

§1 exclusion windows (A is rarely on a minute boundary; a0 = A floored to the minute)
- "24h before A" = the 1440 1m bars with open time in [a0 − 24h, a0); every one has closed by A.
- "No perp 1m klines" = none of those bars exists in the archive.
- "24h quote volume" = sum of their quote volume.
- "Median 1m volume" = median quote volume over the bars that exist.
- "[A−30m, A+30m]" = the 61 bars with open time in [a0 − 30m, a0 + 30m]; the event is kept if their largest quote volume is ≥ 3 × that median.
- The rules are applied in PREREG order (no klines → volume < $5M → D − A < 12h → timestamp); each excluded event is reported once, under the first rule it fails.
- An event that passes §1 but lacks its entry bar, its exit bar, the BTCUSDT bar at entry or exit, or a fundingRate month inside [A − 24h, D] is dropped and reported as data-missing. This is checked from bar/file presence only, before any outcome. Item 1 counts the remaining events.

§2 trade
- Entry bar = the first 1m bar opening at or after A + 30m. Exit bar = the bar opening at N − 30m.
- Gross = (entry − exit) / entry. Net = gross − 2 × 5 bps taker − 2 × buffer (25 / 50 / 125 bps per side at 1× / 2× / 5×) + funding.
- Funding: settlements with entry-bar open < time ≤ exit-bar open are summed (archive `last_funding_rate`). A short receives +rate. Funding = rate × entry notional (no mark-to-market).
- BTC-relative: BTC return r = BTCUSDT close of the exit bar / close of the entry bar − 1; BTC-relative net = net + r (the short's return on the token minus BTC).

§4 verdict
- Episode net = the mean of its usable events. Episodes with no usable event are dropped.
- Bootstrap: 10,000 resamples of episodes with replacement (numpy `default_rng(20261103).integers`). The one-sided 99% lower bound is the 1st percentile of the replicate means; the 99% upper bound (significantly negative check) is the 99th percentile.
- Item 6 removes the 3 episodes with the highest 1× net and needs the mean of the rest > 0.

§5 descriptive (EXPLORATORY; computed in the same single run, no claims)
- A → A+15m: close of the bar opening at a0 + 15m / open of the bar containing A (opening at a0) − 1.
- Entry at A+15m / A+60m: same rule with the delay replaced.
- Bar extremes: short at the entry bar's low, cover at the exit bar's high.
- Exit at D − 24h: cover at max(open, close) of the bar opening at D − 24h, if after entry.
- Long mirror: buy at max(open, close) of the entry bar, sell at min(open, close) of the exit bar; pays the funding the short receives.
- Max adverse move: highest high over the hold / entry − 1.
- Also: results by year, restriction-flag split, and funding share (|funding| / (|gross| + |funding|)).
- Spot-delisting vs futures-only is NOT computed: the event list has no spot-delisting field, and adding one now would change §1 after the list was frozen.
- All §5 items are at 1× costs.
