"""
Each jurisdiction's path through a housing element cycle (6th and 7th): first submittal, adoption, HCD's
finding of compliance, and how long each step took.

    python3 scripts/cycle_pathways.py      # -> he_letters/pathways.csv

One row per jurisdiction and cycle, from the review letters (letters_analysis.csv, milestones.csv), the Download
Tool (housing_elements.csv) and HCD's Review and Compliance Report (compliance.csv):

  first_submittal    the earliest submittal of the cycle: the first Download Tool document, or the first submittal a
                     letter names (whichever is earlier)
  adopted_date       the first adoption on or after the first submittal: the earlier of the adoption date a letter
                     states ("adopted on March 28, 2023") and the date HCD received the first adopted element (Tool;
                     a Tool document labeled adopted whose file name says draft is not counted)
  compliant_date     the first HCD letter finding an adopted element in compliance; else, when HCD's report shows
                     an adopted element reviewed "In" for that cycle, the report's review date (the report's
                     compliance_status alone isn't used: during a 7th-cycle draft it reflects the 6th-cycle element)
  days_to_adoption, days_to_compliance, days_adoption_to_compliance   between those dates
  statutory_due_date the due date the letters state most often for that cycle, else the region's (COG/MPO
                     deadlines generally follow county lines: the date most common in the county; due_source: letters or region); days_late = compliant_date - due
  submittals, hcd_letters, out_letters, in_letters   counts within the cycle
  submittal_dates    the cycle's submittals (Download Tool documents, else the submittals the letters name)
  path               HCD's letters in order: D (draft) or A (adopted) with the finding, e.g. "D-Out > D-Out > A-In"
                     ("?" when the finding is unknown, mostly "Contact HCD" letters with no public copy);
                     path_dates gives each letter's date; unknown_findings counts the "?"s. A jurisdiction whose
                     letters are unknown can have no compliant_date even if HCD found it in compliance.
  exposure_windows   periods without a housing element HCD has found in compliance, when the builder's remedy can
                     apply: "start..end reason" (after the statutory deadline / decertified), "; "-separated, no end = ongoing
  exposure_days      their total length (ongoing periods counted to today); exposed_now: yes/no
  within_120_days    found in compliance within 120 days after the due date (Gov. Code 65588(e)(4));
                     rezone_deadline: one year after the due date when it wasn't (AB 1398, 120 days ending 2022+)
  status_now         HCD's report today for that cycle: compliance_status (In, Out, ...); report_status is its
                     record type / review status. Blank when the report has no row (it lists only the current cycle)

A letter's cycle is cycle_from_tool when link_submittals.py set it (HCD's label disagreed with the submittal it
names), else HCD's label. Letters that review no submittal (no_submittal_reviewed) are left out of the path.
"""
import csv
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HE = ROOT / "he_letters"
sys.path.insert(0, str(ROOT / "scripts"))
from build_site_data import jkey  # noqa: E402

CYCLES = ("6", "7")
DUE_RANGE = {"6": ("2018-01-01", "2024-12-31"), "7": ("2024-01-01", "2034-12-31")}  # plausible statutory due dates
ADOPT = re.compile(r"ad+opt", re.I)
DRAFT = re.compile(r"draft", re.I)


def d(s):
    try:
        return date.fromisoformat((s or "")[:10]) if s else None
    except ValueError:
        return None


def read(name):
    p = HE / name
    return list(csv.DictReader(open(p, encoding="utf-8"))) if p.exists() else []


def cycle_of(r):
    return (r.get("cycle_from_tool") or r.get("cycle") or "").strip()


def token(r):
    t = r.get("type") or ""
    kind = "A" if ADOPT.search(t) else "D" if DRAFT.search(t) else "O"
    f = r.get("finding") if r.get("finding") in ("In", "Out") else "?"
    return f"{kind}-{f}"


