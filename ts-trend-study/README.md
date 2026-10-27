# Time-series trend on Binance perpetuals: a pre-registered, one-look test

**Result: FAIL.** A fixed Donchian breakout rule, traded long and short on the 30 most liquid Binance USDT-M
perpetuals with volatility-scaled sizing, lost 18.5% over 2022–2023 at the judged cost (2x) and still lost
14.7% at base cost: no edge, not an edge eaten by costs. Start with `RESULT.md`.

## Files

| File | What it is |
|---|---|
| `RESULT.md` | One-page plain-English summary: question, design, verdict, diagnostics, disclosures, limits |
| `VERDICT_REPORT.md` | The full verdict report from the single verdict run, byte-identical to the original |
| `CALIBRATION.md` | The fake-data calibration of the pass rule, run before the freeze, byte-identical to the original |
| `PREREG.md` | The pre-registration as frozen, byte-identical to the original |

Reading notes:
- **`PREREG.md` is the frozen file.** sha256 `6e4bd3c48e5331a130076a0ac0672edac52ce70f1173ca64c014870ce207540a`,
  frozen 2026-10-27 (tag `prereg-v1.0` in the private study repository). Its header still says
  "DRAFT v0.9 … NOT FROZEN". The file was frozen by hash exactly as written, so the header was left
  byte-identical on purpose: changing it would break the hash.
- The prereg refers to earlier studies and a trials ledger (#38). They are the author's own records and are
  not part of this repository.

**Not included:** the code and the data. All inputs were public Binance data: daily klines and funding rates
from data.binance.vision, plus contract metadata and delisting announcements published by Binance.
