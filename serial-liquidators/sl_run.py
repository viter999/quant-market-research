# Serial Liquidators - one script, frozen plan v2 (RULES_LOG.md, 14 Nov 2026).
# Prints ONLY the checks. Results go to sl_report.txt (not to be opened before Shawn's yes).
import os, sys, math, datetime, random
import duckdb, numpy as np

SRC = os.environ.get('SL_SRC', '../life_after_liquidation/data')
OUT = os.environ.get('SL_OUT', '.')
TMP = os.environ.get('SL_TMP', './duck_tmp')
os.makedirs(TMP, exist_ok=True)
E = datetime.date(1970, 1, 1).toordinal()
D0 = datetime.date(2025, 12, 1).toordinal() - E      # first day of the period
DH = datetime.date(2026, 3, 1).toordinal() - E       # first day of the second half
D1 = datetime.date(2026, 5, 31).toordinal() - E      # last day of the period
DEC_END = datetime.date(2025, 12, 31).toordinal() - E
D_24MAY = datetime.date(2026, 5, 24).toordinal() - E
D_1MAY = datetime.date(2026, 5, 1).toordinal() - E
MS = 86400000

con = duckdb.connect()
con.execute(f"set temp_directory='{TMP}'"); con.execute("set memory_limit='3GB'"); con.execute("set threads=4")
q = lambda s: con.execute(s).fetchall()
R = []          # report lines
C = []          # check lines
def w(s=''): R.append(s)
def pct(a, b): return f"{100.0*a/b:6.2f}%" if b else '   n/a'
ok_all = True
def check(name, ok, detail):
    global ok_all
    ok_all = ok_all and bool(ok)
    C.append(f"  {'PASS' if ok else 'FAIL'}  {name}: {detail}")

# ---------- load
con.execute(f"create table lf as select \"user\" u, coin, time, sz*px notional, time // {MS} d from '{SRC}/liq_fills.parquet'")
con.execute(f"create table wd as select \"user\" u, day d, n, notional, maker, nliq from '{SRC}/wallet_day.parquet' where day between {D0} and {D1}")
con.execute(f"create table ep as select \"user\" u, bool_or(is_mm) is_mm, count(*) n_ep from '{SRC}/episodes.parquet' group by 1")

n_lf = q("select count(*) from lf")[0][0]
n_lf_period = q(f"select count(*) from lf where d between {D0} and {D1}")[0][0]
check('(a) liquidation fills read = 2,161,385 (LAL figure), all inside the period', n_lf == 2161385 and n_lf_period == n_lf, f"{n_lf:,} read, {n_lf_period:,} in period")

# clusters (all wallets, before exclusions)
def cluster_sql(gap_min):
    return f"""select u, time, notional, d,
        sum(case when prev is null or time - prev >= {gap_min*60000} then 1 else 0 end) over (partition by u order by time, rn) cl
        from (select *, lag(time) over (partition by u order by time, rn) prev from (select *, row_number() over (partition by u order by time) rn from lf))"""
n_cl60_all = q(f"select count(*) from (select distinct u, cl from ({cluster_sql(60)}))")[0][0]
n_ep_tab = q(f"select count(*) from '{SRC}/episodes.parquet'")[0][0]
check('(b) 60-min clusters rebuilt = 710,878 = episodes.parquet rows', n_cl60_all == 710878 and n_ep_tab == 710878, f"rebuilt {n_cl60_all:,}, table {n_ep_tab:,}")

wd_liq = q(f"select cast(sum(nliq) as bigint) from wd")[0][0]
check('(c) wallet_day liquidation-fill total = liq_fills rows', wd_liq == n_lf, f"wallet_day {wd_liq:,}, liq_fills {n_lf:,}")

# wallets
con.execute(f"""create table wl as select u, sum(notional) tn, sum(maker) mk,
    count(*) filter (where n > 0) act, min(d) filter (where n > 0) first_d,
    count(*) filter (where n > 0 and d < {DH}) act1,
    count(*) filter (where n > nliq and d >= {DH}) nonliq2
    from wd group by 1""")
con.execute("alter table wl add column is_mm boolean"); con.execute("update wl set is_mm = (tn > 0 and mk >= 0.7*tn)")
dis = q("select count(*) from ep join wl using(u) where ep.is_mm <> wl.is_mm")[0][0]
miss = q("select count(*) from ep left join wl using(u) where wl.u is null")[0][0]
check('(d) market-maker flag from wallet_day agrees with episodes.parquet for every wallet there', dis == 0 and miss == 0, f"{dis:,} disagree, {miss:,} missing from wallet_day")

