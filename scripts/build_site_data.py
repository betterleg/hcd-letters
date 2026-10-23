"""
Build the JSON the web page reads, from the CSVs both jobs keep in this repo.

    python3 scripts/build_site_data.py            # writes site/data/*.json

Inputs (whatever exists; a missing file just leaves that part of the page empty):
  hau/hau_letters.csv, hau/letters_index.csv
  he_letters/letters_analysis.csv, he_letters/letters_index.csv, he_letters/compliance.csv
  (letters_index.csv rows with local_pdf are letters requested from HCD; see scripts/requested_letters.py)
Outputs:
  site/data/hau.json         one row per HAU letter
  site/data/he.json          one row per housing element review letter
  site/data/compliance.json  current status per jurisdiction (Review and Compliance Report)
  site/data/citations.json   the citation strings that rows' "cites" lists point to (from */citations.csv)
  site/data/meta.json        build time, repo name, counts
Rows are arrays with value dictionaries to keep the files small; app.js unpacks them.
"""
import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("HCD_ROOT") or Path(__file__).resolve().parent.parent)
OUT = ROOT / "site" / "data"

# Same place, different spellings across HCD's three dashboards.
ALIASES = {
    "sanbuenaventura": "ventura", "cathedralcity": "cathedral", "sanluisobispoco": "sanluisobispocounty",
    "ranchostmargarita": "ranchosantamargarita", "sthelena": "sainthelena", "amadorcity": "amador",
    "carmelbythesea": "carmel", "lacanadaflintridge": "lacanadaflintridge", "venturacity": "ventura",
}


def jkey(name):
    k = re.sub(r"[^a-z]", "", (name or "").lower().replace("city of ", "").replace("town of ", ""))
    return ALIASES.get(k, k)


def read(path):
    p = ROOT / path
    if not p.exists():
        print(f"  (skipping {path}: not found)")
        return []
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


class Dict:
    """Value dictionary: store each distinct string once, rows hold its index."""
    def __init__(self):
        self.values, self.ix = [], {}

    def __call__(self, v):
        v = (v or "").strip()
        if v not in self.ix:
            self.ix[v] = len(self.values)
            self.values.append(v)
        return self.ix[v]


def split(v):
    return [x.strip() for x in (v or "").split(" | ") if x.strip()]


CITE = Dict()  # normalized statute citations shared by both letter sets (scripts/parse_citations.py)


def load_cites():
    """text path (as used in the site, e.g. he_letters/letters/x.txt) -> [citation index, ...]"""
    out = {}
    for folder in ("hau", "he_letters"):
        for r in read(f"{folder}/citations.csv"):
            out.setdefault(f"{folder}/{r['text_file']}", []).append(CITE(r["normalized"]))
    return out


def keyword_cleaner():
    """raw HCD keyword -> [grouped keywords], from hau/keyword_map.csv (scripts/clean_keywords.py)."""
    rows = read("hau/keyword_map.csv")
    if rows:
        return {r["raw"]: [x for x in r["clean"].split(" | ") if x] for r in rows}
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import clean_keywords
        return clean_keywords.build(clean_keywords.raw_counts_from(ROOT / "hau" / "hau_letters.csv"), {})
    except Exception:  # noqa: BLE001
        return {}


def type_group(t):
    t = (t or "").lower()
    if "technical assistance" in t:
        return "Technical assistance"
    if any(s in t for s in ("inquiry", "violation", "noncompliance", "decertification")):
        return "Enforcement"
    if "ordinance" in t or "findings letter" in t:
        return "Ordinance review"
    if any(s in t for s in ("successful completion", "recertification", "support", "determination")):
        return "Resolution & support"
    return "Other"


