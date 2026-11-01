"""
Find every statute citation in the letter text and write one standardized row per letter and
citation, so each one can be grouped by section or subdivision and linked to a code-section tool.

    python3 scripts/parse_citations.py hau          # -> hau/citations.csv (+ hau/CITATIONS.md)
    python3 scripts/parse_citations.py he           # -> he_letters/citations.csv (+ CITATIONS.md)

Standard format (TODO #1): section(subdivision)(paragraph)(subparagraph), no spaces, letters kept
as written:  Gov. Code, § 65915, subd. (o)(8)  ->  65915(o)(8)
             Health & Saf. Code, § 17021.5     ->  HSC 17021.5
Codes other than the Government Code get a prefix: HSC, PRC, CIV, CCP, RTC, EVID, FAM, PEN, WAT, WIC.

Handles: "Gov. Code, §", "Government Code section(s)", "§§", lists joined by commas / "and" / "or",
"subd(s).", "subdivision(s)", "para.", "paragraph", "subparagraph", attached paths ("65585(j)"),
"subdivision (c) of section 65583" (path written first), ranges ("§§ 65580-65589.11", "65580
through 65589.11"), "et seq.", and "Id." / "Ibid." (they repeat the previous citation).
A section number cited with no code named ("section 65583.2") takes the code the same letter uses
for that section elsewhere; failing that, common Health and Safety Code numbers (17000s, 50000s)
are HSC and other 4-6 digit numbers are the Government Code. Those rows have code_inferred=true.

citations.csv: one row per letter x normalized citation (count = mentions in that letter):
  letter_key  task (HAU) or weblink (review letters)
  jurisdiction, letter_date, text_file
  code  section  subdivision_path  normalized  level_section  level_subdivision
  range_end   end of a range, e.g. 65589.11 (normalized is then "65580-65589.11")
  et_seq      true when written "et seq."
  code_inferred
  count       mentions in the letter
  in_footnote true if any mention is on a line that starts with a footnote number (best effort)
  raw         the first mention exactly as written (whitespace collapsed)
  snippet     about 200 characters around the first mention

For HAU letters, CITATIONS.md also compares the sections found with HCD's own Statutory Reference
tags, letter by letter, as an accuracy check.
"""
import bisect
import csv
import re
import sys
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = {
    "hau": {"dir": ROOT / "hau", "key": "task", "date": "letter_date"},
    "he": {"dir": ROOT / "he_letters", "key": "weblink", "date": "reviewed"},
}

CODES = [
    ("GOV", r"Gov(?:ernment|['’]?t|\.)?\s*Code|\bG\.?C\.?(?=\s*§)"),
    ("HSC", r"Health\s*(?:and|&)\s*Saf(?:ety|\.)?\s*Code|\bH\.?\s?S\.?\s?C\.?(?=\s*§)"),
    ("PRC", r"Pub(?:lic|\.)\s*Res(?:ources|\.)?\s*Code"),
    ("CCP", r"Code\s*(?:of\s*)?Civ(?:il|\.)\s*Proc(?:edure|\.)?"),
    ("CIV", r"Civ(?:il|\.)\s*Code"),
    ("RTC", r"Rev(?:enue|\.)\s*(?:and|&)\s*Tax(?:ation|\.)?\s*Code"),
    ("EVID", r"Evid(?:ence|\.)\s*Code"),
    ("FAM", r"Fam(?:ily|\.)\s*Code"),
    ("PEN", r"Pen(?:al|\.)\s*Code"),
    ("WAT", r"Wat(?:er|\.)\s*Code"),
    ("WIC", r"Welf(?:are|\.)\s*(?:and|&)\s*Inst(?:itutions|\.)?\s*Code"),
]
CODE_RX = "|".join(f"(?P<{k}>{v})" for k, v in CODES)
TOK = r"\(\s?(?:[a-z]{1,4}|[A-Z]{1,2}|\d{1,3})\s?\)"          # (c) (10) (A) (iv)
PATH = rf"(?:{TOK})+"
SEC = r"\d{3,6}(?:\.\d{1,3})?(?![\d.]\d)"
MARK = r"§§?|\bSecs?\.|\bSections?\b|\bsecs?\.|\bsections?\b"
SUBD = r"(?:subd(?:s|ivisions?)?\.?|subdivisions?)"
PARA = r"(?:subpara(?:graph)?s?\.?|para(?:graph)?s?\.?)"