# ---------- per-wallet liquidation counts (non market makers)
con.execute("create table lfx as select lf.* from lf join wl using(u) where not wl.is_mm")
con.execute("create table ld as select u, d, sum(notional) notional, count(*) nf from lfx group by 1,2")
con.execute("""create table ldx as select *, sum(case when pd is null or d - pd > 1 then 1 else 0 end) over (partition by u order by d) spell
    from (select *, lag(d) over (partition by u order by d) pd from ld)""")
for g in (30, 60, 120):
    con.execute(f"create table cl{g} as select u, count(distinct cl) c from ({cluster_sql(g)}) where u in (select u from wl where not is_mm) group by 1")
con.execute(f"""create table lw as select a.u, a.days, a.spells, a.notional, a.nf, c30.c c30, c60.c c60, c120.c c120,
        wl.tn, wl.first_d, b.btceth,
        a.days1, a.days2
    from (select u, count(*) as days, max(spell) spells, sum(notional) notional, sum(nf) nf,
                 count(*) filter (where d < {DH}) days1, count(*) filter (where d >= {DH}) days2 from ldx group by 1) a
    join cl30 c30 using(u) join cl60 c60 using(u) join cl120 c120 using(u) join wl using(u)
    join (select u, bool_and(coin in ('BTC','ETH')) btceth from lfx group by 1) b using(u)""")
N = q("select count(*) from lw")[0][0]

def grp(col): return f"case when {col}=1 then '1' when {col}=2 then '2' when {col}<=5 then '3-5' when {col}<=10 then '6-10' else '11+' end"
GORD = ['1', '2', '3-5', '6-10', '11+']

def gini(x):
    x = np.sort(np.asarray(x, dtype=float)); n = len(x); s = x.sum()
    if n == 0 or s == 0: return float('nan')
    return float((2*np.arange(1, n+1) - n - 1).dot(x) / (n*s))

def m1m2(where, label, unit='days', full=True):
    rows = q(f"select u, {unit} k, notional from lw where {where}")
    n = len(rows)
    w(f"--- {label}: {n:,} liquidated wallets, unit = {unit} ---")
    if n == 0: w('  (none)'); return
    k = np.array([r[1] for r in rows], dtype=float); nt = np.array([r[2] for r in rows], dtype=float)
    tot_k, tot_n = k.sum(), nt.sum()
    def gname(v): return '1' if v == 1 else '2' if v == 2 else '3-5' if v <= 5 else '6-10' if v <= 10 else '11+'
    cnt = {g: 0 for g in GORD}
    for v in k: cnt[gname(v)] += 1
    w("  M1 share of wallets by count: " + ' | '.join(f"{g}: {pct(cnt[g], n)}" for g in GORD) + f"   (sum {100.0*sum(cnt.values())/n:.2f}%)")
    w(f"  M1 median {np.median(k):.0f}, p90 {np.percentile(k, 90):.0f}, p99 {np.percentile(k, 99):.0f}, max {k.max():.0f}; total {unit} {tot_k:,.0f}; total liquidated notional ${tot_n:,.0f}")
    sh = []
    for t in (3, 5, 10):
        m = k >= t
        sh.append((t, m.sum(), k[m].sum()/tot_k, nt[m].sum()/tot_n))
        w(f"  M2 wallets with >= {t} {unit}: {pct(m.sum(), n)} of wallets, {100*k[m].sum()/tot_k:6.2f}% of all {unit}, {100*nt[m].sum()/tot_n:6.2f}% of liquidated notional")
    if full:
        us = [r[0] for r in rows]
        by_k = sorted(range(n), key=lambda i: (-k[i], -nt[i], us[i]))
        by_n = sorted(range(n), key=lambda i: (-nt[i], -k[i], us[i]))
        tops = {}
        for p in (0.01, 0.10):
            g = math.ceil(p*n)
            a = np.array(by_k[:g]); b = np.array(by_n[:g])
            tops[p] = (k[a].sum()/tot_k, nt[b].sum()/tot_n)
            w(f"  M2 top {int(p*100)}% (= {g:,} wallets) ranked by {unit}: {100*k[a].sum()/tot_k:6.2f}% of {unit}, {100*nt[a].sum()/tot_n:6.2f}% of notional | ranked by notional: {100*k[b].sum()/tot_k:6.2f}% of {unit}, {100*nt[b].sum()/tot_n:6.2f}% of notional")
        w(f"  M2 Gini of {unit} {gini(k):.3f}; Gini of liquidated notional {gini(nt):.3f}")
        return cnt, n, sh, tops
    return cnt, n, sh, None

