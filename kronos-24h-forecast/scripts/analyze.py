"""ONE LOOK: outcomes, PRIMARY/SECONDARY tests and report-only stats, exactly as PREREG_kronos.md §7-8.

Refuses to run if results/REPORT_kronos.md already exists, or if the forecast file is incomplete.
"""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kt_common as kt
import kt_binance as kb

import numpy as np
import pandas as pd
from scipy import stats

HOUR = pd.Timedelta(hours=1)
REPORT = os.path.join(kt.RESULTS, "REPORT_kronos.md")


def validate(fc, syms, days):
    """Completeness and internal consistency of the forecast file. Raises on any problem."""
    n = len(days) * len(syms)
    if len(fc) != n:
        raise SystemExit(f"expected {n} forecast rows, found {len(fc)}")
    if fc.duplicated(["day", "symbol"]).any():
        raise SystemExit("duplicate (day, symbol) rows")
    if set(fc.day) != {d.strftime("%Y-%m-%d") for d in days} or set(fc.symbol) != set(syms):
        raise SystemExit("days or symbols differ from the prereg")
    idx = fc.symbol.map({s: i for i, s in enumerate(syms)})
    if not (fc.coin_index.astype(int) == idx).all():
        raise SystemExit("coin_index does not match the frozen universe order")
    seeds = [kt.seed_for(pd.Timestamp(d), i) for d, i in zip(fc.day, idx)]
    if not (fc.seed.astype(np.int64).to_numpy() == np.array(seeds, dtype=np.int64)).all():
        raise SystemExit("seed column does not follow the prereg formula")
    sig = np.sign(fc.p24.astype(float) - fc.c0.astype(float)).astype(int)
    if not (sig == fc.signal.astype(int)).all():
        raise SystemExit("signal column is not sign(p24 - c0)")


