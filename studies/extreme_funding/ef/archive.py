"""Archive access for extreme-funding (metadata listings + guarded, checksummed downloads),
built on the frozen crash-absorption downloader and inventory code."""
import datetime as dt
import tempfile
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd

from ca import downloader as DL
from ca import params as P
from ca.guard import assert_allowed
from ca.inventory import LISTING_BASE, NS, date_fragments
from ef.guardx import assert_file_listing_allowed

ARCHIVE = DL.ARCHIVE


def list_zips(fetch, prefix: str) -> list[tuple[str, int]]:
    assert_file_listing_allowed(prefix)
    out, token = [], None
    while True:
        q = {"list-type": "2", "prefix": prefix}
        if token:
            q["continuation-token"] = token
        root = ET.fromstring(fetch.get(f"{LISTING_BASE}/?{urllib.parse.urlencode(q)}"))
        for c in root.findall("s:Contents", NS):
            k = c.findtext("s:Key", namespaces=NS)
            if k.endswith(".zip"):
                assert_allowed(k)
                out.append((k, int(c.findtext("s:Size", namespaces=NS))))
        if root.findtext("s:IsTruncated", namespaces=NS) != "true":
            return out
        token = root.findtext("s:NextContinuationToken", namespaces=NS)


def monthly_prefixes(path: str, stem: str, start: dt.date) -> list[str]:
    """e.g. path='data/futures/um/monthly/fundingRate/BTCUSDT', stem='BTCUSDT-fundingRate'."""
    return [f"{path}/{stem}-{f}" for f in date_fragments("monthly", start)]


def daily_prefixes(path: str, stem: str, start: dt.date) -> list[str]:
    return [f"{path}/{stem}-{f}" for f in date_fragments("daily", start)]


def fetch_csv(fetch, key: str, names: list[str]) -> pd.DataFrame:
    """Guarded + CHECKSUM-verified download of one archive zip, parsed, zip deleted."""
    with tempfile.TemporaryDirectory() as td:
        z = DL._fetch_zip(fetch, f"{ARCHIVE}/{key}", Path(td))
        if z is None:
            raise FileNotFoundError(key)
        return DL._read_csv_member(z, names)


FUNDING_COLS = ["calc_time", "funding_interval_hours", "last_funding_rate"]


def parse_funding(df: pd.DataFrame, month: str) -> pd.DataFrame:
    df.columns = FUNDING_COLS[: len(df.columns)]
    a, b = DL._period_bounds("monthly", month)
    out = pd.DataFrame({"ts": df["calc_time"].astype(np.int64), "interval_h_archive": df["funding_interval_hours"].astype(float),
                        "rate": df["last_funding_rate"].astype(float)})
    if len(out) and (out["ts"].min() < a or out["ts"].max() >= b):
        raise DL.DataValidationError(f"funding {month}: calc_time outside month")
    return out
