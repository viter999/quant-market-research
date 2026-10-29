"""LF-1 step 1: parse the raw Binance 'Futures Will Launch' announcements into
the event list (PREREG v0.2 §1). Reads only events_raw/*.json; no price data.

Usage: parse_events.py RAW_JSON   (RAW_JSON.sha256 must sit next to it)

Outputs (studies/listing_fade/):
  events.csv    one row per (article, USDT-margined perp symbol)
  articles.csv  one row per selected article, with its parse status

Rules:
  A = release_ms; L = the 'Launch Time' stated for that symbol in the body's
  contract table (sentence fallback when an article has no table). Episode =
  all USDT symbols in one article. USDT-margined perps only (USDC-margined,
  COIN-M and delivery contracts dropped). Family exclusions = the frozen
  crash-absorption EXCLUSIONS.json named lists (1000/1M prefixes allowed);
  the body's underlying type (equity/index/metal/FX) is recorded as a check.
"""
import csv
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
EXCL = HERE.parents[0] / "crash_absorption" / "EXCLUSIONS.json"
TIME = r"(20\d\d-\d\d-\d\d \d\d:\d\d) ?\(UTC ?\)"
TIME_CELL = r"(20\d\d-\d\d-\d\d \d\d:\d\d)(?: ?\(UTC ?\))?"  # some 2026 tables omit '(UTC)'; checked against the body below
SYMROW = re.compile(r"(USDⓈ-M|COIN-M) (Perpetual|Delivery) Contracts?$")
FAMILIES = ("stablecoin", "tokenized_metal", "tokenized_equity", "index", "fiat", "equity_ticker_collision",
            "possible_index", "pegged_rule2", "not_checkable_on_dev")

TEST = (dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc), dt.datetime(2026, 3, 6, tzinfo=dt.timezone.utc))
HOLDOUT = (dt.datetime(2026, 3, 15, tzinfo=dt.timezone.utc), dt.datetime(2026, 9, 28, tzinfo=dt.timezone.utc))


