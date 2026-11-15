# Fade the Comeback - test on MADE-UP data with a planted answer. Touches no real data.
# Usage: python _t_ftc.py <scratch_dir>
import os, sys, subprocess, shutil, duckdb, numpy as np, pandas as pd
_c = duckdb.connect()
def wp(df, path):
    _c.register('t_', df); _c.execute("copy t_ to '" + path.replace(os.sep, '/') + "' (format parquet)"); _c.unregister('t_')

T = sys.argv[1]; HERE = os.path.dirname(os.path.abspath(__file__))
MIN, HOUR, DAY = 60000, 3600000, 86400000
D0 = 1764547200000  # 1 Dec 2025 00:00 UTC
ALTS = ['AAA', 'BBB', 'CCC', 'DDD']; NDAYS = 60

def build(root, move):
    shutil.rmtree(root, ignore_errors=True)
    for p in ('fills', 'kl', 'out', 'rep'): os.makedirs(os.path.join(root, p))
    pd.DataFrame({'coin': ['BTC'] + ALTS, 'binance': ['BTCUSDT'] + [a + 'USDT' for a in ALTS], 'status': 'PASS'}).to_csv(os.path.join(root, 'coin_map.csv'), index=False)
    ot = D0 + np.arange(72 * 1440) * MIN
    wp(pd.DataFrame({'open_time': ot, 'close': 100.0}), os.path.join(root, 'kl', 'BTCUSDT.parquet'))
    rows, tid = [], [0]
    def fill(u, c, t, d, liq=False):
        tid[0] += 1; rows.append((u, c, t, tid[0], d, u if liq else None))
    px = {a: np.full(len(ot), 10.0) for a in ALTS}
    for d in range(NDAYS):
        for ci, a in enumerate(ALTS):
            h0 = D0 + d * DAY + 6 * HOUR; E = h0 + HOUR
            i0 = (E + 3 * MIN - D0) // MIN; px[a][i0:i0 + 241] = 10.0 * (1 + move * np.arange(241) / 240)
            for i in range(12):
                u = f"0xw{d:02d}{ci}{i:02d}"; fill(u, a, h0 + 5 * MIN, 'Close Long', True)
                fill(u, a, h0 + (20 if i < 10 else 25) * MIN + i, 'Open Long' if i < 10 else 'Open Short')
            fill(f"0xw{d:02d}{ci}00", a, h0 + 30 * MIN, 'Open Short')                      # second open: must not count again
            u = f"0xearly{d:02d}{ci}"; fill(u, a, h0 + 2 * MIN, 'Open Short'); fill(u, a, h0 + 5 * MIN, 'Close Long', True)   # opened BEFORE the liquidation
            u = f"0xlate{d:02d}{ci}"; fill(u, a, h0 + 5 * MIN, 'Close Long', True); fill(u, a, h0 + 70 * MIN, 'Open Short')    # 65 min later
            for i in range(5):
                for tag in ('mm', 'vault'):
                    u = f"0x{tag}{i}"; fill(u, a, h0 + 5 * MIN, 'Close Long', True); fill(u, a, h0 + 22 * MIN + i, 'Open Short')
    for a in ALTS: wp(pd.DataFrame({'open_time': ot, 'close': px[a]}), os.path.join(root, 'kl', a + 'USDT.parquet'))
    f = pd.DataFrame(rows, columns=['user', 'coin', 'time', 'tid', 'dir', 'liq_user'])
    ts = pd.to_datetime(f.time, unit='ms')
    for (dd, hh), g in f.groupby([ts.dt.strftime('%Y%m%d'), ts.dt.strftime('%H')]):
        os.makedirs(os.path.join(root, 'fills', dd), exist_ok=True); wp(g, os.path.join(root, 'fills', dd, hh + '.parquet'))
    lq = f[(f.liq_user == f.user) & ~f.user.str.startswith('0xvault')][['user', 'coin', 'time', 'tid', 'dir']]
    wp(lq, os.path.join(root, 'liq.parquet'))
    us = f.user.unique(); wp(pd.DataFrame({'user': us, 'is_mm': [u.startswith('0xmm') for u in us]}), os.path.join(root, 'epi.parquet'))
    pd.DataFrame({'address': [f"0xvault{i}" for i in range(5)], 'create_time_ms': 0}).to_csv(os.path.join(root, 'vaults.csv'), index=False)

def run(root):
    env = dict(os.environ, FTC_FILLS=os.path.join(root, 'fills'), FTC_LIQ=os.path.join(root, 'liq.parquet'), FTC_EPI=os.path.join(root, 'epi.parquet'),
               FTC_VAULTS=os.path.join(root, 'vaults.csv'), FTC_CMAP=os.path.join(root, 'coin_map.csv'), FTC_KL=os.path.join(root, 'kl'),
               FTC_OUT=os.path.join(root, 'out'), FTC_REP=os.path.join(root, 'rep'), FTC_CHECK_C='A1')
    for s in ('ftc_build.py', 'ftc_run.py'):
        r = subprocess.run([sys.executable, os.path.join(HERE, s)], env=env, capture_output=True, text=True)
        print(r.stdout.strip()[-900:]);
        if r.returncode: print(r.stderr[-1500:])
    return open(os.path.join(root, 'rep', 'ftc_report.txt'), encoding='utf-8').read()

ok = True
build(os.path.join(T, 'planted'), -0.01); rep = run(os.path.join(T, 'planted')); print(rep)
for need in ('CHECK PASS', 'VERDICT (4-hour aggregate only): PASS', 'n=240 on 60 days', 'gross mean +1.000%'):
    if need not in rep: ok = False; print('MISSING in planted run:', need)
build(os.path.join(T, 'null'), 0.0); rep = run(os.path.join(T, 'null'))
for need in ('CHECK PASS', 'VERDICT (4-hour aggregate only): FAIL', 'n=240 on 60 days'):
    if need not in rep: ok = False; print('MISSING in null run:', need)
print(rep.split('ALSO REPORTED')[0])
print('TEST ' + ('FINISHED OK' if ok else 'FAILED exit 1')); sys.exit(0 if ok else 1)
