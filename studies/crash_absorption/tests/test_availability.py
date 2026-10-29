import inspect

import numpy as np

from ca.availability import exit_data_available

F = 1_750_000_000_000
T = F + 900_000


def test_windows():
    ts = np.array([T - 60_000, T + 10_000, T + 10_001])
    assert exit_data_available(ts, np.array([True, False, False]), F) == {"vwap_window": False, "last_window": True, "available": True}
    assert exit_data_available(ts, np.array([False, True, False]), F)["vwap_window"]
    assert not exit_data_available(ts, np.array([False, False, True]), F)["available"]
    assert not exit_data_available(np.array([T - 60_001]), np.array([True]), F)["available"]


def test_takes_no_prices():
    assert list(inspect.signature(exit_data_available).parameters) == ["ts", "is_buyer_maker", "fill_ts", "hold_min"]