rx_mark = re.compile(MARK)
rx_code_before = re.compile(rf"(?:{CODE_RX})\s*,?\s*$")
rx_code_after = re.compile(rf"\s*,?\s*(?:of\s+(?:the\s+)?(?:California\s+)?)(?:{CODE_RX})")
rx_code_paren = re.compile(rf"\s*\(?\s*(?:{CODE_RX})")
rx_code_num = re.compile(rf"(?:{CODE_RX})s?\s*,?\s*(?=\(?\d{{4,6}}(?:\.\d+)?\b)")         # "Government Code 65660"                        # "§ 65583 Gov. Code"
rx_path_before = re.compile(rf"((?:(?:{SUBD}|{PARA})\s*{PATH}\s*,?\s*of\s+(?:the\s+)?)+)$", re.I)
rx_path_piece = re.compile(rf"(?:{SUBD}|{PARA})\s*({PATH})", re.I)
rx_sec = re.compile(rf"\s*({SEC})(\s?{PATH})?")
rx_range = re.compile(rf"\s*(?:-|–|—|\bthrough\b|\bto\b)\s*({SEC})(\s?{PATH})?")
rx_sub = re.compile(rf"\s*,?\s*(?:{SUBD})\s*({PATH})((?:\s*(?:,|\band\b|\bor\b|&)\s*{PATH})*)", re.I)
rx_para = re.compile(rf"\s*,?\s*(?:{PARA})\s*({PATH})", re.I)
rx_more_path = re.compile(rf"\s*(?:,|\band\b|\bor\b|&)\s*({PATH})")
rx_etseq = re.compile(r"\s*,?\s*et\.?\s*seq\.?", re.I)
rx_sep = re.compile(rf"\s*(?:,\s*(?:and|or)?|;|\band\b|\bor\b|&)\s*(?:(?:{MARK})\s*)?(?=\d{{3,6}}(?:\.\d+)?\b(?!\s*(?:units?|homes|percent|%|acres|square|sq|feet|dwelling|people|residents)))", re.I)
rx_id = re.compile(rf"\b(Id\.|Ibid\.?)(\s*,?\s*(?:{SUBD}|{PARA})\s*{PATH}(?:\s*(?:,|\band\b|\bor\b)\s*{PATH})*)?", re.I)
rx_fn_line = re.compile(r"^\s{0,12}\d{1,2}\s+\S")


def clean_path(p):
    return re.sub(r"\s+", "", p or "")


def tokens(p):
    return re.findall(r"\(([^)]+)\)", clean_path(p))


def code_of(m):
    return next(k for k, _ in CODES if m.group(k))


class Flat:
    """Whitespace-collapsed text with a map back to original line numbers (for footnotes)."""
    def __init__(self, text):
        self.lines = text.splitlines()
        parts, starts, pos = [], [], 0
        for ln in self.lines:
            s = " ".join(ln.split())
            starts.append(pos)
            parts.append(s)
            pos += len(s) + 1
        self.text = " ".join(parts)
        self.starts = starts

    def line_of(self, i):
        return max(0, bisect.bisect_right(self.starts, i) - 1)

    def footnote(self, i):
        ln = self.line_of(i)
        # a footnote is a line starting with its number, or a continuation line right after one
        for j in range(ln, max(-1, ln - 4), -1):
            t = self.lines[j] if j < len(self.lines) else ""
            if rx_fn_line.match(t):
                return True
            if not t.strip():
                return False
        return False


