"""
Milestones for each jurisdiction's housing element, from HCD's review letters (and the Download Tool).

    python3 scripts/letter_milestones.py      # -> he_letters/milestones.csv

Every review letter opens by saying what HCD reviewed and when it arrived. This script reads those dates and
records each one as a milestone, labeled by HCD's own wording:

  Submittal received for review   "received for review on July 2, 2025" (also "modifications received for
                                  review"). A new submittal: HCD's review period starts here.
  Revisions received              "along with revisions received on August 26, 2025", "technical modifications
                                  received on ...". Material sent during a review; it does not restart the
                                  review period, which still runs from the submittal.
  Other material received         "received on" / "received" without "for review" (resolutions, ordinances,
                                  correspondence). When a letter has no "received for review" date, its first
                                  "received" date is the submittal instead, as in parse_letters.py.
  Adopted                         "adopted on March 28, 2023".
  Posted for public review        "posted on the City's website on July 10, 2023".
  Meeting with HCD                "a telephone conversation on ...", "facilitated by a conversation on ...".
  Statutory due date              "the statutory deadline (October 15, 2021)", "housing element was due ...".
  HCD letter                      the letter itself, with its finding (In / Out).
  Posted on Download Tool         a document on HCD's Housing Element Download Tool (housing_elements.csv).

References to HCD's own earlier reviews ("described in HCD's May 3, 2023 review") are skipped: those letters
are milestones of their own.

milestones.csv columns: jurisdiction, county, cycle, date, event, detail, letter_date, letter_type, finding,
review_start, review_days, source, phrase. For a letter, review_start is the submittal it reviewed (the
latest "received for review" date, see parse_letters.py) and review_days counts from it, so revisions sent
during a review never change the review period.
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HE = ROOT / "he_letters"
sys.path.insert(0, str(HE))
from parse_letters import D, to_date  # noqa: E402

RX_DATE = re.compile(D, re.I)
RULES = [  # (event, regex on the words between the previous date and this one); first match wins
    ("Submittal received for review", r"received\s+for\s+review\s*(on\s*)?$"),
    ("HCD review (earlier letter)", r"(hcd['’]s|its|department['’]s)\s*$|(hcd['’]s|its)\s+review\s+(on\s*)?$|reviewed\s+(on\s*)?$|described\s+in\s+hcd"),
    ("Statutory due date", r"statutory\s+(deadline|due\s+date)[^.]{0,20}$|was\s+due\s*(on\s*)?$|due\s+(on|by)\s*$"),
    ("Meeting with HCD", r"conversations?\s+(on|with[^.]{0,60}on)\s*$|meetings?\s+(on|with[^.]{0,60}on)\s*$|call\s+on\s*$"),
    ("Posted for public review", r"posted[^.]{0,60}\s+on\s*$|made\s+available[^.]{0,60}on\s*$"),
    ("Revisions received", r"(revisions?|modifications?|amendments?|changes)[^.]{0,40}received\s*(on\s*)?$|(revisions?|modifications?)\s+(on\s*)?$|received\s+(additional\s+)?revisions?\s+on\s*$"),
    ("Adopted", r"adopted\s*(on\s*)?$"),
    ("Other material received", r"received\s*(on\s*)?$"),
]
RULES = [(e, re.compile(rx, re.I)) for e, rx in RULES]


def opening(text):
    flat = re.sub(r"\s+", " ", text)
    i = flat.lower().find("thank you for")
    return flat[i:i + 1800] if i >= 0 else flat[300:2100]


def events(text, letter_date):
    head = opening(text)
    out, seen, prev_end = [], set(), 0
    for m in RX_DATE.finditer(head):
        d = to_date(m.group(1))
        start, prev_end = max(prev_end, m.start() - 90), m.end()
        if not d:
            continue
        pre = head[start:m.start()]  # only the words since the previous date
        ev = next((e for e, rx in RULES if rx.search(pre)), None)
        if not ev or ev == "HCD review (earlier letter)":
            continue
        if ev != "Statutory due date" and letter_date and d > letter_date:
            continue  # can't have happened after the letter
        detail = ""
        if ev in ("Submittal received for review", "Revisions received", "Other material received", "Adopted"):
            w = re.search(r"(revised draft|draft|adopted|modifications?|technical modifications|revisions?|ordinance[^,.;]{0,30}|resolution[^,.;]{0,30}|amendments?|rezon\w*)[^,.;]{0,40}$",
                          pre, re.I)
            detail = w.group(1).strip() if w else ""
        key = (ev, d)
        if key in seen:
            continue
        seen.add(key)
        s = max(0, m.start() - 110)
        if s:  # start the quote at a word boundary
            sp = head.find(" ", s)
            s = sp + 1 if 0 <= sp < m.start() else s
        out.append({"event": ev, "date": d, "detail": detail, "phrase": ("…" if s else "") + head[s:m.end()].strip()})
    # Same rule as parse_letters.py: with no "received for review" date, the first "received" date is the submittal.
    if not any(e["event"] == "Submittal received for review" for e in out):
        other = [e for e in out if e["event"] == "Other material received"]
        if other:
            first = min(other, key=lambda e: e["date"])
            first["event"] = "Submittal received for review"
            first["detail"] = (first["detail"] + " " if first["detail"] else "") + "(letter says \"received\")"
    return out


def read(p):
    return list(csv.DictReader(open(p, encoding="utf-8"))) if p.exists() else []


def main():
    index = read(HE / "letters_index.csv")
    if not index:
        print("he_letters/letters_index.csv not found yet; skipping milestones.")
        return
    analysis = {(r["jurisdiction"], r["letter_date"], r.get("type", "")): r for r in read(HE / "letters_analysis.csv")}
    rows = []
    for r in index:
        a = analysis.get((r["jurisdiction"], r["reviewed"], r.get("type", "")), {})
        base = {"jurisdiction": r["jurisdiction"], "county": r.get("county", ""), "cycle": r.get("cycle", ""),
                "letter_date": r["reviewed"], "letter_type": r.get("type", ""), "finding": a.get("finding", "")}
        rows.append(dict(base, date=r["reviewed"], event="HCD letter",
                         detail=" · ".join(x for x in (r.get("type", ""), a.get("finding", "")) if x),
                         review_start=a.get("submittal_date", ""), review_days=a.get("review_days", ""),
                         source="letter" if r.get("status", "").startswith("downloaded") else "dashboard (no copy)",
                         phrase=""))
        tf = r.get("text_file", "")
        if r.get("status", "").startswith("downloaded") and tf and (HE / tf).exists():
            for e in events((HE / tf).read_text(encoding="utf-8", errors="replace"), r["reviewed"]):
                rows.append(dict(base, **e, review_start="", review_days="", source="letter text"))
    for h in read(HE / "housing_elements.csv"):
        if h.get("received_date"):
            rows.append({"jurisdiction": h.get("jurisdiction", ""), "county": h.get("county", ""),
                         "cycle": re.sub(r"\D", "", h.get("planning_period", ""))[:1], "date": h["received_date"],
                         "event": "Posted on Download Tool", "detail": h.get("type", ""), "letter_date": "", "letter_type": "",
                         "finding": "", "review_start": "", "review_days": "", "source": "Download Tool", "phrase": h.get("pdf_url", "")})
    rows.sort(key=lambda x: (x["jurisdiction"], x["date"], x["event"]))
    cols = ["jurisdiction", "county", "cycle", "date", "event", "detail", "letter_date", "letter_type", "finding",
            "review_start", "review_days", "source", "phrase"]
    with open(HE / "milestones.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    c = Counter(x["event"] for x in rows)
    print("he_letters/milestones.csv: " + ", ".join(f"{k} {v:,}" for k, v in c.most_common()))


if __name__ == "__main__":
    main()