def build_hau(cites):
    rows = read("hau/hau_letters.csv")
    kw = keyword_cleaner()
    variants = {}
    idx = read("hau/letters_index.csv")
    text = {r["task"]: r.get("text_file", "") for r in idx if r.get("status", "").startswith("downloaded")}
    req = {r["task"]: r["local_pdf"] for r in idx if r.get("local_pdf")}  # PDFs requested from HCD, in requested/
    D = {k: Dict() for k in ("jur", "type", "law", "statute", "keyword")}
    out = []
    for r in rows:
        tf = text.get(r["task"], "")
        out.append([
            r.get("letter_date", ""), D["jur"](r.get("jurisdiction")), D["type"](r.get("letter_type")),
            [D["law"](x) for x in split(r.get("housing_laws"))], [D["statute"](x) for x in split(r.get("statutes"))],
            sorted({D["keyword"](c) for x in split(r.get("keywords")) for c in kw.get(x, [x])}),
            r.get("letter_url", "") if (r.get("letter_url") or "").startswith("http") else "",
            ("hau/" + tf) if tf else "", r.get("case_number", ""), r["task"], req.get(r["task"], ""),
            cites.get("hau/" + tf, []) if tf else [],
        ])
        for x in split(r.get("keywords")):
            for c in kw.get(x, [x]):
                if c != x:
                    variants.setdefault(c, set()).add(x)
    groups = {t: type_group(t) for t in D["type"].values}
    return {
        "cols": ["date", "jur", "type", "laws", "statutes", "keywords", "pdf", "text", "case", "task", "req", "cites"],
        "dict": {k: d.values for k, d in D.items()}, "typeGroup": groups,
        "keywordVariants": {k: sorted(v) for k, v in variants.items()},
        "jurKey": [jkey(j) for j in D["jur"].values], "rows": out,
    }


def build_he(cites):
    rows = read("he_letters/letters_analysis.csv")
    text, req = {}, {}
    for r in read("he_letters/letters_index.csv"):
        if r.get("status", "").startswith("downloaded"):
            text[(r["jurisdiction"], r["reviewed"], r["weblink"])] = r.get("text_file", "")
        if r.get("local_pdf"):  # requested from HCD: no public link, so key on jurisdiction + date + type
            req[(r["jurisdiction"], r["reviewed"], r["type"])] = (r.get("text_file", ""), r["local_pdf"])
    D = {k: Dict() for k in ("jur", "county", "type", "heType")}
    out = []
    for r in rows:
        pdf = r.get("pdf_url", "") if (r.get("pdf_url") or "").startswith("http") else ""
        tf = text.get((r["jurisdiction"], r["letter_date"], pdf), "") if pdf else ""
        rq = "" if pdf else req.get((r["jurisdiction"], r["letter_date"], r.get("type", "")), ("", ""))
        if rq:
            tf, rq = rq
        days = r.get("review_days", "")
        out.append([
            r.get("letter_date", ""), D["jur"](r.get("jurisdiction")), D["county"](r.get("county")), D["type"](r.get("type")),
            r.get("cycle", ""), r.get("finding", "") if r.get("finding") in ("In", "Out") else "",
            r.get("submittal_date", ""), int(days) if days.lstrip("-").isdigit() else None, pdf,
            ("he_letters/" + tf) if tf else "", r.get("he_pdf_url", ""), D["heType"](r.get("he_type")),
            "contact" if r.get("status") == "contact_hcd" and not rq else "", rq,
            cites.get("he_letters/" + tf, []) if tf else [],
        ])
    return {
        "cols": ["date", "jur", "county", "type", "cycle", "finding", "submittal", "days", "pdf", "text", "hePdf", "heType", "contact", "req", "cites"],
        "dict": {k: d.values for k, d in D.items()}, "jurKey": [jkey(j) for j in D["jur"].values], "rows": out,
    }


def build_compliance():
    rows = read("he_letters/compliance.csv")
    return {
        "cols": ["county", "jurisdiction", "cycle", "recordType", "reviewStatus", "received", "reviewed", "status", "jurKey"],
        "rows": [[r.get("county", ""), r.get("jurisdiction", "").title(), r.get("planning_period", ""),
                  r.get("record_type", ""), r.get("review_status", ""), r.get("date_received", ""), r.get("date_reviewed", ""),
                  r.get("compliance_status", "") or "Not listed", jkey(r.get("jurisdiction"))] for r in rows],
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cites = load_cites()
    hau, he, comp = build_hau(cites), build_he(cites), build_compliance()
    cit = {"dict": CITE.values}
    meta = {
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": os.environ.get("GITHUB_REPOSITORY", "betterleg/hcd-letters"),
        "counts": {"hau": len(hau["rows"]), "he": len(he["rows"]), "compliance": len(comp["rows"])},
    }
    for name, obj in (("hau", hau), ("he", he), ("compliance", comp), ("citations", cit), ("meta", meta)):
        p = OUT / f"{name}.json"
        p.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
        print(f"  {p.relative_to(ROOT)}: {p.stat().st_size / 1024:,.0f} KB")


if __name__ == "__main__":
    main()
