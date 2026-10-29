"""Task 3 prep (inputs only; no detection, no outcomes on VERDICT).
  klines    VERDICT 1m klines for universe symbol-months (+ previous month as lookback):
            monthly files through 2026-02, daily files 2026-03-01..13 (guard on)
  funding   archive fundingRate months 2025-08..2026-02 for the same symbols
  coverage  funding coverage pre-check for every universe member-day (archive part;
            2026-03-01..13 needs the REST file from Shawn)
Usage: python -I scripts/verdict_prep.py <data_dir> klines|funding|coverage"""
import concurrent.futures as cf
import datetime as dt
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ca import downloader as DL  # noqa: E402
from ca import inventory as I  # noqa: E402
from ca import params as P  # noqa: E402
from ca.pipeline import load_daily, segment_days  # noqa: E402
from ca.universe import build_universe, check_reviewed, load_exclusions  # noqa: E402

SEG = "verdict"
KLINE_COLS = ["open_time", "high", "low", "close", "quote_volume"]


def vdir(d: Path) -> Path:
    out = d / "verdict"
    out.mkdir(exist_ok=True)
    return out


def log(d: Path, step: str, info: dict) -> None:
    path = vdir(d) / "prep_steps.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    data[step] = info
    path.write_text(json.dumps(data, indent=1, default=str, ensure_ascii=False))
    print(json.dumps({step: info}, indent=1, default=str, ensure_ascii=False))


def universe(d: Path) -> dict:
    """VERDICT universe from 1d quote volume only (frozen exclusions)."""
    path = vdir(d) / "universe.json"
    if path.exists():
        return {dt.date.fromisoformat(k): frozenset(v) for k, v in json.loads(path.read_text()).items()}
    daily = load_daily(d)
    ex = load_exclusions(require_frozen=True)
    check_reviewed(daily["symbol"].unique(), ex)
    uni = build_universe(daily, ex, segment_days(SEG), DL.DOWNLOAD_START)
    path.write_text(json.dumps({str(k): sorted(v) for k, v in uni.items()}, ensure_ascii=False))
    return uni


def kline_plan(d: Path) -> dict[str, list[tuple[str, str]]]:
    uni = universe(d)
    months: dict[str, set] = {}
    for day, syms in uni.items():
        prev = day.replace(day=1) - dt.timedelta(days=1)
        for s in syms:
            months.setdefault(s, set()).update({f"{day:%Y-%m}", f"{prev:%Y-%m}"})
    inv = json.loads((d / "inventory_klines.json").read_text())["files"]
    plan = {}
    for s, ms in months.items():
        have = [I.period_of(k) for k, _ in inv[s]["1m"]]
        plan[s] = sorted(p for p in have if p[1][:7] in ms)
    return plan


def klines(d: Path) -> None:
    t0 = time.time()
    plan = kline_plan(d)
    fetch, errors = DL.HttpFetcher(), {}
    inv = json.loads((d / "inventory_klines.json").read_text())["files"]
    sizes = {k: sz for s in plan for k, sz in inv[s]["1m"]}

    def one(s):
        if (vdir(d) / "klines" / "1m" / f"{s}.parquet").exists():
            return s, None
        try:
            DL.download_klines(s, "1m", vdir(d), fetch, periods=plan[s], columns=KLINE_COLS)
            return s, None
        except Exception as e:
            return s, f"{type(e).__name__}: {e}"

    with cf.ThreadPoolExecutor(8) as ex:
        for s, err in ex.map(one, sorted(plan)):
            if err:
                errors[s] = err
    listed = sum(sz for s, ps in plan.items() for k, sz in inv[s]["1m"] if I.period_of(k) in set(ps))
    pq = sum(f.stat().st_size for f in (vdir(d) / "klines" / "1m").glob("*.parquet"))
    last = max(p[1] for ps in plan.values() for p in ps)
    log(d, "klines", {"symbols": len(plan), "files": sum(map(len, plan.values())), "zip_bytes_listed": listed,
                      "parquet_bytes": pq, "latest_period": last, "errors": errors,
                      "seconds": round(time.time() - t0)})
    del sizes


def funding(d: Path) -> None:
    t0 = time.time()
    syms = sorted(kline_plan(d))
    months = [("monthly", f"{m:%Y-%m}") for m in
              (dt.date(2025, 8, 1), dt.date(2025, 9, 1), dt.date(2025, 10, 1), dt.date(2025, 11, 1),
               dt.date(2025, 12, 1), dt.date(2026, 1, 1), dt.date(2026, 2, 1))]
    fetch, errors, none = DL.HttpFetcher(), {}, []

    def one(s):
        try:
            return s, DL.download_funding(s, d, fetch, periods=months), None
        except Exception as e:
            return s, None, f"{type(e).__name__}: {e}"

    with cf.ThreadPoolExecutor(8) as ex:
        for s, path, err in ex.map(one, syms):
            if err:
                errors[s] = err
            elif path is None:
                none.append(s)
    log(d, "funding", {"symbols": len(syms), "no_archive_file_any_month": none, "errors": errors,
                       "seconds": round(time.time() - t0)})


def member_spans(uni: dict) -> dict[str, list[tuple[int, int]]]:
    """Per symbol: [day start, min(next day 02:00, VERDICT end)] for each member day
    (an event at 23:59 + 5 min fill window + 60 min hold ends before 01:10)."""
    limit = P.date_to_ms(P.SEGMENTS[SEG][1] + dt.timedelta(days=1)) - 1
    spans: dict[str, list] = {}
    for day, syms in uni.items():
        a = P.date_to_ms(day)
        b = min(a + P.DAY_MS + 2 * 3600_000, limit)
        for s in syms:
            spans.setdefault(s, []).append((a, b))
    return spans


def coverage_gaps(d: Path, uni: dict, rest_required: bool) -> dict:
    """Member-day spans not covered by the loaded funding. Archive-only check
    (rest_required=False): spans are clipped to before the REST period."""
    rest_start = DL.rest_funding_span()[0]
    gaps = {}
    for s, spans in member_spans(uni).items():
        fu = DL.load_funding(s, d)
        bad = []
        for a, b in spans:
            if not rest_required:
                if a >= rest_start:
                    continue
                b = min(b, rest_start - 1)
            if not any(ca <= a and b <= cb for ca, cb in fu.cover):
                bad.append(str(P.ms_to_date(a)))
        if bad:
            gaps[s] = bad
    return gaps


def coverage(d: Path) -> None:
    gaps = coverage_gaps(d, universe(d), rest_required=False)
    log(d, "coverage_archive_part", {"symbols_with_gaps": len(gaps), "gaps": gaps})


if __name__ == "__main__":
    d = Path(sys.argv[1])
    {"klines": klines, "funding": funding, "coverage": coverage}[sys.argv[2]](d)
