"""DL-1 step 1: parse the raw Binance Futures delisting announcements into the
event list (PREREG v0.2 §1). Reads only events_raw/*.json; no price data.

Usage: parse_events.py RAW_JSON   (RAW_JSON.sha256 must sit next to it)

Outputs (studies/delisting/):
  events.csv      one row per (article, USDT-margined perp symbol)
  articles.csv    one row per selected article, with its parse status
  unselected.csv  catalog titles about futures contracts that fail the frozen
                  §1 title filter (excluded by rule, listed for the record)

Rules (PREREG §1):
  A = release_ms of the article; D = settlement time stated in the body for that
  symbol; N = no-new-orders time stated in the body for that symbol, else D - 1h.
  Episode = all USDT symbols in one article. USDT-margined only (COIN-M ...USD,
  BUSD- and USDC-margined contracts are dropped). Postponement notices are not
  episodes; D and N stay as stated in the episode's own article (what a trader
  knew at A) and the later date is recorded in D_postponed_utc.
  Time-only exclusions known before any price data are marked in
  excluded_by_time_rule: D - A < 12h, and window_past_data_limit (a TEST event
  whose exit window needs data after 2026-03-13).
"""
import csv
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
TITLE_FILTER = re.compile(r"Futures Will Delist|Perpetual Contract", re.I)  # frozen §1 selection
FUTURES_WORDS = re.compile(r"Futures|Perpetual", re.I)

TEST = (dt.datetime(2022, 2, 17, tzinfo=dt.timezone.utc), dt.datetime(2026, 3, 14, tzinfo=dt.timezone.utc))
HOLDOUT = (dt.datetime(2026, 3, 15, tzinfo=dt.timezone.utc), dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc))
DATA_LIMIT_MS = int(dt.datetime(2026, 3, 14, tzinfo=dt.timezone.utc).timestamp() * 1000)  # data ≤ 2026-03-13

TIME = r"(20\d\d-\d\d-\d\d \d\d:\d\d) ?\(UTC ?\)"
SYM = re.compile(r"(?<![0-9A-Za-z])([0-9A-Z]{2,20}USDT)(?![0-9A-Za-z])")
RESTRICT = re.compile(r"[^.]*\b(?:will|has)\s+(?:adjust|adjusted|update|updated)\s+the\s+leverage\s+and\s+margin\s+tiers[^.]*",
                      re.I)


