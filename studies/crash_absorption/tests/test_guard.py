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


from ca.guard import assert_file_listing_allowed  # noqa: E402

K = "data/futures/um/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-"
A = "data/futures/um/daily/aggTrades/BTCUSDT/BTCUSDT-aggTrades-"


@pytest.mark.parametrize("prefix", [K + "2024-", K + "2025-", K + "2023-12", K + "2026-02", A + "2024-", A + "2026-03-0",
                                    A + "2026-03-10.", A + "2026-03-13.", A + "2026-03-13", A + "2026-02-",
                                    "data/futures/um/daily/klines/BTCUSDT/1d/BTCUSDT-1d-2026-03-12."])
def test_file_listing_allowed(prefix):
    assert_file_listing_allowed(prefix)


@pytest.mark.parametrize("prefix", [K + "2026-", K + "2026-03", K + "2026-0", K + "202", A + "2026-03-1", A + "2026-03-",
                                    A + "2026-03-14.", A + "2026-03-14", A + "2026-", "data/futures/um/monthly/klines/BTCUSDT/1m/",
                                    "data/futures/um/monthly/klines/", "data/spot/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2024-"])
def test_file_listing_refused(prefix):
    with pytest.raises(HoldoutViolation):
        assert_file_listing_allowed(prefix)
