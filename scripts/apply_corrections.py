"""
Fix known mistakes in HCD's dashboard tables, the same way every run.

    python3 scripts/apply_corrections.py hau   # hau/corrections.csv -> hau_letters.csv and letters_index.csv
    python3 scripts/apply_corrections.py he    # he_letters/corrections.csv -> letters.csv and letters_index.csv

The scrapers rewrite the tables from HCD's dashboards every run, so a hand edit would be lost. Each correction
names one letter, one column, the value HCD shows (old_value) and the right value (new_value):

  hau/corrections.csv         task,field,old_value,new_value,note
  he_letters/corrections.csv  jurisdiction,letter_date,type,field,old_value,new_value,note

A correction is applied only while the table still shows old_value. If HCD fixes its table (the value is
already new_value) nothing changes; if HCD now shows something else, the correction is skipped and reported,
so a stale fix never overwrites newer data. Changing a letter's link in letters_index.csv also clears its
text, so the next download fetches the right PDF (extract_letters.py).

Runs at the end of each folder's run_all.sh (after every dashboard pull) and at the start of
scripts/reparse_all.sh (Analysis). Never fails a job: problems are printed.
"""
import csv
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("HCD_ROOT") or Path(__file__).resolve().parent.parent)
SETUP = {
    # folder, corrections key columns -> table columns, tables, link column
    "hau": ("hau", {"task": "task"}, ["hau_letters.csv", "letters_index.csv"], "letter_url"),
    "he": ("he_letters", {"jurisdiction": "jurisdiction", "letter_date": "reviewed", "type": "type"},
           ["letters.csv", "letters_index.csv"], "weblink"),
}


def apply(which):
    folder, keymap, tables, link_col = SETUP[which]
    base = ROOT / folder
    cpath = base / "corrections.csv"
    if not cpath.exists():
        print(f"{folder}/corrections.csv: none")
        return
    fixes = [c for c in csv.DictReader(open(cpath, encoding="utf-8")) if (c.get("field") or "").strip()]
    for name in tables:
        p = base / name
        if not p.exists():
            continue
        with open(p, encoding="utf-8", newline="") as f:
            eol = "\r\n" if "\r\n" in f.readline() else "\n"   # keep the file's own line endings
            f.seek(0)
            rd = csv.DictReader(f)
            cols, rows = list(rd.fieldnames or []), list(rd)
        changed = 0
        for c in fixes:
            field = c["field"].strip()
            if field not in cols:
                continue
            hits = [r for r in rows if all((r.get(t) or "") == (c.get(k) or "").strip() for k, t in keymap.items())]
            label = " / ".join((c.get(k) or "").strip() for k in keymap) + f" {field}"
            if not hits:
                print(f"  {folder}/{name}: no letter matches {label} (correction not used)")
            for r in hits:
                cur, old, new = r.get(field) or "", c.get("old_value") or "", c.get("new_value") or ""
                if cur == new:
                    continue
                if cur != old:
                    print(f"  {folder}/{name}: {label} is now {cur!r}, not {old!r}; correction skipped (check HCD's table)")
                    continue
                r[field] = new
                changed += 1
                if field == link_col and "text_file" in cols:  # new PDF: drop the old text so it is downloaded again
                    r.update(text_file="", status="not_downloaded_yet", fetched_from="")
        if changed:
            with open(p, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=cols, lineterminator=eol)
                w.writeheader()
                w.writerows(rows)
        print(f"{folder}/{name}: {changed} correction(s) applied")


if __name__ == "__main__":
    for w in (sys.argv[1:] or ["hau", "he"]):
        apply(w)
