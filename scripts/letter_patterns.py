"""
Find the standard language in HCD's letters: section headings, boilerplate paragraphs that recur
across letters, and the variants of each.

    python3 scripts/letter_patterns.py he      # -> he_letters/PATTERNS.md, he_letters/patterns.csv
    python3 scripts/letter_patterns.py hau     # -> hau/PATTERNS.md, hau/patterns.csv

How it works
  1. Splits each letter into paragraphs (pdftotext layout; wrapped lines re-joined, page headers
     and letterhead dropped) and keeps paragraphs of 20+ words.
  2. Normalizes them so letters to different places compare as equal: the jurisdiction and county
     names become <JUR>, dates <DATE>, numbers <N> (Gov. Code section numbers are kept),
     "City/County/Town" <JTYPE>. Letterhead blocks are skipped.
  3. Groups near-identical paragraphs (MinHash on 5-word shingles, then Jaccard >= 0.5) and,
     inside each group, tighter variants (Jaccard >= 0.85).
  4. Counts recurring headings (lines like "A. Review and Revision" or "1. Sites Inventory").

patterns.csv: one row per paragraph group seen in at least MIN_LETTERS letters:
  group, letters, share, first_year, last_year, variants, out_share (review letters: share of the
  group's letters with an Out finding), example (normalized text of the most typical paragraph)
patterns.json: the same groups for the website (use by year, variants, word diffs, member letters).
PATTERNS.md: the headings, the top groups with their main variants and a word-level diff of how
the most common variants differ.
Needs numpy. Takes about a minute for 2,000 letters.
"""
import csv
import difflib
import json
import re
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CFG = {"he": {"dir": ROOT / "he_letters", "date": "reviewed", "analysis": "letters_analysis.csv"},
       "hau": {"dir": ROOT / "hau", "date": "letter_date", "analysis": None}}
MIN_WORDS, MIN_LETTERS, SHINGLE, PERMS, BANDS = 20, 25, 5, 64, 16
LOOSE, TIGHT = 0.5, 0.85

MONTH = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
RX_DATE = re.compile(rf"\b{MONTH}\.?\s+\d{{1,2}},?\s+\d{{4}}\b|\b\d{{1,2}}/\d{{1,2}}/\d{{2,4}}\b", re.I)
RX_NUM = re.compile(r"(?<![\w.])(?!6\d{4}(?:\.\d+)?\b)\d[\d,]*(?:\.\d+)?(?![\w.])")  # keeps 6xxxx section numbers
RX_LETTERHEAD = re.compile(r"www\.hcd\.ca\.gov|Governor\s+DEPARTMENT OF HOUSING|^STATE OF CALIFORNIA", re.I)
RX_HEADER = re.compile(r"^\s*(?:Page \d+|.*\bPage \d+\s*$)")
RX_HEADING = re.compile(r"^\s{0,12}((?:[A-H]|[1-9]|1[0-9]|[ivx]{1,4})[.)]\s+[A-Z][A-Za-z ,'’&/()-]{3,90})\s*$")


def paragraphs(text):
    """Blocks of text between blank lines, with wrapped lines joined and page headers removed."""
    lines = text.splitlines()
    out, cur = [], []
    for i, ln in enumerate(lines):
        if RX_HEADER.match(ln) or (i + 1 < len(lines) and re.match(r"^\s*Page \d+\s*$", lines[i + 1])):
            continue
        if ln.strip():
            cur.append(ln.strip())
        elif cur:
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return [re.sub(r"\s+", " ", p) for p in out]


def headings(text):
    return [m.group(1).strip() for ln in text.splitlines() if (m := RX_HEADING.match(ln))]


def normalizer(names):
    names = sorted({n for n in names if n and len(n) > 2}, key=len, reverse=True)
    rx_names = re.compile(r"\b(?:" + "|".join(re.escape(n) for n in names) + r")(?:['’]s)?\b", re.I) if names else None

    def norm(p):
        s = RX_DATE.sub("<DATE>", p)
        if rx_names:
            s = rx_names.sub("<JUR>", s)
        s = re.sub(r"\b(?:City|County|Town)(?:['’]s)?\b", "<JTYPE>", s)
        s = RX_NUM.sub("<N>", s)
        return s
    return norm


def words(s):
    return re.findall(r"<\w+>|[a-z0-9']+", s.lower())


def shingles(ws):
    # crc32, not hash(): Python's string hash changes between runs, which would change the groups week to week
    return {zlib.crc32(" ".join(ws[i:i + SHINGLE]).encode()) for i in range(max(1, len(ws) - SHINGLE + 1))}


