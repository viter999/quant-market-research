# Fade the Comeback - step 2: events, returns, checks, verdict. Rules: RULES_LOG.md (frozen plan v2, notes N1-N11).
# Prints only the checks. Results go to ftc_report.txt and are not shown on screen.
import os, sys, math, duckdb, numpy as np, pandas as pd

ROOT = os.environ.get('FTC_ROOT', '..')
FILLS = os.environ.get('FTC_FILLS', os.path.join(ROOT, 'data', 'fills'))
LIQ = os.environ.get('FTC_LIQ', os.path.join(ROOT, 'life_after_liquidation', 'data', 'liq_fills.parquet'))
EPI = os.environ.get('FTC_EPI', os.path.join(ROOT, 'life_after_liquidation', 'data', 'episodes.parquet'))
VAULTS = os.environ.get('FTC_VAULTS', os.path.join(ROOT, 'data', 'vaults.csv'))
CMAP = os.environ.get('FTC_CMAP', os.path.join(ROOT, 'data', 'coin_map.csv'))
KL = os.environ.get('FTC_KL', os.path.join(ROOT, 'data', 'binance_1m'))
OUT = os.environ.get('FTC_OUT', 'data'); REP = os.environ.get('FTC_REP', '.')
CHECK_C = os.environ.get('FTC_CHECK_C', 'frozen')   # 'frozen' = check (c) as frozen; 'A1' = amended (c') if Shawn approves
MIN, HOUR, DAY = 60000, 3600000, 86400000
COST, NB, SEED = 0.004, 10000, 20261115
SPLIT = 1772323200000  # 1 Mar 2026 00:00 UTC
DEC31 = 1767139200000  # 31 Dec 2025 00:00 UTC

con = duckdb.connect(); con.execute("set memory_limit='2GB'"); con.execute("set threads=2")
cm = con.execute(f"select coin, binance from read_csv_auto('{CMAP}') where status = 'PASS'").df()
SYM = dict(zip(cm.coin, cm.binance)); COINS = [c for c in cm.coin if c != 'BTC']
R, C = [], []; ok_all = True
def w(s=''): R.append(s)
def check(name, ok, detail):
    global ok_all
    ok_all = ok_all and bool(ok); C.append(f"  {'PASS' if ok else 'FAIL'}  {name}: {detail}")

# ---------- prices ----------
PX = {}
for c in COINS + ['BTC']:
    k = con.execute(f"select open_time, close from '{KL}/{SYM[c]}.parquet'").df()
    PX[c] = pd.Series(k.close.values, index=k.open_time.values)
def closes(c, t):  # close of the 1m candle opening at t (NaN if missing)
    return PX[c].reindex(np.asarray(t, dtype='int64')).values
def rel_ret(c, t_in, t_out):
    a, b = closes(c, t_in), closes(c, t_out); x, y = closes('BTC', t_in), closes('BTC', t_out)
    return b / a - 1 - (y / x - 1), b / a - 1

# ---------- re-entries (first opening fill after a liquidation fill, within 60 min) ----------
re = con.execute(f"""select u, coin, time, tid, dir, s from read_parquet('{OUT}/reentry/*.parquet')
    qualify row_number() over (partition by u, coin, s order by time, tid) = 1""").df()
re['hour'] = re.time // HOUR; re['side'] = np.where(re.dir == 'Open Long', 1, -1)
con.register('re_v', re[['u', 'time']])
con.execute(f"""create table chron as select r.u, r.time,
    (select count(distinct l.time // {DAY}) from '{LIQ}' l where l."user" = r.u and l.time >= r.time - {30*DAY} and l.time < r.time) nd
    from (select distinct u, time from re_v) r""")
re = re.merge(con.execute("select u, time, nd from chron").df(), on=['u', 'time'], how='left')

def hourly(df, min_n):  # one row per coin-hour: wallets by side (each wallet once, first fill in the hour)
    f = df.sort_values(['time', 'tid']).drop_duplicates(['u', 'coin', 'hour'])
    g = f.groupby(['coin', 'hour']).side.agg(nL=lambda x: int((x == 1).sum()), nS=lambda x: int((x == -1).sum())).reset_index()
    g['n'] = g.nL + g.nS; g['maj'] = g[['nL', 'nS']].max(axis=1)
    g = g[(g.n >= min_n) & (g.maj * 10 >= g.n * 7)].copy()
    g['crowd'] = np.where(g.nL >= g.nS, 1, -1); g['E'] = (g.hour + 1) * HOUR
    return g.sort_values(['E', 'coin']).reset_index(drop=True), f

