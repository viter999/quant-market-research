# Kronos-small next-24h direction on Binance perpetuals: a pre-registered, one-look test

**Result: DROP.** Kronos-small's next-24h direction forecast did not beat random after fees, and showed no
BTC-relative skill before fees either. Both pre-registered tests failed.

## What was tested

- **Question:** does the Kronos-small foundation model's next-24h direction forecast on Binance USDT-M perpetual
  futures beat random after fees?
- **Model:** Kronos-small, Hugging Face `NeoQuasar/Kronos-small` at revision `901c26c1…`, tokenizer
  `NeoQuasar/Kronos-Tokenizer-base` at `0e011738…`, code `shiyu-coder/Kronos` at commit `67b630e6…`.
  The full pins and weight hashes are in `PREREG_kronos.md` §2.
- **Test window:** 457 daily forecasts, 2025-07-01 to 2026-09-30.
  - It starts on the first 00:00 UTC day after the weights were published on Hugging Face (2025-06-30 16:44 UTC).
  - The paper (arXiv:2508.02739, Appendix D) says the pre-training data extends up to June 2024, so the window is out of sample.
- **Universe:** the top 30 USDT-M perpetuals by quote volume in June 2025, frozen before the test.
  - Stablecoin and metal pairs were excluded.
  - Each coin needed complete hourly data for the window plus 512 warm-up bars.
  - The list is in `PREREG_kronos.md` §4.
- **Forecast:** every day at 00:00 UTC, for each coin:
  - Input: the previous 512 hourly bars.
  - Kronos-small predicts 24 hours ahead with T = 1.0, top_p = 0.9 and 10 sample paths, using a fixed seed per coin-day.
  - Signal = sign(mean predicted close at +24h − last close).
- **Tests** (pre-registered, α = 0.05, one-sided t-test on the 457 daily values):
  - **PRIMARY:** daily mean over the 30 coins of signal × 24h return − 0.10% fee per trade.
  - **SECONDARY:** daily mean over the 29 non-BTC coins of signal × (return − BTC return), before fees.
  - PASS only if both pass, and PASS would mean a written follow-up plan, never trading. Otherwise DROP.
- **One look:** the analysis ran exactly once. It allowed no reruns with other settings.

## Result

| Test | Mean per day | t | one-sided p | Result |
|---|---|---|---|---|
| PRIMARY (after 0.10% fee) | −0.108% | −1.20 | 0.88 | fail |
| SECONDARY (BTC-relative, before fees) | −0.002% | −0.04 | 0.51 | fail |

Report-only figures (not part of the decision):
- **Hit rate:** 50.53% of 13,508 coin-days.
- **Random-sign comparison:** 58% of 10,000 random-sign runs scored at least as well as Kronos on the primary test.
- **Always-long:** −0.158% per day after fees.
- **Before fees:** every coin-day traded, so the primary result before fees is about −0.008% per day.

Full details, including the per-month table, are in `REPORT_kronos.md`.

## Files

| File | What it is |
|---|---|
| `REPORT_kronos.md` | The one-look report written by `scripts/analyze.py` |
| `PREREG_kronos.md` | The pre-registration, frozen before any test-window computation |
| `AMENDMENTS_kronos.md` | Every change after the freeze, logged before any result. Two passages are redacted for privacy (marked); they concern the operator's setup, not the method or the data |
| `FREEZE_kronos.sha256` | SHA-256 of the prereg, scripts, universe, Kronos code, weights and the 480 input data files |
| `colab/FREEZE_colab.sha256` | SHA-256 of the Colab GPU files, frozen before the Colab run |
| `results/forecasts.csv` | All 13,710 forecasts of the counted run (one row per coin-day: context-window fields, last close `c0`, signal, 24 predicted closes) |
| `results/colab_manifest.json` | Completion manifest of the counted run (row count, forecasts.csv SHA-256, software versions) |
| `results/analysis.json` | Every number from the one analysis, written by `analyze.py` together with the report |
| `results/daily_series.csv` | The 457 daily values: PRIMARY, SECONDARY, always-long net, hits and trades per day |
| `data/universe/universe_frozen.json` | The frozen 30-coin universe (listed in `FREEZE_kronos.sha256`) |
| `data/universe/ranking_2025-06_quote_volume.csv` | June-2025 quote-volume ranking of all USDT-M perpetuals, used to pick the universe (listed in `FREEZE_kronos.sha256`) |
| `scripts/*.py` | The frozen laptop scripts: universe, forecasts, analysis, tests |
| `colab/*.py`, `colab/kronos_colab.ipynb` | The frozen Colab GPU forecast loop, notebook, acceptance script and tests |
| `HASHES.txt` | SHA-256 of every file in this bundle |

