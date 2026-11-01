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
  site/data/requirements.json  Requirements tab: each 6th/7th-cycle review letter's round, compliance, kind,
                             requirements, issues and commitments (he_letters/letter_outcomes.csv), and programs
  site/data/language.json    Language tab: standard paragraph groups (*/patterns.json) and hashes of standard
                             sentences, so the letter reader can dim them
  site/data/citations.json   the citation strings that rows' "cites" lists point to (from */citations.csv)
  site/data/meta.json        build time, repo name, counts
Rows are arrays with value dictionaries to keep the files small; app.js unpacks them.
"""
import csv
from collections import Counter
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


def build_requirements():
    """Requirements tab: one row per 6th/7th-cycle review letter (he_letters/letter_outcomes.csv) + programs."""
    rows = read("he_letters/letter_outcomes.csv")
    if not rows:
        return None
    D = {k: Dict() for k in ("jur", "county", "type", "compliance", "kind", "req", "issue", "commit", "program", "category", "text")}
    split_ = lambda v: [x for x in (v or "").split(" | ") if x]
    out = []
    for r in rows:
        out.append([D["jur"](r["jurisdiction"]), D["county"](r["county"]), r["letter_date"], D["type"](r["type"]), r.get("cycle", "6"),
                    int(r["round"]), D["compliance"](r["compliance"]), D["kind"](r["kind"]),
                    [D["req"](x) for x in split_(r["requirements_specific"])], [D["issue"](x) for x in split_(r["issues_specific"])],
                    [D["commit"](x) for x in split_(r["commitments_specific"])], D["text"]("he_letters/" + r["text_file"]), int(r.get("specific_words") or 0)])
    progs = [[D["jur"](r["jurisdiction"]), r["letter_date"], r.get("cycle", "6"), D["program"](r["program"]), D["category"](r["category"]),
              D["text"]("he_letters/" + r["text_file"])] for r in read("he_letters/programs.csv")]
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from letter_requirements import REQ_LABELS
    except Exception:  # noqa: BLE001
        REQ_LABELS = {}
    return {"cols": ["jur", "county", "date", "type", "cycle", "round", "compliance", "kind", "reqs", "issues", "commits", "text", "words"],
            "dict": {k: d.values for k, d in D.items()}, "reqLabels": {k: REQ_LABELS.get(k, k) for k in D["req"].values},
            "rows": out, "programs": progs}


def sentence_key(sentence, names):
    """Must match sentenceKey() in site/app.js. Text is split into paragraphs at blank lines, then into sentences
    at ". ", "; " or ": " followed by a capital letter, an opening parenthesis or a bullet (same in app.js)."""
    k = sentence.lower()
    for n in names:
        n = (n or "").lower().replace(" county", "").strip()
        if len(n) > 2:
            k = k.replace(n, " ")
    k = re.sub(r"\b(city|county|town)('s|’s)?\b", " ", k)
    k = re.sub(r"[\d,]+(\.\d+)?", "#", k)
    k = re.sub(r"[^a-z#]+", " ", k).strip()
    return k if len(k) > 30 else None


def fnv1a(s):
    h = 0x811C9DC5
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def build_language(hau, he, min_letters=25):
    """Language tab: paragraph groups (*/patterns.json) and hashes of standard sentences (in min_letters+ letters)."""
    out = {"sources": {}}
    for src, folder, data, names_of in (("HE", "he_letters", he, lambda r, d: (d["jur"][r[1]], d["county"][r[2]])),
                                        ("HAU", "hau", hau, lambda r, d: (d["jur"][r[1]],))):
        pj = ROOT / folder / "patterns.json"
        pat = json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else None
        if pat:
            pat["letters"] = [f"{folder}/{t}" for t in pat["letters"]]
        ti = data["cols"].index("text")
        seen, count = set(), Counter()
        for r in data["rows"]:
            tf = r[ti]
            if not tf or tf in seen or not (ROOT / tf).exists():
                continue
            seen.add(tf)
            text = (ROOT / tf).read_text(encoding="utf-8", errors="replace")
            keys = {sentence_key(x, names_of(r, data["dict"])) for para in re.split(r"\n\s*\n", text)
                    for x in re.split(r"(?<=[.;:])\s+(?=[A-Z(•])", re.sub(r"\s+", " ", para).strip())}
            count.update(k for k in keys if k)
        std = sorted(format(fnv1a(k), "x") for k, n in count.items() if n >= min_letters)
        out["sources"][src] = {"patterns": pat, "standard": std, "letters": len(seen)}
    return out


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
    reqs, lang = build_requirements(), build_language(hau, he)
    for name, obj in (("hau", hau), ("he", he), ("compliance", comp), ("citations", cit), ("requirements", reqs),
                      ("language", lang), ("meta", meta)):
        if obj is None:
            continue
        p = OUT / f"{name}.json"
        p.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
        print(f"  {p.relative_to(ROOT)}: {p.stat().st_size / 1024:,.0f} KB")


if __name__ == "__main__":
    main()
