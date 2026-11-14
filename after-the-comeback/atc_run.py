# After the Comeback - main run (rules: RULES_LOG.md, FROZEN PLAN v3, 14 Nov 2026 22:58 BKK).
# Prints only the checks. Results go to atc_report.txt.
import os, sys, datetime
import duckdb, numpy as np, pandas as pd

SRC = os.environ.get('ATC_SRC', '../life_after_liquidation/data')
OUT = os.environ.get('ATC_OUT', '.')
TEST = os.environ.get('ATC_TEST')            # synthetic smoke test: expected totals are not enforced
H, DAY = 3600000, 86400000
CUT = int(datetime.datetime(2026, 4, 2, tzinfo=datetime.timezone.utc).timestamp() * 1000)
NB, SEED = 2000, 20261114
con = duckdb.connect()
con.execute("set memory_limit='3GB'"); con.execute("set threads=4")
R, C = [], []
def w(s=''): R.append(s)
ok_all = True
def check(name, ok, detail):
    global ok_all
    ok_all = ok_all and bool(ok); C.append(f"  {'PASS' if ok else 'FAIL'}  {name}: {detail}")

# ---------- load ----------
con.execute(f"create table m as select * from '{SRC}/measures.parquet' where role = 'E'")
con.execute(f"create table ep as select \"user\" u, t0 from '{SRC}/episodes.parquet'")
con.execute(f"attach '{SRC}/lal.duckdb' as lal (read_only)")
con.execute("create table wp as select eid, wiped from lal.ev2")
con.execute(f"create table wd as select \"user\" u, day d from '{SRC}/wallet_day.parquet' where n > 0")
con.execute(f"""create table x as select m.eid, m.subj u, m.D, m.T, m.tf1, m.mins, m.tilt, m.dbef, m.nbef, m.samecoin, m.cb30d, m.liq30, m.liq7, wp.wiped,
    (select count(*) from ep e where e.u = m.subj and e.t0 > m.T and e.t0 <= m.T + {30*DAY}) as epT30,
    (select count(*) from ep e where e.u = m.subj and e.t0 > m.tf1 and e.t0 <= m.tf1 + {30*DAY}) as ep30,
    (select count(*) from ep e where e.u = m.subj and e.t0 > m.tf1 and e.t0 <= m.tf1 + {7*DAY}) as ep7,
    (select min(e.t0) from ep e where e.u = m.subj and e.t0 > m.tf1 and e.t0 <= m.tf1 + {30*DAY}) as nxt,
    (select count(*) from ep e where e.u = m.subj and e.t0 > m.T and e.t0 < m.tf1) as pre,
    (select count(*) from wd where wd.u = m.subj and wd.d > m.tf1 // {DAY} and wd.d <= m.tf1 // {DAY} + 30) as aft
    from m left join wp using (eid)""")
df = con.execute("select * from x").df()
N = len(df)

# ---------- checks a, b, e ----------
cb = 100 * df.cb30d.mean()
check('(a) index events and comeback share', (N == 54180 and abs(cb - 80.5) < 0.1) or TEST, f"{N:,} events; {cb:.2f}% with a comeback within 30 days")
rT = 100 * (df.epT30 > 0).mean()
same = int(((df.epT30 > 0).astype(int) == df.liq30).sum())
check('(b) outcome code from T reproduces the earlier study', (abs(rT - 52.4) < 0.1 or TEST) and same == N, f"{rT:.2f}% liquidated again within 30 days of T; equal to the earlier per-event flag on {same:,} of {N:,}")
nw = int((df.wiped.astype(str) == 'wiped').sum()); npart = int((df.wiped.astype(str) == 'partial').sum())
check('(e) wiped label present for every event', nw + npart == N and (TEST or (nw == 34304 and npart == 19876)), f"wiped {nw:,} + partial {npart:,} = {nw+npart:,} of {N:,}")