def take(ev, hold=240):  # one open trade per coin; drop events with a missing candle
    rows, skipped, dropped = [], 0, 0
    for c, g in ev.groupby('coin'):
        t_in = g.E.values + 3 * MIN; t_out = t_in + hold * MIN
        rr, raw = rel_ret(c, t_in, t_out); busy = -1
        for i in range(len(g)):
            if g.E.values[i] < busy: skipped += 1; continue
            if not np.isfinite(rr[i]): dropped += 1; continue
            busy = t_out[i] + MIN
            rows.append((c, g.E.values[i], -g.crowd.values[i], rr[i], raw[i], g.n.values[i]))
    t = pd.DataFrame(rows, columns=['coin', 'E', 'd', 'rel', 'raw', 'n'])
    t['g'] = t.d * t.rel; t['graw'] = t.d * t.raw; t['day'] = (t.E + 3 * MIN) // DAY
    return t.sort_values('E').reset_index(drop=True), skipped, dropped

rng = np.random.default_rng(SEED)
def boot(vals, days):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    s = np.bincount(inv, weights=vals, minlength=nd); n = np.bincount(inv, minlength=nd).astype(float)
    W = rng.multinomial(nd, np.ones(nd) / nd, size=NB).astype(float)
    m = (W @ s) / np.maximum(W @ n, 1e-12)
    return np.percentile(m, [5, 95])
def line(label, t, col='g'):
    if len(t) == 0: return f"  {label}: no events"
    lo, hi = boot(t[col].values, t.day.values) if t.day.nunique() > 1 else (float('nan'), float('nan'))
    return (f"  {label}: n={len(t):,} on {t.day.nunique()} days | gross mean {100*t[col].mean():+.3f}% [{100*lo:+.3f}, {100*hi:+.3f}] "
            f"| median {100*t[col].median():+.3f}% | hit rate {100*(t[col] > 0).mean():.1f}% | net at 0.40% {100*(t[col].mean()-COST):+.3f}%")

ev, first = hourly(re, 10)
T, skipped, dropped = take(ev)
n, nd = len(T), T.day.nunique() if len(T) else 0

