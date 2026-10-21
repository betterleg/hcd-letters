"""
Stage 3: download the HAU letters listed in hau_letters.csv, extract text with pdftotext,
and keep only <out>/<name>.txt + <name>.json (the PDFs are never written to disk).

    python3 extract_letters.py --dry-run
    python3 extract_letters.py --law "Density Bonus" --max-rows 10        # smoke test
    python3 extract_letters.py                                           # all ~1,300 PDFs

Filters (repeatable; same flag = OR, different flags = AND)
  --law TEXT           housing law contains TEXT (matches the housing_laws list)
  --type TEXT          letter type contains TEXT (e.g. "Notice of Violation", "Technical Assistance")
  --statute TEXT       a tagged statutory reference contains TEXT (e.g. 65915, 66300)
  --keyword TEXT       a tagged keyword contains TEXT (e.g. parking)
  --jurisdiction J     exact match, case-insensitive
  --since YYYY-MM-DD   letter dated on or after this date
  --filter COL=VALUE   substring match on any CSV column

Other flags
  --csv PATH           default hau_letters.csv
  --url-column NAME    default letter_url
  --out DIR            default letters
  --index PATH         default letters_index.csv
  --max-rows N         cap the number of documents after filtering
  --concurrency N      parallel downloads, max 15 (default 6)
  --dry-run            list what would be fetched; download nothing
  --overrides PATH     corrected links for known-bad dashboard links (default url_overrides.csv)
  --no-fallback        don't try overrides

Letters the dashboard marks "Contact HCD for a copy" have no public PDF; they are counted and
listed in letters_index.csv as contact_hcd (request them from HAUportal@hcd.ca.gov).
A PDF listed under more than one letter is fetched once; its .json lists the others under
"also_listed_as". Resumable: existing .txt/.json pairs are skipped. Requires pdftotext.

After every run, letters_index.csv lists EVERY letter in the CSV (not just this run's filters)
with: all CSV columns + status + fetched_from + text_file + error. Status is one of
  downloaded / downloaded_scanned (no text layer: OCR candidate) / contact_hcd / failed /
  not_downloaded_yet / no_link
"""

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

TIMEOUT_S = 90
RETRIES = 2


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", default="hau_letters.csv")
    p.add_argument("--url-column", default="letter_url")
    for f in ("law", "type", "statute", "keyword", "jurisdiction", "filter"):
        p.add_argument(f"--{f}", action="append", default=[])
    p.add_argument("--since")
    p.add_argument("--out", default="letters")
    p.add_argument("--index", default="letters_index.csv")
    p.add_argument("--max-rows", type=int)
    p.add_argument("--concurrency", type=int, default=6)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-fallback", action="store_true")
    p.add_argument("--overrides", default="url_overrides.csv")
    a = p.parse_args()
    if a.concurrency > 15:
        print("Capping --concurrency at 15 to avoid Azure throttling.")
        a.concurrency = 15
    return a


def safe(s, n=50):
    s = re.sub(r"[/\\:*?\"<>|]", "-", (s or "").strip())
    return re.sub(r"\s+", "_", s)[:n]


def quote_url(u):
    """Percent-encode spaces etc. in the path (22 HCD links contain spaces)."""
    p = urllib.parse.urlsplit(u)
    return urllib.parse.urlunsplit((p.scheme, p.netloc, urllib.parse.quote(urllib.parse.unquote(p.path)), p.query, p.fragment))


def build_name(row, url):
    tail = Path(urllib.parse.unquote(urllib.parse.urlsplit(url).path)).stem
    parts = [row.get(k, "") for k in ("jurisdiction", "letter_type", "letter_date", "case_number")]
    return "_".join(safe(x, 40) for x in parts if x) + "__" + safe(tail, 60)


def link_of(row, col):
    u = (row.get(col) or "").strip()
    return u if re.match(r"https?://", u, re.I) else ""


def write_index(path, all_rows, cols, url_col, name_of, out, failures):
    """One row per letter in the full CSV with its status; reflects everything on disk."""
    counts = defaultdict(int)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols + ["status", "fetched_from", "text_file", "error"])
        for r in all_rows:
            u = link_of(r, url_col)
            text_file = err = via = ""
            if not u:
                raw = (r.get(url_col) or "").strip().lower()
                contact = raw.startswith("mailto:") or (r.get("hcd_letter") or "").strip().lower().startswith("contact hcd")
                status = "contact_hcd" if contact else "no_link"
            else:
                name = name_of[u]
                txt, meta = out / f"{name}.txt", out / f"{name}.json"
                if txt.exists() and meta.exists():
                    text_file = str(txt)
                    try:
                        m = json.loads(meta.read_text(encoding="utf-8"))
                        scanned, via = m.get("text_empty"), m.get("fetched_from", "dashboard_link")
                    except Exception:  # noqa: BLE001
                        scanned = False
                    status = "downloaded_scanned" if scanned else "downloaded"
                elif u in failures:
                    status, err = "failed", failures[u]
                else:
                    status = "not_downloaded_yet"
            counts[status] += 1
            w.writerow([r.get(c, "") for c in cols] + [status, via, text_file, err])
    return counts


