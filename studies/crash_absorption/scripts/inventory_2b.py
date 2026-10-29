"""Task 2b: symbol listing, 1m/1d inventories (names + sizes), 1d downloads.
Usage: python -I scripts/inventory_2b.py <data_dir> list|download1d"""
import concurrent.futures as cf
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ca import downloader as DL  # noqa: E402
from ca import inventory as I  # noqa: E402

START = DL.DOWNLOAD_START


def listing(data_dir: Path):
    fetch = DL.HttpFetcher()
    syms = DL.list_symbols(fetch, I.LISTING_BASE)
    print(f"symbol directories under um/monthly/klines/: {len(syms)}")

    def inv(sym):
        return sym, {iv: [f for p in I.kline_prefixes(sym, iv, START) for f in I.list_files(fetch, p)] for iv in ("1m", "1d")}

    res = {}
    with cf.ThreadPoolExecutor(16) as ex:
        for sym, d in ex.map(inv, syms):
            res[sym] = d
    (data_dir / "inventory_klines.json").write_text(json.dumps({"symbol_dirs": syms, "files": res}))
    in_range = sorted(s for s, d in res.items() if d["1m"])
    print(f"symbols with any 1m kline file 2023-12-01..{DL.MAX_ALLOWED}: {len(in_range)}")


def download1d(data_dir: Path):
    inv = json.loads((data_dir / "inventory_klines.json").read_text())["files"]
    fetch = DL.HttpFetcher()
    todo = {s: [I.period_of(k) for k, _ in d["1d"]] for s, d in inv.items() if d["1m"] and d["1d"]}
    errors = {}

    def one(sym):
        try:
            DL.download_klines(sym, "1d", data_dir, fetch, periods=todo[sym])
            return sym, None
        except Exception as e:  # report every failure verbatim
            return sym, f"{type(e).__name__}: {e}"

    with cf.ThreadPoolExecutor(16) as ex:
        for sym, err in ex.map(one, sorted(todo)):
            if err:
                errors[sym] = err
    (data_dir / "download_1d_errors.json").write_text(json.dumps(errors, indent=1))
    n_files = sum(len(v) for v in todo.values())
    print(f"1d: symbols {len(todo)}, files {n_files}, errors {len(errors)}")


if __name__ == "__main__":
    d = Path(sys.argv[1])
    d.mkdir(parents=True, exist_ok=True)
    {"list": listing, "download1d": download1d}[sys.argv[2]](d)