def build():
    letters, tool, comp, ms = read("letters_analysis.csv"), read("housing_elements.csv"), read("compliance.csv"), read("milestones.csv")
    if not letters and not tool:
        print("he_letters/letters_analysis.csv not found yet; skipping pathways.")
        return []
    names, county = {}, {}
    L, T, A, R = defaultdict(list), defaultdict(list), defaultdict(list), {}
    for r in letters:
        c = cycle_of(r)
        if c in CYCLES and d(r.get("letter_date")):
            k = jkey(r["jurisdiction"]); L[k, c].append(r)
            names.setdefault(k, r["jurisdiction"]); county.setdefault(k, r.get("county", ""))
    for r in tool:
        c = (r.get("planning_period") or "").strip()
        if c in CYCLES and d(r.get("received_date")) and not re.search(r"nullif|rescind", r.get("type") or "", re.I):
            k = jkey(r["jurisdiction"]); T[k, c].append(r)
            names.setdefault(k, r["jurisdiction"]); county.setdefault(k, r.get("county", ""))
    for r in ms:  # adoption dates stated in the letters
        if r.get("event") == "Adopted" and d(r.get("date")):
            k = jkey(r["jurisdiction"])
            A[k, (r.get("cycle") or "").strip()].append(d(r["date"]))
    for r in comp:
        c = re.sub(r"\D", "", r.get("planning_period", ""))[:1]
        k = jkey(r["jurisdiction"])
        R[k, c] = r
        names.setdefault(k, (r["jurisdiction"] or "").title()); county.setdefault(k, r.get("county", ""))

    out = []
    for k, c in sorted(set(L) | set(T) | {kc for kc in R if kc[1] in CYCLES}, key=lambda x: (names.get(x[0], ""), x[1])):
        ls = sorted(L.get((k, c), []), key=lambda r: r["letter_date"])
        ts = T.get((k, c), [])
        rep = R.get((k, c))
        subs = [d(r["received_date"]) for r in ts] + [d(r.get("submittal_date")) for r in ls if d(r.get("submittal_date"))]
        start = min(subs) if subs else None
        src_start = ("Download Tool" if ts and start == min(d(r["received_date"]) for r in ts) else "letter") if start else ""
        # adoption: the first stated adoption on or after the first submittal, else the first adopted element HCD received
        stated = sorted(x for x in A.get((k, c), []) if start and x >= start)
        # the Tool's type label is sometimes wrong (a draft filed as "Adopted"), so its file name must not say draft
        received = sorted(d(r["received_date"]) for r in ts if ADOPT.search(r.get("type") or "")
                          and not DRAFT.search((r.get("pdf_url") or "").rsplit("/", 1)[-1])
                          and (not start or d(r["received_date"]) >= start))
        if stated and (not received or stated[0] <= received[0]):
            adopted, src_adopted = stated[0], "letter"
        elif received:
            adopted, src_adopted = received[0], "Download Tool (received)"
        elif rep and ADOPT.search(rep.get("record_type") or "") and d(rep.get("date_received")):
            adopted, src_adopted = d(rep["date_received"]), "compliance report (received)"
        else:
            adopted, src_adopted = None, ""
        # compliance: the first letter finding an adopted element in compliance, else HCD's report
        ins = [d(r["letter_date"]) for r in ls if r.get("finding") == "In" and ADOPT.search(r.get("type") or "")
               and (not start or d(r["letter_date"]) >= start)]
        if ins:
            compliant, src_compliant = ins[0], "HCD letter"
        elif rep and ADOPT.search(rep.get("record_type") or "") and rep.get("review_status") == "In" and d(rep.get("date_reviewed")):
            compliant, src_compliant = d(rep["date_reviewed"]), "compliance report"
        else:
            compliant, src_compliant = None, ""
        if adopted and compliant and adopted > compliant:  # a later readoption; the element was found in compliance first
            later = [x for x in stated + received if x <= compliant]
            adopted = min(later) if later else adopted
        # a letter can quote an earlier cycle's deadline; keep dates that fit this cycle
        dues = Counter(r["statutory_due_date"] for r in ls if r.get("statutory_due_date")
                       and DUE_RANGE[c][0] <= r["statutory_due_date"][:10] <= DUE_RANGE[c][1])
        due = d(dues.most_common(1)[0][0]) if dues else None
        path_letters = [r for r in ls if "no_submittal_reviewed" not in (r.get("review_flags") or "")
                        and (ADOPT.search(r.get("type") or "") or DRAFT.search(r.get("type") or ""))]
        span = lambda a, b: (b - a).days if a and b and b >= a else ""
        out.append({
            "jurisdiction": names.get(k, k), "county": county.get(k, ""), "cycle": c,
            "statutory_due_date": due or "", "first_submittal": start or "", "first_submittal_source": src_start,
            "adopted_date": adopted or "", "adopted_source": src_adopted,
            "compliant_date": compliant or "", "compliant_source": src_compliant,
            "days_to_adoption": span(start, adopted), "days_to_compliance": span(start, compliant),
            "days_adoption_to_compliance": span(adopted, compliant),
            "days_late": (compliant - due).days if compliant and due else "",
            "submittals": len({r["received_date"] for r in ts}), "hcd_letters": len(ls),
            "out_letters": sum(r.get("finding") == "Out" for r in ls), "in_letters": sum(r.get("finding") == "In" for r in ls),
            "path": " > ".join(token(r) for r in path_letters),
            "path_dates": " > ".join(r["letter_date"] for r in path_letters),
            "unknown_findings": sum(r.get("finding") not in ("In", "Out") for r in path_letters),
            "submittal_dates": " > ".join(sorted({r["received_date"] for r in ts}) or sorted({r["submittal_date"] for r in ls if r.get("submittal_date")})),
            "status_now": (rep or {}).get("compliance_status", ""),
            "report_status": " / ".join(x for x in ((rep or {}).get("record_type", ""), (rep or {}).get("review_status", "")) if x),
        })
    # A jurisdiction whose letters state no due date gets its region's: due dates are set by COG/MPO region, which
    # generally follows county lines, so the date most common among the county's jurisdictions is used
    by_county = defaultdict(Counter)
    for r in out:
        if r["statutory_due_date"]:
            by_county[r["county"], r["cycle"]][r["statutory_due_date"]] += 1
    for r in out:
        r["due_source"] = "letters" if r["statutory_due_date"] else ""
        common = by_county.get((r["county"], r["cycle"]))
        if not r["statutory_due_date"] and common and common.most_common(1)[0][1] >= 2:
            r["statutory_due_date"], r["due_source"] = common.most_common(1)[0][0], "region"
            if r["compliant_date"]:
                r["days_late"] = (r["compliant_date"] - r["statutory_due_date"]).days
    exposure(out)
    return out


