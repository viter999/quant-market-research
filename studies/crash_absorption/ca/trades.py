"""aggTrades container. `origin` travels with the data so the outcome lock can
tell synthetic test data from archive data."""
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Trades:
    ts: np.ndarray        # int64 ms, sorted ascending (ties broken by agg_id)
    price: np.ndarray     # float64
    qty: np.ndarray       # float64, base units
    is_buyer_maker: np.ndarray  # bool; True = seller-initiated (trade at the bid)
    origin: str

    @classmethod
    def from_frame(cls, df: pd.DataFrame, origin: str) -> "Trades":
        df = df.sort_values(["ts", "agg_id"], kind="stable")
        return cls(df["ts"].to_numpy(np.int64), df["price"].to_numpy(np.float64),
                   df["qty"].to_numpy(np.float64), df["is_buyer_maker"].to_numpy(bool), origin)

    @classmethod
    def from_rows(cls, rows, origin: str) -> "Trades":
        """rows: iterable of (ts, price, qty, is_buyer_maker); agg_id = row order."""
        df = pd.DataFrame(list(rows), columns=["ts", "price", "qty", "is_buyer_maker"])
        df["agg_id"] = np.arange(len(df))
        return cls.from_frame(df, origin)