def minhash(sets):
    rng = np.random.default_rng(7)
    p = np.uint64(4294967311)
    a = rng.integers(1, 2**32 - 1, PERMS, dtype=np.uint64)
    b = rng.integers(0, 2**32 - 1, PERMS, dtype=np.uint64)
    sig = np.empty((len(sets), PERMS), dtype=np.uint64)
    for i, s in enumerate(sets):
        x = np.fromiter(s, dtype=np.uint64)
        sig[i] = ((np.outer(x, a) + b) % p).min(axis=0)
    return sig


class DSU:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.p[b] = a


def jac(a, b):
    return len(a & b) / max(1, len(a | b))


def cluster(sig, sets, idx, thresh):
    """Union-find over LSH candidate pairs among rows idx, keeping pairs with Jaccard >= thresh."""
    d = DSU(len(idx))
    r = PERMS // BANDS
    for band in range(BANDS):
        buckets = defaultdict(list)
        for k, i in enumerate(idx):
            buckets[sig[i, band * r:(band + 1) * r].tobytes()].append(k)
        for ks in buckets.values():
            if len(ks) < 2:
                continue
            anchor = ks[0]
            for k in ks[1:]:  # chain to the first member; cheap and enough for near-duplicates
                if d.find(k) != d.find(anchor) and jac(sets[idx[k]], sets[idx[anchor]]) >= thresh:
                    d.union(anchor, k)
    groups = defaultdict(list)
    for k, i in enumerate(idx):
        groups[d.find(k)].append(i)
    return list(groups.values())


def medoid(members, sets, cap=60):
    sample = members[:cap]
    return max(sample, key=lambda i: sum(jac(sets[i], sets[j]) for j in sample))


def diff_words(a, b):
    wa, wb = a.split(), b.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, wa, wb, autojunk=False).get_opcodes():
        if op == "equal":
            seg = wa[i1:i2]
            out.append(" ".join(seg) if len(seg) <= 12 else " ".join(seg[:5]) + " … " + " ".join(seg[-5:]))
        if op in ("delete", "replace"):
            out.append("~~" + " ".join(wa[i1:i2]) + "~~")
        if op in ("insert", "replace"):
            out.append("**" + " ".join(wb[j1:j2]) + "**")
    return " ".join(out)


def diff_ops(a, b):
    """Word diff as [["=", text], ["-", text], ["+", text]] for the website."""
    wa, wb = a.split(), b.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, wa, wb, autojunk=False).get_opcodes():
        if op == "equal":
            out.append(["=", " ".join(wa[i1:i2])])
        if op in ("delete", "replace"):
            out.append(["-", " ".join(wa[i1:i2])])
        if op in ("insert", "replace"):
            out.append(["+", " ".join(wb[j1:j2])])
    return out


