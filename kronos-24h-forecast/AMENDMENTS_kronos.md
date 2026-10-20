- 2026-10-18T11:34:03Z: Bug fix found in plumbing check: kt_common.py called SetPriorityClass/SetThreadExecutionState/GetSystemPowerStatus via ctypes without declared types, so the 64-bit process handle was truncated and priority stayed Normal. Declared HANDLE/DWORD types and made failures raise. No design change; no test-window forecast had run. Aborted plumbing output kept in results/plumbing_aborted_1 (1 pre-window row). (new FREEZE SHA-256 a7b9ba2a38419443b4363a2b4d69689157dcebacb73704c1e4452269ed5fbee8)
- 2026-10-18T12:47Z: Note, no code change, no re-freeze. Plumbing check (attempt 2) ran all 90 forecasts and all 14 checks passed; results/plumbing/PLUMBING_REPORT.md was fully written. The script then exited 1 because its final console print of that report contained a non-ASCII character the cp874 console cannot encode (-I makes Python ignore PYTHONIOENCODING). Checked that run_forecasts.py, analyze.py, kt_common.py and kt_binance.py print only ASCII.
- 2026-10-18T14:06Z: **AMENDMENT 2 (owner, before any result exists): add a Google Colab GPU run.**
  Logged before any Colab file was built. No outcome has been computed; `results/forecasts.csv` has not been opened.
  - Only the device changes: CPU -> Colab CUDA GPU. Same frozen Kronos commit `67b630e6...`, same model and tokenizer
    revisions (`901c26c...`, `0e01173...`, weight SHA-256 as in FREEZE), same input data files (SHA-256 checked inside
    Colab against `FREEZE_kronos.sha256` = `a7b9ba2a...`), same settings (Kronos-small, pred_len 24, T=1.0, top_p=0.9,
    top_k=0, sample_count=10, clip=5, one coin per call, seed = YYYYMMDD*100 + coin index), same 13,710 forecasts,
    same `scripts/analyze.py` (run once, here), one look.
  - The laptop CPU run keeps going as a backup. Its `forecasts.csv` stays unopened.
  - Which run counts (owner's rule): the Colab run, IF it completes all 13,710 forecasts. Then the CPU run stops and its
    output is retired unopened. If Colab fails, the CPU run counts and Colab's output is retired unopened. Never analyze both.
  - Clarifications added by Claude when logging (stated before any result; owner may object before Colab runs):
    1. Cutoff: "Colab completes" means a complete 13,710-row forecasts file, matching the SHA-256 in its manifest,
       is delivered to this laptop before the CPU run reaches 13,710. The frozen CPU runner starts `analyze.py` by itself
       at 13,710, so that moment is the deadline; if the CPU run gets there first, the CPU run counts.
    2. Retiring the CPU run = stop its process, remove the log-on task `KronosTest-ResumeFullRun` so it cannot restart,
       move `results/forecasts.csv` unopened to `results/retired_cpu_run/` and record its SHA-256 only.
       The Colab file is then copied to `results/forecasts.csv` and the frozen `analyze.py` runs once, unchanged.
    3. GPU numbers will not equal CPU numbers. For the same seed, CUDA draws a different random stream than the CPU, and
       GPU float arithmetic differs, so the Colab run is an independent draw of the same frozen procedure (reproducible
       against itself), not a copy of the CPU run.
    4. Software around Kronos differs: Colab's own Python/torch/numpy/pandas versions, recorded in the run manifest.
       einops 0.8.1, safetensors 0.6.2 and huggingface_hub 0.33.1 are pinned as on the laptop. TF32 is switched off,
       so the GPU uses full fp32 as on the CPU.
    5. The frozen runner is Windows-only, so Colab uses a new loop, `colab/colab_forecasts.py`, that mirrors
       `scripts/run_forecasts.py`. Before use it must reproduce frozen pre-window plumbing forecasts bit for bit on this
       laptop's CPU, and on Colab it checks a SHA-256 of the parsed input bars, not just of the files.
    6. SHA-256 of the Colab files (script, notebook, bundle) will be appended here before Colab runs anything.
  - 2026-10-18T14:16Z: Owner accepted clarifications 1-6. Owner added clarification 7:
    7. Only one analysis can ever run. The moment the Colab file is accepted (complete 13,710 rows, SHA-256 matching
       its manifest, all consistency checks passed), and BEFORE it is copied into `results/`:
       a. Stop the CPU run: end its `run_forecasts.py --mode full` processes.
       b. Switch off its automatic analysis so it can never fire: delete the log-on task `KronosTest-ResumeFullRun`,
          rename `START_OR_RESUME_FULL_RUN.cmd` to `START_OR_RESUME_FULL_RUN.cmd.retired`, and hold the CPU runner's
          lock (`results/run.lock`) through acceptance and the analysis, so no copy of the CPU runner can start.
       c. Retire its partial forecasts unopened: move `results/forecasts.csv` and `results/progress.txt` to
          `results/retired_cpu_run/`, recording only SHA-256 and byte size.
       Only then is the Colab file copied to `results/forecasts.csv` and the frozen `analyze.py` run once. Its own guard
       (refuses if `results/REPORT_kronos.md` exists) stays as the last line of defence.
       If instead the CPU run counts, Colab's output stays on Google Drive, never downloaded or opened.
  - 2026-10-18T15:43Z: Clarification 6 done. Colab files frozen before Colab ran anything:
    `colab/FREEZE_colab.sha256` SHA-256 **75031286af34d744c885121f0b715f00de4170d1003c50f62cb068c57510d9a2**, listing
    colab_forecasts.py `deafda18...`, kronos_colab_bundle.zip `f967be10...`, kronos_colab.ipynb `affc7fb4...`,
    accept_colab.py `c1076040...` and 6 helper/test files. accept_colab.py refuses real acceptance unless every listed file
    still matches, and every Colab session must report the frozen script and bundle hashes and the pinned helper versions.
  - Review before freezing: one fresh read-only reviewer (owner's choice, instead of a multi-agent workflow) checked the
    one-analysis guarantee, blinding, Colab fidelity and acceptance robustness. 11 findings, all confirmed by Claude
    against the code and fixed. No blinding leak and no fidelity difference was found. Main fix: acceptance now stops the
    CPU runner and holds its lock FIRST, re-checks under the lock, and only then disarms and retires (it previously checked
    before stopping, a narrow race that could have produced two analyses).
  - How clarifications 1 and 7 are implemented: the deadline is evaluated at acceptance time, under the CPU runner's lock
    (the safe direction). Acceptance also refuses and leaves the decision to the owner, changing nothing, if the CPU run
    is at 13,700 or more, or if any analysis has ever started (`logs/analysis_attempts.log`, `analysis.json` or
    `daily_series.csv` exists), or an analyze.py process is running. accept_colab.py is run detached (own window) so no
    caller timeout can interrupt the analysis, and it logs to `logs/accept_colab.log`.
  - Laptop tests on the frozen versions (CPU): Colab script reproduces the frozen runner's pre-window rows bit for bit
    (2 rows x 37 columns); stop/resume/complete rehearsal passes; self-test passes; acceptance sandbox 25/25 checks pass;
    read-only preflight on the real system finds the CPU runner (launcher + child), the log-on task and the launcher.
  - KNOWN LIMITATION for the final report (owner, 2026-10-18; no change to the universe): the "full data for the window plus
    512 warm-up bars" rule dropped two coins from the June-2025 top 30, both through the warm-up part because they listed
    in June 2025: RESOLVUSDT (June rank 25, listed 2025-06-10, 21 warm-up bars missing) and SAHARAUSDT (June rank 29,
    listed 2025-06-26, 404 bars missing). Ranks 31-32 (LTCUSDT, MOODENGUSDT) took their places. No coin was dropped for a
    delisting or a gap inside the test window, so the survivor condition (prereg §10.1) removed nothing in practice;
    the universe still favours coins old enough to have 21 days of history.
- 2026-10-19T16:26Z: OPERATIONAL NOTE (no method change, no code change, frozen files untouched).
  [Redacted for public release: private operator details.]
- 2026-10-20T19:00Z: PRE-ACCEPTANCE AUDIT (read-only, no change). Colab download in `incoming/colab_final/`: forecasts.csv
  SHA-256 `ba1edccbae797e991f7a54c4108a843376481ae1fb83b9056aaca9cc9cc4e86c`. This equals the hash the owner read in
  Colab's final cell and the hash in colab_manifest.json (complete, 13,710 rows, finished 2026-10-20T18:37:02Z, frozen
  script `deafda18...`, FREEZE digest `a7b9ba2a...`). `accept_colab.py --check-only` passed: 13,710 rows, all frozen
  consistency checks, c0 equal to the frozen input data, 4 sessions all on Tesla T4 with the frozen script, bundle and
  pinned packages (Python 3.13.15, torch 2.11.0+cu130, CUDA 13.0, pandas 2.2.3), same-seed self-test bit-identical in all 4.
  Row provenance, from the day and finished_utc columns only: d12b214f36d2 rows 1-8,190; 633e61143e7f rows 8,191-8,199;
  ac5b69977e9e rows 8,200-11,091; 9cb0c81770c3 rows 11,092-13,710. The blocks are consecutive and do not overlap in
  time; the file is in schedule order. [Redacted for public release: private operator details.]
  CPU backup at this time: 2,861 / 13,710, so acceptance is allowed under clarifications 1 and 7.
  - 2026-10-20T19:01:34Z: ACCEPTANCE (clarification 7). Colab forecasts accepted: 13,710 rows,
    SHA-256 ba1edccbae797e991f7a54c4108a843376481ae1fb83b9056aaca9cc9cc4e86c, 4 session(s) on Tesla T4. CPU run stopped (2 process(es)) and its
    lock held; log-on task removed; launcher renamed. Retired unopened: forecasts.csv sha256 c700b6bd90eadfce0113af34d2c47565a9bbd550bd2667e8ce116825ba81550d bytes 1681549; progress.txt sha256 db57905d5b9ec851065ab277610b449b8b5d1d7a661c18e7518ba408582534b8 bytes 151.
    Colab file installed as results/forecasts.csv; running the frozen analyze.py once.
  - 2026-10-20T19:01:41Z: analyze.py exited 0; REPORT_kronos.md written.
