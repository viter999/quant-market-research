# After the Comeback - EXPLORATORY check X (rules in RULES_LOG.md, written before this code ran).
# Prints only the checks. Results go to atcx_report.txt.
import os, sys, datetime
import duckdb, numpy as np

SRC = os.environ.get('ATC_SRC', '../life_after_liquidation/data')
OUT = os.environ.get('ATC_OUT', '.')
DAY = 86400000
CUT = int(datetime.datetime(2026, 4, 2, tzinfo=datetime.timezone.utc).timestamp() * 1000)
NB, SEED = 2000, 20261114
con = duckdb.connect(); con.execute("set memory_limit='3GB'"); con.execute("set threads=4")
R, C = [], []
def w(s=''): R.append(s)
ok_all = True
def check(name, ok, detail):
    global ok_all
    ok_all = ok_all and bool(ok); C.append(f"  {'PASS' if ok else 'FAIL'}  {name}: {detail}")

con.execute(f"create table m as select * from '{SRC}/measures.parquet' where role = 'E' and T < {CUT} and tf1 is not null")
con.execute(f"create table ep as select \"user\" u, t0 from '{SRC}/episodes.parquet'")
con.execute(f"create table wd as select \"user\" u, day d from '{SRC}/wallet_day.parquet' where n > 0")
k = con.execute(f"""select m.D, m.mins, m.samecoin,
    ((select count(*) from ep e where e.u = m.subj and e.t0 > m.tf1 and e.t0 <= m.tf1 + {30*DAY}) > 0)::int as y,
    (select count(*) from wd where wd.u = m.subj and wd.d > m.tf1 // {DAY} and wd.d <= m.tf1 // {DAY} + 30) as aft
    from m""").df()
k['A'] = np.select([k.mins < 60, k.mins < 1440, k.mins < 10080], [0, 1, 2], 3)
k['Cg'] = (k.samecoin == 1).astype(int)
k['pb'] = np.select([k.aft <= 2, k.aft <= 7, k.aft <= 14], [0, 1, 2], 3)
AN = ['under 1 hour', '1-24 hours', '1-7 days', '7-30 days']; CN = ['other coin', 'same coin']; PN = ['0-2 days', '3-7 days', '8-14 days', '15-30 days']

nA = [int((k.A == g).sum()) for g in range(4)]; rA = [100 * k[k.A == g].y.mean() for g in range(4)]
check('(i) kept wallets, group sizes and raw rates equal the main run',
      len(k) == 35335 and nA == [9463, 14501, 7913, 3458] and all(abs(a - b) < 0.06 for a, b in zip(rA, [72.6, 70.0, 59.3, 46.8])),
      f"{len(k):,} kept; " + ' / '.join(f"{r:.1f}% (n={n:,})" for r, n in zip(rA, nA)))
check('(ii) every wallet falls in one later-activity band', k.pb.isin([0, 1, 2, 3]).all() and sum(int((k.pb == b).sum()) for b in range(4)) == len(k),
      ' / '.join(f"{PN[b]}: {int((k.pb == b).sum()):,}" for b in range(4)))

days = np.sort(k.D.unique()); di = {d: i for i, d in enumerate(days)}; ND = len(days)
rng = np.random.default_rng(SEED); W = rng.multinomial(ND, np.ones(ND) / ND, size=NB).astype(float)
def ci(a): return np.percentile(a, [2.5, 97.5])
def run(gcol, names, hi, lo, title):
    G = len(names); n = np.zeros((ND, G, 4)); kk = np.zeros((ND, G, 4))
    ix = (k.D.map(di).values, k[gcol].values, k.pb.values)
    np.add.at(n, ix, 1); np.add.at(kk, ix, k.y.values)
    cn, ck = n.sum(0), kk.sum(0)
    w(title)
    w("  Share of each group in each later-activity band:")
    for g in range(G): w(f"  {names[g]:>13}: " + ' | '.join(f"{PN[b]}: {100*cn[g,b]/cn[g].sum():4.1f}%" for b in range(4)))
    w("  Liquidated again within 30 days of the comeback, inside each later-activity band (rate, n):")
    for b in range(4): w(f"  {PN[b]:>10}: " + ' | '.join(f"{names[g]}: {100*ck[g,b]/max(cn[g,b],1):5.1f}% (n={int(cn[g,b]):,})" for g in range(G)))
    use = (cn >= 30).all(axis=0); pop = cn.sum(0); wt = np.where(use, pop, 0.0); cover = wt.sum() / pop.sum(); wt = wt / wt.sum()
    adj = 100 * ((ck / np.maximum(cn, 1)) * wt).sum(1)
    bn = np.einsum('bd,dgc->bgc', W, n); bk = np.einsum('bd,dgc->bgc', W, kk)
    badj = 100 * ((bk / np.maximum(bn, 1e-9)) * wt).sum(2)
    raw = 100 * ck.sum(1) / cn.sum(1)
    w(f"  At the same later-activity mix ({int(use.sum())} of 4 bands used, coverage {100*cover:.1f}%):")
    for g in range(G):
        l, h = ci(badj[:, g]); w(f"  {names[g]:>13}: raw {raw[g]:5.1f}% | same later-activity mix {adj[g]:5.1f}% [{l:.1f}, {h:.1f}]")
    gl, gh = ci(badj[:, hi] - badj[:, lo]); gap = adj[hi] - adj[lo]
    w(f"  GAP {names[hi]} minus {names[lo]}: raw {raw[hi]-raw[lo]:+.1f} | same later-activity mix {gap:+.1f} points [{gl:+.1f}, {gh:+.1f}]")
    keep = abs(gap) >= 5 and (gl > 0 or gh < 0)
    w(f"  Pre-set reading: {'the gap is NOT only about trading on more days afterwards' if keep else 'the gap MOSTLY reflects trading on more days afterwards'}.")
    w()

w("AFTER THE COMEBACK - EXPLORATORY check X (added after the main results were read). Association only.")
w("Caution: activity after the comeback can itself be changed by a liquidation, so this check over-adjusts.")
w()
run('A', AN, 0, 3, "=== X1: WAIT, at similar activity AFTER the comeback ===")
run('Cg', CN, 1, 0, "=== X2: SAME COIN, at similar activity AFTER the comeback ===")

status = 'CHECK PASS' if ok_all else 'CHECK FAIL'
open(os.path.join(OUT, 'atcx_report.txt'), 'w', encoding='utf-8').write('\n'.join([status] + C + ([''] + R if ok_all else ['', 'Checks failed: no results written.'])) + '\n')
print('After the Comeback exploratory check X. Results written to atcx_report.txt.')
print(status); print('\n'.join(C))
print('FINISHED OK' if ok_all else 'FAILED exit 1')
sys.exit(0 if ok_all else 1)