def main(which):
    cfg = CFG[which]
    d = cfg["dir"]
    idx = [r for r in csv.DictReader(open(d / "letters_index.csv", encoding="utf-8"))
           if r.get("status", "").startswith("downloaded") and r.get("text_file")]
    finding = {}
    if cfg["analysis"] and (d / cfg["analysis"]).exists():
        for r in csv.DictReader(open(d / cfg["analysis"], encoding="utf-8")):
            finding[(r["jurisdiction"], r["letter_date"], r.get("type", ""))] = r.get("finding", "")
    names = {x for r in idx for x in (r.get("jurisdiction"), r.get("county"))}
    names |= {re.sub(r"\s+County$", "", n) for n in names if n}
    norm = normalizer(names)

    paras, meta, head_count, letters_seen = [], [], Counter(), {}
    seen_text = set()
    for li, r in enumerate(idx):
        p = d / r["text_file"]
        if not p.exists() or r["text_file"] in seen_text:
            continue
        seen_text.add(r["text_file"])
        text = p.read_text(encoding="utf-8", errors="replace")
        year = (r.get(cfg["date"]) or "")[:4]
        letters_seen[li] = (year, finding.get((r.get("jurisdiction", ""), r.get(cfg["date"], ""), r.get("type", "")), ""), r.get("type", ""))
        hs = set()
        for h in headings(text):
            h = re.sub(r"^\S+\s+", "", norm(h)).strip(" .:")
            ws = h.split()
            hs.add(" ".join(ws[:7]) + (" …" if len(ws) > 7 else ""))  # headings that quote a statute wrap; compare the start
        for h in hs:
            head_count[h] += 1
        for para in paragraphs(text):
            n = norm(para)
            ws = words(n)
            if len(ws) >= MIN_WORDS and not RX_LETTERHEAD.search(para):
                paras.append(n)
                meta.append(li)
    sets = [shingles(words(p)) for p in paras]
    print(f"{len(letters_seen):,} letters, {len(paras):,} paragraphs of {MIN_WORDS}+ words")
    sig = minhash(sets)
    groups = [g for g in cluster(sig, sets, list(range(len(paras))), LOOSE) if len({meta[i] for i in g}) >= MIN_LETTERS]
    groups.sort(key=lambda g: -len({meta[i] for i in g}))
    N = len(letters_seen)

    rows, md_groups, jgroups = [], [], []
    for gi, g in enumerate(groups, 1):
        lets = {meta[i] for i in g}
        years = sorted(y for y in (letters_seen[m][0] for m in lets) if y)
        fnd = [letters_seen[m][1] for m in lets if letters_seen[m][1] in ("In", "Out")]
        variants = sorted(cluster(sig, sets, g, TIGHT), key=lambda v: -len({meta[i] for i in v}))
        variants = [v for v in variants if len({meta[i] for i in v}) >= 5]
        ex = paras[medoid(g, sets)]
        rows.append({"group": gi, "letters": len(lets), "share": f"{len(lets) / N:.3f}",
                     "first_year": years[0] if years else "", "last_year": years[-1] if years else "",
                     "variants": len(variants), "out_share": f"{fnd.count('Out') / len(fnd):.2f}" if fnd else "",
                     "example": ex})
        vinfo = []
        for v in variants[:4]:
            vl = {meta[i] for i in v}
            vy = sorted(y for y in (letters_seen[m][0] for m in vl) if y)
            vinfo.append((len(vl), vy[0] if vy else "", vy[-1] if vy else "", paras[medoid(v, sets)]))
        md_groups.append((gi, len(lets), years, fnd, ex, vinfo))
        vjson = []
        for k, v in enumerate(variants[:6]):
            vl = {meta[i] for i in v}
            vex = paras[medoid(v, sets)]
            vjson.append({"letters": len(vl), "byYear": dict(Counter(letters_seen[m][0] for m in vl if letters_seen[m][0])),
                          "example": vex, "diff": diff_ops(paras[medoid(variants[0], sets)], vex) if k else []})
        jgroups.append({"id": gi, "letters": len(lets), "outShare": round(fnd.count("Out") / len(fnd), 3) if fnd else None,
                        "byYear": dict(Counter(letters_seen[m][0] for m in lets if letters_seen[m][0])), "example": ex,
                        "variants": vjson, "members": sorted(lets)})

    with open(d / "patterns.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["group"])
        w.writeheader()
        w.writerows(rows)

    # for the website: letters are referred to by their position in "letters"
    order = sorted({m for g in jgroups for m in g["members"]})
    pos = {m: i for i, m in enumerate(order)}
    for g in jgroups:
        g["members"] = [pos[m] for m in g["members"]]
    (d / "patterns.json").write_text(json.dumps({
        "letters": [idx[m]["text_file"] for m in order], "total": N, "groups": jgroups,
        "headings": [[h, n] for h, n in head_count.most_common(60) if n >= 10]}, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")

    label = "housing element review" if which == "he" else "HAU"
    out = [f"# Standard language in HCD's {label} letters", "",
           f"From {N:,} letters with text and {len(paras):,} paragraphs of {MIN_WORDS}+ words, by `scripts/letter_patterns.py`. "
           "Names, dates and numbers are replaced with <JUR>, <DATE> and <N> so letters to different places compare as equal. "
           f"A *group* is paragraphs that share at least half their 5-word phrases; a *variant* is a tighter group "
           f"(85%) inside it. Groups in fewer than {MIN_LETTERS} letters are left out. Data: [`patterns.csv`](patterns.csv).", "",
           "## Recurring headings", "", "| Heading | Letters |", "|---|---|"]
    out += [f"| {h} | {n:,} |" for h, n in head_count.most_common(40) if n >= 10]
    out += ["", "## Recurring paragraphs", ""]
    for gi, n, years, fnd, ex, vinfo in md_groups[:40]:
        span = f"{years[0]}–{years[-1]}" if years else ""
        fs = f"; {fnd.count('Out') / len(fnd):.0%} of these letters are Out findings" if fnd else ""
        out += [f"### Group {gi}: {n:,} letters ({n / N:.0%}), {span}{fs}", "", "> " + ex, ""]
        if len(vinfo) > 1:
            out += ["| Variant | Letters | Years |", "|---|---|---|"]
            out += [f"| {k} | {vn:,} | {a}–{b} |" for k, (vn, a, b, _) in enumerate(vinfo, 1)]
            out += ["", f"How variant 2 differs from variant 1 (~~removed~~, **added**):", "",
                    "> " + diff_words(vinfo[0][3], vinfo[1][3]), ""]
    (d / "PATTERNS.md").write_text("\n".join(out), encoding="utf-8")
    print(f"{d.name}/PATTERNS.md: {len(groups)} recurring paragraph groups, {sum(1 for n in head_count.values() if n >= 10)} recurring headings")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "he")
