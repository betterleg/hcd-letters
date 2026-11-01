"""
Add letters you obtained from HCD by request (the "Contact HCD for a copy" letters) to the tracker.

Put the PDFs anywhere under requested/ and push. This script then, for each PDF:
  1. extracts its text (pdftotext; OCR with tesseract when the PDF is a scan),
  2. matches it to a dashboard row:
       HAU letters by task number (CSTASK...) or case number found in the file name or text;
       otherwise, either source, by jurisdiction + letter date (within 3 days),
  3. saves the text next to the public letters (hau/letters/ or he_letters/letters/) and marks
     that row in letters_index.csv as downloaded, fetched_from=requested_from_hcd, with a
     local_pdf link to the PDF in this repo,
  4. records the result in requested/manifest.csv and writes requested/README.md.

    python3 scripts/requested_letters.py              # both sources
    python3 scripts/requested_letters.py --only he    # after he_letters/extract_letters.py
    python3 scripts/requested_letters.py --only hau   # after hau/extract_letters.py

Run it AFTER extract_letters.py, which rewrites letters_index.csv from the dashboard each week;
this script then re-applies every requested letter on top.

requested/manifest.csv (one row per PDF; edit it to fix or force a match)
  file          path under requested/
  source        hau | he
  task          HAU task number (CSTASK...), for HAU letters
  jurisdiction  as spelled on the dashboard, for review letters
  letter_date   YYYY-MM-DD, as on the dashboard ("reviewed" date) for review letters
  type          review letters only, needed when a jurisdiction has two letters on one date
  match         auto | manual | needs_review | no_match | not_on_dashboard | ignore
  note          what the script found, or your note

To fix a match: fill in source + task (HAU) or source + jurisdiction + letter_date (+ type) and
set match=manual. The script never changes manual, not_on_dashboard or ignore rows; it retries
needs_review and no_match rows on every run (a letter may appear on the dashboard later).
Letters that are not on either dashboard: set match=not_on_dashboard; their text goes to
requested/text/ so GitHub search still finds it. Unmatched PDFs' text goes there too.
"""
import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQ = ROOT / "requested"
MANIFEST = REQ / "manifest.csv"
MCOLS = ["file", "source", "task", "jurisdiction", "letter_date", "type", "match", "note"]
FROZEN = {"manual", "not_on_dashboard", "ignore"}
SRC = {
    "hau": {"dir": ROOT / "hau", "label": "HAU letter"},
    "he": {"dir": ROOT / "he_letters", "label": "Housing element review letter"},
}
DATE_WINDOW = 3
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                       "september", "october", "november", "december"], 1)}
MONTHS.update({m[:3]: i for m, i in list(MONTHS.items())})
MONTHS["sept"] = 9


# ---------- text ----------
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pdftotext(p):
    r = subprocess.run(["pdftotext", "-layout", "-nopgbrk", str(p), "-"], capture_output=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[:200])
    return r.stdout.decode("utf-8", "replace")


def ocr(p, max_pages=80):
    if not (shutil.which("tesseract") and shutil.which("pdftoppm")):
        return ""
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["pdftoppm", "-r", "300", "-gray", "-png", "-l", str(max_pages), str(p), f"{td}/pg"],
                       capture_output=True, timeout=900)
        pages = []
        for img in sorted(Path(td).glob("pg*.png")):
            r = subprocess.run(["tesseract", str(img), "-", "--psm", "1"], capture_output=True, timeout=300)
            pages.append(r.stdout.decode("utf-8", "replace"))
        return "\n\n".join(pages)


def get_text(p):
    """(text, method). method: pdf_text | ocr | none"""
    try:
        t = pdftotext(p)
    except Exception:  # noqa: BLE001
        t = ""
    if len(re.sub(r"\s", "", t)) >= 200:
        return t, "pdf_text"
    o = ocr(p)
    if len(re.sub(r"\s", "", o)) > len(re.sub(r"\s", "", t)):
        return o, "ocr"
    return t, "pdf_text" if t.strip() else "none"