w("SERIAL LIQUIDATORS - results (frozen plan v2). Hyperliquid perps, 1 Dec 2025 - 31 May 2026 UTC. Vaults and market makers excluded.")
w("Liquidated notional = position size closed by liquidation, not dollars lost.")
w()
mm = q("select count(*), coalesce(sum(x.days),0), coalesce(sum(x.notional),0) from (select u, count(distinct d) as days, sum(notional) notional from lf join wl using(u) where wl.is_mm group by 1) x")[0]
allt = q("select count(distinct u), count(*), sum(notional) from lf")[0]
alld = q("select count(*) from (select distinct u, d from lf)")[0][0]
w(f"Before exclusion: {allt[0]:,} wallets with a liquidation fill, {allt[1]:,} fills, {alld:,} liquidation days, ${allt[2]:,.0f} liquidated notional.")
w(f"Market makers (reported once): {mm[0]:,} liquidated market-maker wallets, {mm[1]:,} liquidation days ({pct(mm[1], alld)}), ${mm[2]:,.0f} liquidated notional ({pct(mm[2], allt[2])}). Excluded below.")
w()
w("=== M1 / M2: ALL LIQUIDATED WALLETS ===")
res_days = m1m2('true', 'ALL', 'days')
res_sp = m1m2('true', 'ALL', 'spells')
for g in (60, 30, 120):
    m1m2('true', f'ALL (clusters, {g}-min gap)', f'c{g}')
w()
w("M1 median liquidated notional per liquidation day, by wallet group (number of liquidation days):")
gm = {r[0]: (r[1], r[2]) for r in q(f"select {grp('lw.days')} g, median(ld.notional), count(*) from ld join lw using(u) group by 1")}
w("  " + ' | '.join(f"{g}: ${gm[g][0]:,.0f} ({gm[g][1]:,} wallet-days)" if g in gm else f"{g}: n/a" for g in GORD))
w()

# ---------- M3
w("=== M3: BASE RATE (wallets with >= 1 liquidation day, among wallets that are not market makers) ===")
con.execute("create table wb as select wl.*, (lw.u is not null) liq from wl left join lw using(u) where not wl.is_mm and wl.act > 0")
def m3(where, label):
    for band, n, k in q(f"""select case when act<=2 then 'a 1-2' when act<=9 then 'b 3-9' when act<=29 then 'c 10-29' else 'd 30+' end b, count(*), count(*) filter (where liq) from wb where {where} group by 1 order by 1"""):
        w(f"  {label} active days {band[2:]:>5}: {n:>9,} wallets, {pct(k, n)} liquidated at least once")
    n, k = q(f"select count(*), count(*) filter (where liq) from wb where {where} and act >= 3")[0]
    w(f"  {label} active >= 3 days: {n:,} wallets, {pct(k, n)} liquidated at least once")
    n, k = q(f"select count(*), count(*) filter (where liq) from wb where {where}")[0]
    w(f"  {label} any fill: {n:,} wallets, {pct(k, n)} liquidated at least once")
m3('true', 'ALL')
for lab, cond in (('traded < $100k', 'tn < 1e5'), ('traded $100k-$10M', 'tn >= 1e5 and tn <= 1e7'), ('traded > $10M', 'tn > 1e7'), ('first seen Dec 2025', f'first_d <= {DEC_END}'), ('first seen later', f'first_d > {DEC_END}')):
    m3(cond, lab)
w()

# ---------- M4
w("=== M4: REPEAT ACROSS HALVES (first half Dec-Feb, second half Mar-May) ===")
w("Wallets active on >= 3 days in the first half, grouped by first-half liquidation days. 95% intervals: 2,000 bootstrap draws of wallets.")
rng = np.random.default_rng(20261114)
rows = q(f"""select case when coalesce(lw.days1,0)=0 then 'a 0' when lw.days1=1 then 'b 1' when lw.days1=2 then 'c 2' when lw.days1<=5 then 'd 3-5' else 'e 6+' end g,
    count(*) n,
    count(*) filter (where wb.nonliq2 > 0 and coalesce(lw.days2,0) > 0) a_l,
    count(*) filter (where wb.nonliq2 > 0 and coalesce(lw.days2,0) = 0) a_n,
    count(*) filter (where wb.nonliq2 = 0) gone,
    count(*) filter (where coalesce(lw.days2,0) > 0) any_l
    from wb left join lw using(u) where wb.act1 >= 3 group by 1 order by 1""")
for g, n, a_l, a_n, gone, any_l in rows:
    dr = rng.multinomial(n, [a_l/n, a_n/n, gone/n], size=2000)
    den = dr[:, 0] + dr[:, 1]
    hd = np.where(den > 0, dr[:, 0]/np.maximum(den, 1), np.nan)
    lo, hi = np.nanpercentile(hd, [2.5, 97.5])
    al = rng.binomial(n, any_l/n, size=2000)/n
    lo2, hi2 = np.percentile(al, [2.5, 97.5])
    w(f"  first-half liquidation days {g[2:]:>4}: {n:>9,} wallets | HEADLINE still trading in 2nd half and liquidated in 2nd half: {pct(a_l, a_l+a_n)} [{100*lo:.2f}, {100*hi:.2f}] (n={a_l+a_n:,}) | over all: {pct(any_l, n)} [{100*lo2:.2f}, {100*hi2:.2f}] | gone (no non-liquidation fill in 2nd half): {pct(gone, n)}")