def compute(fc, closes, syms):
    """fc: one row per (day, symbol) with c0 and signal. closes: symbol -> 1h close Series (naive UTC open_time)."""
    fc = fc.copy()
    fc["D"] = pd.to_datetime(fc.day)
    fc["signal"] = fc.signal.astype(int)
    fc["c0"] = fc.c0.astype(float)
    parts = []
    for sym, g in fc.groupby("symbol", sort=False):
        c0_data = closes[sym].reindex(g.D - HOUR).to_numpy()
        c24 = closes[sym].reindex(g.D + 23 * HOUR).to_numpy()
        if np.isnan(c0_data).any() or np.isnan(c24).any():
            raise SystemExit(f"missing settlement bars for {sym}")
        if not np.allclose(c0_data, g.c0.to_numpy(), rtol=1e-12, atol=0):
            raise SystemExit(f"c0 in forecasts does not match the data for {sym}")
        parts.append(g.assign(r=c24 / c0_data - 1.0))
    fc = pd.concat(parts)

    days = sorted(fc.D.unique())
    R = fc.pivot(index="D", columns="symbol", values="r").loc[days, syms].to_numpy()
    Sg = fc.pivot(index="D", columns="symbol", values="signal").loc[days, syms].to_numpy()
    btc = syms.index("BTCUSDT")
    others = [j for j in range(len(syms)) if j != btc]
    Rrel = R[:, others] - R[:, [btc]]

    P = (Sg * R - kt.FEE * np.abs(Sg)).mean(axis=1)                 # PRIMARY daily series
    S = (Sg[:, others] * Rrel).mean(axis=1)                          # SECONDARY daily series
    AL = (R - kt.FEE).mean(axis=1)                                   # always-long net (report only)
    t_p = stats.ttest_1samp(P, 0.0, alternative="greater")
    t_s = stats.ttest_1samp(S, 0.0, alternative="greater")
    t_al = stats.ttest_1samp(AL, 0.0)

    traded = (Sg != 0) & (R != 0)
    hits = (np.sign(R) == Sg) & traded

    rng = np.random.default_rng(kt.NULL_SEED)
    chunk = 500
    null_p, null_s = [], []
    for _ in range(kt.NULL_RUNS // chunk):
        signs = (rng.integers(0, 2, size=(chunk,) + R.shape, dtype=np.int8) * 2 - 1).astype(np.float64)
        null_p.append((signs * R).mean(axis=(1, 2)) - kt.FEE)
        null_s.append((signs[:, :, others] * Rrel).mean(axis=(1, 2)))
    null_p, null_s = np.concatenate(null_p), np.concatenate(null_s)

    daily = pd.DataFrame({"day": pd.DatetimeIndex(days), "P": P, "S": S, "always_long_net": AL,
                          "hits": hits.sum(axis=1), "traded": traded.sum(axis=1)})
    m = daily.groupby(daily.day.dt.to_period("M"))
    monthly = pd.DataFrame({"days": m.size(), "mean_P": m.P.mean(), "mean_S": m.S.mean(),
                            "hit_rate": m.hits.sum() / m.traded.sum(),
                            "mean_always_long_net": m.always_long_net.mean()})

    primary_pass = bool(t_p.pvalue < kt.ALPHA)
    secondary_pass = bool(t_s.pvalue < kt.ALPHA)
    return {
        "n_days": len(days), "n_coins": len(syms),
        "primary": {"mean": float(P.mean()), "std": float(P.std(ddof=1)), "t": float(t_p.statistic),
                    "p_one_sided": float(t_p.pvalue), "pass": primary_pass},
        "secondary": {"mean": float(S.mean()), "std": float(S.std(ddof=1)), "t": float(t_s.statistic),
                      "p_one_sided": float(t_s.pvalue), "pass": secondary_pass},
        "decision": "PASS" if primary_pass and secondary_pass else "DROP",
        "report_only": {
            "hit_rate": float(hits.sum() / traded.sum()), "hit_n": int(traded.sum()),
            "always_long_net_mean": float(AL.mean()), "always_long_net_t": float(t_al.statistic),
            "null_primary_share_ge": float((null_p >= P.mean()).mean()),
            "null_primary_p95": float(np.percentile(null_p, 95)),
            "null_secondary_share_ge": float((null_s >= S.mean()).mean()),
            "null_secondary_p95": float(np.percentile(null_s, 95)),
            "signals_long": int((Sg == 1).sum()), "signals_short": int((Sg == -1).sum()),
            "signals_zero": int((Sg == 0).sum()),
        },
        "daily": daily, "monthly": monthly,
    }


def pct(x, nd=3):
    return f"{100 * x:.{nd}f}%"


def write_report(res, path, freeze_digest):
    p, s, ro = res["primary"], res["secondary"], res["report_only"]
    lines = [
        "# REPORT — Kronos-small next-24h direction (one look)",
        "",
        f"Generated {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by `scripts/analyze.py`. "
        f"Frozen spec: `PREREG_kronos.md`; `FREEZE_kronos.sha256` SHA-256 `{freeze_digest}`.",
        f"{res['n_days']} forecast days × {res['n_coins']} coins.",
        "",
        f"## Decision: **{res['decision']}**",
        "",
        "| Test | Mean per day | Std | t | one-sided p | α = 0.05 |",
        "|---|---|---|---|---|---|",
        f"| PRIMARY: mean_i(s·r − 0.10% if s ≠ 0) | {pct(p['mean'], 4)} | {pct(p['std'], 3)} | {p['t']:.3f} | {p['p_one_sided']:.4f} | {'pass' if p['pass'] else 'fail'} |",
        f"| SECONDARY: mean_i≠BTC s·(r − r_BTC), gross | {pct(s['mean'], 4)} | {pct(s['std'], 3)} | {s['t']:.3f} | {s['p_one_sided']:.4f} | {'pass' if s['pass'] else 'fail'} |",
        "",
        "## Report only (not part of the decision)",
        "",
        f"- Hit rate: {pct(ro['hit_rate'], 2)} of {ro['hit_n']:,} coin-days with s ≠ 0 and r ≠ 0",
        f"- Always-long net: {pct(ro['always_long_net_mean'], 4)} per day (t = {ro['always_long_net_t']:.3f})",
        f"- Random-sign null, {kt.NULL_RUNS:,} runs: PRIMARY share of runs ≥ Kronos {ro['null_primary_share_ge']:.4f}, "
        f"95th pct {pct(ro['null_primary_p95'], 4)}; SECONDARY share ≥ Kronos {ro['null_secondary_share_ge']:.4f}, "
        f"95th pct {pct(ro['null_secondary_p95'], 4)}",
        f"- Signals: long {ro['signals_long']:,}, short {ro['signals_short']:,}, zero {ro['signals_zero']:,}",
        "",
        "### Per month",
        "",
        "| Month | Days | Mean PRIMARY | Mean SECONDARY | Hit rate | Mean always-long net |",
        "|---|---|---|---|---|---|",
    ]
    for month, row in res["monthly"].iterrows():
        lines.append(f"| {month} | {int(row.days)} | {pct(row.mean_P, 4)} | {pct(row.mean_S, 4)} | "
                     f"{pct(row.hit_rate, 2)} | {pct(row.mean_always_long_net, 4)} |")
    lines += ["", "Daily series: `results/daily_series.csv`. All numbers: `results/analysis.json`.", ""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def save_outputs(res, out_dir, report_path, freeze_digest):
    res["daily"].to_csv(os.path.join(out_dir, "daily_series.csv"), index=False)
    out = {k: v for k, v in res.items() if k not in ("daily", "monthly")}
    out["monthly"] = {str(k): {c: float(v) for c, v in row.items()} for k, row in res["monthly"].iterrows()}
    with open(os.path.join(out_dir, "analysis.json"), "w") as f:
        json.dump(out, f, indent=2)
    write_report(res, report_path, freeze_digest)


def main():
    if os.path.exists(REPORT):
        raise SystemExit("REPORT_kronos.md already exists: the one look has been taken. Not rerunning.")
    with open(os.path.join(kt.LOGS, "analysis_attempts.log"), "a") as f:
        f.write(f"{dt.datetime.now(dt.timezone.utc).isoformat()} analyze.py started pid={os.getpid()}\n")
    kt.verify_freeze()
    syms = kt.universe()
    days = list(pd.date_range(kt.FULL_FIRST_DAY, kt.FULL_LAST_DAY, freq="D"))
    fc = pd.read_csv(os.path.join(kt.RESULTS, "forecasts.csv"), dtype=str)
    validate(fc, syms, days)
    closes = {s: kb.load_1h_bars(s, *kt.DATA_MONTHS)["close"] for s in syms}
    res = compute(fc, closes, syms)
    save_outputs(res, kt.RESULTS, REPORT, kt.sha256_file(kt.FREEZE))
    print(f"decision {res['decision']}; report written to {REPORT}")


if __name__ == "__main__":
    main()
