"""DL-1 step 2: download 1m klines (A-24h .. D) and monthly fundingRate for every
TEST event in events.csv, plus BTCUSDT 1m on the same days. Events marked
window_past_data_limit and all HOLDOUT / out-of-range events are never requested.
Writes only under studies/delisting/data/ (gitignored)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dl import archive, events as E  # noqa: E402
from dl.guard import assert_event_allowed  # noqa: E402

DATA = E.ROOT / "data"


def main() -> int:
    evs = [e for e in E.load_events() if e["segment"] == "TEST" and e["excluded_by_time_rule"] != "window_past_data_limit"]
    for e in evs:
        assert_event_allowed(e)
    fetch = archive.HttpFetcher()
    by_sym: dict[str, set] = {}
    months: dict[str, set] = {}
    btc_days: set = set()
    for e in evs:
        d = E.days_needed(e)
        by_sym.setdefault(e["symbol"], set()).update(d)
        months.setdefault(e["symbol"], set()).update(E.months_needed(e))
        btc_days.update(d)
    report = {"n_events": len(evs), "symbols": len(by_sym), "klines": {}, "funding": {}}
    for i, s in enumerate(sorted(by_sym)):
        k = archive.download_klines(s, sorted(by_sym[s]), DATA / "klines_1m" / f"{s}.parquet", fetch)
        f = archive.download_funding(s, sorted(months[s]), DATA / "funding" / f"{s}.parquet", fetch)
        report["klines"][s] = {"present": len(k["present"]), "missing": k["missing"]}
        report["funding"][s] = {"present": f["present"], "missing": f["missing"]}
        print(f"[{i + 1}/{len(by_sym)}] {s}: kline days {len(k['present'])} present, missing {k['missing']}; "
              f"funding months {f['present']} missing {f['missing']}", flush=True)
    k = archive.download_klines("BTCUSDT", sorted(btc_days), DATA / "klines_1m" / "BTCUSDT.parquet", fetch)
    report["klines"]["BTCUSDT"] = {"present": len(k["present"]), "missing": k["missing"]}
    print(f"BTCUSDT: kline days {len(k['present'])} present, missing {k['missing']}", flush=True)
    (DATA / "download_report.json").write_text(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