def parse(text):
    """Yield dicts: code, section, path, range_end, et_seq, inferred, raw, start."""
    F = Flat(text)
    T = F.text
    out = []
    last = None
    # Id. / Ibid. positions
    ids = [(m.start(), m) for m in rx_id.finditer(T)]
    events = sorted([(m.start(), "mark", m) for m in rx_mark.finditer(T)] + [(p, "id", m) for p, m in ids]
                    + [(m.start(), "codenum", m) for m in rx_code_num.finditer(T)], key=lambda e: e[0])
    consumed_to = -1
    for start, kind, m in events:
        if start < consumed_to:
            continue
        if kind == "id":
            if last is None:
                continue
            extra = m.group(2) or ""
            paths = [clean_path(x) for x in re.findall(PATH, extra)] if extra else [last["path"]]
            for p in paths or [last["path"]]:
                out.append(dict(last, path=p, raw=m.group(0), start=m.start(), footnote=F.footnote(m.start())))
            consumed_to = m.end()
            continue
        pos = m.end()
        seclist = []
        while True:
            s = rx_sec.match(T, pos)
            if not s:
                break
            sec, paths, end = s.group(1), [clean_path(s.group(2))] if s.group(2) else [""], s.end()
            r = rx_range.match(T, end)
            rng = ""
            if r and not s.group(2):
                rng, end = r.group(1), r.end()
            sb = rx_sub.match(T, end)
            if sb:
                ps = [clean_path(sb.group(1))] + [clean_path(x) for x in re.findall(PATH, sb.group(2) or "")]
                paths = [paths[0] + p for p in ps]
                end = sb.end()
            else:
                mp = rx_more_path.match(T, end)
                while mp and paths[0]:
                    paths.append(clean_path(mp.group(1)))
                    end = mp.end()
                    mp = rx_more_path.match(T, end)
            pa = rx_para.match(T, end)
            if pa:
                paths = [p + clean_path(pa.group(1)) for p in paths]
                end = pa.end()
            es = rx_etseq.match(T, end)
            etseq = bool(es)
            if es:
                end = es.end()
            seclist.append((sec, paths, rng, etseq))
            pos = end
            sp = rx_sep.match(T, pos)
            if not sp:
                break
            pos = sp.end()
        if not seclist:
            continue
        # code: before the marker, after the list ("of the Government Code"), or "§ 123 Gov. Code"
        before = T[max(0, start - 60):start]
        cb = rx_code_before.search(before) if kind == "mark" else None
        ca = rx_code_after.match(T, pos) or rx_code_paren.match(T, pos) if kind == "mark" else None
        inferred = False
        if kind == "codenum":
            code, raw_start = code_of(m), start
        elif cb:
            code, raw_start = code_of(cb), start - (len(before) - cb.start())
        elif ca:
            code, raw_start = code_of(ca), start
            pos = ca.end()
        else:
            if not all(re.fullmatch(r"\d{4,6}(?:\.\d+)?", s[0]) for s in seclist):
                continue
            code, raw_start, inferred = guess_code(seclist[0][0]), start, True
        # "subdivision (c) of section 65583" / "paragraph (2) of subdivision (c) of Section ..."
        look = T[max(0, raw_start - 120):raw_start]
        pb = rx_path_before.search(look)
        pre = ""
        if pb:
            pre = "".join(clean_path(x) for x in reversed(rx_path_piece.findall(pb.group(1))))
            raw_start -= len(look) - pb.start()
        raw = T[raw_start:pos].strip(" ,;")
        fn = F.footnote(start)
        for sec, paths, rng, etseq in seclist:
            for p in paths:
                rec = dict(code=code, section=sec, path=(pre + p) if pre and len(seclist) == 1 else p,
                           range_end=rng, et_seq=etseq, inferred=inferred, raw=raw, start=raw_start, footnote=fn)
                out.append(rec)
                last = rec
        consumed_to = pos
    return out, T


# Bare section numbers with no code named: Health and Safety Code sections that housing letters
# cite often; everything else 4-6 digits is taken as the Government Code. A letter that cites the
# same section with its code elsewhere overrides this (see fix_inferred).
HSC_BARE = re.compile(r"(?:170\d\d(?:\.\d+)?|5[0-3]\d{3}(?:\.\d+)?|3417\d(?:\.\d+)?|1795\d(?:\.\d+)?)$")


def guess_code(sec):
    return "HSC" if HSC_BARE.match(sec) else "GOV"


def fix_inferred(cites):
    explicit = {}
    for c in cites:
        if not c["inferred"]:
            explicit.setdefault(c["section"], c["code"])
    for c in cites:
        if c["inferred"] and c["section"] in explicit:
            c["code"] = explicit[c["section"]]
    return cites


def normalized(c):
    base = c["section"] + (f"-{c['range_end']}" if c["range_end"] else "") + c["path"]
    return base if c["code"] == "GOV" else f"{c['code']} {base}"


def level(c, depth):
    pre = "" if c["code"] == "GOV" else c["code"] + " "
    toks = tokens(c["path"])[:depth]
    return pre + c["section"] + "".join(f"({t})" for t in toks)


def plausible(c):
    """Drop obvious non-statute numbers that slip through (years, unit counts)."""
    s = c["section"]
    if c["inferred"] and (re.fullmatch(r"(19|20)\d\d", s) or float(s) < 1000):
        return False
    return True