# ---------- clues ----------
def norm(s):
    s = (s or "").lower().replace("&", "and")
    s = re.sub(r"\b(city|town|county) of\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


def hay_norm(s):
    """Text normalized for finding jurisdiction names: 'County of San Diego' also reads as 'San Diego County'."""
    s = re.sub(r"County of ((?:[A-Z][a-z]+ ?){1,3})", lambda m: f"{m.group(0)} {m.group(1).strip()} County ", s)
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("&", "and"))


def mk(y, m, d):
    try:
        y = int(y)
        y = y + 2000 if y < 70 else (y + 1900 if y < 100 else y)
        return date(y, int(m), int(d))
    except (ValueError, TypeError):
        return None


def dates_in(s):
    """Dates in reading order: 'March 5, 2014', '3/5/2014', '2014-03-05'."""
    found = []
    for m in re.finditer(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})\b", s):
        mo = MONTHS.get(m.group(1).lower())
        if mo:
            found.append((m.start(), mk(m.group(3), mo, m.group(2))))
    for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", s):
        found.append((m.start(), mk(m.group(3), m.group(1), m.group(2))))
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", s):
        found.append((m.start(), mk(*m.groups())))
    return [d for _, d in sorted(found) if d and 1990 <= d.year <= 2100]


def filename_dates(stem):
    """HCD file names end in MMDDYY or MMDDYYYY (e.g. sbd-adelanto-draft-out-051024)."""
    out = dates_in(stem.replace("_", " "))
    for m in re.finditer(r"(?<!\d)(\d{2})(\d{2})(\d{2}|\d{4})(?!\d)", stem):
        d = mk(m.group(3), m.group(1), m.group(2))
        if d:
            out.append(d)
    return out


def iso(s):
    try:
        return date.fromisoformat((s or "")[:10])
    except ValueError:
        return None


