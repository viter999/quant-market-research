# Credits

`LICENSE` and `CREDITS.md` were added after `HASHES.txt` was made, so they are
not listed in it. All other files are.

## Kronos

This study evaluates **Kronos**, a foundation model for financial market data
(K-line / candlestick series). We did not write Kronos. We only used it, as
published and unmodified, and tested its forecasts.

All credit for the model, its code and its weights goes to its authors:

- **Paper:** Shi et al., *Kronos: A Foundation Model for the Language of
  Financial Markets*, arXiv:2508.02739 — https://arxiv.org/abs/2508.02739
- **Code:** https://github.com/shiyu-coder/Kronos (MIT License,
  Copyright (c) 2025 ShiYu), used at commit
  `67b630e67f6a18c9e9be918d9b4337c960db1e9a`
- **Weights:** Hugging Face
  [`NeoQuasar/Kronos-small`](https://huggingface.co/NeoQuasar/Kronos-small)
  at revision `901c26c1332695a2a8f243eb2f37243a37bea320` and
  [`NeoQuasar/Kronos-Tokenizer-base`](https://huggingface.co/NeoQuasar/Kronos-Tokenizer-base)
  at revision `0e0117387f39004a9016484a186a908917e22426`

The Kronos code and weights are not included in this folder. The scripts here
download them at the pinned versions and check them against
`FREEZE_kronos.sha256`.

This study's DROP result covers one model size, one sampling setting, one
horizon and one market window (see `README.md`, "Limitations"). It is not a
verdict on Kronos in general.

## Data

Hourly klines are Binance's public USDT-M futures data from
https://data.binance.vision/. They are not redistributed here.

## This folder

The pre-registration, scripts, notebook and reports in this folder are this
study's own work. The code is MIT-licensed (see `LICENSE`).
