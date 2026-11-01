"""
Stage 2b: merge the HAU letters table with its filter-only fields into one row per letter.

    python3 merge_hau.py        # reads hau.csv, hau_statutes.csv, hau_keywords.csv, hau_laws.csv
                                # writes hau_letters.csv

Added columns (values joined with " | ", sorted):
  housing_laws   every housing law tagged on the letter (the dashboard's Housing Law column
                 shows the case's laws as one comma-joined string; this is the clean list)
  statutes       every Statutory Reference tagged on the letter (e.g. 65583.2(c), 66300)
  keywords       every Keyword tagged on the letter
  n_statutes, n_keywords
  copy           "PDF" when the dashboard links a letter, else "Contact HCD"
Also prints checks: letters, tasks missing from the link tables, links to unknown tasks.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path


def read(path):
    if not Path(path).exists():
        sys.exit(f"ERROR: {path} not found. Run run_all.sh (or scrape + decode each report) first.")
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def links(path, col):
    out = defaultdict(set)
    for r in read(path):
        if r.get("task") and r.get(col):
            out[r["task"]].add(r[col].strip())
    return out


def main():
    letters = read("hau.csv")
    laws = links("hau_laws.csv", "housing_law")
    statutes = links("hau_statutes.csv", "statute")
    keywords = links("hau_keywords.csv", "keyword")
    tasks = {r["task"] for r in letters}
    cols = ["task", "case_number", "letter_date", "jurisdiction", "letter_type", "housing_laws", "statutes",
            "n_statutes", "keywords", "n_keywords", "copy", "letter_url", "hcd_letter", "housing_law"]
    with open("hau_letters.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in sorted(letters, key=lambda x: (x.get("letter_date") or "", x["task"]), reverse=True):
            t = r["task"]
            w.writerow({
                **{k: r.get(k, "") for k in ("task", "case_number", "letter_date", "jurisdiction", "letter_type", "letter_url", "hcd_letter", "housing_law")},
                "housing_laws": " | ".join(sorted(laws.get(t, []))),
                "statutes": " | ".join(sorted(statutes.get(t, []))),
                "n_statutes": len(statutes.get(t, [])),
                "keywords": " | ".join(sorted(keywords.get(t, []))),
                "n_keywords": len(keywords.get(t, [])),
                "copy": "PDF" if (r.get("letter_url") or "").startswith("http") else "Contact HCD",
            })
    pdf = sum(1 for r in letters if (r.get("letter_url") or "").startswith("http"))
    print(f"hau_letters.csv: {len(letters)} letters ({len(tasks)} unique tasks), {pdf} with a PDF link, {len(letters) - pdf} 'Contact HCD'")
    for name, d in (("housing laws", laws), ("statutes", statutes), ("keywords", keywords)):
        print(f"  {name}: {sum(len(v) for v in d.values())} tags on {len(tasks & set(d))} letters; "
              f"{len(tasks - set(d))} letters have none; {len(set(d) - tasks)} tags point to unknown tasks")


if __name__ == "__main__":
    main()
