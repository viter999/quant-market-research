"""Synthetic VERDICT-period world for the runner dry run. Everything is
generated: 1d/1m klines with injected crashes, archive/REST/seam funding with a
sha256 manifest, and a fake archive fetcher that serves aggTrades zips (with
CHECKSUM files) generated from the 1m path. No real data is read."""
import datetime as dt
import hashlib
import io
import json
import re
import zipfile
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from ca import downloader as DL
from ca import params as P

SYMBOLS = ["SYNAUSDT", "SYNBUSDT", "SYNCUSDT", "SYNDUSDT"]
DAILY_START = dt.date(2025, 8, 1)
DAILY_END = dt.date(2025, 10, 31)
MIN_START = dt.date(2025, 8, 24)
MIN_END = dt.date(2025, 10, 20)  # exclusive
EXCLUSIONS = {"status": "FROZEN", "excluded_prefixes": [], "excluded_symbols": {}, "perp_suffixes": ["USDT"]}


def minute_path(seed: int, crashes_per_day: float = 6.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t0, t1 = P.date_to_ms(MIN_START), P.date_to_ms(MIN_END)
    n = (t1 - t0) // P.MINUTE_MS
    r = rng.normal(0, 0.001, n)
    qv = rng.lognormal(np.log(2e5), 0.3, n)
    k = int(crashes_per_day * n / 1440)
    for i in rng.choice(np.arange(300, n - 10), size=k, replace=False):
        r[i] = -rng.uniform(0.012, 0.04)
        qv[i] *= rng.uniform(6, 15)
        if rng.random() < 0.85:  # continuation dip, then partial rebound
            r[i + 1] -= 0.006
            r[i + 2] -= 0.004
            r[i + 6] += rng.normal(0.006, 0.006)
    for i in rng.choice(np.arange(300, n - 10), size=int(6 * n / 1440), replace=False):
        r[i] -= 0.004  # small non-event dips (no volume spike): lets placebo orders fill sometimes
        r[i + 3] += 0.004
    close = 100 * np.cumprod(1 + r)
    return pd.DataFrame({"open_time": t0 + np.arange(n, dtype=np.int64) * P.MINUTE_MS,
                         "high": close * 1.001, "low": close * 0.999, "close": close, "quote_volume": qv})


def trades_for_day(kl: pd.DataFrame, day: dt.date, seed: int, per_min: int = 20) -> pd.DataFrame:
    """~20 trades per minute along the close path (linear between closes, small noise)."""
    a, b = P.date_to_ms(day), P.date_to_ms(day + dt.timedelta(days=1))
    k = kl[(kl["open_time"] >= a - P.MINUTE_MS) & (kl["open_time"] < b)].reset_index(drop=True)
    rng = np.random.default_rng(seed)
    m = len(k) - 1
    p0 = np.repeat(k["close"].to_numpy()[:-1], per_min)
    p1 = np.repeat(k["close"].to_numpy()[1:], per_min)
    ot = np.repeat(k["open_time"].to_numpy()[1:], per_min)
    off = np.sort(rng.integers(0, P.MINUTE_MS, (m, per_min)), axis=1).ravel()
    ts = ot + off
    px = (p0 + (p1 - p0) * off / P.MINUTE_MS) * (1 + rng.normal(0, 0.0003, m * per_min))
    df = pd.DataFrame({"ts": ts, "price": px.round(6), "qty": (rng.exponential(1500.0, m * per_min) / px).round(6),
                       "ibm": rng.random(m * per_min) < 0.5})
    return df[(df["ts"] >= a) & (df["ts"] < b)].sort_values("ts", kind="stable").reset_index(drop=True)


class SyntheticArchive:
    """Fake fetcher for data.binance.vision aggTrades URLs (zip + CHECKSUM)."""
    PAT = re.compile(r"/daily/aggTrades/([^/]+)/[^/]+-aggTrades-(\d{4}-\d{2}-\d{2})\.zip(\.CHECKSUM)?$")

    def __init__(self, minutes: dict[str, pd.DataFrame]):
        self.minutes, self.cache, self.requested = minutes, {}, []

    def _zip(self, sym, day):
        key = (sym, day)
        if key not in self.cache:
            df = trades_for_day(self.minutes[sym], dt.date.fromisoformat(day), zlib.crc32(f'{sym}|{day}'.encode()))
            out = pd.DataFrame({"agg_trade_id": np.arange(len(df)), "price": df.price, "quantity": df.qty,
                                "first_trade_id": np.arange(len(df)), "last_trade_id": np.arange(len(df)),
                                "transact_time": df.ts, "is_buyer_maker": np.where(df.ibm, "true", "false")})
            csv = out.to_csv(index=False)
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(f"{sym}-aggTrades-{day}.csv", csv)
            self.cache[key] = buf.getvalue()
        return self.cache[key]

    def get(self, url):
        self.requested.append(url)
        m = self.PAT.search(url)
        if not m or m.group(1) not in self.minutes:
            return None
        z = self._zip(m.group(1), m.group(2))
        if m.group(3):
            return f"{hashlib.sha256(z).hexdigest()}  x.zip\n".encode()
        return z

    def download(self, url, path):
        body = self.get(url)
        if body is None:
            return False
        Path(path).write_bytes(body)
        return True


def _funding_frame(a: int, b: int, rng) -> pd.DataFrame:
    ts = np.arange(a + 8 * 3600_000, b + 1, 8 * 3600_000, dtype=np.int64)
    return pd.DataFrame({"ts": ts, "rate": rng.normal(0.0001, 0.0001, len(ts)).round(8)})


def build(data_dir: Path, seed: int = 7) -> dict:
    """Write the synthetic world; returns {'fetcher', 'expected_funding_sha', 'symbols', 'exclusions'}."""
    from ca.verdict_run import sha256_file
    rng = np.random.default_rng(seed)
    minutes = {}
    for i, s in enumerate(SYMBOLS):
        kl = minute_path(seed * 100 + i)
        minutes[s] = kl
        p = data_dir / "verdict" / "klines" / "1m" / f"{s}.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        kl.to_parquet(p, index=False)
        days = pd.date_range(DAILY_START, DAILY_END, freq="D")
        d1 = pd.DataFrame({"open_time": [P.date_to_ms(x.date()) for x in days], "open": 100.0, "high": 101.0,
                           "low": 99.0, "close": 100.0, "volume": 1.0, "quote_volume": 2e5 * 1440 * (1 + 0.1 * i),
                           "count": 1})
        p = data_dir / "klines" / "1d" / f"{s}.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        d1.to_parquet(p, index=False)
    files = {}
    arch_a, arch_b = P.date_to_ms(dt.date(2025, 8, 1)), DL.seam_span()[1]
    rest_a, rest_b = DL.rest_funding_span()
    seam_a, seam_b = DL.seam_span()
    for s in SYMBOLS:
        arch = _funding_frame(arch_a, arch_b, rng)
        DL._write_funding(arch, [(arch_a, arch_b)], data_dir / "funding" / f"{s}.parquet")
        for sub, (a, b), df in (("funding_rest", (rest_a, rest_b), _funding_frame(rest_a, rest_b, rng)),
                                ("funding_seam", (seam_a, seam_b), arch[(arch.ts >= seam_a) & (arch.ts <= seam_b)])):
            p = DL._write_funding(df.reset_index(drop=True), [(a, b)], data_dir / sub / f"{s}.parquet")
            for f in (p, p.with_suffix(".coverage.json")):
                files[f"{sub}/{f.name}"] = sha256_file(f)
    man = data_dir / "funding_rest_manifest.json"
    man.write_text(json.dumps({"symbols": len(SYMBOLS), "files": files}, indent=1))
    return {"fetcher": SyntheticArchive(minutes), "expected_funding_sha": sha256_file(man),
            "symbols": SYMBOLS, "exclusions": EXCLUSIONS}
