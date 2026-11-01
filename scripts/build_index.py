"""
Build browsable Markdown indexes of the letters for GitHub.

    python3 scripts/build_index.py hau

Writes, under hau/:
  LETTERS.md               counts by year, letter type and housing law, with links to each year
  index/<year>.md          every letter that year: date, jurisdiction, type, laws, statutes,
                           links to the letter's text in this repo and to HCD's PDF
Reads hau_letters.csv and letters_index.csv (for text_file and status).
"""
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote


def esc(s):
    return (s or "").replace("|", "\\|").replace("\n", " ")


def main(root):
    root = Path(root)
    letters = list(csv.DictReader(open(root / "hau_letters.csv", encoding="utf-8")))
    idx = {}
    p = root / "letters_index.csv"
    if p.exists():
        idx = {r["task"]: r for r in csv.DictReader(open(p, encoding="utf-8"))}
    by_year = defaultdict(list)
    for r in letters:
        by_year[(r.get("letter_date") or "")[:4] or "undated"].append(r)
    (root / "index").mkdir(exist_ok=True)
    for year, rows in by_year.items():
        out = [f"# HAU letters, {year}", "", f"{len(rows)} letters. [All years](../LETTERS.md)", "",
               "| Date | Jurisdiction | Letter type | Housing law | Statutes | Text | HCD PDF |", "|---|---|---|---|---|---|---|"]
        for r in sorted(rows, key=lambda x: (x.get("letter_date") or "", x.get("jurisdiction") or ""), reverse=True):
            i = idx.get(r["task"], {})
            tf = i.get("text_file", "")
            text = f"[text](../{quote(tf)})" if tf else {"contact_hcd": "not public", "failed": "PDF missing"}.get(i.get("status", ""), "")
            pdf = (f"[PDF]({r['letter_url']})" if (r.get("letter_url") or "").startswith("http")
                   else f"[PDF](../../{quote(i['local_pdf'])}) (requested)" if i.get("local_pdf") else "Contact HCD")
            st = r.get("statutes", "")
            st = st if len(st) <= 80 else st[:77] + "…"
            out.append(f"| {r.get('letter_date','')} | {esc(r.get('jurisdiction'))} | {esc(r.get('letter_type'))} | "
                       f"{esc(r.get('housing_laws') or r.get('housing_law'))} | {esc(st)} | {text} | {pdf} |")
        (root / "index" / f"{year}.md").write_text("\n".join(out) + "\n", encoding="utf-8")

    with_text = sum(1 for r in letters if idx.get(r["task"], {}).get("text_file"))
    top = lambda col, n: Counter(x.strip() for r in letters for x in (r.get(col) or "").split(" | ") if x.strip()).most_common(n)
    out = ["# HCD Technical Assistance and Enforcement Letters", "",
           f"{len(letters):,} letters from HCD's Housing Accountability Unit, from the "
           "[Technical Assistance and Enforcement Letters Dashboard](https://www.hcd.ca.gov/hau/enforcement-letters). "
           f"{with_text:,} have their full text in [`letters/`](letters/). Updated automatically; see "
           "[CHANGES.md](CHANGES.md) for what changed in the latest run.", "",
           "Search the text with GitHub's search box (\"In this repository\"), e.g. `65915 path:hau/letters`.", "",
           "## By year", "", "| Year | Letters |", "|---|---|"]
    for y in sorted(by_year, reverse=True):
        out.append(f"| [{y}](index/{y}.md) | {len(by_year[y])} |")
    out += ["", "## By letter type", "", "| Letter type | Letters |", "|---|---|"]
    out += [f"| {esc(k)} | {v} |" for k, v in Counter(r.get("letter_type") or "(none)" for r in letters).most_common()]
    out += ["", "## By housing law", "", "| Housing law | Letters |", "|---|---|"]
    out += [f"| {esc(k)} | {v} |" for k, v in top("housing_laws", 30)]
    out += ["", "## Most-cited statutes", "", "| Statute | Letters |", "|---|---|"]
    out += [f"| {esc(k)} | {v} |" for k, v in top("statutes", 25)]
    (root / "LETTERS.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"LETTERS.md + {len(by_year)} year pages; {with_text} letters with text")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "hau")