def pdftotext(pdf):
    proc = subprocess.run(["pdftotext", "-layout", "-nopgbrk", "-", "-"], input=pdf, capture_output=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(f"pdftotext exit {proc.returncode}: {proc.stderr.decode('utf-8', 'replace')[:200]}")
    return proc.stdout.decode("utf-8", "replace")


def fetch(url):
    req = urllib.request.Request(quote_url(url), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        return r.read()


HCD_FALLBACK_DIRS = [
    ("hcd_website_fallback", "https://www.hcd.ca.gov/sites/default/files/docs/planning-and-community/housing-element/"),
    ("hcd_legacy_docs_fallback", "https://www.hcd.ca.gov/community-development/housing-element/docs/"),
]
USE_FALLBACK = True
OVERRIDES = {}  # dashboard weblink -> corrected URL, from url_overrides.csv


def load_overrides(path):
    """url_overrides.csv: weblink,replacement_url,note. For dashboard links whose file exists on
    HCD's site under a slightly different name (typo in the link). Add rows as you find them."""
    p = Path(path)
    if not p.exists():
        p = Path(__file__).with_name(Path(path).name)
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return {r["weblink"].strip(): r["replacement_url"].strip() for r in csv.DictReader(f) if r.get("weblink")}


def candidate_urls(url):
    """(label, url) pairs to try in order: manual override, dashboard link, then the same file
    name in HCD's two website folders. (2026-10: these recovered 98 of 102 blob 404s.)"""
    out = []
    if url in OVERRIDES:
        out.append(("url_override", OVERRIDES[url]))
    out.append(("dashboard_link", url))
    if USE_FALLBACK and "hcdpowerbi.blob.core.windows.net" in url:
        fname = urllib.parse.unquote(urllib.parse.urlsplit(url).path).rsplit("/", 1)[-1]
        out += [(label, d + fname) for label, d in HCD_FALLBACK_DIRS]
    return out


def fetch_pdf(url):
    """Returns PDF bytes, or raises. 404s and non-PDF responses are not retried."""
    err = None
    for attempt in range(RETRIES + 1):
        try:
            data = fetch(url)
            if not data.startswith(b"%PDF"):
                raise RuntimeError(f"not a PDF (starts {data[:20]!r})")
            return data
        except Exception as e:  # noqa: BLE001
            err = e
            if "not a PDF" in str(e) or "HTTP Error 404" in str(e):
                break
            time.sleep(1.0 * (attempt + 1))
    raise err


def process(job, out):
    name, url = job["name"], job["url"]
    txt, meta_p = out / f"{name}.txt", out / f"{name}.json"
    if txt.exists() and meta_p.exists():
        return {"name": name, "status": "skip"}
    errs = []
    for label, cand in candidate_urls(url):
        try:
            data = fetch_pdf(cand)
        except Exception as e:  # noqa: BLE001
            errs.append(f"{label}: {e!r}")
            continue
        try:
            text = pdftotext(data)
        except Exception as e:  # noqa: BLE001
            return {"name": name, "status": "error", "url": url, "error": repr(e)}
        tmp = txt.with_suffix(".txt.tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.rename(txt)
        meta = dict(job["rows"][0])
        meta.update(source_url=cand, fetched_from=label,
                    pdf_bytes=len(data), text_chars=len(text), text_empty=not text.strip())
        if len(job["rows"]) > 1:
            meta["also_listed_as"] = job["rows"][1:]
        tmp = meta_p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        tmp.rename(meta_p)
        return {"name": name, "status": "ok", "empty": meta["text_empty"], "fallback": label != "dashboard_link"}
    return {"name": name, "status": "error", "url": url, "error": " | ".join(errs)}


def main():
    a = parse_args()
    global USE_FALLBACK, OVERRIDES
    USE_FALLBACK = not a.no_fallback
    OVERRIDES = {} if a.no_fallback else load_overrides(a.overrides)
    if OVERRIDES:
        print(f"{len(OVERRIDES)} URL override(s) loaded")
    if not Path(a.csv).exists():
        sys.exit(f"ERROR: {a.csv} not found. Run bash run_all.sh first.")
    with open(a.csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cols = list(rows[0].keys()) if rows else []
    if a.url_column not in cols:
        sys.exit(f"Column {a.url_column!r} not in CSV. Columns: {', '.join(cols)}")
    print(f"{a.csv}: {len(rows)} rows")
    all_rows = rows
    # File names come from the first row listing each URL in the FULL csv, so a PDF listed
    # twice gets the same name whatever filters a run uses.
    name_of = {}
    for r in all_rows:
        u = link_of(r, a.url_column)
        if u and u not in name_of:
            name_of[u] = build_name(r, u)

    def has(col, wanted):
        w = [x.lower() for x in wanted]
        return lambda r: any(x in (r.get(col) or "").lower() for x in w)

    tests = []
    for flag, col in (("law", "housing_laws"), ("type", "letter_type"), ("statute", "statutes"), ("keyword", "keywords")):
        if getattr(a, flag):
            if col not in cols:
                sys.exit(f"--{flag} given but CSV has no {col!r} column")
            tests.append(has(col, getattr(a, flag)))
    if a.jurisdiction:
        js = {x.lower() for x in a.jurisdiction}
        tests.append(lambda r: (r.get("jurisdiction") or "").lower() in js)
    sub = defaultdict(list)
    for f in a.filter:
        if "=" not in f:
            sys.exit(f"--filter needs COL=VALUE, got {f!r}")
        k, v = f.split("=", 1)
        if k not in cols:
            sys.exit(f"Filter column {k!r} not in CSV. Columns: {', '.join(cols)}")
        sub[k].append(v.lower())
    for k, vs in sub.items():
        tests.append(lambda r, k=k, vs=vs: any(v in (r.get(k) or "").lower() for v in vs))
    if a.since:
        tests.append(lambda r: (r.get("letter_date") or "") >= a.since)
    rows = [r for r in rows if all(t(r) for t in tests)]

    by_url = OrderedDict()
    no_link = 0
    for r in rows:
        u = link_of(r, a.url_column)
        if not u:
            no_link += 1
            continue
        by_url.setdefault(u, []).append(r)
    jobs = [{"url": u, "rows": rs, "name": name_of[u]} for u, rs in by_url.items()]
    if a.max_rows:
        jobs = jobs[: a.max_rows]
    print(f"After filters: {len(rows)} rows -> {len(jobs)} downloadable letters "
          f"({no_link} rows have no public PDF ('Contact HCD for a copy'))")

    if a.dry_run:
        for j in jobs[:20]:
            print(f"  {j['name']}\n      {j['url']}")
        if len(jobs) > 20:
            print(f"  ... and {len(jobs) - 20} more")
        print("Hosts:", ", ".join(sorted({urllib.parse.urlsplit(j['url']).netloc for j in jobs})))
        return

    if not shutil.which("pdftotext"):
        sys.exit("ERROR: pdftotext not found. Install with: sudo apt-get install -y poppler-utils")
    out = Path(a.out)
    out.mkdir(exist_ok=True)
    start = time.time()
    ok = skip = fail = empty = fallback = 0
    errors, empties = [], []
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        futs = [ex.submit(process, j, out) for j in jobs]
        for i, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            if r["status"] == "ok":
                ok += 1
                fallback += r.get("fallback", False)
                if r["empty"]:
                    empty += 1
                    empties.append(r["name"])
            elif r["status"] == "skip":
                skip += 1
            else:
                fail += 1
                errors.append(r)
            if i % 25 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)} ok={ok} skip={skip} fail={fail} empty={empty} {time.time() - start:.0f}s")
    if errors:
        Path("letters_errors.log").write_text("\n".join(f"{e['error']}\t{e['name']}\t{e['url']}" for e in errors), encoding="utf-8")
        print(f"{len(errors)} failures -> letters_errors.log")
    if empties:
        Path("letters_empty.log").write_text("\n".join(empties), encoding="utf-8")
        print(f"{len(empties)} scanned/empty PDFs -> letters_empty.log (OCR candidates)")
    print(f"\nDone. ok={ok} (of which {fallback} via fallback/override) skipped={skip} failed={fail} empty={empty}. Output: {out}/")
    counts = write_index(Path(a.index), all_rows, cols, a.url_column, name_of, out,
                         {e["url"]: e["error"] for e in errors})
    print(f"Index of all {len(all_rows)} letters -> {a.index}: "
          + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))


if __name__ == "__main__":
    main()
