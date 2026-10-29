"""Parser unit tests on synthetic CMS node trees."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import parse_events as P  # noqa: E402


def txt(s):
    return {"node": "text", "text": s}


def table(rows):
    return {"node": "element", "tag": "table", "child": [
        {"node": "element", "tag": "tr", "child": [{"node": "element", "tag": "td", "child": [txt(c)]} for c in r]}
        for r in rows]}


def raw(*children):
    return json.dumps({"node": "root", "child": list(children)})


def test_columns_and_bare_time():
    r = raw(table([["USDⓈ-M Perpetual Contracts", "AAAUSDT", "BBBUSDC"],
                   ["Launch Time", "2024-04-04 07:00 (UTC)", "2024-04-04 07:15"],
                   ["Underlying Asset", "Aaa (AAA)", "Bbb (BBB)"], ["Settlement Asset", "USDT", "USDC"]]))
    rows = P.from_tables(r)
    assert [(x["symbol"], x["L"], x["settlement"]) for x in rows] == [("AAAUSDT", "2024-04-04 07:00", "USDT"),
                                                                     ("BBBUSDC", "2024-04-04 07:15", "USDC")]


def test_single_value_spans_columns_and_equity_family():
    r = raw(table([["Contract Type", "USDT-Priced", "USDT-Priced"], ["USDⓈ-M Perpetual Contract", "XUSDT", "YUSDT"],
                   ["Launch Time", "2026-02-05 03:00 (UTC)", "2026-02-05 03:05 (UTC)"],
                   ["Underlying Equity", "X Inc. Common Stock (Nasdaq: X)", "Y Inc. (Nasdaq: Y)"],
                   ["Settlement Asset", "USDT"]]))
    rows = P.from_tables(r)
    assert [x["settlement"] for x in rows] == ["USDT", "USDT"]
    assert P.body_family(rows[0], "TradFi") == "equity"


def test_coin_m_row_kept_as_dropped_kind():
    rows = P.from_tables(raw(table([["COIN-M Perpetual Contract", "WIFUSD"], ["Launch Time", "2024-07-23 12:00 (UTC)"]])))
    assert rows[0]["margin"] == "COIN-M"


def test_segments():
    assert P.segment(P.ms("2024-01-01 00:00")) == "TEST"
    assert P.segment(P.ms("2026-03-05 23:59")) == "TEST"
    assert P.segment(P.ms("2026-03-06 00:00")) == "OUT_OF_RANGE"
    assert P.segment(P.ms("2026-03-15 00:00")) == "HOLDOUT"
    assert P.segment(P.ms("2026-09-28 00:00")) == "OUT_OF_RANGE"
