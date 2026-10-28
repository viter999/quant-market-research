"""Frozen parameters: PREREG v0.3 and CLARIFICATIONS v0.3.1. Nothing here may
change without Shawn's gate (d)."""
import datetime as dt
import json
from pathlib import Path

STUDY_DIR = Path(__file__).resolve().parents[1]
SPLITS = json.loads((STUDY_DIR / "SPLITS.json").read_text())
SEGMENTS = {
    name: (dt.date.fromisoformat(SPLITS[name]["start"]), dt.date.fromisoformat(SPLITS[name]["end"]))
    for name in ("dev", "verdict", "holdout")
}

MINUTE_MS = 60_000
DAY_MS = 86_400_000

# §4 event rule
SIGMA_WINDOW = 240
SIGMA_MULT = 4.0
MIN_DROP = 0.01
VOL_WINDOW = 240
VOL_MULT = 5.0
COOLDOWN_MIN = 30
EPISODE_GAP_MIN = 30
LAST_DAY_CUTOFF_MIN = 23 * 60 + 30  # bar t must close <= 23:30 UTC on a segment's last day

# §2 universe
UNIVERSE_SIZE = 80
RANK_DAYS = 7

# §5 fill
NOTIONAL_USD = 500.0
PRIMARY_DEPTH = 0.005
DEPTHS = (0.0025, 0.005, 0.01)
PRIMARY_LATENCY_S = 2
LATENCIES_S = (2, 5, 10)
PRIMARY_QUEUE_MULT = 20
QUEUE_MULTS = (5, 10, 20)
CANCEL_AFTER_S = 300
GAP_SLIPPAGE = 0.0005

# §6 exit and costs
PRIMARY_HOLD_MIN = 15
EXIT_VWAP_S = 10
EXIT_LAST_MAX_AGE_S = 60
FEE_MAKER = 0.0002
FEE_TAKER = 0.0005
BUFFER_PER_MULT = 0.0005  # 5 bps x {1, 2, 5}
BUFFER_MULTS = (1, 2, 5)

# §7 placebo / sanity check
N_PLACEBO = 5
PLACEBO_MAX_DAYS = 3
PLACEBO_NO_EVENT_MIN = 120
PLACEBO_HOUR_TOL_MIN = 60
PLACEBO_SIGMA_TOL = 0.25
PLACEBO_QV_TOL = 0.50
PLACEBO_QV_WINDOW = 60
SEED_PLACEBO = 20261029
SEED_BOOTSTRAP = 20261030
SEED_SANITY = 20261031
N_SANITY = 50

# §8
N_BOOT = 10_000
POWER_SCALE = SPLITS["verdict"]["days"] / SPLITS["dev"]["days"]  # 200/602
MIN_FILLS, MIN_EPISODES, MIN_DAYS = 300, 100, 40

# Data handling: aggTrades windows around the reference time (bar close), v0.3.2
WINDOW_PRE_MIN = 5
WINDOW_POST_MIN = 70

# No event before the study period (klines from 2023-12-01 are lookback inputs only)
PERIOD_START = dt.date.fromisoformat(SPLITS["period"]["start"])

# §8 verdict thresholds (fractions, not bps)
PASS_MEAN_1X = 0.0015
PASS_LB_LEVEL = 0.999
PASS_MEAN_2X = 0.0005
PASS_PLACEBO_MARGIN = 0.0010
PASS_PLACEBO_LB_LEVEL = 0.99
HOLDOUT_MEAN_1X = 0.0008
HOLDOUT_LB_LEVEL = 0.95


def segment_of(day: dt.date) -> str | None:
    """'dev' / 'verdict' / 'holdout', or None for embargo days and out-of-period days."""
    for name, (a, b) in SEGMENTS.items():
        if a <= day <= b:
            return name
    return None


def ms_to_date(ms: int) -> dt.date:
    return dt.date(1970, 1, 1) + dt.timedelta(days=int(ms) // DAY_MS)


def date_to_ms(day: dt.date) -> int:
    return (day - dt.date(1970, 1, 1)).days * DAY_MS