def main(which):
    cfg = CFG[which]
    d = cfg["dir"]
    idx = list(csv.DictReader(open(d / "letters_index.csv", encoding="utf-8")))
    rows_out = []
    stats = Counter()
    found_by_key = defaultdict(set)
    for r in idx:
        tf = r.get("text_file", "")
        if not (r.get("status", "").startswith("downloaded") and tf):
            continue
        p = d / tf
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        cites, T = parse(text)
        cites = fix_inferred(cites)
        stats["letters"] += 1
        if cites:
            stats["letters_with_citations"] += 1
        agg = OrderedDict()
        for c in cites:
            if not plausible(c):
                continue
            n = normalized(c)
            if n not in agg:
                s0 = max(0, c["start"] - 80)
                agg[n] = dict(c, count=0, fn=False, snippet=T[s0:s0 + 220].strip())
            agg[n]["count"] += 1
            agg[n]["fn"] = agg[n]["fn"] or c["footnote"]
        key = r.get(cfg["key"], "")
        for n, c in agg.items():
            found_by_key[key].add(level(c, 0))
            rows_out.append({
                "letter_key": key, "jurisdiction": r.get("jurisdiction", ""), "letter_date": r.get(cfg["date"], ""),
                "text_file": tf, "code": c["code"], "section": c["section"], "subdivision_path": c["path"],
                "normalized": n, "level_section": level(c, 0), "level_subdivision": level(c, 1),
                "range_end": c["range_end"], "et_seq": str(c["et_seq"]).lower(), "code_inferred": str(c["inferred"]).lower(),
                "count": c["count"], "in_footnote": str(c["fn"]).lower(), "raw": c["raw"][:300], "snippet": c["snippet"],
            })
    cols = ["letter_key", "jurisdiction", "letter_date", "text_file", "code", "section", "subdivision_path", "normalized",
            "level_section", "level_subdivision", "range_end", "et_seq", "code_inferred", "count", "in_footnote", "raw", "snippet"]
    with open(d / "citations.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows_out)
    print(f"{d.name}/citations.csv: {len(rows_out):,} rows from {stats['letters']:,} letters "
          f"({stats['letters_with_citations']:,} with at least one citation)")
    write_report(which, d, rows_out, stats, found_by_key)


def write_report(which, d, rows, stats, found_by_key):
    def letters(col, keep=lambda r: True):
        return Counter(k for k, _ in {(r[col], r["letter_key"]) for r in rows if keep(r)})
    sec = letters("level_section")
    sub = letters("level_subdivision", lambda r: r["subdivision_path"])
    full = letters("normalized", lambda r: len(tokens(r["subdivision_path"])) > 1)
    out = [f"# Statute citations in the letters ({'HAU' if which == 'hau' else 'housing element review'})", "",
           f"Parsed from the letter text by `scripts/parse_citations.py`: {len(rows):,} letter–citation rows from "
           f"{stats['letters']:,} letters with text. Data: [`citations.csv`](citations.csv). Counts are letters citing each, "
           "not mentions.", "",
           "Format: `65915(o)(8)` for the Government Code; other codes are prefixed, e.g. `HSC 17021.5`.", ""]
    if which == "hau":
        tags = {}
        for r in csv.DictReader(open(d / "hau_letters.csv", encoding="utf-8")):
            t = set()
            for x in (r.get("statutes") or "").split(" | "):
                m = re.search(r"(\d{3,6}(?:\.\d+)?)", x)
                if m and "-" not in x:
                    t.add(m.group(1))
            tags[r["task"]] = t
        both = tagged = hit = extra = 0
        for k, found in found_by_key.items():
            t = tags.get(k, set())
            f = {x for x in found if " " not in x}
            if t:
                tagged += 1
                both += len(t & f)
                hit += len(t)
                extra += len(f - t)
        if hit:
            out += ["## Check against HCD's Statutory Reference tags", "",
                    f"Of {hit:,} section tags HCD gave the {tagged:,} tagged letters with text, the parser found "
                    f"**{both / hit:.0%}** in the letter text. It also found {extra:,} cited sections HCD didn't tag "
                    "(HCD tags the main statutes, not every section a letter cites).", ""]
    for title, cnt in (("Most-cited sections", sec), ("Most-cited subdivisions", sub), ("Most-cited full citations", full)):
        out += [f"## {title}", "", "| Citation | Letters |", "|---|---|"]
        out += [f"| `{k}` | {v:,} |" for k, v in cnt.most_common(40)]
        out.append("")
    (d / "CITATIONS.md").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "he")
