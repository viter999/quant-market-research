"""Parser unit tests on synthetic body strings, one per announcement format seen."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import parse_events as P  # noqa: E402


def art(text, title="Binance Futures Will Delist X"):
    raw = {"node": "root", "child": [{"node": "element", "tag": "p", "child": [{"node": "text", "text": text}]}]}
    return {"title": title, "body_raw": json.dumps(raw)}


def times(res):
    return {s: (P.utc(v["D_ms"])[:16], P.utc(v["N_ms"])[:16], v["N_source"]) for s, v in res["symbols"].items()}


def test_sentence_multi_date_and_stated_n():
    r = P.parse_article(art("Binance Futures will close all positions and conduct an automatic settlement on the USDⓈ-M "
                            "AAAUSDT and BBBUSDT USDⓈ-M perpetual contracts at 2024-05-13 09:00 (UTC) , and CCCUSDT USDⓈ-M "
                            "perpetual contracts at 2024-05-14 09:00 (UTC). The contracts will be delisted after the settlement "
                            "is complete. Users are not allowed to open new positions for the aforementioned contracts starting "
                            "from 2024-05-13 08:30 (UTC) ."))
    assert times(r) == {"AAAUSDT": ("2024-05-13 09:00", "2024-05-13 08:30", "stated"),
                        "BBBUSDT": ("2024-05-13 09:00", "2024-05-13 08:30", "stated"),
                        "CCCUSDT": ("2024-05-14 09:00", "2024-05-13 08:30", "stated")}


def test_list_format_with_coin_m_and_list_n():
    r = P.parse_article(art("Binance Futures will close all positions and conduct an automatic settlement on the following "
                            "perpetual contract(s) as below: 2025-12-05 09:00 (UTC) : USDⓈ-M AAAUSDT and BBBUSDT perpetual "
                            "contracts 2025-12-05 09:30 (UTC) : USDⓈ-M CCCUSDT perpetual contracts 2025-12-06 09:00 (UTC) : "
                            "COIN-M DDDUSD Perpetual contract The contracts will be delisted after the settlement is complete. "
                            "Users are not allowed to open new positions for the aforementioned contract(s) as below: "
                            "2025-12-05 08:30 (UTC) : USDⓈ-M AAAUSDT and BBBUSDT 2025-12-05 09:00 (UTC) : USDⓈ-M CCCUSDT "
                            "For More Information"))
    assert times(r) == {"AAAUSDT": ("2025-12-05 09:00", "2025-12-05 08:30", "stated"),
                        "BBBUSDT": ("2025-12-05 09:00", "2025-12-05 08:30", "stated"),
                        "CCCUSDT": ("2025-12-05 09:30", "2025-12-05 09:00", "stated")}


def test_2022_names_am_respectively_and_default_n():
    r = P.parse_article(art("Fellow Binancians, Binance Futures will conduct automatic settlements on the 1000AAA and BBB "
                            "USDT-Margined Contracts, and delist these contracts at 2022-04-11 09:00 AM (UTC) and "
                            "2022-04-12 09:00 AM (UTC) respectively. Please note: Users are advised to close."))
    assert times(r) == {"1000AAAUSDT": ("2022-04-11 09:00", "2022-04-11 08:00", "default_D-1h"),
                        "BBBUSDT": ("2022-04-12 09:00", "2022-04-12 08:00", "default_D-1h")}
    r = P.parse_article(art("Binance Futures will conduct an automatic settlement on the AAAUSDT and BBBUSDT Perpetual "
                            "Futures Contracts at 2022-11-15 04:00 and 2022-11-15 04:30 (UTC) respectively. We will delist."))
    assert times(r)["AAAUSDT"][0] == "2022-11-15 04:00" and times(r)["BBBUSDT"][0] == "2022-11-15 04:30"
    r = P.parse_article(art("Binance Futures will conduct an automatic settlement on the USDT-Margined CCC Perpetual "
                            "Contract at 2022-06-17 09:00 (UTC), and delist this contract after the settlement is complete ."))
    assert list(times(r)) == ["CCCUSDT"]


def test_busd_and_coin_m_dropped():
    r = P.parse_article(art("Binance Futures will conduct an automatic settlement on the AAABUSD USDT-Margined Contract and "
                            "delist this contract at 2022-05-19 09:00 AM (UTC). Please note: x"))
    assert r["status"] == "parsed_no_usdt_symbol"
    r = P.parse_article(art("Binance Futures will conduct an automatic settlement on the CRV Coin-Margined Perpetual Contract "
                            "at 2022-06-30 09:00 (UTC). Please note: x. Note: updated the CRV USDT-Margined Contract to CRV "
                            "Coin-Margined."))
    assert r["status"] == "parsed_no_usdt_symbol"


def test_restriction_flag_per_symbol_ignores_boilerplate():
    r = P.parse_article(art("Binance Futures will close all positions and conduct an automatic settlement on the USDⓈ-M "
                            "AAAUSDT and BBBUSDT perpetual contracts at 2024-05-15 09:00 (UTC). The contracts will be delisted. "
                            "In addition, Binance Futures will adjust the leverage and margin tiers of the USDⓈ-M AAAUSDT "
                            "perpetual contracts at 2024-05-08 10:30 (UTC), as per the tables below. Binance Futures may "
                            "undertake additional protective measures including adjusting the maximum leverage value."))
    assert {s: v["restriction_flag"] for s, v in r["symbols"].items()} == {"AAAUSDT": 1, "BBBUSDT": 0}


def test_postponement_notice_is_not_an_episode():
    r = P.parse_article(art("Binance Futures will postpone the delisting of the USDⓈ-M AAAUSDT Perpetual Contract to "
                            "2024-12-30 09:00 (UTC) .", title="Delisting of USDⓈ-M AAAUSDT Perpetual Contract Postponed"))
    assert r["status"] == "postponement_notice" and r["postpone"] == ("AAAUSDT", "2024-12-30 09:00")