# ---------- dashboard rows ----------
def read_csv(p):
    if not p.exists():
        return [], []
    with open(p, encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        return list(rd), list(rd.fieldnames or [])


def row_key(src, r):
    return r.get("task", "") if src == "hau" else f"{r.get('jurisdiction', '')}|{r.get('reviewed', '')}|{r.get('type', '')}"


def row_date(src, r):
    return iso(r.get("letter_date") if src == "hau" else r.get("reviewed"))


def find_rows(src, rows, m):
    """Rows a manifest entry points at."""
    if src == "hau":
        return [r for r in rows if m.get("task") and r.get("task") == m["task"].strip()]
    j, d, t = norm(m.get("jurisdiction")), (m.get("letter_date") or "").strip(), (m.get("type") or "").strip().lower()
    hits = [r for r in rows if norm(r.get("jurisdiction")) == j and r.get("reviewed") == d]
    if t:
        hits = [r for r in hits if (r.get("type") or "").lower() == t] or hits
    return hits


def without_text(r):
    return not (r.get("status", "").startswith("downloaded")) or r.get("fetched_from") == "requested_from_hcd"


def auto_match(pdf, text, pools, taken):
    """Returns (source, row, note) or (None, candidates, note)."""
    stem = pdf.stem
    head = text[:6000]
    hay = f"{stem} {pdf.parent.name}\n{head}"
    srcs = [s for s in pools if pdf.relative_to(REQ).parts[0].lower() in (s, "he_letters" if s == "he" else s)] or list(pools)

    # 1. HAU task / case number
    if "hau" in srcs:
        rows = pools["hau"]
        tasks = set(re.findall(r"CSTASK\d{5,9}", hay, re.I))
        hits = [r for r in rows if r.get("task", "").upper() in {t.upper() for t in tasks}]
        if not hits:
            toks = set(re.findall(r"\b[A-Z]{2,6}-?\d{5,9}\b", hay.upper()))
            toks |= {t.replace("-", "") for t in toks}
            hits = [r for r in rows if r.get("case_number") and r["case_number"].upper() in toks]
        hits = [r for r in hits if row_key("hau", r) not in taken]
        if len({r["task"] for r in hits}) == 1:
            how = "task number" if tasks else "case number"
            return "hau", hits[0], f"{how} in file name/text"

    # 2. jurisdiction + date
    fn_d = filename_dates(stem)
    tx_d = dates_in(text[:2500])[:4]
    want = fn_d + tx_d
    if not want:
        return None, [], "no letter date found in file name or first page"
    hay_n = hay_norm(hay)
    words = norm(stem.replace("-", " "))
    cands = []
    for s in srcs:
        for r in pools[s]:
            if row_key(s, r) in taken:
                continue
            j = norm(r.get("jurisdiction"))
            if len(j) < 4 or (j not in hay_n and j not in words):
                continue
            d = row_date(s, r)
            if not d:
                continue
            gap = min(abs((d - w).days) for w in want)
            if gap <= DATE_WINDOW:
                cands.append((gap, -len(j), s, r))
    if not cands:
        return None, [], f"no dashboard row for a jurisdiction named in it within {DATE_WINDOW} days of {want[0].isoformat()}"
    cands.sort(key=lambda c: (c[0], c[1]))
    best, seen = [], set()
    for c in cands:  # rows tied for best; identical duplicate rows on the dashboard count once
        if c[:2] == cands[0][:2] and (c[2], row_key(c[2], c[3])) not in seen:
            seen.add((c[2], row_key(c[2], c[3])))
            best.append(c)
    if len(best) > 1:
        # same jurisdiction + date, different type: try the type word in the text
        typed = [c for c in best if (c[3].get("type") or "").split()[0].lower() in hay.lower()]
        if len(typed) == 1:
            best = typed
    if len(best) == 1:
        g, _, s, r = best[0]
        return s, r, f"jurisdiction + date ({'same day' if g == 0 else f'{g} day(s) apart'})"
    return None, [(c[2], c[3]) for c in best[:5]], "several dashboard rows fit"


def describe(src, r):
    if src == "hau":
        return f"hau {r.get('task')} {r.get('jurisdiction')} {r.get('letter_date')} {r.get('letter_type', '')[:40]}"
    return f"he {r.get('jurisdiction')} {r.get('reviewed')} {r.get('type')}"


def safe(s, n=50):
    s = re.sub(r"[/\\:*?\"<>|]", "-", (s or "").strip())
    return re.sub(r"\s+", "_", s)[:n]


def text_name(src, r):
    keys = ("jurisdiction", "letter_type", "letter_date", "case_number") if src == "hau" else \
        ("county", "jurisdiction", "type", "cycle", "reviewed")
    return "_".join(safe(r.get(k, ""), 40) for k in keys if r.get(k)) + "__requested"


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=["hau", "he"], help="update only this source's letters_index.csv")
    a = ap.parse_args()
    if not shutil.which("pdftotext"):
        sys.exit("pdftotext not found (sudo apt-get install -y poppler-utils)")
    REQ.mkdir(exist_ok=True)
    pdfs = sorted(p for p in REQ.rglob("*") if p.suffix.lower() == ".pdf" and p.is_file())

    idx, fields = {}, {}
    for s, cfg in SRC.items():
        idx[s], fields[s] = read_csv(cfg["dir"] / "letters_index.csv")
    pools = {s: [r for r in idx[s] if without_text(r)] for s in SRC if idx[s]}
    man = {r["file"]: r for r in read_csv(MANIFEST)[0]}

    textdir = REQ / "text"
    results, taken = [], {}
    # frozen + auto rows first so they keep their claim on a dashboard row
    order = sorted(pdfs, key=lambda p: (man.get(p.relative_to(REQ).as_posix(), {}).get("match") not in FROZEN | {"auto"}, p.as_posix()))
    for pdf in order:
        rel = pdf.relative_to(REQ).as_posix()
        m = dict(man.get(rel) or {c: "" for c in MCOLS})
        m["file"] = rel
        if m.get("match") == "ignore":
            results.append((m, None, None, None))
            continue
        text, method = get_text(pdf)
        src, row = None, None
        if m.get("match") in ("manual", "auto") and m.get("source") in pools:
            hits = find_rows(m["source"], idx[m["source"]], m)
            if len(hits) == 1:
                src, row = m["source"], hits[0]
            elif m["match"] == "manual":
                m["note"] = f"manual entry matches {len(hits)} dashboard rows; check task / jurisdiction / letter_date / type"
            else:
                m["match"] = ""  # auto match no longer valid: retry below
        if not row and m.get("match") not in FROZEN:
            src, got, note = auto_match(pdf, text, pools, taken)
            if src:
                row = got
                m.update(source=src, match="auto", note=note, type="" if src == "hau" else got.get("type", ""),
                         task=got.get("task", "") if src == "hau" else "",
                         jurisdiction=got.get("jurisdiction", ""),
                         letter_date=got.get("letter_date" if src == "hau" else "reviewed", ""))
            else:
                m["match"] = "needs_review" if got else "no_match"
                m["note"] = note + ("" if not got else ": " + "; ".join(describe(s, r) for s, r in got))
        if row is not None:
            k = (src, row_key(src, row))
            if k in taken:
                m["match"], m["note"] = "needs_review", f"same dashboard row as {taken[k]}"
                src, row = None, None
            else:
                taken[k] = rel
        results.append((m, src, row, (text, method)))

    # write text + update indexes
    applied = {s: {} for s in SRC}
    textdir.mkdir(exist_ok=True)
    keep_loose = set()
    for m, src, row, tm in results:
        if tm is None:
            continue
        text, method = tm
        pdf = REQ / m["file"]
        meta = {"requested_pdf": f"requested/{m['file']}", "pdf_sha256": sha(pdf), "text_method": method,
                "text_chars": len(text), "text_empty": not text.strip(), "fetched_from": "requested_from_hcd",
                "match": m.get("match"), "match_note": m.get("note", "")}
        if row is not None:
            out = SRC[src]["dir"] / "letters"
            out.mkdir(exist_ok=True)
            name = text_name(src, row)
            meta.update({k: v for k, v in row.items() if k not in ("status", "fetched_from", "text_file", "error", "local_pdf")})
            dest = out / f"{name}.txt"
        else:
            dest = textdir / (Path(m["file"]).with_suffix("").as_posix().replace("/", "__") + ".txt")
            keep_loose.add(dest.name)
        old = dest.with_suffix(".json")
        if not (dest.exists() and old.exists() and json.loads(old.read_text()).get("pdf_sha256") == meta["pdf_sha256"]):
            dest.write_text(text, encoding="utf-8")
            old.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        if row is not None:
            applied[src][row_key(src, row)] = (dest.relative_to(SRC[src]["dir"]).as_posix(), meta)
    for f in textdir.glob("*"):  # drop loose text for PDFs that were removed or are now matched
        if f.with_suffix(".txt").name not in keep_loose:
            f.unlink()
    for s in SRC:  # drop matched text for PDFs that were removed or re-matched elsewhere
        live = {Path(tf).name for tf, _ in applied[s].values()}
        for f in (SRC[s]["dir"] / "letters").glob("*__requested.*"):
            if f.with_suffix(".txt").name not in live:
                f.unlink()

    for s in ([a.only] if a.only else list(SRC)):
        if not idx[s]:
            continue
        cols = fields[s] + (["local_pdf"] if "local_pdf" not in fields[s] else [])
        n = 0
        for r in idx[s]:
            hit = applied[s].get(row_key(s, r))
            if hit:
                tf, meta = hit
                r.update(status="downloaded_scanned" if meta["text_empty"] else "downloaded",
                         fetched_from="requested_from_hcd", text_file=tf, error="", local_pdf=meta["requested_pdf"])
                n += 1
            elif r.get("fetched_from") == "requested_from_hcd":  # PDF removed or re-matched
                r.update(status="contact_hcd", fetched_from="", text_file="", local_pdf="")
            else:
                r.setdefault("local_pdf", "")
        with open(SRC[s]["dir"] / "letters_index.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(idx[s])
        print(f"{s}: {n} requested letters applied to {SRC[s]['dir'].name}/letters_index.csv")

    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MCOLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted((m for m, *_ in results), key=lambda m: m["file"]))
    write_readme(results)
    tally = {}
    for m, *_ in results:
        tally[m.get("match") or "?"] = tally.get(m.get("match") or "?", 0) + 1
    print(f"{len(pdfs)} PDFs in requested/: " + ", ".join(f"{k} {v}" for k, v in sorted(tally.items())))


