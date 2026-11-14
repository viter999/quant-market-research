# Serial Liquidators - EXPLORATORY check X (rules in RULES_LOG.md, 14 Nov 2026 20:12 BKK).
# Prints only the checks. Results go to slx_report.txt.
import os, sys, datetime
import duckdb, numpy as np

SRC = os.environ.get('SL_SRC', '../life_after_liquidation/data')
OUT = os.environ.get('SL_OUT', '.')
TMP = os.environ.get('SL_TMP', './duck_tmp')
os.makedirs(TMP, exist_ok=True)
E = datetime.date(1970, 1, 1).toordinal()
D0 = datetime.date(2025, 12, 1).toordinal() - E
DH = datetime.date(2026, 3, 1).toordinal() - E
D1 = datetime.date(2026, 5, 31).toordinal() - E
MS = 86400000
con = duckdb.connect()
con.execute(f"set temp_directory='{TMP}'"); con.execute("set memory_limit='3GB'"); con.execute("set threads=4")
q = lambda s: con.execute(s).fetchall()
R, C = [], []
def w(s=''): R.append(s)
ok_all = True
def check(name, ok, detail):
    global ok_all
    ok_all = ok_all and bool(ok); C.append(f"  {'PASS' if ok else 'FAIL'}  {name}: {detail}")

con.execute(f"create table wd as select \"user\" u, day d, n, notional, maker, nliq from '{SRC}/wallet_day.parquet' where day between {D0} and {D1}")
con.execute(f"""create table wl as select u, sum(notional) tn, sum(maker) mk,
    count(*) filter (where n > 0) act,
    count(*) filter (where n > 0 and d < {DH}) act1,
    count(*) filter (where n > nliq and d >= {DH}) nonliq2,
    coalesce(sum(notional) filter (where d < {DH}), 0) tn1
    from wd group by 1""")
con.execute(f"""create table ld as select \"user\" u, time // {MS} d from '{SRC}/liq_fills.parquet' group by 1, 2""")
con.execute(f"""create table lw as select u, count(*) as days, count(*) filter (where d < {DH}) days1, count(*) filter (where d >= {DH}) days2 from ld group by 1""")
con.execute("""create table p as select wl.u, wl.act, wl.act1, wl.nonliq2, wl.tn1,
    coalesce(lw.days,0) as days, coalesce(lw.days1,0) days1, coalesce(lw.days2,0) days2
    from wl left join lw using(u) where not (wl.tn > 0 and wl.mk >= 0.7*wl.tn) and wl.act > 0""")

G = "case when days1=0 then 0 when days1=1 then 1 when days1=2 then 2 when days1<=5 then 3 else 4 end"
GN = ['0', '1', '2', '3-5', '6+']
A1 = "case when act1<=9 then 0 when act1<=29 then 1 else 2 end"; A1N = ['3-9', '10-29', '30+']
A2 = "case when nonliq2<=9 then 0 when nonliq2<=29 then 1 else 2 end"; A2N = ['1-9', '10-29', '30+']
T1 = "case when tn1<1e5 then 0 when tn1<=1e7 then 1 else 2 end"; T1N = ['< $100k', '$100k-$10M', '> $10M']
POP = "act1 >= 3 and nonliq2 > 0"
rows = q(f"select {G} g, {A1} a1, {A2} a2, {T1} t1, count(*) n, count(*) filter (where days2 > 0) k from p where {POP} group by 1,2,3,4")
n = np.zeros((5, 3, 3, 3)); k = np.zeros((5, 3, 3, 3))
for g, a1, a2, t1, nn, kk in rows: n[g, a1, a2, t1] = nn; k[g, a1, a2, t1] = kk
tot = n.sum()
raw_n = n.sum(axis=(1, 2, 3)); raw_k = k.sum(axis=(1, 2, 3)); raw = 100*raw_k/raw_n
exp_rate = [23.67, 44.16, 56.14, 70.19, 86.94]; exp_n = [68732, 16182, 8833, 11227, 9098]
check('(i) raw rates and group sizes equal the M4 headline', all(abs(raw[i]-exp_rate[i]) < 0.006 for i in range(5)) and [int(x) for x in raw_n] == exp_n,
      ' / '.join(f"{raw[i]:.2f}% (n={int(raw_n[i]):,})" for i in range(5)))

cellw = n.sum(axis=0)/tot                      # weight of each of the 27 cells in the whole population
use = (n >= 30).all(axis=0)                    # cells where all five groups have >= 30 wallets
cover = cellw[use].sum()
check('(ii) cell weights: all 27 sum to 100%, used cells sum to the coverage', abs(cellw.sum()-1) < 1e-9 and 0 < cover <= 1, f"all cells {100*cellw.sum():.2f}%, used {int(use.sum())} of 27 cells covering {100*cover:.2f}% of the population")

wu = np.where(use, cellw, 0.0); wu = wu/wu.sum()
rate = np.divide(k, n, out=np.zeros_like(k), where=n > 0)
adj = 100*(rate*wu).sum(axis=(1, 2, 3))
rng = np.random.default_rng(20261114)
draw = np.zeros((2000, 5))
for g in range(5):
    kk = rng.binomial(n[g].astype(int), rate[g], size=(2000, 3, 3, 3))
    rr = np.divide(kk, n[g], out=np.zeros(kk.shape), where=n[g] > 0)
    draw[:, g] = 100*(rr*wu).sum(axis=(1, 2, 3))
