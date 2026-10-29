"""Streamed bookTicker download (guard + CHECKSUM via the frozen crash-absorption
downloader): keep only rows inside the needed windows plus, for each window, the
last update before it starts (so 'the quote in force' at any time in the window is
exact), write parquet, delete the zip."""
import datetime as dt
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from ca import downloader as DL
from ca import params as P

COLS = ["update_id", "best_bid_price", "best_bid_qty", "best_ask_price", "best_ask_qty", "transaction_time", "event_time"]
URL = DL.ARCHIVE + "/" + DL.UM + "/daily/bookTicker/{s}/{s}-bookTicker-{d}.zip"


def bookticker_url(symbol: str, day: dt.date) -> str:
    return URL.format(s=symbol, d=day.isoformat())


def windows_for(refs) -> dict[dt.date, list[tuple[int, int]]]:
    """Per UTC day, merged windows [a, b] (ms) split at midnight."""
    spans = sorted(refs)
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    out: dict = {}
    for a, b in merged:
        while a <= b:
            end = (a // P.DAY_MS + 1) * P.DAY_MS - 1
            out.setdefault(P.ms_to_date(a), []).append((a, min(b, end)))
            a = end + 1
    return out


def filter_chunks(chunks, windows, lo: int, hi: int, name: str) -> pd.DataFrame:
    """Rows inside any window, plus per window the last row (max ts, then max
    update_id) strictly before its start. Pure function of the chunk stream."""
    kept, carry = [], [None] * len(windows)
    for ch in chunks:
        if list(ch.columns) != COLS:
            raise DL.DataValidationError(f"{name}: unexpected columns {list(ch.columns)}")
        ts = ch["transaction_time"].to_numpy(np.int64)
        if len(ts) and (ts.min() < lo - 60_000 or ts.max() >= hi + 60_000):
            raise DL.DataValidationError(f"{name}: transaction_time outside its day (ms units?)")
        m = np.zeros(len(ch), bool)
        for j, (a, b) in enumerate(windows):
            m |= (ts >= a) & (ts <= b)
            pre = ts < a
            if pre.any():
                t_max = ts[pre].max()
                cand = np.flatnonzero(pre & (ts == t_max))
                k = cand[np.argmax(ch["update_id"].to_numpy(np.int64)[cand])]
                best = ch.iloc[k]
                if carry[j] is None or (int(best["transaction_time"]), int(best["update_id"])) > \
                        (int(carry[j]["transaction_time"]), int(carry[j]["update_id"])):
                    carry[j] = best
        kept.append(ch[m])
    rows = [c.to_frame().T for c in carry if c is not None]
    df = pd.concat(kept + rows, ignore_index=True) if kept or rows else pd.DataFrame(columns=COLS)
    df = df.astype({"update_id": np.int64, "transaction_time": np.int64, "event_time": np.int64,
                    "best_bid_price": float, "best_bid_qty": float, "best_ask_price": float, "best_ask_qty": float})
    df = df.drop_duplicates("update_id").sort_values(["transaction_time", "update_id"], kind="stable")
    return pd.DataFrame({"ts": df["transaction_time"], "update_id": df["update_id"], "bid": df["best_bid_price"],
                         "bid_qty": df["best_bid_qty"], "ask": df["best_ask_price"], "ask_qty": df["best_ask_qty"],
                         "event_time": df["event_time"]}).reset_index(drop=True)


def stream_bookticker(symbol: str, day: dt.date, windows, out_dir: Path, fetch, chunksize: int = 2_000_000):
    out = Path(out_dir) / "bookticker" / symbol / f"{day.isoformat()}.parquet"
    if out.exists():
        return out
    tmp = Path(tempfile.mkdtemp(prefix="bookticker-"))
    try:
        z = DL._fetch_zip(fetch, bookticker_url(symbol, day), tmp)  # guard + CHECKSUM
        if z is None:
            return None
        lo, hi = P.date_to_ms(day), P.date_to_ms(day + dt.timedelta(days=1))
        with DL._csv_member(z, COLS, chunksize=chunksize) as reader:
            df = filter_chunks(reader, windows, lo, hi, z.name)
        z.unlink()
        out.parent.mkdir(parents=True, exist_ok=True)
        part = out.with_suffix(".parquet.tmp")
        df.to_parquet(part, index=False, compression="zstd")
        part.replace(out)
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
