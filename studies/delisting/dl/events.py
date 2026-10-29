"""Event list and window arithmetic (CLARIFICATIONS v0.2.1)."""
import csv
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN = 60_000
HOUR = 3_600_000
DAY = 86_400_000


def load_events(path: Path = ROOT / "events.csv") -> list[dict]:
    rows = list(csv.DictReader(open(path)))
    for r in rows:
        for k in ("A_ms", "D_ms", "N_ms"):
            r[k] = int(r[k])
    return rows


def floor_min(ms: int) -> int:
    return ms - ms % MIN


def ceil_min(ms: int) -> int:
    return -(-ms // MIN) * MIN


def windows(ev: dict) -> dict:
    """Bar open times (ms) used for one event."""
    a0 = floor_min(ev["A_ms"])
    return {
        "pre_lo": a0 - DAY, "pre_hi": a0,                   # 1440 bars [a0-24h, a0), all closed by A
        "ts_lo": a0 - 30 * MIN, "ts_hi": a0 + 30 * MIN,     # 61 bars, open_time in [a0-30m, a0+30m]
        "entry": ceil_min(ev["A_ms"] + 30 * MIN),           # first bar opening at or after A+30m
        "exit": ev["N_ms"] - 30 * MIN,                      # bar [N-30m, N-29m)
    }


def days_needed(ev: dict) -> list[dt.date]:
    """UTC days covering [A-24h, D]."""
    a = dt.datetime.fromtimestamp((ev["A_ms"] - DAY) / 1000, dt.timezone.utc).date()
    b = dt.datetime.fromtimestamp(ev["D_ms"] / 1000, dt.timezone.utc).date()
    return [a + dt.timedelta(days=i) for i in range((b - a).days + 1)]


def months_needed(ev: dict) -> list[str]:
    days = days_needed(ev)
    return sorted({d.strftime("%Y-%m") for d in days})