def write_readme(results):
    from urllib.parse import quote
    n = len(results)
    matched = sum(1 for _, s, r, _ in results if r is not None)
    review = [m for m, *_ in results if m.get("match") in ("needs_review", "no_match")]
    out = ["# Letters requested from HCD", "",
           "PDFs of letters that HCD's dashboards list as \"Contact HCD for a copy\", obtained by request. "
           "Each weekly job (and any push to this folder) extracts their text, matches them to the dashboard and adds them "
           "to the indexes and the website, marked *requested from HCD*. Instructions are at the bottom of this page.", "",
           f"**{n} PDFs**: {matched} matched to a dashboard letter, {len(review)} to check. "
           f"Updated {datetime.now().strftime('%Y-%m-%d')}.", ""]
    if review:
        out += ["## Need a look", "", "Fix these in [`manifest.csv`](manifest.csv) (see below).", "",
                "| File | Status | What the script found |", "|---|---|---|"]
        out += [f"| [{m['file']}]({quote(m['file'])}) | {m['match']} | {m.get('note', '').replace('|', '/')} |" for m in review]
        out.append("")
    out += ["## All requested letters", "", "| File | Source | Jurisdiction | Letter date | Type / task | Match | Text |", "|---|---|---|---|---|---|---|"]
    for m, s, r, tm in sorted(results, key=lambda x: (x[0].get("letter_date") or "", x[0]["file"]), reverse=True):
        src = {"hau": "HAU", "he": "Review"}.get(m.get("source"), "")
        txt = ""
        if r is not None:
            d = SRC[s]["dir"].name
            txt = f"[text](../{d}/letters/{quote(text_name(s, r))}.txt)"
        elif tm is not None:
            txt = f"[text](text/{quote(Path(m['file']).with_suffix('').as_posix().replace('/', '__'))}.txt)"
        out.append(f"| [{m['file']}]({quote(m['file'])}) | {src} | {m.get('jurisdiction', '')} | {m.get('letter_date', '')} | "
                   f"{m.get('task') or m.get('type', '')} | {m.get('match', '')} | {txt} |")
    out += ["", "## How to add letters", "",
            "1. Upload the PDFs into this folder: on GitHub, **Add file** → **Upload files**, or drag them into a codespace. "
            "Subfolders are fine; a `hau/` or `he/` subfolder tells the matcher which dashboard to look in.",
            "2. Commit. The **Requested letters** workflow runs on its own, matches each PDF, saves its text and rebuilds the website.",
            "3. Check **Need a look** above. File names that help the matcher: HCD's own (`sbd-adelanto-draft-out-051024.pdf`), "
            "or jurisdiction + date (`Adelanto 2014-03-05.pdf`). For HAU letters, the task number (`CSTASK0027569.pdf`).", "",
            "## Fixing a match in manifest.csv", "",
            "Edit the PDF's row and set `match` to `manual`:", "",
            "- **HAU letter:** `source` = `hau`, `task` = the CSTASK number from `hau/hau_letters.csv`.",
            "- **Review letter:** `source` = `he`, `jurisdiction` and `letter_date` exactly as in `he_letters/letters.csv` "
            "(`letter_date` is its `reviewed` date), plus `type` if that jurisdiction has two letters that day.",
            "- **Not on either dashboard:** `match` = `not_on_dashboard`. Its text stays in `text/` and is searchable.",
            "- **Skip a file:** `match` = `ignore`.", "",
            "This repo is public, so anything here is public. Letters HCD sends on request are public records; "
            "don't add anything with personal information you wouldn't post.", ""]
    (REQ / "README.md").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    main()