All files except this README, `HASHES.txt` and `AMENDMENTS_kronos.md` are byte-identical to the project originals.
Those listed in the two FREEZE files can be checked against them.

AMENDMENTS_kronos.md in this bundle is redacted (private operator details only), so its hash differs from the internal original; no method, code or result changed.

**Not included:**
- **Public inputs:** the Binance input data, the Kronos code and the model weights. Each can be re-downloaded and
  checked against `FREEZE_kronos.sha256`.
- **The unused CPU backup run:** it was stopped at 2,861 of 13,710 forecasts and retired unopened under the
  pre-declared rule; it was never analysed.

## How the counted run was produced

- **Planned:** the forecasts were first run on a laptop CPU (about 50 s per forecast).
- **Amendment 2:** before any result existed, a GPU run on Google Colab (Tesla T4) was added, with the same frozen
  code, data, settings and seeds. Under a pre-declared rule, the Colab run counts if it completes first.
- **Outcome:** it completed (4 sessions; forecasts.csv SHA-256 `ba1edccb…4e86c`, recorded in the manifest and in
  `AMENDMENTS_kronos.md`). The CPU run was then retired unopened, and the frozen analysis ran once.

## How to reproduce

**1. Check the published numbers without the original layout (easiest).**
- Use `results/forecasts.csv` plus Binance's public hourly klines
  (`https://data.binance.vision/data/futures/um/monthly/klines/<SYMBOL>/1h/`).
- For each row:
  - `r = close of the bar opening at day+23h / c0 − 1`, where c0 is the close of the bar opening at day−1h.
  - `P_day` = mean over the 30 coins of `signal·r − 0.001`.
  - `S_day` = mean over the 29 non-BTC coins of `signal·(r − r_BTC)`.
- Run one-sided one-sample t-tests (mean > 0) on the 457 values of `P_day` and of `S_day`.
- The full specification is in `PREREG_kronos.md` §6–7.

**2. Re-run the frozen analysis exactly.**
- **Environment:** Windows, Python 3.11, with numpy 2.4.6, pandas 2.2.2, scipy 1.17.1 and torch 2.14.1 (CPU).
  The key versions are in `PREREG_kronos.md` §2.
- **Layout:** the scripts expect the project at `C:\kronos-test` (the `ROOT` constant in `scripts/kt_common.py`).
- **Files:** `analyze.py` first checks every file listed in `FREEZE_kronos.sha256` at its relative path, so all of
  them must be present:
  - the prereg, scripts and Kronos `model/*.py`
  - both model folders
  - the 480 data zips under `data/raw/futures_um_monthly_klines/`
  - the two universe files under `data/universe/`
- **Universe files:** both are included in this bundle under `data/universe/` and match `FREEZE_kronos.sha256`.
- **Run:**
  1. Create `C:\kronos-test\logs\`.
  2. Put `results/forecasts.csv` in place.
  3. Run `python -I scripts\analyze.py`.

  It refuses to run if `results/REPORT_kronos.md` already exists. The random-sign comparison uses the fixed seed
  20250701.

**3. Re-run the forecasts.**
- **On CPU:** `scripts/run_forecasts.py --mode full` takes about 7–9 days on a 6-core laptop.
- **On GPU:** use `colab/kronos_colab.ipynb` with a data bundle built by `colab/make_bundle.py`.
- **What to expect:** the seeds are fixed, but GPU and CPU draw different random streams, and results can differ
  across hardware and software versions. A fresh run is a new draw of the same procedure, not a copy of the
  published one.

## Limitations

- **Universe selection:** the full-data rule dropped two June-2025 top-30 coins, RESOLVUSDT (rank 25) and
  SAHARAUSDT (rank 29). They listed in June 2025, too late for the 512-hour warm-up, and ranks 31–32 replaced them.
  No coin was dropped for a delisting or a data gap inside the window. The universe still favours coins with at
  least about 21 days of history.
- **Costs:** a flat 0.10% round trip per coin-day. Funding payments, slippage and spread are not modelled.
- **Statistics:** a plain t-test on 457 daily values. Serial correlation is not corrected for; that was pre-registered.
- **Device:** the counted run was on a GPU, decided before any result (Amendment 2). GPU and CPU forecasts are
  different random draws of the same procedure.
- **Scope:** one model size (small), one sampling setting, one horizon (24h), 30 coins, one 15-month window. The
  result says nothing about other models, settings, horizons or markets.
- **Model internals:** the model's 512-bar context equals the input length, so the oldest context slides out as it
  generates. The pinned code is used unmodified.
