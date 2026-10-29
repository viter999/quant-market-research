"""Event list and window arithmetic."""
import csv
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN, HOUR, DAY = 60_000, 3_600_000, 86_400_000
LAUNCH_SPAN = 25 * HOUR + 10 * MIN   # aggTrades kept for [L, L+25h10m]: [L, L+24h] + room for T0+62m and L+24h+2m
EXIT_LO, EXIT_HI = 72 * HOUR - 5 * MIN, 72 * HOUR + 10 * MIN   # around T0+72h
KLINE_SPAN = 73 * HOUR


def load_events(path: Path = ROOT / "events.csv") -> list[dict]:
    rows = list(csv.DictReader(open(path)))
    for r in rows:
        for k in ("A_ms", "L_ms"):
            r[k] = int(r[k])
    return rows


def universe(evs: list[dict]) -> list[dict]:
    """TEST rows not removed by the frozen family lists."""
    return [e for e in evs if e["segment"] == "TEST" and e["excluded_by_family"] == "0"]


def day(ms: int) -> dt.date:
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).date()


def days_between(a_ms: int, b_ms: int) -> list[dt.date]:
    a, b = day(a_ms), day(b_ms - 1)
    return [a + dt.timedelta(days=i) for i in range((b - a).days + 1)]


def months_between(a_ms: int, b_ms: int) -> list[str]:
    return sorted({d.strftime("%Y-%m") for d in days_between(a_ms, b_ms)})
