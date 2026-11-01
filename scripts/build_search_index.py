"""
Build the full-text search index the website's Search tab uses (TODO #5).

    python3 scripts/build_site_data.py && python3 scripts/build_search_index.py

Reads site/data/hau.json and he.json (for the letter order and text paths) and every letter's
text, and writes site/search/:
  docs.json        doc id -> [source, row]: source 0 = HAU (hau.json), 1 = review letter (he.json)
  s/<n>.json       512 shards of the inverted index; a word or two-word phrase lives in shard
                   fnv1a(term) % 512, so a query loads only the shards for its own words
  meta.json        doc count, shard count, build time

Each shard maps a term to "ids" or "ids|tfs":
  ids  doc ids, delta-encoded in base 36, comma-separated
  tfs  one base-36 digit per doc: how often the word occurs (capped at 35), for ranking; single
       words only. Two-word terms ("sites inventory") have ids only; they make "exact phrase"
       searches work: a quoted phrase must contain each of its consecutive word pairs.

Words are lower-cased runs of letters/digits, keeping inner dots and apostrophes (65583.2,
builder's). site/app.js tokenizes queries the same way; keep the two in step.
No dependencies; GitHub Pages serves the shards gzip-compressed.
"""
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("HCD_ROOT") or Path(__file__).resolve().parent.parent)
DATA = ROOT / "site" / "data"
OUT = ROOT / "site" / "search"
SHARDS = 512
TOKEN = re.compile(r"[a-z0-9]+(?:['.][a-z0-9]+)*")
B36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def tokens(text):
    return TOKEN.findall(text.lower().replace("’", "'").replace("‘", "'"))


def fnv1a(s):
    h = 0x811C9DC5
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def b36(n):
    if n == 0:
        return "0"
    out = ""
    while n:
        n, r = divmod(n, 36)
        out = B36[r] + out
    return out


def main():
    hau = json.loads((DATA / "hau.json").read_text(encoding="utf-8"))
    he = json.loads((DATA / "he.json").read_text(encoding="utf-8"))
    docs = []
    for src, obj in ((0, hau), (1, he)):
        ti = obj["cols"].index("text")
        for i, row in enumerate(obj["rows"]):
            if row[ti]:
                docs.append((src, i, row[ti]))
    uni = defaultdict(list)   # term -> [(doc, tf)]
    bi = defaultdict(list)    # "a b" -> [doc]
    missing = 0
    for d, (_, _, path) in enumerate(docs):
        p = ROOT / path
        if not p.exists():
            missing += 1
            continue
        toks = tokens(p.read_text(encoding="utf-8", errors="replace"))
        for t, n in Counter(toks).items():
            uni[t].append((d, min(n, 35)))
        for pair in set(zip(toks, toks[1:])):
            bi[f"{pair[0]} {pair[1]}"].append(d)
    shards = defaultdict(dict)
    for t, post in uni.items():
        prev, ids = 0, []
        for d, _ in post:
            ids.append(b36(d - prev))
            prev = d
        shards[fnv1a(t) % SHARDS][t] = ",".join(ids) + "|" + "".join(B36[n] for _, n in post)
    for t, post in bi.items():
        prev, ids = 0, []
        for d in post:
            ids.append(b36(d - prev))
            prev = d
        shards[fnv1a(t) % SHARDS][t] = ",".join(ids)
    (OUT / "s").mkdir(parents=True, exist_ok=True)
    for f in (OUT / "s").glob("*.json"):
        f.unlink()
    total = 0
    for n in range(SHARDS):
        p = OUT / "s" / f"{n}.json"
        p.write_text(json.dumps(shards.get(n, {}), separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
        total += p.stat().st_size
    (OUT / "docs.json").write_text(json.dumps([[s, i] for s, i, _ in docs], separators=(",", ":")), encoding="utf-8")
    (OUT / "meta.json").write_text(json.dumps({
        "docs": len(docs), "shards": SHARDS, "words": len(uni), "pairs": len(bi),
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}), encoding="utf-8")
    print(f"site/search: {len(docs):,} letters ({missing} text files missing), {len(uni):,} words, "
          f"{len(bi):,} word pairs, {total / 1e6:,.1f} MB in {SHARDS} shards")


if __name__ == "__main__":
    main()