# ---------- population ----------
late = df[df['T'] >= CUT]; early = df[df['T'] < CUT]
noc = early[early.tf1.isna()]; k = early[early.tf1.notna()].copy()
k['y'] = (k.ep30 > 0).astype(int); k['y7'] = (k.ep7 > 0).astype(int)
k['A'] = np.select([k.mins < 60, k.mins < 1440, k.mins < 10080], [0, 1, 2], 3)
k['Cg'] = (k.samecoin == 1).astype(int)                       # 1 = same coin
k['B'] = np.where(k.tilt.isna(), -1, np.select([k.tilt < 0.5, k.tilt < 2], [0, 1], 2))
k['ab'] = np.select([k.dbef <= 9, k.dbef <= 19], [0, 1], 2)
k['nbb'] = np.select([k.nbef < 1e4, k.nbef <= 1e6], [0, 1], 2)
k['cell'] = k.ab * 3 + k.nbb
k['w'] = (k.wiped.astype(str) == 'wiped').astype(int); k['prej'] = (k.pre > 0).astype(int)   # fixed 14 Nov 23:05: label is the text 'wiped' / 'partial'
k['hrs'] = (k.nxt - k.tf1) / H
AN = ['under 1 hour', '1-24 hours', '1-7 days', '7-30 days']; BN = ['under 0.5x', '0.5-2x', '2x or more']; CN = ['other coin', 'same coin']
ABN = ['3-9 days', '10-19 days', '20-30 days']
check('(c) dropped + kept = all events; group shares add to 100%',
      len(late) + len(noc) + len(k) == N and k.A.isin([0, 1, 2, 3]).all() and k.Cg.isin([0, 1]).all() and (k.B >= 0).sum() + (k.B < 0).sum() == len(k),
      f"T too late {len(late):,} + no comeback {len(noc):,} + kept {len(k):,} = {len(late)+len(noc)+len(k):,}")

# ---------- check d: recount 20 wallets from raw liquidation fills, separate code ----------
rng = np.random.default_rng(SEED)
samp = k.sample(n=min(20, len(k)), random_state=SEED)
bad = 0
for _, r in samp.iterrows():
    ts = [t for (t,) in con.execute(f"select time from '{SRC}/liq_fills.parquet' where \"user\" = ? order by time", [r.u]).fetchall()]
    starts, prev = [], None
    for t in ts:
        if prev is None or t - prev >= 60 * 60000: starts.append(t)
        prev = t
    got = int(any(r.tf1 < s <= r.tf1 + 30 * DAY for s in starts))
    bad += int(got != r.y)
check('(d) 20 random kept wallets recounted from raw liquidation fills', bad == 0, f"{len(samp)} recounted, {bad} mismatches")

# ---------- analysis helpers ----------
days = np.sort(k.D.unique()); di = {d: i for i, d in enumerate(days)}; ND = len(days)
W = rng.multinomial(ND, np.ones(ND) / ND, size=NB).astype(float)          # day weights per bootstrap draw
def cube(d, gcol, G, ycol):
    n = np.zeros((ND, G, 9)); kk = np.zeros((ND, G, 9))
    ix = (d.D.map(di).values, d[gcol].values, d.cell.values)
    np.add.at(n, ix, 1); np.add.at(kk, ix, d[ycol].values)
    return n, kk
