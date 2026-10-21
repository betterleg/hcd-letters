"""
Build browsable Markdown indexes of the housing element review letters for GitHub.

    python3 scripts/build_he_index.py he_letters

Reads he_letters/letters_analysis.csv (from link_submittals.py) and letters_index.csv.
Writes he_letters/LETTERS.md (counts and links) and he_letters/index/<year>.md (every letter
that year: jurisdiction, type, cycle, HCD finding, submittal date, days to letter, links to the
letter's text in this repo, HCD's PDF and the housing element it reviewed).
"""
import csv
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote


def esc(s):
    return (s or "").replace("|", "\\|").replace("\n", " ")


def main(root):
    root = Path(root)
    rows = list(csv.DictReader(open(root / "letters_analysis.csv", encoding="utf-8")))
    text_of = {}
    p = root / "letters_index.csv"
    if p.exists():
        for r in csv.DictReader(open(p, encoding="utf-8")):
            text_of[(r["jurisdiction"], r["reviewed"], r["weblink"])] = r.get("text_file", "")
    by_year = defaultdict(list)
    for r in rows:
        by_year[(r.get("letter_date") or "undated")[:4]].append(r)
    (root / "index").mkdir(exist_ok=True)
    for year, rs in by_year.items():
        out = [f"# Housing element review letters, {year}", "", f"{len(rs)} letters. [All years](../LETTERS.md)", "",
               "| Date | Jurisdiction | Type | Cycle | Finding | Submittal | Days | Text | Letter | Element reviewed |",
               "|---|---|---|---|---|---|---|---|---|---|"]
        for r in sorted(rs, key=lambda x: (x.get("letter_date") or "", x.get("jurisdiction") or ""), reverse=True):
            tf = text_of.get((r["jurisdiction"], r["letter_date"], r.get("pdf_url") or r.get("weblink", "")), "")
            if not tf and r.get("pdf_url"):
                tf = text_of.get((r["jurisdiction"], r["letter_date"], r["pdf_url"]), "")
            text = f"[text](../{quote(tf)})" if tf else ("not public" if r.get("status") == "contact_hcd" else "")
            pdf = f"[PDF]({r['pdf_url']})" if (r.get("pdf_url") or "").startswith("http") else "Contact HCD"
            he = f"[{esc(r.get('he_type'))}]({r['he_pdf_url']})" if (r.get("he_pdf_url") or "").startswith("http") else ""
            out.append(f"| {r.get('letter_date','')} | {esc(r.get('jurisdiction'))} | {esc(r.get('type'))} | {r.get('cycle','')} | "
                       f"{r.get('finding','')} | {r.get('submittal_date','')} | {r.get('review_days','')} | {text} | {pdf} | {he} |")
        (root / "index" / f"{year}.md").write_text("\n".join(out) + "\n", encoding="utf-8")

    with_text = sum(1 for r in rows if r.get("status") == "downloaded")
    days = [int(r["review_days"]) for r in rows if (r.get("review_days") or "").strip().lstrip("-").isdigit()]
    found = Counter(r["finding"] for r in rows if r.get("finding") in ("In", "Out"))
    out = ["# HCD housing element review letters", "",
           f"{len(rows):,} review letters from HCD's [Housing Element Download Tool](https://www.hcd.ca.gov/housing-open-data-tools/housing-element-download-tool) "
           f"review-letter page. {with_text:,} have their full text in [`letters/`](letters/); "
           f"{sum(1 for r in rows if r.get('status') == 'contact_hcd'):,} are listed as \"Contact HCD\" with no public copy. "
           "Updated automatically; see [CHANGES.md](CHANGES.md) for the latest run.", "",
           "Search the text with GitHub's search box (\"In this repository\"), e.g. `\"sites inventory\" path:he_letters/letters`.", "",
           f"Of letters with a finding, HCD found {found['Out']:,} out of compliance and {found['In']:,} in compliance. "
           + (f"Median {statistics.median(days):.0f} days from submittal to letter." if days else ""), "",
           "Finding: HCD's in/out label in the letter's file name, else wording in the letter. "
           "Submittal date: the \"received for review\" date stated in the letter, else the matching submittal on the Download Tool.", "",
           "## By year", "", "| Year | Letters |", "|---|---|"]
    out += [f"| [{y}](index/{y}.md) | {len(by_year[y])} |" for y in sorted(by_year, reverse=True)]
    out += ["", "## By submittal type", "", "| Type | Letters |", "|---|---|"]
    out += [f"| {esc(k)} | {v} |" for k, v in Counter(r.get("type") or "(none)" for r in rows).most_common()]
    out += ["", "## By cycle", "", "| Cycle | Letters |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in Counter(r.get("cycle") or "(not listed)" for r in rows).most_common()]
    (root / "LETTERS.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"LETTERS.md + {len(by_year)} year pages; {with_text} letters with text")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "he_letters")
