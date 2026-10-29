# RESULT — Crash absorption with resting limit orders: **KILL**

Pre-registered test (PREREG v0.3 + CLARIFICATIONS v0.3.1–v0.3.5), run once on the VERDICT period 2025-08-26 → 2026-03-13 on 2026-10-29. Fill-proxy study; no claim of a tradable edge either way.

## Question and answer
**Question.** On Binance USDT-M perps, after a 1-minute crash bar, does a resting buy limit 0.5 % below the bar's close, filled under a conservative trade-level rule, earn a positive mean return over the next 15 minutes after realistic costs, and more than matched placebo orders?

**Answer.** No. Filled orders lost 18.8 bps on average after costs, and did worse than placebo orders placed at comparable times.

## Primary result (d = 0.5 %, 20× queue, 2 s latency, 15-min exit)
| Item (PREREG §8) | Result | Required | |
|---|---|---|---|
| 1. Sample | 8,150 fills, 2,486 episodes, 200 days | ≥ 300 / 100 / 40 | pass |
| 2. Mean net per fill, 1× buffer | **−18.8 bps**; 99.9 % lower bound −41.0 (1-day blocks), −39.5 (7-day blocks) | ≥ +15 bps and LB > 0 under both | fail |
| 3. Mean net per fill, 2× buffer | **−23.8 bps** | ≥ +5 bps | fail |
| 4. Beats placebo, per fill | difference **−4.8 bps**; 99 % LB −29.7 | ≥ +10 bps and LB > 0 | fail |
| 4. Beats placebo, per order | difference **−5.2 bps**; 99 % LB −17.1 | > 0 and LB > 0 | fail |

15,820 events (372 symbols), 51.5 % filled (667 gap/taker fills, 7,483 maker fills), 0 dropped fills, 0 missing aggTrades files in either arm. Bootstrap: whole UTC days resampled, 10,000 replicates, no empty replicates.

## Why it failed
- **Maker fills are adversely selected.** Under the queue rule an order fills only after 20× its size has traded *below* the limit, i.e. only when sellers keep pushing through the level. Those fills are followed by further weakness: maker fills averaged **−15.1 bps gross** before any fee or buffer (−26.6 bps net). Fills happen precisely when absorbing the flow is a bad trade.
- **No edge over the placebo.** Placebo orders at matched times (same symbol, hour, volatility and volume) also lose (−14.1 bps net per fill), but the event orders lose more. Liquidity provision into these crashes was not paid; if anything it was penalised relative to ordinary volatile minutes.
- Costs (2 bps maker, 5 bps taker exit, 5 bps buffer) are not the reason: the gross result of all primary fills is already negative (−7.2 bps).

## EXPLORATORY — descriptive only, no claims
The following patterns were seen *after* the outcome was known. They are post-hoc, were not part of the test, and none would justify a re-fit. Each would need its own pre-registration and evaluation on data not used here (the untouched HOLDOUT, or later data).
- **Gap fills** (the first trade after the order goes live is already at or below the limit; taker entry): **+67.7 bps net** on **667 fills** (+81.3 gross). Small and selected sample.
- **October 2025** is the only month with a positive mean (+29.7 bps net per fill on 1,489 fills); all seven other months are negative (−12.6 to −47.2).
- **Depth 1.0 %** is less negative (−14.0 bps net per fill at 20× / 2 s, fill rate 34 %) than 0.5 % (−18.8) or 0.25 % (−16.9); still negative in every latency/queue cell.
- Also descriptive: 60-min exit −8.1 bps net, 30-min −34.2; B2 (taker buy at the crash-bar close) −7.8 bps net (+6.8 gross); all 27 depth × latency × queue cells are net negative.

## Limitations
- **Fill proxy, not real fills.** Without order-book replay, queue position is approximated by "20× the order size traded strictly below the limit". Real fills and placement lag can only be measured live.
- **No order-book data.** Exits use seller-initiated trades as the bid; spreads, depth and slippage beyond the fixed buffer are not observed.
- **30 % of events had no placebo** (4,746 of 15,820) because no comparable minute met the matching rules; item 4 uses the other 11,074 events. Items 1–3 use all events.
- Universe artefact (noted before the run, not changed): delisted symbols can stay in the top-80 for up to 7 days on earlier volume (23 of 16,000 VERDICT member-days); no order can fill on those days.
- VERDICT funding for 2026-03-01…13 came from the REST API (fetched by Shawn in a browser, Thailand); it matched the archive exactly on the 2026-02 overlap (176 symbols, 0 ms / 0 rate difference).

## Reproducibility
| Item | Value |
|---|---|
| PREREG v0.3 | commit `9a1a7bc` (first commit; nothing run) |
| CLARIFICATIONS | v0.3.1 `190b2a0`, v0.3.2 `916f350`, v0.3.3 `acb4000`, v0.3.4 `a98044b`, v0.3.5 `1fdb170` — all before any outcome; approved (gate d) with gate b |
| Splits (`SPLITS.json`, `fe3f06b`) | DEV 2024-01-01→2025-08-24, VERDICT 2025-08-26→2026-03-13, HOLDOUT 2026-03-15→2026-09-30, 1-day embargoes |
| Exclusions | `EXCLUSIONS.json` v1.0 FROZEN, `089965a` |
| Code run | HEAD `a516b7794311f89f3922e94aa7ca539139c1ca6b` (`CA_RUN_VERDICT`; HEAD and tree verified unchanged at the end) |
| Funding | raw file sha256 `006e11f6c1e4cbcefa177e0722a978b98c9ad54f45c66a72915fce40aaddb3f2` (commit `339c051`); converted manifest sha256 `8c0dc5c099fc69cf6656abe16076bd29ac78d25202376e675b6e173b7ed5a858` |
| Seeds | placebo draws 20261029, bootstrap 20261030, sanity sample 20261031 |
| Result | commit `d3b4b03`: `results/verdict/VERDICT_RESULT.json` sha256 `458e1548…c0fd`, `VERDICT_REPORT.md` `f36ef347…563b` |
| Run | once, 2026-10-29 07:08:39 → 08:07:28 UTC; no re-run, no parameter change |

**HOLDOUT (2026-03-15 → 2026-09-30) is untouched and has not been downloaded.** The code refuses any file dated after 2026-03-13. Under the PREREG, HOLDOUT is only used after a PASS, so this study ends here.
