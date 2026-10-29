import datetime as dt

import pytest

from ca import inventory as I
from ca.guard import assert_file_listing_allowed


def _expand(frags, freq):
    days = set()
    d = dt.date(2023, 1, 1)
    while d <= dt.date(2027, 1, 1):
        name = f"{d:%Y-%m}" if freq == "monthly" else f"{d:%Y-%m-%d}."
        if any(name.startswith(f) for f in frags):
            days.add(d if freq == "daily" else (d.year, d.month))
        d += dt.timedelta(days=1)
    return days


def test_daily_fragments_cover_exactly():
    fr = I.date_fragments("daily", dt.date(2024, 1, 1))
    assert fr[:2] == ["2024-", "2025-"] and fr[-4:] == ["2026-03-10.", "2026-03-11.", "2026-03-12.", "2026-03-13."]
    days = _expand(fr, "daily")
    assert min(days) == dt.date(2024, 1, 1) and max(days) == dt.date(2026, 3, 13) and len(days) == 803


def test_daily_fragments_mid_month_start():
    days = _expand(I.date_fragments("daily", dt.date(2023, 12, 5)), "daily")
    assert min(days) == dt.date(2023, 12, 5) and max(days) == dt.date(2026, 3, 13)
    assert len(days) == (dt.date(2026, 3, 13) - dt.date(2023, 12, 5)).days + 1


def test_monthly_fragments():
    assert I.date_fragments("monthly", dt.date(2023, 12, 1)) == ["2023-12", "2024-", "2025-", "2026-01", "2026-02"]


def test_kline_prefixes_all_pass_guard():
    ps = I.kline_prefixes("BTCUSDT", "1m", dt.date(2023, 12, 1))
    assert len(ps) == 10 and ps[5].endswith("BTCUSDT-1m-2026-03-0")
    for p in ps + I.aggtrades_prefixes("BTCUSDT", dt.date(2024, 1, 1)):
        assert_file_listing_allowed(p)


def test_period_of():
    assert I.period_of("data/futures/um/monthly/klines/X/1d/X-1d-2024-05.zip") == ("monthly", "2024-05")
    assert I.period_of("data/futures/um/daily/aggTrades/X/X-aggTrades-2026-03-13.zip") == ("daily", "2026-03-13")


def test_list_files_paginates_and_filters():
    ns = 'xmlns="http://s3.amazonaws.com/doc/2006-03-01/"'
    p1 = (f'<ListBucketResult {ns}><Contents><Key>data/futures/um/monthly/klines/X/1m/X-1m-2024-01.zip</Key><Size>5</Size></Contents>'
          '<Contents><Key>data/futures/um/monthly/klines/X/1m/X-1m-2024-01.zip.CHECKSUM</Key><Size>1</Size></Contents>'
          '<IsTruncated>true</IsTruncated><NextContinuationToken>t</NextContinuationToken></ListBucketResult>').encode()
    p2 = (f'<ListBucketResult {ns}><Contents><Key>data/futures/um/monthly/klines/X/1m/X-1m-2024-02.zip</Key><Size>7</Size></Contents>'
          '<IsTruncated>false</IsTruncated></ListBucketResult>').encode()

    class F:
        pages, urls = [p1, p2], []

        def get(self, url):
            self.urls.append(url)
            return self.pages.pop(0)

    f = F()
    out = I.list_files(f, "data/futures/um/monthly/klines/X/1m/X-1m-2024-")
    assert [s for _, s in out] == [5, 7] and "continuation-token=t" in f.urls[1]
