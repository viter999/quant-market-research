import pytest

from ca.guard import HoldoutViolation
from ef.guardx import assert_file_listing_allowed


@pytest.mark.parametrize("p", ["data/spot/daily/klines/SOLUSDT/1m/SOLUSDT-1m-2024-01-0",
                               "data/spot/monthly/klines/SOLUSDT/1m/SOLUSDT-1m-2025-",
                               "data/futures/um/daily/metrics/SOLUSDT/SOLUSDT-metrics-2026-03-13",
                               "data/futures/um/monthly/fundingRate/X/X-fundingRate-2026-02"])
def test_allowed(p):
    assert_file_listing_allowed(p)


@pytest.mark.parametrize("p", ["data/spot/daily/klines/SOLUSDT/1m/SOLUSDT-1m-2026-03-1",
                               "data/spot/monthly/klines/SOLUSDT/1m/SOLUSDT-1m-2026-",
                               "data/spot/daily/klines/SOLUSDT/1m/",
                               "data/futures/cm/daily/klines/X/1m/X-1m-2024-",
                               "data/futures/um/daily/metrics/X/X-metrics-2026-03-14"])
def test_refused(p):
    with pytest.raises(HoldoutViolation):
        assert_file_listing_allowed(p)
