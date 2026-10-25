# Deviations from PREREG_v0.1 (sha256 b97646e941795872f6001c0aa87af32a334d6df2cd8287a320e5346a5dbde5ff)

## DEV-1 — free-RAM guard around P02/P03 (2026-10-22, after code freeze, before P02)

**Decided by:** the operator, in chat, 2026-10-22, before any P02 output existed: "P02 must check free
RAM before loading and between steps. If it's under 3 GB, pause and wait; never push through. Whale Lab
is running on this [redacted: machine detail] and must not be starved."

**What changes.** Nothing in the analysis. Two files are added: `scripts/ramguard.py` (reads available
physical memory; below 3 GB it pauses and re-checks every 30 s until memory is back) and
`scripts/p02_guarded.py`, which runs the same steps as the frozen `p02_run.main` by calling the frozen
functions (`load`, `analyse_config`, `discovery_verdict`, `confirmation_verdict`, `report`, `sha256`)
unchanged, with a RAM check before loading, before the primary configuration, before each sensitivity
and before writing. The frozen `p02_run.py`, `stats.py`, `vol.py`, `universe.py`, `common.py` and
`breakout_study.py` are not edited; `CODE_FREEZE.sha256` still verifies.

**Why it is a deviation.** §11 says the analysis code is hashed before P01 and any later change is a
DEV-n. The wrapper is run-time plumbing, but it is code that runs the look, so it is logged here and
hashed in `CODE_FREEZE_DEV1.sha256` before P02 starts. Its RAM log is `p02_ramguard.log`.

**What had been seen before this deviation.** P00 (file hashes and dates) and P01 (eligibility counts).
No range, forecast, loss or verdict.

## DEV-2 — confirmation-stage tooling written after the code freeze (2026-10-22, after P02, before P00c)

**Decided by:** the operator's instruction in chat, 2026-10-22: run P00c (download 2020-01..2022-08,
exclusions from names + metadata before any price is read) and P00d (data audit), then stop.

**What changes.** Nothing in the analysis. Three run-time scripts are added, adapted from the frozen
breakout tools: `scripts/download_confirm.py` (plan phase lists the archive and the files in range,
fetch phase downloads them; 4 workers, 429/418 back-off, RAM guard that pauses at 3 GB; USDT perpetuals
by name, i.e. symbols ending in USDT without "_", the same filter the breakout download applied),
`scripts/build_exclusions_confirm.py` (the DEV-1 "crypto only" rule, run between plan and fetch so the
list is written and hashed before any kline exists on disk) and `scripts/p00d_audit.py` (the breakout
P00b checks, klines only). Metadata: `metadata/exchangeInfo_20261022.json` is a byte copy of the breakout
study's same-day snapshot (sha256 `aeabf21a6268357b94c94bff41c1729476f960e38cde08718629cb67b80768ab`);
no new metadata fetch. The frozen analysis files are not edited; `CODE_FREEZE.sha256` still verifies.
Hashes of the new files, and of this file after this entry, are in `CODE_FREEZE_DEV2.sha256`.

**What had been seen before this deviation.** P00, P01 and the P02 discovery look (WINNER C). No
confirmation kline existed on this [redacted: machine detail].

## DEV-3 — confirmation exclusions v2: DOTECOUSDT excluded (2026-10-22, after P00c/P00d, before P01c)

**Decided by:** the operator, in chat, 2026-10-22: "Exclude DOTECOUSDT (index, same as BLUEBIRD/FOOTBALL):
exclusions_confirm v2, logged as a DEV before P01c."

**What changes.** `exclusions_confirm_v2.txt` = v1 (sha256
`e8b499c4e810d08862d48bc401d11e37c380d2ccd4ed539270c27c749a1bb9c5`, unchanged, no longer used) plus
DOTECOUSDT, the DOT ecosystem index contract: no metadata today, an index by name, the same case as
BLUEBIRD and FOOTBALL under the breakout DEV-1. One line of the frozen `scripts/common.py` changes: the
CONFIRMATION sample's exclusions path now points at v2. Nothing else in the code changes; the new hash of
`common.py` and the v2 file are in `CODE_FREEZE_DEV3.sha256`, and `CODE_FREEZE.sha256` now reports
`common.py` as changed for this one line. Included confirmation symbols: 154 (was 155). DOTECOUSDT has 31
rows (2021-01-20 .. 2021-02-19) and could never pass the 120-day clock, so no count or statistic moves.

**Also ruled (no file change):** the 2022 archive holes (2022-02-26..28 and 2022-04-01..02, about 50
symbols each) stay as the frozen cleaning rules treat them, non-trading days with no clock restart;
no extra daily files are fetched.

**What had been seen before this deviation.** P00c (dates, hashes) and P00d (data audit). No forecast,
loss or count on the confirmation data.

## DEV-4 — universe filter written down: USDT-margined perpetuals by name (2026-10-22, before P01c)

**Decided by:** the operator, in chat, 2026-10-22: "Universe filter (USDT-margined, no underscore):
accepted; log it as a DEV for consistency with discovery."

**What it is.** The archive listing holds 1,056 symbol folders. Only those ending in `USDT` with no `_`
(900) were planned and downloaded: BUSD-margined perpetuals (`…BUSD`) and dated delivery contracts
(`…USDT_YYMMDD`) are outside the universe. This is the filter the breakout download applied to the
discovery data (`download_log/symbols_archive.csv` there), so the two samples use the same universe
rule; PREREG_v0.1 names "Binance USDT-M crypto perpetuals" but did not spell the filter out. No file or
code changes; the list of all archive symbols with the flag is `download_log_confirm/symbols_archive.csv`.