both, n1, n2 = q("select count(*) filter (where days1>0 and days2>0), count(*) filter (where days1>0), count(*) filter (where days2>0) from lw")[0]
w(f"  Of all {N:,} liquidated wallets: {pct(both, N)} have liquidation days in both halves ({both:,}); liquidated in first half {n1:,}, in second half {n2:,}.")
w()

# ---------- M5
w("=== M5: SPACING (forward-looking) ===")
con.execute("create table nx as select u, d, lead(d) over (partition by u order by d) nd from ld")
def m5(where, label):
    a = q(f"select count(*), count(*) filter (where nd - d <= 1), count(*) filter (where nd - d <= 7) from nx where d <= {D_24MAY} and {where}")[0]
    b = q(f"select count(*), count(*) filter (where nd - d <= 30) from nx where d <= {D_1MAY} and {where}")[0]
    w(f"  {label}: liquidation days on or before 24 May: {a[0]:,}; followed by another within 1 day {pct(a[1], a[0])}, within 7 days {pct(a[2], a[0])} | on or before 1 May: {b[0]:,}; within 30 days {pct(b[1], b[0])}")
m5('true', 'ALL')
gq = q("select quantile_cont(nd - d, [0.25, 0.5, 0.75]), count(*) from nx where nd is not null")[0]
w(f"  Gap between consecutive liquidation days (wallets with >= 2; cut by the window): quartiles {gq[0][0]:.0f} / {gq[0][1]:.0f} / {gq[0][2]:.0f} days, {gq[1]:,} gaps")
w()

# ---------- splits
w("=== SPLITS (fixed in the plan): M1, M2 (>= 3 days), M5 (7 days) ===")
splits = (('traded < $100k', 'tn < 1e5'), ('traded $100k-$10M', 'tn >= 1e5 and tn <= 1e7'), ('traded > $10M', 'tn > 1e7'),
          ('liquidation fills BTC/ETH only', 'btceth'), ('liquidation fills include other coins', 'not btceth'),
          ('first seen Dec 2025', f'first_d <= {DEC_END}'), ('first seen later', f'first_d > {DEC_END}'))
split_n = {}
for lab, cond in splits:
    r = m1m2(cond, lab, 'days', full=False); split_n[lab] = r[1] if r else 0
    m5(f"u in (select u from lw where {cond})", lab)
w()

# ---------- checks e, f
cnt, n, sh, tops = res_days
e_ok = (sum(cnt.values()) == n == N) and sh[0][2] >= sh[1][2] >= sh[2][2] and sh[0][3] >= sh[1][3] >= sh[2][3] and tops[0.10][0] >= tops[0.01][0] and tops[0.10][1] >= tops[0.01][1]
e_ok = e_ok and split_n['traded < $100k'] + split_n['traded $100k-$10M'] + split_n['traded > $10M'] == N and split_n['liquidation fills BTC/ETH only'] + split_n['liquidation fills include other coins'] == N and split_n['first seen Dec 2025'] + split_n['first seen later'] == N
check('(e) M1 shares sum to 100%, ">= k" shares fall as k rises, top 10% >= top 1%, each split adds up to all wallets', e_ok, f"wallets {N:,}; group sum {sum(cnt.values()):,}")

random.seed(20261114)
us = [r[0] for r in q("select u from lw order by u")]
pick = random.sample(us, 20)
bad = 0
for u in pick:
    fills = q(f"select time, sz*px from '{SRC}/liq_fills.parquet' where \"user\" = '{u}' order by time")
    days = sorted({t // MS for t, _ in fills})
    spells = 1 + sum(1 for i in range(1, len(days)) if days[i] - days[i-1] > 1)
    nt = sum(v for _, v in fills)
    a = q(f"select days, spells, notional from lw where u = '{u}'")[0]
    if a[0] != len(days) or a[1] != spells or abs(a[2] - nt) > 1e-6*max(1.0, abs(nt)): bad += 1
check('(f) 20 random liquidated wallets: liquidation days, spells and notional recounted from liq_fills', bad == 0, f"{20-bad}/20 match")

status = 'CHECK PASS' if ok_all else 'CHECK FAIL'
open(os.path.join(OUT, 'sl_report.txt'), 'w', encoding='utf-8').write('\n'.join([status] + C + [''] + R) + '\n')
con.execute(f"copy lw to '{os.path.join(OUT, 'sl_wallets.parquet')}' (format parquet)")
print('Serial Liquidators run. Results written to sl_report.txt (NOT shown here).')
print(status)
print('\n'.join(C))
print('FINISHED OK' if ok_all else 'FAILED exit 1')
sys.exit(0 if ok_all else 1)
