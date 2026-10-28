import datetime as dt
import hashlib
import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from ca import downloader as DL
from ca.guard import HoldoutViolation, assert_allowed, assert_listing_allowed
from tests.synth import ms

DAY = dt.date(2024, 3, 5)


class FakeFetcher:
    def __init__(self, files: dict[str, bytes]):
        self.files, self.requested = files, []

    def get(self, url):
        self.requested.append(url)
        return self.files.get(url)

    def download(self, url, path: Path):
        self.requested.append(url)
        if url not in self.files:
            return False
        Path(path).write_bytes(self.files[url])
        self.seen_tmp = Path(path)
        return True


def _zip(name: str, text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(name, text)
    return buf.getvalue()


def _publish(files, url, payload, checksum=None):
    files[url] = payload
    digest = checksum or hashlib.sha256(payload).hexdigest()
    files[url + ".CHECKSUM"] = f"{digest}  {url.rsplit('/', 1)[-1]}\n".encode()


def _agg_csv(rows, header=True):
    lines = ["agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker"] if header else []
    lines += [f"{i},{p},{q},{i},{i},{t},{'true' if m else 'false'}" for i, (t, p, q, m) in enumerate(rows)]
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize("header", [True, False])
def test_stream_aggtrades_keeps_windows_and_deletes_zip(tmp_path, header):
    t0 = ms(DAY, 12, 0)
    rows = [(t0 - 10 * 60_000, 1.0, 1.0, True), (t0 - 5 * 60_000, 2.0, 1.0, False), (t0, 3.0, 2.0, True),
            (t0 + 25 * 60_000, 4.0, 1.0, False), (t0 + 25 * 60_000 + 1, 5.0, 1.0, True)]
    url = DL.aggtrades_url("SOLUSDT", DAY)
    files = {}
    _publish(files, url, _zip("SOLUSDT-aggTrades-2024-03-05.csv", _agg_csv(rows, header)))
    fetch = FakeFetcher(files)
    win = DL.trade_windows([t0])
    out = DL.stream_aggtrades("SOLUSDT", DAY, win[DAY], tmp_path, fetch, chunksize=2)
    df = pd.read_parquet(out)
    assert df["price"].tolist() == [2.0, 3.0, 4.0]
    assert df["is_buyer_maker"].tolist() == [False, True, False]
    assert not fetch.seen_tmp.exists() and not fetch.seen_tmp.parent.exists()
    for u in fetch.requested:
        assert_allowed(u)
    assert DL.load_aggtrades(out).origin == "archive"


def test_checksum_mismatch_raises_and_cleans(tmp_path):
    url = DL.aggtrades_url("SOLUSDT", DAY)
    files = {}
    _publish(files, url, _zip("x.csv", _agg_csv([(ms(DAY, 1), 1.0, 1.0, True)])), checksum="0" * 64)
    fetch = FakeFetcher(files)
    with pytest.raises(DL.ChecksumError):
        DL.stream_aggtrades("SOLUSDT", DAY, [(0, 2 ** 62)], tmp_path, fetch)
    assert not fetch.seen_tmp.exists()


def test_missing_checksum_raises(tmp_path):
    url = DL.aggtrades_url("SOLUSDT", DAY)
    fetch = FakeFetcher({url: _zip("x.csv", _agg_csv([]))})
    with pytest.raises(DL.ChecksumError):
        DL.stream_aggtrades("SOLUSDT", DAY, [(0, 2 ** 62)], tmp_path, fetch)


def test_microsecond_timestamps_rejected(tmp_path):
    url = DL.aggtrades_url("SOLUSDT", DAY)
    files = {}
    _publish(files, url, _zip("x.csv", _agg_csv([(ms(DAY, 1) * 1000, 1.0, 1.0, True)])))
    with pytest.raises(DL.DataValidationError):
        DL.stream_aggtrades("SOLUSDT", DAY, [(0, 2 ** 62)], tmp_path, FakeFetcher(files))


def test_404_returns_none(tmp_path):
    assert DL.stream_aggtrades("SOLUSDT", DAY, [(0, 1)], tmp_path, FakeFetcher({})) is None


@pytest.mark.parametrize("day", [dt.date(2026, 3, 14), dt.date(2026, 3, 15), dt.date(2026, 9, 30)])
def test_holdout_refused_before_any_request(tmp_path, day):
    fetch = FakeFetcher({})
    with pytest.raises(HoldoutViolation):
        DL.stream_aggtrades("SOLUSDT", day, [(0, 1)], tmp_path, fetch)
    assert fetch.requested == []


def test_last_allowed_day_requested(tmp_path):
    fetch = FakeFetcher({})
    DL.stream_aggtrades("SOLUSDT", dt.date(2026, 3, 13), [(0, 1)], tmp_path, fetch)
    assert fetch.requested == [DL.aggtrades_url("SOLUSDT", dt.date(2026, 3, 13))]


def test_file_periods_stop_at_verdict_end():
    per = list(DL.file_periods())
    assert per[0] == ("monthly", "2023-12")
    assert ("monthly", "2026-02") in per and ("monthly", "2026-03") not in per
    assert per[-1] == ("daily", "2026-03-13") and len([p for p in per if p[0] == "daily"]) == 13
    for f, p in per:
        assert_allowed(DL.kline_url("BTCUSDT", "1m", f, p))


def _kline_csv(open_times, header=True):
    lines = [",".join(DL.KLINE_COLS)] if header else []
    lines += [f"{t},1,2,0.5,1.5,10,{t + 59_999},15,3,5,7,0" for t in open_times]
    return "\n".join(lines) + "\n"


def test_download_klines_monthly_and_daily(tmp_path):
    files = {}
    m_url = DL.kline_url("XUSDT", "1m", "monthly", "2024-01")
    d_url = DL.kline_url("XUSDT", "1m", "daily", "2026-03-13")
    _publish(files, m_url, _zip("a.csv", _kline_csv([ms(dt.date(2024, 1, 1)), ms(dt.date(2024, 1, 31), 23, 59)])))
    _publish(files, d_url, _zip("b.csv", _kline_csv([ms(dt.date(2026, 3, 13), 0, 0)], header=False)))
    fetch = FakeFetcher(files)
    out = DL.download_klines("XUSDT", "1m", tmp_path, fetch)
    df = pd.read_parquet(out)
    assert len(df) == 3 and df["quote_volume"].tolist() == [15.0] * 3
    assert all("2026-03-14" not in u and "2026-03.zip" not in u for u in fetch.requested)


def test_klines_outside_period_rejected(tmp_path):
    files = {}
    url = DL.kline_url("XUSDT", "1m", "monthly", "2024-01")
    _publish(files, url, _zip("a.csv", _kline_csv([ms(dt.date(2024, 2, 1))])))
    with pytest.raises(DL.DataValidationError):
        DL.download_klines("XUSDT", "1m", tmp_path, FakeFetcher(files), periods=[("monthly", "2024-01")])


def test_funding_parse(tmp_path):
    files = {}
    url = DL.funding_url("XUSDT", "2024-01")
    csv = "calc_time,funding_interval_hours,last_funding_rate\n1704096000000,8,0.0001\n1704124800000,8,-0.00005\n"
    _publish(files, url, _zip("f.csv", csv))
    out = DL.download_funding("XUSDT", tmp_path, FakeFetcher(files), periods=[("monthly", "2024-01")])
    df = pd.read_parquet(out)
    assert df["rate"].tolist() == [0.0001, -0.00005]


def test_funding_never_requests_partial_month(tmp_path):
    fetch = FakeFetcher({})
    DL.download_funding("XUSDT", tmp_path, fetch)
    assert not any("2026-03" in u for u in fetch.requested)


def test_trade_windows_split_and_merge():
    t = ms(DAY, 23, 50)
    w = DL.trade_windows([t, t + 60_000])
    nxt = DAY + dt.timedelta(days=1)
    assert w[DAY] == [(t - 300_000, ms(nxt) - 1)]
    assert w[nxt] == [(ms(nxt), t + 60_000 + 25 * 60_000)]


def test_list_symbols(tmp_path):
    ns = 'xmlns="http://s3.amazonaws.com/doc/2006-03-01/"'
    xml = (f'<ListBucketResult {ns}><IsTruncated>false</IsTruncated>'
           '<CommonPrefixes><Prefix>data/futures/um/monthly/klines/BTCUSDT/</Prefix></CommonPrefixes>'
           '<CommonPrefixes><Prefix>data/futures/um/monthly/klines/ETHUSDT/</Prefix></CommonPrefixes>'
           '</ListBucketResult>').encode()

    class F(FakeFetcher):
        def get(self, url):
            self.requested.append(url)
            return self.files["x"]

    assert DL.list_symbols(F({"x": xml})) == ["BTCUSDT", "ETHUSDT"]
    with pytest.raises(DL.DataValidationError):
        DL.list_symbols(F({"x": b"<html>"}))
    bad = xml.replace(b"<IsTruncated>", b"<Contents><Key>k</Key><Size>1</Size></Contents><IsTruncated>")
    with pytest.raises(DL.DataValidationError):
        DL.list_symbols(F({"x": bad}))


def test_listing_guard():
    assert_listing_allowed("data/futures/um/monthly/klines/", "/")
    with pytest.raises(HoldoutViolation):
        assert_listing_allowed("data/futures/um/monthly/klines/BTCUSDT/1m/", "/")
    with pytest.raises(HoldoutViolation):
        assert_listing_allowed("data/futures/um/monthly/klines/", None)