def ci(a): return np.percentile(a, [2.5, 97.5])
def block(d, gcol, names, hi, lo, title, ycol='y', adjust=True):
    G = len(names); n, kk = cube(d, gcol, G, ycol)
    n1, k1 = n.sum(2), kk.sum(2)                               # days x groups
    Nt, Kt = n1.sum(0), k1.sum(0); rate = 100 * Kt / np.maximum(Nt, 1)
    bn, bk = W @ n1, W @ k1; br = 100 * bk / np.maximum(bn, 1)
    w(title)
    for g in range(G):
        lo_, hi_ = ci(br[:, g]); flag = '  (under 100 wallets: shown, not read)' if Nt[g] < 100 else ''
        w(f"  {names[g]:>13}: n={int(Nt[g]):>6,} | liquidated again {rate[g]:5.1f}% [{lo_:.1f}, {hi_:.1f}]{flag}")
    gap = rate[hi] - rate[lo]; gl, gh = ci(br[:, hi] - br[:, lo]); small = Nt[hi] < 100 or Nt[lo] < 100
    w(f"  GAP {names[hi]} minus {names[lo]}: {gap:+.1f} points [{gl:+.1f}, {gh:+.1f}]")
    res = {'raw': (gap, gl, gh, small)}
    if adjust:
        cn = n.sum(0)                                          # groups x cells
        use = (cn >= 30).all(axis=0); pop = cn.sum(0); wt = np.where(use, pop, 0.0)
        if wt.sum() > 0:
            cover = wt.sum() / pop.sum(); wt = wt / wt.sum()
            cr = kk.sum(0) / np.maximum(cn, 1); adj = 100 * (cr * wt).sum(1)
            bcn = np.einsum('bd,dgc->bgc', W, n); bck = np.einsum('bd,dgc->bgc', W, kk)
            badj = 100 * ((bck / np.maximum(bcn, 1e-9)) * wt).sum(2)
            w(f"  Adjusted to the same activity and size mix ({int(use.sum())} of 9 cells, {int((cn[:, use]).sum()):,} wallets kept, coverage {100*cover:.1f}%):")
            for g in range(G):
                lo_, hi_ = ci(badj[:, g]); w(f"  {names[g]:>13}: {adj[g]:5.1f}% [{lo_:.1f}, {hi_:.1f}]")
            ag = adj[hi] - adj[lo]; al, ah = ci(badj[:, hi] - badj[:, lo])
            w(f"  ADJUSTED GAP: {ag:+.1f} points [{al:+.1f}, {ah:+.1f}]")
            res['adj'] = (ag, al, ah, small)
        else:
            w("  Adjusted: no cell has 30+ wallets in every group."); res['adj'] = None
    w(); return res
def rates_line(d, gcol, names, ycol='y'):
    out = []
    for g, nm in enumerate(names):
        s = d[d[gcol] == g]
        out.append(f"{nm}: {100*s[ycol].mean():5.1f}% (n={len(s):,})" if len(s) else f"{nm}: n/a")
    return ' | '.join(out)
def verdict(name, raw, adj, wraw):
    def good(t): return t is not None and not t[3] and abs(t[0]) >= 5 and (t[1] > 0 or t[2] < 0)
    sign_ok = raw is not None and adj is not None and wraw is not None and np.sign(raw[0]) == np.sign(adj[0]) == np.sign(wraw[0])
    v = 'GOES WITH' if (good(raw) and good(adj) and good(wraw) and sign_ok) else 'NO CLEAR DIFFERENCE'
    w(f"  {name}: {v}  (raw {'ok' if good(raw) else 'no'}, adjusted {'ok' if good(adj) else 'no'}, wiped raw {'ok' if good(wraw) else 'no'})")

