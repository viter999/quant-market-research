import pytest

from ca.guard import HoldoutViolation, assert_allowed, assert_ms_allowed


def test_allows_verdict_end_daily():
    assert_allowed("SOLUSDT-aggTrades-2026-03-13.zip")


@pytest.mark.parametrize("name", [
    "SOLUSDT-aggTrades-2026-03-14.zip",
    "BTCUSDT-1m-2026-03.zip",
    "BTCUSDT-1m-2026-09.zip",
    "BTCUSDT-fundingRate-2026-04.zip",
    "BTCUSDT-1m.zip",
])
def test_refuses_holdout_and_unknown(name):
    with pytest.raises(HoldoutViolation):
        assert_allowed(name)


def test_allows_monthly_before():
    assert_allowed("https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2026-02.zip")


def test_rest_end_time():
    assert_ms_allowed(1773446399999)  # 2026-03-13T23:59:59.999Z
    with pytest.raises(HoldoutViolation):
        assert_ms_allowed(1773446400000)  # 2026-03-14T00:00:00Z