def ms(s: str) -> int:
    return int(dt.datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


def utc(m: int) -> str:
    return dt.datetime.fromtimestamp(m / 1000, dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def segment(l_ms: int) -> str:
    t = dt.datetime.fromtimestamp(l_ms / 1000, dt.timezone.utc)
    if TEST[0] <= t < TEST[1]:
        return "TEST"
    if HOLDOUT[0] <= t < HOLDOUT[1]:
        return "HOLDOUT"
    return "OUT_OF_RANGE"


def clean(t: str) -> str:
    return re.sub(r"\s+", " ", t.replace("&nbsp;", " ").replace("\xa0", " ").replace("&amp;", "&")).strip()


def _texts(n, out):
    if n.get("node") == "text":
        out.append(n.get("text", ""))
    for c in n.get("child", []) or []:
        _texts(c, out)
    return out


def body_text(raw: str) -> str:
    return clean(" ".join(_texts(json.loads(raw), [])))


def tables(raw: str) -> list[list[list[str]]]:
    """Every <table> as rows of cell texts."""
    res = []

    def rows_of(n, rows):
        if n.get("tag") == "tr":
            rows.append([clean(" ".join(_texts(c, []))) for c in n.get("child", []) or [] if c.get("tag") in ("td", "th")])
            return rows
        for c in n.get("child", []) or []:
            rows_of(c, rows)
        return rows

    def walk(n):
        if n.get("tag") == "table":
            res.append(rows_of(n, []))
            return
        for c in n.get("child", []) or []:
            walk(c)
    walk(json.loads(raw))
    return res


def col(vals: list[str], i: int, n: int) -> str:
    """Value for column i of n; a single value spans all columns."""
    if len(vals) == n:
        return vals[i]
    return vals[0] if len(vals) == 1 else ""


def from_tables(raw: str) -> list[dict]:
    out = []
    for tb in tables(raw):
        rows = {r[0]: r[1:] for r in tb if r}
        sk = [k for k in rows if SYMROW.match(k)]
        if not sk or "Launch Time" not in rows:
            continue
        syms = [s for s in rows[sk[0]] if s]
        n = len(syms)
        und = [(k, v) for k, v in rows.items() if k.startswith("Underlying") and not k.endswith("Info")]
        for i, s in enumerate(syms):
            lt = re.findall(TIME_CELL, col(rows["Launch Time"], i, n))
            out.append({"symbol": s, "margin": sk[0].split()[0], "kind": sk[0].split()[1],
                        "L": lt[0] if len(lt) == 1 else None,
                        "settlement": col(rows.get("Settlement Asset", [""]), i, n),
                        "contract_type": col(rows.get("Contract Type", [""]), i, n)[:20],
                        "underlying_label": und[0][0] if und else "",
                        "underlying": col(und[0][1], i, n)[:80] if und else ""})
    return out


def from_sentence(text: str) -> list[dict]:
    m = re.search(r"will launch the (?:USDⓈ-M )?([0-9A-Z]{2,20}USDT)\b[^.]*? at " + TIME, text)
    if not m:
        return []
    return [{"symbol": m.group(1), "margin": "USDⓈ-M", "kind": "Perpetual", "L": m.group(2), "settlement": "USDT",
             "contract_type": "", "underlying_label": "sentence", "underlying": ""}]


def body_family(r: dict, title: str) -> str:
    lab, u = r["underlying_label"], (r["underlying"] + " " + title).lower()
    if "fx" in lab.lower():
        return "fx"
    if "index" in lab.lower() and ("index" in r["underlying"].lower() or "etf" in r["underlying"].lower()
                                   or lab == "Underlying Index"):
        return "index"
    if "equity" in lab.lower():
        return "equity"
    if re.search(r"\b(gold|silver|platinum|palladium|copper)\b", r["underlying"].lower()):
        return "metal"
    if "index" in u and "composite index" in u:
        return "index"
    return "crypto"


def main(raw_path: str) -> int:
    path = Path(raw_path)
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    want = Path(str(path) + ".sha256").read_text().split()[0]
    if sha != want:
        print(f"raw sha256 mismatch: {sha} != {want}", file=sys.stderr)
        return 1
    excl = json.loads(EXCL.read_text())
    assert excl["status"] == "FROZEN"
    named = {s: f for f in FAMILIES for s in excl["excluded_symbols"].get(f, [])}
    r = json.loads(raw)
    arts = sorted(r["articles"], key=lambda a: int(a["release_ms"]))
    ev_rows, art_rows = [], []
    for a in arts:
        rel = int(a["release_ms"])
        title = clean(a["title"])
        text = body_text(a["body_raw"])
        rows = from_tables(a["body_raw"]) or from_sentence(text)
        src = "table" if from_tables(a["body_raw"]) else ("sentence" if rows else "")
        premarket = int(bool(re.search(r"pre-market", title + " " + text, re.I)))
        note = re.search(r"updated on 20\d\d-\d\d-\d\d to update the launch time[^.]*", text)
        usdt = [x for x in rows if x["margin"] == "USDⓈ-M" and x["kind"] == "Perpetual" and x["symbol"].endswith("USDT")
                and x["settlement"] in ("USDT", "")]
        bad = [x["symbol"] for x in usdt if x["L"] is None]
        status = ("unparsed" if not rows else "unparsed_launch_time" if bad else
                  "parsed" if usdt else "parsed_no_usdt_perp")
        art_rows.append({"code": a["code"], "A_ms": rel, "A_utc": utc(rel), "title": title, "status": status,
                         "source": src, "n_rows": len(rows), "n_usdt_perps": len(usdt),
                         "dropped": ";".join(f"{x['symbol']}({x['margin']} {x['kind']})" for x in rows if x not in usdt),
                         "note": ("no launch time for " + ",".join(bad)) if bad else (note.group(0)[:150] if note else "")})
        if bad:
            continue
        for x in usdt:
            l_ms = ms(x["L"])
            fam = named.get(x["symbol"], "")
            ev_rows.append({"episode": a["code"], "A_ms": rel, "A_utc": utc(rel), "symbol": x["symbol"],
                            "L_ms": l_ms, "L_utc": utc(l_ms), "launch_day": utc(l_ms)[:10], "segment": segment(l_ms),
                            "L_minus_A_h": round((l_ms - rel) / 3600_000, 3), "premarket_flag": premarket,
                            "contract_type": x["contract_type"], "underlying_label": x["underlying_label"],
                            "underlying": x["underlying"], "body_family": body_family(x, title),
                            "exclusions_family": fam, "excluded_by_family": int(bool(fam)),
                            "L_in_body_utc": int(f"{x['L']} (UTC)" in text or f"{x['L']}(UTC)" in text),
                            "launch_time_note": note.group(0)[:150] if note else ""})
    for name, rows in (("events.csv", ev_rows), ("articles.csv", art_rows)):
        with open(HERE / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    print(f"raw {path.name} sha256 ok; {len(art_rows)} articles; {len(ev_rows)} USDT-perp rows")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