# ---------- report ----------
w("AFTER THE COMEBACK - main report. Descriptive, association only. Returners only.")
w()
w("=== POPULATION (no outcome) ===")
w(f"Index events: {N:,}. Dropped, event ends on or after 2 Apr 2026: {len(late):,}. Left: {len(early):,}.")
w(f"Of those, never came back within 30 days: {len(noc):,} ({100*len(noc)/max(len(early),1):.1f}%). Kept (came back): {len(k):,}.")
w(f"Kept wallets: wiped {int(k.w.sum()):,}, partial {int((1-k.w).sum()):,}; liquidated again before the comeback {int(k.prej.sum()):,}; with a usual size (5+ prior positions) {int((k.B>=0).sum()):,}.")
w(f"All kept wallets: liquidated again within 30 days of the comeback {100*k.y.mean():.1f}%, within 7 days {100*k.y7.mean():.1f}%.")
w()
kb = k[k.B >= 0]; kw = k[k.w == 1]; kbw = kb[kb.w == 1]
w("=== A. WAIT BEFORE THE COMEBACK ===")
A = block(k, 'A', AN, 0, 3, "All kept wallets (30 days):")
Aw = block(kw, 'A', AN, 0, 3, "Wiped only:", adjust=False)
block(k[k.w == 0], 'A', AN, 0, 3, "Partial only:", adjust=False)
block(k[k.prej == 0], 'A', AN, 0, 3, "No liquidation between the event and the comeback:", adjust=False)
block(k[k.prej == 1], 'A', AN, 0, 3, "Liquidated again before the comeback:", adjust=False)
block(k, 'A', AN, 0, 3, "Secondary, within 7 days of the comeback:", ycol='y7', adjust=False)
w("Inside each prior active-day band:")
for a in range(3): w(f"  {ABN[a]:>10}: " + rates_line(k[k.ab == a], 'A', AN))
w("Inside same coin / other coin:")
for c in (1, 0): w(f"  {CN[c]:>10}: " + rates_line(k[k.Cg == c], 'A', AN))
w("Inside each size group (wallets with a usual size):")
for b in range(3): w(f"  {BN[b]:>10}: " + rates_line(kb[kb.B == b], 'A', AN))
w("Inside the usual-size subset: " + rates_line(kb, 'A', AN))
w()
w("=== C. SAME COIN ===")
Cc = block(k, 'Cg', CN, 1, 0, "All kept wallets (30 days):")
Cw = block(kw, 'Cg', CN, 1, 0, "Wiped only:", adjust=False)
block(k[k.w == 0], 'Cg', CN, 1, 0, "Partial only:", adjust=False)
block(k[k.prej == 0], 'Cg', CN, 1, 0, "No liquidation between the event and the comeback:", adjust=False)
block(k[k.prej == 1], 'Cg', CN, 1, 0, "Liquidated again before the comeback:", adjust=False)
block(k, 'Cg', CN, 1, 0, "Secondary, within 7 days of the comeback:", ycol='y7', adjust=False)
w("Inside each prior active-day band:")
for a in range(3): w(f"  {ABN[a]:>10}: " + rates_line(k[k.ab == a], 'Cg', CN))
w("Inside the usual-size subset: " + rates_line(kb, 'Cg', CN))
w()
w("=== B. SIZE OF THE FIRST NEW POSITION (separate analysis: wallets with a usual size only) ===")
B = block(kb, 'B', BN, 2, 0, "All such wallets (30 days):")
Bw = block(kbw, 'B', BN, 2, 0, "Wiped only:", adjust=False)
block(kb[kb.w == 0], 'B', BN, 2, 0, "Partial only:", adjust=False)
block(kb[kb.prej == 0], 'B', BN, 2, 0, "No liquidation between the event and the comeback:", adjust=False)
block(kb[kb.prej == 1], 'B', BN, 2, 0, "Liquidated again before the comeback:", adjust=False)
block(kb, 'B', BN, 2, 0, "Secondary, within 7 days of the comeback:", ycol='y7', adjust=False)
w("Inside each prior active-day band:")
for a in range(3): w(f"  {ABN[a]:>10}: " + rates_line(kb[kb.ab == a], 'B', BN))
w()
w("=== DESCRIPTION ONLY ===")
for col, names, d in (('A', AN, k), ('Cg', CN, k), ('B', BN, kb)):
    for g, nm in enumerate(names):
        s = d[d[col] == g]; rl = s[s.y == 1]
        w(f"  {nm:>13}: median active days in the 30 days after the comeback {s.aft.median():.0f} | median hours from comeback to next liquidation (those liquidated again) {rl.hrs.median():.0f}" if len(s) else f"  {nm:>13}: n/a")
w()
w("=== READING RULE (pre-set: gap of 5+ points with interval excluding 0 in all wallets raw, all wallets adjusted, wiped raw) ===")
verdict('A. Wait (under 1 hour minus 7-30 days)', A['raw'], A.get('adj'), Aw['raw'])
verdict('B. Size (2x or more minus under 0.5x)', B['raw'], B.get('adj'), Bw['raw'])
verdict('C. Same coin (yes minus no)', Cc['raw'], Cc.get('adj'), Cw['raw'])
w("This is a pre-set descriptive threshold, not a significance test or proof of a meaningful effect.")

status = 'CHECK PASS' if ok_all else 'CHECK FAIL'
body = [status] + C + ([''] + R if ok_all else ['', 'Checks failed: no results written.'])
open(os.path.join(OUT, 'atc_report.txt'), 'w', encoding='utf-8').write('\n'.join(body) + '\n')
print('After the Comeback main run. Results written to atc_report.txt.' + (' (SYNTHETIC TEST)' if TEST else ''))
print(status); print('\n'.join(C))
print('FINISHED OK' if ok_all else 'FAILED exit 1')
sys.exit(0 if ok_all else 1)