def ms(s: str) -> int:
    return int(dt.datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


def utc(m: int) -> str:
    return dt.datetime.fromtimestamp(m / 1000, dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def segment(a_ms: int) -> str:
    t = dt.datetime.fromtimestamp(a_ms / 1000, dt.timezone.utc)
    if TEST[0] <= t < TEST[1]:
        return "TEST"
    if HOLDOUT[0] <= t < HOLDOUT[1]:
        return "HOLDOUT"
    return "EMBARGO" if TEST[1] <= t < HOLDOUT[0] else "OUT_OF_RANGE"


def clean(t: str) -> str:
    t = t.replace("&nbsp;", " ").replace("\xa0", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", t)


def assign_times(seg: str) -> dict[str, str]:
    """Map each USDT symbol in `seg` to its time. List format ('as below: <time>
    (UTC) : USDⓈ-M X and Y ...') puts the time before its symbols; sentence
    format ('X, Y ... at <time> (UTC), and Z ... at <time>') puts it after."""
    times = [(m.start(), m.group(1)) for m in re.finditer(TIME, seg)]
    syms = [(m.start(), m.group(1)) for m in SYM.finditer(seg)]
    if not times:
        return {}
    listed = re.search(TIME + r"\s*:", seg) is not None
    out: dict[str, str] = {}
    for pos, s in syms:
        if listed:
            prev = [t for p, t in times if p < pos]
            t = prev[-1] if prev else None
        else:
            nxt = [t for p, t in times if p > pos]
            t = nxt[0] if nxt else (times[-1][1] if len(times) == 1 else None)
        if t is not None and s not in out:
            out[s] = t
    return out


def settlement_segment(text: str) -> str | None:
    m = re.search(r"(?:close all positions|conduct (?:an )?automatic settlements?)", text, re.I)
    if not m:
        return None
    end = re.search(r"The contracts? will be delisted|will be delisted after|In addition|Please Note", text[m.start():])
    return text[m.start(): m.start() + (end.start() if end else 1500)]


def noopen_segment(text: str) -> str | None:
    m = re.search(r"not (?:be )?allowed to (?:open new|place new)", text, re.I)
    if not m:
        return None
    end = re.search(r"\bAt 20\d\d-|In order to protect|During the|This information|For More Information|Note:",
                    text[m.start():], re.I)
    return text[m.start(): m.start() + (end.start() if end else 600)]


def parse_article(a: dict) -> dict:
    text = clean(a["body_text"])
    title = clean(a["title"])
    res = {"symbols": {}, "status": None, "note": ""}
    if re.search(r"postpone", title, re.I):
        sym = SYM.findall(title)
        new = re.search(r"postpone the delisting of the USDⓈ-M (\w+) Perpetual Contract to " + TIME, text)
        res["status"] = "postponement_notice"
        res["postpone"] = (new.group(1), new.group(2)) if new else (sym[0] if sym else None, None)
        return res
    seg = settlement_segment(text)
    if seg is None:
        res["status"] = "no_settlement_sentence"
        return res
    d_map = assign_times(seg)
    all_usdt = sorted(set(SYM.findall(seg)))
    if not all_usdt:
        res["status"] = "parsed_no_usdt_symbol"
        res["note"] = "COIN-M only" if "COIN-M" in seg else ("BUSD only" if "BUSD" in seg else "no USDT symbol")
        return res
    missing = [s for s in all_usdt if s not in d_map]
    if missing:
        res["status"] = "unparsed_symbol_time"
        res["note"] = "no settlement time for " + ",".join(missing)
        return res
    nseg = noopen_segment(text)
    n_map, n_single = {}, None
    if nseg:
        n_map = assign_times(nseg)
        ts = re.findall(TIME, nseg)
        if len(set(ts)) == 1:
            n_single = ts[0]
    restrict_sents = [s.strip() for s in RESTRICT.findall(text)]
    for s in all_usdt:
        d = d_map[s]
        if s in n_map:
            n, src = n_map[s], "stated"
        elif n_single is not None:
            n, src = n_single, "stated"
        else:
            n, src = None, "default_D-1h"
        d_ms = ms(d)
        n_ms = ms(n) if n else d_ms - 3600_000
        rs = [x for x in restrict_sents if s in x or not SYM.search(x)]
        res["symbols"][s] = {"D_ms": d_ms, "N_ms": n_ms, "N_source": src,
                             "restriction_flag": int(bool(rs)), "restriction_text": " | ".join(rs)[:300]}
    res["status"] = "parsed"
    return res


def main(raw_path: str) -> int:
    path = Path(raw_path)
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    want = Path(str(path) + ".sha256").read_text().split()[0]
    if sha != want:
        print(f"raw sha256 mismatch: {sha} != {want}", file=sys.stderr)
        return 1
    r = json.loads(raw)
    titles = {x["code"]: x for x in r["all_titles"]}
    arts = sorted(r["articles"], key=lambda a: int(a.get("release_ms") or titles[a["code"]]["release"]))
    art_rows, ev_rows, postpone = [], [], {}
    for a in arts:
        if "error" in a:
            rel = int(titles[a["code"]]["release"])
            art_rows.append({"code": a["code"], "A_ms": rel, "A_utc": utc(rel), "segment": segment(rel),
                             "title": clean(titles[a["code"]]["title"]), "status": "fetch_failed",
                             "n_usdt_symbols": "", "note": a["error"][:120]})
            continue
        rel = int(a["release_ms"])
        p = parse_article(a)
        if p["status"] == "postponement_notice":
            postpone.setdefault(p["postpone"][0], []).append((rel, p["postpone"][1]))
        art_rows.append({"code": a["code"], "A_ms": rel, "A_utc": utc(rel), "segment": segment(rel),
                         "title": clean(a["title"]), "status": p["status"],
                         "n_usdt_symbols": len(p["symbols"]), "note": p["note"]})
        for s, v in p["symbols"].items():
            notes = []
            if v["N_ms"] >= v["D_ms"] or v["N_ms"] <= rel:
                notes.append("N_not_between_A_and_D")
            ev_rows.append({"episode": a["code"], "A_ms": rel, "A_utc": utc(rel), "segment": segment(rel),
                            "symbol": s, "D_ms": v["D_ms"], "D_utc": utc(v["D_ms"]), "N_ms": v["N_ms"],
                            "N_utc": utc(v["N_ms"]), "N_source": v["N_source"],
                            "D_minus_A_h": round((v["D_ms"] - rel) / 3600_000, 3),
                            "restriction_flag": v["restriction_flag"], "D_postponed_utc": "",
                            "excluded_by_time_rule": ("D_minus_A_lt_12h" if v["D_ms"] - rel < 12 * 3600_000 else
                                                      "window_past_data_limit"
                                                      if segment(rel) == "TEST" and v["D_ms"] >= DATA_LIMIT_MS else ""),
                            "notes": ";".join(notes), "restriction_text": v["restriction_text"]})
    for e in ev_rows:  # postponement notices published after A and before the original D
        for rel, new in postpone.get(e["symbol"], []):
            if e["A_ms"] < rel < e["D_ms"] and new:
                e["D_postponed_utc"] = new + ":00"
                e["notes"] = ";".join(x for x in (e["notes"], f"postponed_by_notice_{utc(rel)[:10]}_trade_uses_original_D_N") if x)
            elif e["A_ms"] < rel and new and e["D_postponed_utc"] and rel < ms(e["D_postponed_utc"][:16]):
                e["D_postponed_utc"] = new + ":00"
                e["notes"] += f";further_postponed_{utc(rel)[:10]}"
    selected = {a["code"] for a in r["articles"]}
    assert all(TITLE_FILTER.search(clean(titles[c]["title"])) for c in selected), "selected title fails filter"
    unsel = [{"code": x["code"], "A_ms": int(x["release"]), "A_utc": utc(int(x["release"])),
              "segment": segment(int(x["release"])), "title": clean(x["title"]),
              "reason": "title fails frozen §1 filter"}
             for x in sorted(r["all_titles"], key=lambda x: int(x["release"]))
             if x["code"] not in selected and FUTURES_WORDS.search(x["title"])
             and not TITLE_FILTER.search(clean(x["title"]))]
    for name, rows in (("events.csv", ev_rows), ("articles.csv", art_rows), ("unselected.csv", unsel)):
        with open(HERE / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    print(f"raw {path.name} sha256 ok; {len(art_rows)} articles; {len(ev_rows)} symbol-events; "
          f"{len(unsel)} unselected futures titles")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
