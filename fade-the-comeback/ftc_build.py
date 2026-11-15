# Fade the Comeback - step 1: pull candidate re-entries out of the raw fills (no prices, no outcomes).
# Rules: RULES_LOG.md (frozen plan v2 + notes N1, N2). Usage: python ftc_build.py [first_day_index] [last_day_index]
import os, sys, duckdb

ROOT = os.environ.get('FTC_ROOT', '..')
FILLS = os.environ.get('FTC_FILLS', os.path.join(ROOT, 'data', 'fills'))
LIQ = os.environ.get('FTC_LIQ', os.path.join(ROOT, 'life_after_liquidation', 'data', 'liq_fills.parquet'))
EPI = os.environ.get('FTC_EPI', os.path.join(ROOT, 'life_after_liquidation', 'data', 'episodes.parquet'))
CMAP = os.environ.get('FTC_CMAP', os.path.join(ROOT, 'data', 'coin_map.csv'))
OUT = os.environ.get('FTC_OUT', 'data')
HOUR = 3600000

os.makedirs(os.path.join(OUT, 'reentry'), exist_ok=True)
con = duckdb.connect(); con.execute("set memory_limit='2GB'"); con.execute("set threads=2")
coins = [r[0] for r in con.execute(f"select coin from read_csv_auto('{CMAP}') where coin <> 'BTC' and status = 'PASS'").fetchall()]
cl = ','.join("'" + c + "'" for c in coins)
con.execute(f"""create table lq as select "user" u, coin, time from '{LIQ}'
    where coin in ({cl}) and "user" not in (select "user" from '{EPI}' where is_mm)""")
days = sorted(d for d in os.listdir(FILLS) if d.isdigit())
a = int(sys.argv[1]) if len(sys.argv) > 1 else 0
b = int(sys.argv[2]) if len(sys.argv) > 2 else len(days)
done = 0
for d in days[a:b]:
    out = os.path.join(OUT, 'reentry', d + '.parquet')
    if os.path.exists(out): continue
    con.execute(f"""copy (
        with o as (select distinct "user" u, coin, time, tid, dir from read_parquet('{FILLS}/{d}/*.parquet')
                   where dir in ('Open Long', 'Open Short') and coin in ({cl})),
             j as (select o.*, l.time as s from o asof join lq l on o.u = l.u and o.coin = l.coin and o.time > l.time)
        select * from j where time - s <= {HOUR}) to '{out}.tmp' (format parquet)""")
    os.replace(out + '.tmp', out); done += 1
have = len([f for f in os.listdir(os.path.join(OUT, 'reentry')) if f.endswith('.parquet')])
print(f"coins {len(coins)}; days in TRAIN {len(days)}; written this call {done}; day files present {have}")
print('FINISHED OK' if have <= len(days) else 'FAILED exit 1')
