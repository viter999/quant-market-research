# FROZEN — listing-fade VERDICT code (PREREG v0.2 + CLARIFICATIONS v0.2.1 PROPOSED)

Frozen 29 Oct 2026 before any outcome. The unlock is LF_RUN_VERDICT = the HEAD of the commit that adds this file, with a clean studies/listing_fade tree. If the review changes CLARIFICATIONS or code, a new freeze commit replaces this one.

- Sample after §1 (exclusions_summary.json): 249 universe rows → 211 usable rows, **157 episodes on 143 distinct launch days** (item 1 needs ≥ 120 / ≥ 70). Excluded: 36 vol_1h_lt_5M, 1 funding_record_missing (KATUSDT, 2026-03 beyond guard), 1 aggtrades_files_missing (AIAUSDT relaunch). §2 drops: 0 / 0 / 0.
- Tests: 16 passed. Dry run: synthetic world only (130 episodes); a real run without the token is refused (OutcomeLocked).

| file | sha256 |
|---|---|
| PREREG.md | 53a9becfefc8f20d… |
| CLARIFICATIONS.md | 69191430a06f6889… |
| events.csv | 8c326101c1d29f99… |
| articles.csv | 7e25d2d0345e50ef… |
| exclusions.csv | 8b395450f79e24a6… |
| exclusions_summary.json | 260eed04da4e0539… |
| events_raw/binance_futures_launches_2023-2026.json | 0f82229c2f12c6f3… |
| events_raw/delisting_catalog161_titles.json | dda37fa2fdbad0db… |
| lf/__init__.py | e3b0c44298fc1c14… |
| lf/archive.py | 84d171e0d7ac4cae… |
| lf/events.py | 5b2a99536fec34b0… |
| lf/guard.py | 26daf225bd9708bf… |
| lf/lock.py | 22d78d6055062790… |
| lf/verdict.py | bd08827534816906… |
| scripts/download_data.py | f7f33855b769ac1c… |
| scripts/exclusions.py | 70a4e32abbd78761… |
| scripts/parse_events.py | ddd0f483924481c4… |
| scripts/run_verdict.py | 98d72daa0125b69b… |
| tests/test_guard.py | d27bb530749d9c62… |
| tests/test_parse_events.py | 3d51cbea03de1fd5… |
| tests/test_verdict.py | a55a3f0e93eac7ce… |