# ---------- checks ----------
check('(a) event count and day count', True, f"{len(ev):,} events flagged; {n:,} traded on {nd} days; {skipped:,} skipped (trade still open); {dropped:,} dropped (missing candle)")
check('(b) entry and exit candles exist for at least 99% of events', (n + dropped) > 0 and dropped <= 0.01 * (n + dropped), f"{dropped:,} of {n + dropped:,} missing")
r2 = np.random.default_rng(SEED + 1)
hmin = int(min(PX[c].index.min() for c in COINS) // HOUR) + 2; hmax = int(PX['BTC'].index.max() // HOUR) - 5
rc = r2.integers(0, len(COINS), 1000); rh = r2.integers(hmin, hmax, 1000)
samp = np.array([rel_ret(COINS[i], np.array([(h + 1) * HOUR + 3 * MIN]), np.array([(h + 1) * HOUR + 243 * MIN]))[0][0] for i, h in zip(rc, rh)])
if CHECK_C == 'A1':
    alt = []
    for i, h in zip(rc, rh):
        t1, t2 = (h + 1) * HOUR + 3 * MIN, (h + 1) * HOUR + 243 * MIN
        q = con.execute(f"""select (select close from '{KL}/{SYM[COINS[i]]}.parquet' where open_time = {t2}) / (select close from '{KL}/{SYM[COINS[i]]}.parquet' where open_time = {t1})
              - (select close from '{KL}/BTCUSDT.parquet' where open_time = {t2}) / (select close from '{KL}/BTCUSDT.parquet' where open_time = {t1})""").fetchone()[0]
        alt.append(np.nan if q is None else q)
    alt = np.array(alt); both = np.isfinite(samp) & np.isfinite(alt)
    same = (np.isfinite(samp) == np.isfinite(alt)).all() and (np.abs(samp[both] - alt[both]) < 1e-9).all()
    check("(c') 1,000 random coin-hour returns match a separate SQL recompute", same, f"{int(both.sum())} compared, max difference {np.abs(samp[both]-alt[both]).max() if both.any() else float('nan'):.2e}")
else:
    m = np.nanmean(samp)
    check('(c) mean BTC-relative 4h return of 1,000 random coin-hours within 0.02% of zero', abs(m) <= 0.0002, f"mean {100*m:+.4f}% (n={int(np.isfinite(samp).sum())})")
# (d) recount 20 random events straight from the raw fills, separate SQL
r3 = np.random.default_rng(SEED + 2); pick = T.iloc[r3.choice(len(T), min(20, len(T)), replace=False)] if len(T) else T
evx = ev.set_index(['coin', 'E']); bad = 0
for _, e in pick.iterrows():
    E = int(e.E); files = []
    for hh in range(E - 3 * HOUR, E + 2 * HOUR, HOUR):
        ts = pd.Timestamp(hh, unit='ms'); p = os.path.join(FILLS, ts.strftime('%Y%m%d'), ts.strftime('%H') + '.parquet')
        if os.path.exists(p): files.append("'" + p.replace(os.sep, '/') + "'")
    q = con.execute(f"""
      with f as (select distinct "user" u, coin, time, tid, dir, liq_user from read_parquet([{','.join(files)}]) where coin = '{e.coin}' and time >= {E - 2*HOUR} and time < {E}),
           lq as (select u, time from f where liq_user = u and lower(u) not in (select lower(address) from read_csv_auto('{VAULTS}'))
                  and u not in (select "user" from '{EPI}' where is_mm)),
           op as (select * from f where dir in ('Open Long', 'Open Short')),
           x as (select o.u, o.time, o.tid, o.dir, (select max(l.time) from lq l where l.u = o.u and l.time < o.time) s from op o),
           y as (select * from x where s is not null and time - s <= {HOUR}
                 and not exists (select 1 from op p where p.u = x.u and p.time > x.s and (p.time < x.time or (p.time = x.time and p.tid < x.tid)))),
           z as (select u, arg_min(dir, (time, tid)) dir from y where time >= {E - HOUR} group by u)
      select count(*) filter (where dir = 'Open Long'), count(*) filter (where dir = 'Open Short') from z""").fetchone()
    main = evx.loc[(e.coin, E)]
    if (int(main.nL), int(main.nS)) != (int(q[0]), int(q[1])): bad += 1
check('(d) 20 random events recounted from raw fills by separate code', len(pick) > 0 and bad == 0, f"{len(pick) - bad} of {len(pick)} match")

# ---------- verdict ----------
w("FADE THE COMEBACK - frozen plan v2. One look. TRAIN only (1 Dec 2025 - 31 May 2026).")
w(f"Signal: per coin-hour, 10+ just-liquidated wallets re-enter, 70%+ on one side. Trade: against them, entry +3 min, hold 4h, BTC-relative, cost 0.40%.")
w()
if n < 200 or nd < 40:
    w(f"VERDICT: NOT EVALUABLE. {n} events on {nd} days; the plan needs at least 200 events on at least 40 days.")
else:
    net = T.g.values - COST; lo, hi = boot(net, T.day.values)
    k = math.ceil(0.01 * n); trimmed = np.sort(T.g.values)[:-k] - COST
    c1 = net.mean() > 0 and lo > 0; c2 = np.median(T.g.values) > 0; c3 = trimmed.mean() > 0
    w(f"VERDICT (4-hour aggregate only): {'PASS' if (c1 and c2 and c3) else 'FAIL'}")
    w(f"  (1) mean net at 0.40% cost {100*net.mean():+.3f}%, 90% interval [{100*lo:+.3f}, {100*hi:+.3f}] -> {'holds' if c1 else 'does not hold'}")
    w(f"  (2) median gross {100*np.median(T.g.values):+.3f}% -> {'holds' if c2 else 'does not hold'}")
    w(f"  (3) mean net after dropping the largest {k} events {100*trimmed.mean():+.3f}% -> {'holds' if c3 else 'does not hold'}")
    w(f"  Mean net at 0.20% cost {100*(T.g.mean()-0.002):+.3f}%; at 0.80% cost {100*(T.g.mean()-0.008):+.3f}%.")
w()
w("ALSO REPORTED (no verdict; none of this can rescue or soften a FAIL)")
w(line('4 hours, all events', T))
for hold, nm in ((60, '1 hour'), (1440, '24 hours')):
    rr = np.full(len(T), np.nan)
    for c, g in T.groupby('coin'):
        rr[g.index.values] = rel_ret(c, g.E.values + 3 * MIN, g.E.values + (3 + hold) * MIN)[0]
    t2 = T.assign(g=T.d.values * rr); t2 = t2[np.isfinite(t2.g)]
    w(line(f"{nm}, same events", t2))
w(line('Fade a long crowd (we short)', T[T.d == -1])); w(line('Fade a short crowd (we long)', T[T.d == 1]))
w(line('First half (before 1 Mar 2026)', T[T.E < SPLIT])); w(line('Second half', T[T.E >= SPLIT]))
w(line('Raw returns (not BTC-relative)', T, 'graw'))
w(f"  Distinct event-hours: {T.E.nunique():,}; unique wallets in traded events: {first.merge(T.assign(hour=T.E // HOUR - 1)[['coin', 'hour']], on=['coin', 'hour']).u.nunique():,}")
w("  Events per coin: " + ', '.join(f"{c} {k}" for c, k in T.coin.value_counts().items()))
ch = re[(re.nd >= 3) & (re.time >= DEC31)]; evc, _ = hourly(ch, 5); Tc, _, _ = take(evc)
w(line('Chronic-only subset (3+ liquidation days in prior 30 days; 5+ wallets; from 31 Dec 2025)', Tc))
lq = con.execute(f"""select "user" u, coin, time, tid, dir from '{LIQ}' where coin in ({','.join("'" + c + "'" for c in COINS)})
    and "user" not in (select "user" from '{EPI}' where is_mm)""").df()
lq['hour'] = lq.time // HOUR; lq['side'] = np.where(lq.dir.str.contains('Long'), 1, -1)
evA, _ = hourly(lq, 10); TA, _, _ = take(evA)
w(line('Baseline A (10+ liquidated wallets on one side, no re-entry condition; trade against the liquidated side)', TA))
# Baseline B
if len(T):
    Tp = np.full(len(T), np.nan)
    for c, g in T.groupby('coin'):
        Tp[g.index.values] = rel_ret(c, g.E.values - 61 * MIN, g.E.values - MIN)[0]
    okp = np.isfinite(Tp); cuts = np.quantile(np.abs(Tp[okp]), [1/3, 2/3])
    Tr = np.sign(T.d.values * Tp); Tt = np.digitize(np.abs(Tp), cuts)
    evset = set(zip(ev.coin, ev.E)); cells = {}
    for c in COINS:
        hs = np.arange(int(PX[c].index.min() // HOUR) + 2, int(PX[c].index.max() // HOUR) - 5) * HOUR
        hs = np.array([h for h in hs if (c, h) not in evset])
        p = rel_ret(c, hs - 61 * MIN, hs - MIN)[0]; f = rel_ret(c, hs + 3 * MIN, hs + 243 * MIN)[0]
        m = np.isfinite(p) & np.isfinite(f) & (p != 0); p, f = p[m], f[m]; th = np.digitize(np.abs(p), cuts)
        for r in (1, -1):
            for k in (0, 1, 2):
                cells.setdefault((r, k), []).append((r * np.sign(p) * f)[th == k])
    base, wsum = 0.0, 0
    for (r, k), parts in cells.items():
        cnt = int(((Tr == r) & (Tt == k) & okp).sum())
        v = np.concatenate(parts)
        if cnt and len(v): base += cnt * v.mean(); wsum += cnt
    if wsum:
        base /= wsum
        w(f"  Baseline B (same fade in matched non-event hours): gross mean {100*base:+.3f}%; events minus baseline {100*(T.g[okp].mean()-base):+.3f}%")
w()
w("Known limit: the 19 coins were chosen on 5 Nov 2026 using whole-period volume, so the list is not point-in-time.")

status = 'CHECK PASS' if ok_all else 'CHECK FAIL'
open(os.path.join(REP, 'ftc_report.txt'), 'w', encoding='utf-8').write('\n'.join([status] + C + ([''] + R if ok_all else ['', 'Checks failed: no results written.'])) + '\n')
print('Fade the Comeback. Results written to ftc_report.txt (not shown here).')
print(status); print('\n'.join(C))
print('FINISHED OK' if ok_all else 'FAILED exit 1')
sys.exit(0 if ok_all else 1)
