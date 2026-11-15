# Fade the Comeback

**When wallets that were just liquidated on a coin rush back into that coin, does the coin then move against them?**

No, not by enough to trade. This is a pre-registered trading test with a pass/fail rule, run once on data from 1 December 2025 to 31 May 2026. **Verdict: FAIL.**

It follows [After the Comeback](../after-the-comeback/), which found that 72.6% of liquidated wallets that opened a new position within an hour were liquidated again within 30 days. That raised a simple question: if these traders keep losing, is the side they pick on their comeback a signal to trade against?

## Result

| | 4 hours, against BTC |
|---|---|
| Trades | 515, on 145 days |
| Average gross return [90% CI] | +0.026% [−0.143, +0.195] |
| Median gross return | +0.013% |
| Win rate | 50.3% |
| Average net return after 0.40% costs [90% CI] | **−0.374%** [−0.542, −0.207] |
| Net, after dropping the 6 largest trades | −0.467% |

A pass needed all three: a positive average net return with its whole 90% interval above zero, a positive median, and a positive net average without the largest 1% of trades. Only the median passed. The average move was about a fifteenth of the cost.

**How to read this.** The test found no fade effect large enough to trade. The interval on the gross return does not rule out a small positive effect, but it does rule out one that pays 0.40%. It also does not show *why* these wallets are liquidated again: leverage and account size are not in the data. What it shows is narrower: the side they pick when they come back told us nothing useful about the next 4 hours.

## The rule (frozen before any code was written)

- **Re-entry:** a wallet opens a new position on coin C within 60 minutes after one of its own liquidation fills on C, with no other opening on C in between. Everything used is known at that moment.
- **Event:** in a UTC hour, 10 or more such wallets on one coin, at least 70% on the same side. Each wallet counts once per coin-hour.
- **Trade:** take the other side, entering at the close of the Binance 1-minute candle that opens 3 minutes after the hour ends. Exit 240 minutes later. One open trade per coin at a time.
- **Return:** trade direction × (coin return − BTC return), from the same Binance 1-minute closes, minus a 0.40% round-trip cost.
- **Coins:** 19 liquid non-BTC coins mapped from Hyperliquid to Binance USDT-M perps. Market makers and vaults excluded.
- **Statistics:** 90% intervals from 10,000 bootstrap draws of whole UTC days (all coins together).
- **One look.** A pass would only have been a hypothesis for a new test on later data. A fail closes the idea with no variants.

Before the run, four outside models (Grok, ChatGPT, Gemini, Qwen) reviewed the plan with no opinion attached. Their main catch: the first draft timed the signal from the end of a liquidation episode, which is only known an hour later. The frozen plan uses only the latest liquidation fill, known at the time. The full rules log, with every draft, change and timestamp, is kept with the study files.

## Also reported (no verdict; none of this can change a FAIL)

| | Trades | Gross mean | Median | Win rate |
|---|---|---|---|---|
| 1 hour, same trades | 515 | +0.038% | −0.006% | 49.5% |
| 24 hours, same trades | 514 | −0.073% | −0.355% | 44.9% |
| Fading a crowd that went long | 332 | +0.018% | −0.011% | 49.7% |
| Fading a crowd that went short | 183 | +0.040% | +0.021% | 51.4% |
| Dec 2025 – Feb 2026 | 339 | +0.034% | +0.051% | 53.4% |
| Mar – May 2026 | 176 | +0.011% | −0.126% | 44.3% |
| Raw returns, not against BTC | 515 | +0.103% | −0.015% | 49.1% |
| Chronic wallets only (liquidated on 3+ days in the prior 30) | 521 | −0.029% | −0.082% | 45.7% |
| Baseline A: any hour with 10+ liquidated wallets on one side, no re-entry condition | 2,229 | −0.000% | −0.051% | 47.7% |

Baseline B, the same fade in comparable hours with no event (matched on the previous hour's move), averaged −0.028%; the events beat it by +0.049%, far below the cost.

Trades per coin: SOL 151, ETH 148, HYPE 63, ZEC 47, XRP 43, FARTCOIN 31, other 11 coins 32.

## Checks (all passed before the result was read)

- 827 events found; 515 traded, 312 skipped because a trade on that coin was still open, 0 missing prices.
- 1,000 random 4-hour returns from the main code matched a separate recompute exactly.
- 20 random events recounted from the raw fills by separate code: 20 of 20 matched.
- The code was first run on made-up data with a planted answer: it found the planted +1.000% and passed, and failed on the same data with no move.

One check in the frozen plan was replaced before any outcome data existed, because it was badly calibrated (noise alone would have failed it about two times in three). The change is recorded in the rules log.

## Limits

- **Entry timing.** A trade enters up to an hour after the re-entries it reacts to, so a faster move would be missed.
- **Skipped events.** 312 of 827 events were skipped while a trade on the same coin was open; they may differ from the traded ones.
- **Concentration.** SOL and ETH are 58% of the trades.
- **Coin list.** The 19 coins were picked using volume over the whole period, so the list is not strictly point-in-time.
- **Choices.** The 4-hour horizon, the 70% and 10-wallet thresholds and the BTC-relative target were fixed in advance, not searched. Other choices were not tested and will not be.
- **One exchange's wallets, six months.** Results may not hold elsewhere.

## Files

| File | What it is |
|---|---|
| [`ftc_report.txt`](ftc_report.txt) | Full output of the one run |
| [`ftc_build.py`](ftc_build.py) | Step 1: finds re-entries in the raw fills (no prices, no outcomes) |
| [`ftc_run.py`](ftc_run.py) | Step 2: events, returns, checks and verdict |
| [`_t_ftc.py`](_t_ftc.py) | Test on made-up data with a planted answer |

Data: Hyperliquid's public fills archive and Binance's public 1-minute klines, already downloaded for the earlier wallet studies. They are not redistributed here.

Prior work: [After the Comeback](../after-the-comeback/), [Serial Liquidators](../serial-liquidators/), [Life After Liquidation](../life-after-liquidation/).