def hau_compliance_letters():
    """{jurisdiction key: ([decertification dates], [recertification dates])} from the HAU letters."""
    p = ROOT / "hau" / "hau_letters.csv"
    rows = list(csv.DictReader(open(p, encoding="utf-8"))) if p.exists() else []
    out = defaultdict(lambda: ([], []))
    for r in rows:
        t, when = (r.get("letter_type") or "").lower(), d(r.get("letter_date"))
        if when and ("decertification" in t or "revocation" in t):
            out[jkey(r["jurisdiction"])][0].append(when)
        elif when and "recertification" in t:
            out[jkey(r["jurisdiction"])][1].append(when)
    return out


def exposure(out):
    """Periods without a housing element HCD has found in compliance, when the builder's remedy can apply
    (Gov. Code 65589.5(d)(5); since AB 1886 only an HCD or court finding counts, so adoption alone doesn't end it):
      - from the cycle's statutory due date until HCD's first finding of compliance ("after the statutory deadline")
      - from an HAU decertification letter until the next recertification letter ("decertified")
    A period with no end is ongoing when HCD's report shows the jurisdiction out of compliance today; when the end
    can't be told (no compliance date, letters with no public copy) the period is left open-ended and not counted.
    within_120_days: found in compliance within 120 days after the due date (Gov. Code 65588(e)(4)). When it wasn't
    and the 120 days ended on or after Jan 1, 2022 (AB 1398), rezone_deadline is one year after the due date."""
    rows = [r for r in out]
    data_date = max([r["compliant_date"] for r in rows if r["compliant_date"]] + [date.today()])
    hau = hau_compliance_letters()
    by_jur = defaultdict(dict)
    for r in rows:
        by_jur[jkey(r["jurisdiction"])][r["cycle"]] = r
    for r in rows:
        r.update(exposure_windows="", exposure_days="", exposed_now="", within_120_days="", rezone_deadline="")
    for k, cyc in by_jur.items():
        windows = defaultdict(list)                       # cycle -> [(start, end or None, reason, known_end)]
        for c, r in cyc.items():
            due, comp = d(str(r["statutory_due_date"])), d(str(r["compliant_date"]))
            if not due:
                continue
            nxt = cyc.get(str(int(c) + 1))
            next_due = d(str(nxt["statutory_due_date"])) if nxt else None
            if comp and comp <= due:
                pass
            elif comp:
                windows[c].append((due, comp, "after the statutory deadline", True))
            elif next_due and next_due <= data_date:      # moved on to the next cycle without a finding here
                windows[c].append((due, next_due, "after the statutory deadline (until the next cycle's deadline)", r["unknown_findings"] == 0))
            elif (r["status_now"] or "").lower().endswith("out") or not r["unknown_findings"]:
                windows[c].append((due, None, "after the statutory deadline", True))
            else:
                windows[c].append((due, None, "after the statutory deadline (end unknown)", False))
            r["within_120_days"] = ("yes" if comp and (comp - due).days <= 120 else "no") if (comp or due + timedelta(days=120) <= data_date) else ""
            if r["within_120_days"] == "no" and due + timedelta(days=120) >= date(2022, 1, 1):
                r["rezone_deadline"] = due + timedelta(days=365)
        decert, recert = hau.get(k, ([], []))
        for dd in sorted(set(decert)):
            # the cycle whose compliance it took away: the latest one found in compliance before it
            cands = [(d(str(r["compliant_date"])), c) for c, r in cyc.items() if d(str(r["compliant_date"])) and d(str(r["compliant_date"])) < dd]
            if not cands:
                continue
            c = max(cands)[1]
            ends = sorted(x for x in recert if x > dd)
            if ends:
                windows[c].append((dd, ends[0], "decertified", True))
            else:
                ongoing = (cyc[c]["status_now"] or "").lower().endswith("out")
                windows[c].append((dd, None, "decertified" if ongoing else "decertified (end unknown)", ongoing))
        for c, ws in windows.items():
            r = cyc[c]
            ws.sort(key=lambda w: w[0])
            r["exposure_windows"] = "; ".join(f"{a}..{b or ''} {why}" for a, b, why, _ in ws)
            counted = [(a, b or data_date) for a, b, _, known in ws if known]
            r["exposure_days"] = sum((b - a).days for a, b in counted) if counted else ""
            r["exposed_now"] = "yes" if any(b is None and known for _, b, _, known in ws) else "no"


def main():
    rows = build()
    if not rows:
        return
    cols = list(rows[0])
    with open(HE / "pathways.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    for c in CYCLES:
        rs = [r for r in rows if r["cycle"] == c]
        dc = [r["days_to_compliance"] for r in rs if r["days_to_compliance"] != ""]
        da = [r["days_to_adoption"] for r in rs if r["days_to_adoption"] != ""]
        print(f"{c}th cycle: {len(rs)} jurisdictions, {sum(1 for r in rs if r['first_submittal'])} with a submittal, "
              f"{len(da)} adopted (median {statistics.median(da) if da else '-'} days), "
              f"{len(dc)} found in compliance (median {statistics.median(dc) if dc else '-'} days from first submittal)")
    print("he_letters/pathways.csv:", len(rows), "rows")


if __name__ == "__main__":
    main()
