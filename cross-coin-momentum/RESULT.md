# Result — Cross-coin momentum, Binance USDT-M perps (PREREG_v0.2)

**Verdict: H1 FAIL. H2 not run (dropped). Project closed 2026-10-23.**

## Question

Do coins with the highest past 28-day return (skipping the last day) keep beating those with the lowest over the next week? Long top third / short bottom third, weekly, equal weight, funding included, net of 21 bps per side × turnover.

## Primary (one look, 2020-04-06 to 2022-12-19, 142 weeks)

- **Average net profit: −0.6 bps per week** (Newey-West t = −0.01, p = 0.50). Needed t > 1.645.
- **Without the 2 best weeks: −30.1 bps per week** (t = −0.57).
- Before costs: +31.6 bps per week (price +28.0, funding +3.6). Costs: 32.2 bps per week. Costs eat the whole gross edge.
- The two best weeks (2021-05-03, 2021-03-08) gave about +21% each, more than all the other weeks combined.
- Leg BTC betas: long 1.10, short 1.14.
- The test could only detect about 1.1–1.7% per week, so this does not prove momentum is zero. It shows no tradable edge after costs.

## Checks

- Prereg frozen before any signal-vs-return number: sha256 `ad213a5d…dc8f`, HASHES.txt.
- Fake-data check passed first: 6% of 200 shuffles rejected on gross (limit 9%), mean −1.3 bps (z = −0.51).
- Code and implementation notes hashed before the check; results hashed and read-only.

## Replication 2023-2026 (descriptive only, already seen, not pass/fail)

- 195 weeks: **−24.3 bps per week** net (t = −0.95); −35.6 without the 2 best weeks.
- Before costs +7.5 bps; costs 31.9 bps.

## H2 (AMT value-area score)

Not run. Dropped by the user on 2026-10-23 before any AMT data was downloaded or looked at, because the primary failed and momentum earns nothing after costs.

## Files

PREREG_v0.2.md, DATA_REPORT.md, IMPLEMENTATION_NOTES.md, HASHES.txt, CHANGELOG.md, TRIALS_LEDGER.md, results/.
