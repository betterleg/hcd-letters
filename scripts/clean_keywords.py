"""
Merge HCD's free-typed HAU keywords into a cleaner list (TODO: keyword cleanup).

    python3 scripts/clean_keywords.py          # writes hau/keyword_map.csv

HCD types keywords by hand, so the same idea appears many ways: "housing element" and "housing
element law", "LOI" and "letter of inquiry", "concession" and "concessions", or two keywords in one
("LOI, Housing Element Law"). The raw tags stay untouched in hau_letters.csv / hau_keywords.csv;
this writes a lookup the website uses to group them.

hau/keyword_map.csv columns
  raw     the keyword exactly as HCD typed it
  clean   the grouped keyword(s); several are joined with " | "; empty drops the keyword
  rule    auto (this script) or manual (yours)
  letters how many letters carry the raw keyword

To change a grouping, edit that row's `clean` and set `rule` to `manual`. Manual rows are kept as
they are on every run; auto rows are recomputed.
"""
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HAU = ROOT / "hau"

# lower-case variant -> grouped label
SYNONYMS = {
    "loi": "Letter of inquiry", "letter of inquiry": "Letter of inquiry",
    "nov": "Notice of violation", "notice of violation": "Notice of violation",
    "haa": "Housing Accountability Act", "housing accountability act": "Housing Accountability Act",
    "sdbl": "Density bonus", "density bonus law": "Density bonus", "state density bonus law": "Density bonus",
    "density bonus": "Density bonus",
    "affh": "Affirmatively furthering fair housing", "affirmatively furthering fair housing": "Affirmatively furthering fair housing",
    "psh": "Permanent supportive housing", "permanent supportive housing": "Permanent supportive housing",
    "housing element law": "Housing element", "housing element": "Housing element",
    "housing crisis act of 2019": "Housing Crisis Act", "housing crisis act": "Housing Crisis Act", "hca": "Housing Crisis Act",
    "sb 330": "Housing Crisis Act",
    "sla": "Surplus Land Act", "surplus land act": "Surplus Land Act",
    "no net loss of jurisdiction capacity": "No net loss", "housing element no net loss": "No net loss", "no net loss": "No net loss",
    "builders remedy": "Builder's remedy", "builder's remedy": "Builder's remedy",
    "pre-application": "Preliminary application", "preliminary application": "Preliminary application",
    "adu": "ADU", "adus": "ADU", "accessory dwelling unit": "ADU", "accessory dwelling units": "ADU",
    "jadu": "JADU", "junior accessory dwelling unit": "JADU",
    "adu ordinance": "ADU ordinance", "adu ordinance review": "ADU ordinance",
    "adu ordinance repeal request": "ADU ordinance repeal request",
    "ceqa": "CEQA", "rhna": "RHNA", "pra": "Permit Streamlining Act", "psa": "Permit Streamlining Act",
    "permit streamlining act": "Permit Streamlining Act",
    "sb 35": "SB 35", "sb35": "SB 35", "sb 9": "SB 9", "sb9": "SB 9", "sb 79": "SB 79", "sb79": "SB 79",
    "ab 2011": "AB 2011", "ab2011": "AB 2011",
    "height limit": "Height", "height": "Height",
    "deed restriction": "Deed restriction", "deed restrictions": "Deed restriction",
    "group homes": "Group homes", "group home": "Group homes",
    "findings of denial": "Findings of denial", "haa findings of denial": "Findings of denial",
}


def split_raw(raw):
    return [p for p in (x.strip(" .\t") for x in re.split(r"\s*[,;]\s*", raw or "")) if p]


def build(raw_counts, manual):
    """raw keyword -> list of clean labels."""
    parts = {raw: [re.sub(r"\s+", " ", p) for p in split_raw(raw)] for raw in raw_counts}
    lower_count = Counter()
    spelled = defaultdict(Counter)
    for raw, ps in parts.items():
        for p in ps:
            lower_count[p.lower()] += raw_counts[raw]
            spelled[p.lower()][p] += raw_counts[raw]

    def canon_key(k):
        if k in SYNONYMS:
            return k
        for suf, rep in (("ies", "y"), ("es", ""), ("s", "")):  # plural -> singular when the singular is also used
            if k.endswith(suf) and len(k) > 4 and (k[: -len(suf)] + rep) in lower_count:
                return k[: -len(suf)] + rep
        return k

    def label(k):
        k = canon_key(k)
        if k in SYNONYMS:
            return SYNONYMS[k]
        best = spelled[k].most_common(1)[0][0] if spelled[k] else k
        return best[0].upper() + best[1:] if best == best.lower() else best

    out = {}
    for raw, ps in parts.items():
        if raw in manual:
            out[raw] = [x.strip() for x in manual[raw].split(" | ") if x.strip()]
        else:
            seen = []
            for p in ps:
                lab = label(p.lower())
                if lab not in seen:
                    seen.append(lab)
            out[raw] = seen
    return out


def load_manual(path=HAU / "keyword_map.csv"):
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return {r["raw"]: r.get("clean", "") for r in csv.DictReader(f) if r.get("rule") == "manual"}


def raw_counts_from(path=HAU / "hau_letters.csv"):
    c = Counter()
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for k in (r.get("keywords") or "").split(" | "):
                if k.strip():
                    c[k.strip()] += 1
    return c


def main():
    if not (HAU / "hau_letters.csv").exists():
        sys.exit("hau/hau_letters.csv not found")
    counts = raw_counts_from()
    manual = load_manual()
    m = build(counts, manual)
    with open(HAU / "keyword_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["raw", "clean", "rule", "letters"])
        for raw in sorted(m, key=lambda k: (-counts[k], k.lower())):
            w.writerow([raw, " | ".join(m[raw]), "manual" if raw in manual else "auto", counts[raw]])
    n_clean = len({c for v in m.values() for c in v})
    print(f"hau/keyword_map.csv: {len(m):,} raw keywords -> {n_clean:,} grouped ({len(manual)} manual)")


if __name__ == "__main__":
    main()
