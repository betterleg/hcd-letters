"""
Build the JSON the web page reads, from the CSVs both jobs keep in this repo.

    python3 scripts/build_site_data.py            # writes site/data/*.json

Inputs (whatever exists; a missing file just leaves that part of the page empty):
  hau/hau_letters.csv, hau/letters_index.csv
  he_letters/letters_analysis.csv, he_letters/letters_index.csv, he_letters/compliance.csv
Outputs:
  site/data/hau.json         one row per HAU letter
  site/data/he.json          one row per housing element review letter
  site/data/compliance.json  current status per jurisdiction (Review and Compliance Report)
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


def build_hau():
    rows = read("hau/hau_letters.csv")
    text = {r["task"]: r.get("text_file", "") for r in read("hau/letters_index.csv") if r.get("status", "").startswith("downloaded")}
    D = {k: Dict() for k in ("jur", "type", "law", "statute", "keyword")}
    out = []
    for r in rows:
        tf = text.get(r["task"], "")
        out.append([
            r.get("letter_date", ""), D["jur"](r.get("jurisdiction")), D["type"](r.get("letter_type")),
            [D["law"](x) for x in split(r.get("housing_laws"))], [D["statute"](x) for x in split(r.get("statutes"))],
            [D["keyword"](x) for x in split(r.get("keywords"))], r.get("letter_url", "") if (r.get("letter_url") or "").startswith("http") else "",
            ("hau/" + tf) if tf else "", r.get("case_number", ""), r["task"],
        ])
    groups = {t: type_group(t) for t in D["type"].values}
    return {
        "cols": ["date", "jur", "type", "laws", "statutes", "keywords", "pdf", "text", "case", "task"],
        "dict": {k: d.values for k, d in D.items()}, "typeGroup": groups,
        "jurKey": [jkey(j) for j in D["jur"].values], "rows": out,
    }


def build_he():
    rows = read("he_letters/letters_analysis.csv")
    text = {}
    for r in read("he_letters/letters_index.csv"):
        if r.get("status", "").startswith("downloaded"):
            text[(r["jurisdiction"], r["reviewed"], r["weblink"])] = r.get("text_file", "")
    D = {k: Dict() for k in ("jur", "county", "type", "heType")}
    out = []
    for r in rows:
        pdf = r.get("pdf_url", "") if (r.get("pdf_url") or "").startswith("http") else ""
        tf = text.get((r["jurisdiction"], r["letter_date"], pdf), "") if pdf else ""
        days = r.get("review_days", "")
        out.append([
            r.get("letter_date", ""), D["jur"](r.get("jurisdiction")), D["county"](r.get("county")), D["type"](r.get("type")),
            r.get("cycle", ""), r.get("finding", "") if r.get("finding") in ("In", "Out") else "",
            r.get("submittal_date", ""), int(days) if days.lstrip("-").isdigit() else None, pdf,
            ("he_letters/" + tf) if tf else "", r.get("he_pdf_url", ""), D["heType"](r.get("he_type")),
            "contact" if r.get("status") == "contact_hcd" else "",
        ])
    return {
        "cols": ["date", "jur", "county", "type", "cycle", "finding", "submittal", "days", "pdf", "text", "hePdf", "heType", "contact"],
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
    hau, he, comp = build_hau(), build_he(), build_compliance()
    meta = {
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": os.environ.get("GITHUB_REPOSITORY", "betterleg/hcd-letters"),
        "counts": {"hau": len(hau["rows"]), "he": len(he["rows"]), "compliance": len(comp["rows"])},
    }
    for name, obj in (("hau", hau), ("he", he), ("compliance", comp), ("meta", meta)):
        p = OUT / f"{name}.json"
        p.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
        print(f"  {p.relative_to(ROOT)}: {p.stat().st_size / 1024:,.0f} KB")


if __name__ == "__main__":
    main()