lo, hi = np.percentile(draw, [2.5, 97.5], axis=0)
dlo, dhi = np.percentile(draw[:, 4]-draw[:, 0], [2.5, 97.5])
# same population restricted to the used cells, unadjusted, for a like-for-like raw figure
raw_u = 100*(k*use).sum(axis=(1, 2, 3))/(n*use).sum(axis=(1, 2, 3))

w("SERIAL LIQUIDATORS - EXPLORATORY check X (added after the main results were read). Association only.")
w()
w("=== X1: REPEAT PATTERN AT SIMILAR ACTIVITY ===")
w(f"Population: wallets active >= 3 days in Dec-Feb and with a non-liquidation fill in Mar-May: {int(tot):,}.")
w(f"Cells = Dec-Feb active days x Mar-May active days x Dec-Feb traded notional. Used: {int(use.sum())} of 27 cells (all five groups have >= 30 wallets), covering {100*cover:.1f}% of the population.")
w("Share liquidated in Mar-May, by Dec-Feb liquidation days:")
for g in range(5):
    w(f"  {GN[g]:>4}: raw {raw[g]:6.2f}% | raw, used cells only {raw_u[g]:6.2f}% | ADJUSTED to the same activity mix {adj[g]:6.2f}% [{lo[g]:.2f}, {hi[g]:.2f}]")
w(f"  Adjusted 6+ minus 0: {adj[4]-adj[0]:.2f} points [{dlo:.2f}, {dhi:.2f}] (raw: {raw[4]-raw[0]:.2f}).")
w()
w("Inside each Dec-Feb active-day band (rate, n):")
for a in range(3):
    nn = n[:, a].sum(axis=(1, 2)); kk = k[:, a].sum(axis=(1, 2))
    w(f"  active {A1N[a]:>5} days: " + ' | '.join(f"{GN[g]}: {100*kk[g]/nn[g]:5.1f}% (n={int(nn[g]):,})" if nn[g] else f"{GN[g]}: n/a" for g in range(5)))
w("Inside each Mar-May active-day band (rate, n):")
for a in range(3):
    nn = n[:, :, a].sum(axis=(1, 2)); kk = k[:, :, a].sum(axis=(1, 2))
    w(f"  active {A2N[a]:>5} days: " + ' | '.join(f"{GN[g]}: {100*kk[g]/nn[g]:5.1f}% (n={int(nn[g]):,})" if nn[g] else f"{GN[g]}: n/a" for g in range(5)))
w("Inside each Dec-Feb traded-notional band (rate, n):")
for a in range(3):
    nn = n[:, :, :, a].sum(axis=(1, 2)); kk = k[:, :, :, a].sum(axis=(1, 2))
    w(f"  traded {T1N[a]:>11}: " + ' | '.join(f"{GN[g]}: {100*kk[g]/nn[g]:5.1f}% (n={int(nn[g]):,})" if nn[g] else f"{GN[g]}: n/a" for g in range(5)))
w("Narrowest cell view (Dec-Feb active 30+ days, Mar-May active 30+ days), by traded notional:")
for t in range(3):
    w(f"  traded {T1N[t]:>11}: " + ' | '.join(f"{GN[g]}: {100*k[g,2,2,t]/n[g,2,2,t]:5.1f}% (n={int(n[g,2,2,t]):,})" if n[g,2,2,t] else f"{GN[g]}: n/a" for g in range(5)))
w()
w("=== X2: HOW MANY TIMES, AT SIMILAR ACTIVITY (liquidated wallets, six months) ===")
B = "case when act<=2 then 0 when act<=9 then 1 when act<=29 then 2 else 3 end"; BN = ['1-2', '3-9', '10-29', '30+']
GG = "case when days=1 then 0 when days=2 then 1 when days<=5 then 2 when days<=10 then 3 else 4 end"
x2 = q(f"select {B} b, count(*), median(100.0*days/act), sum(case when {GG}=0 then 1 else 0 end), sum(case when {GG}=1 then 1 else 0 end), sum(case when {GG}=2 then 1 else 0 end), sum(case when {GG}=3 then 1 else 0 end), sum(case when {GG}=4 then 1 else 0 end) from p where days > 0 group by 1 order by 1")
tot2 = 0
for b, nn, med, c1, c2, c3, c4, c5 in x2:
    tot2 += nn
    w(f"  active {BN[b]:>5} days: {nn:>7,} liquidated wallets | liquidation days 1: {100*c1/nn:5.1f}% | 2: {100*c2/nn:5.1f}% | 3-5: {100*c3/nn:5.1f}% | 6-10: {100*c4/nn:5.1f}% | 11+: {100*c5/nn:5.1f}% | median liquidation days per 100 active days: {med:.1f}")
check('(iii) X2 band counts sum to 177,432', tot2 == 177432, f"{tot2:,}")

status = 'CHECK PASS' if ok_all else 'CHECK FAIL'
open(os.path.join(OUT, 'slx_report.txt'), 'w', encoding='utf-8').write('\n'.join([status] + C + [''] + R) + '\n')
print('Serial Liquidators exploratory check X. Results written to slx_report.txt.')
print(status); print('\n'.join(C))
print('FINISHED OK' if ok_all else 'FAILED exit 1')
sys.exit(0 if ok_all else 1)
