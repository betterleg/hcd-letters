"""
Compare this run's hau_letters.csv with the previous one and stop if something looks wrong.

    python3 scripts/compare_runs.py PREVIOUS.csv CURRENT.csv REPORT.md [hau|he]

hau (default): HAU letters table (hau_letters.csv), keyed by task.
he: housing element review letters table (letters.csv), keyed by the letter's PDF link, or by
    jurisdiction + date + type when there is no link.

- Fails (exit 1) if the letter count dropped by more than 5% or by more than 25 letters, which
  usually means HCD changed the dashboard and the saved query needs re-capturing; nothing is
  committed in that case.
- Writes REPORT.md: letters new since last run, and letters whose PDF became available.
- Prints "new=<n> newly_posted=<n>" for the workflow to read.
A missing PREVIOUS.csv (first run) counts every letter as new and skips the drop check.
"""
import csv
import sys
from pathlib import Path


PROFILE = "hau"


def norm(r):
    """Give both tables the same fields: key, letter_date, jurisdiction, letter_type, laws, letter_url, copy."""
    if PROFILE == "he":
        url = r.get("weblink", "")
        has_pdf = url.startswith("http")
        return {**r, "key": url if has_pdf else f"{r.get('jurisdiction')}|{r.get('reviewed')}|{r.get('type')}",
                "letter_date": r.get("reviewed", ""), "letter_type": r.get("type", ""),
                "housing_laws": f"cycle {r['cycle']}" if r.get("cycle") else "", "letter_url": url if has_pdf else "",
                "copy": "PDF" if has_pdf else "Contact HCD"}
    return {**r, "key": r["task"]}


def load(path):
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return None
    with open(p, encoding="utf-8") as f:
        return {n["key"]: n for n in map(norm, csv.DictReader(f))}


def esc(s):
    return (s or "").replace("|", "\\|").replace("\n", " ")


def row_md(r):
    link = f"[PDF]({r['letter_url']})" if r.get("letter_url", "").startswith("http") else "Contact HCD"
    laws = r.get("housing_laws") or r.get("housing_law") or ""
    return f"| {r.get('letter_date','')} | {esc(r.get('jurisdiction'))} | {esc(r.get('letter_type'))} | {esc(laws)} | {link} |"


def main(prev_path, cur_path, out_path):
    prev, cur = load(prev_path), load(cur_path)
    if cur is None:
        sys.exit(f"{cur_path} is missing or empty")
    if prev is not None:
        drop = len(prev) - len(cur)
        if drop > 25 or (prev and drop / len(prev) > 0.05):
            fix = ("node scrape_report.js --report hau --capture && node make_link_templates.js" if PROFILE == "hau"
                   else "node scrape_report.js --report letters --capture")
            print(f"ERROR: letters fell from {len(prev)} to {len(cur)}. The dashboard probably changed; re-capture with: {fix}")
            sys.exit(1)
    prev = prev or {}
    with open(cur_path, encoding="utf-8") as f:
        n_rows = sum(1 for _ in csv.DictReader(f))
    new = [cur[t] for t in cur if t not in prev]
    posted = [cur[t] for t in cur if t in prev and cur[t].get("copy") == "PDF" and prev[t].get("copy") != "PDF"]
    removed = [prev[t] for t in prev if t not in cur]
    key = lambda r: (r.get("letter_date") or "", r.get("jurisdiction") or "")
    title = "HCD housing element review letters" if PROFILE == "he" else "HCD HAU letters"
    lines = [f"# {title}: changes since last run", "",
             f"{n_rows:,} letters on the dashboard ({len(new)} new, {len(posted)} newly posted as PDF, {len(removed)} no longer listed).", ""]
    head = ["| Letter date | Jurisdiction | Letter type | " + ("Cycle" if PROFILE == "he" else "Housing law") + " | Copy |", "|---|---|---|---|---|"]
    if new:
        lines += ["## New letters", ""] + head + [row_md(r) for r in sorted(new, key=key, reverse=True)] + [""]
    if posted:
        lines += ["## PDF now available", ""] + head + [row_md(r) for r in sorted(posted, key=key, reverse=True)] + [""]
    if removed:
        lines += ["## No longer on the dashboard", ""] + head + [row_md(r) for r in sorted(removed, key=key, reverse=True)] + [""]
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"new={len(new)} newly_posted={len(posted)} removed={len(removed)}")


if __name__ == "__main__":
    if len(sys.argv) > 4:
        PROFILE = sys.argv[4]
    main(*sys.argv[1:4])
