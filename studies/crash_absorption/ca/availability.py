"""Exit-DATA availability (Task 2c): would an exit price exist for a fill?
Only trade timestamps and the seller-initiated flag are passed in, never
prices, so no exit price, return or markout can be computed here."""
import numpy as np

from ca import params as P


def exit_data_available(ts: np.ndarray, is_buyer_maker: np.ndarray, fill_ts: int,
                        hold_min: float = P.PRIMARY_HOLD_MIN) -> dict:
    """(a) any seller-initiated trade in [T, T+10 s]; (b) any in [T-60 s, T]."""
    T = int(fill_ts + round(hold_min * P.MINUTE_MS))
    s = ts[is_buyer_maker]
    a = bool(np.any((s >= T) & (s <= T + P.EXIT_VWAP_S * 1000)))
    b = bool(np.any((s >= T - P.EXIT_LAST_MAX_AGE_S * 1000) & (s <= T)))
    return {"vwap_window": a, "last_window": b, "available": a or b}
