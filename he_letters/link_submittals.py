"""Attach the Housing Element submittal each letter reviewed, from the HE Download Tool CSV.

Review rounds (2026-11): HCD's review clock starts with the first submittal received after HCD's previous letter
to the jurisdiction and runs to this letter. A letter closes a round only within its own cycle, or when either
letter's cycle is blank: a letter about another cycle's element (e.g. a 65585(i) letter on 5th-cycle programs sent
during a 6th-cycle review) doesn't. Type and status don't matter: "Conditional", contact_hcd and no-cycle letters
all close rounds.
A letter's cycle is HCD's label, except when the received date the letter names matches a Download Tool submittal
(within 14 days) in another cycle and none in its own: then the Tool's cycle is used (HCD's letter table sometimes
labels a 5th-cycle letter as 6th, or a 6th as 7th; the Tool's cycle agrees with its file names). cycle_from_tool
records the Tool's cycle when it was used; the cycle column keeps HCD's label. Amendments or revisions sent during that review (to answer comments
or after meetings) are recorded but don't reset it. Two sources are kept side by side and never override each
other's columns:
  review_start_text   the earliest date the letter itself names that falls after the previous letter
  round_start_tool    the earliest Download Tool submittal (same cycle) after the previous letter, up to this letter
submittal_date / review_days use the Tool date when there is one, else the letter's date; review_days_text keeps
the letter-based count. review_limit_days is the statutory review period (Gov. Code 65585): 90 days for the
jurisdiction's first submittal of the cycle, 60 for every submittal after it. review_flags lists:
over_statutory_limit, tool_text_disagree (more than 7 days apart), no_tool_submittal, no_submittal_reviewed.
no_submittal_reviewed replaces no_tool_submittal for a letter that reviews no submittal (due-date notices,
65585(i) letters, technical assistance): it has text, names no received date, has no Tool submittal in its round
and isn't labeled adopted. Its review_limit_days is blank.
he_received_date / he_type / he_pdf_url (the housing element reviewed) point at the round's first Download Tool
submittal when there is one; otherwise at the Tool document nearest the letter's received date (submittal_match says which).
Tool documents are only matched within the letter's cycle (planning_period) when the letter has one; with no match
he_* stay blank.
"""
import csv, json, re, sys, collections
from datetime import date, timedelta

ALIASES = {"sanbuenaventura": "ventura", "sanluisobispoco": "sanluisobispocounty",
           "ranchostmargarita": "ranchosantamargarita", "amadorcity": "amador"}
norm = lambda s: re.sub(r"[^a-z]", "", (s or "").lower())
# Statutory review periods, Gov. Code 65585 (days): 90 for the jurisdiction's first submittal of the cycle, 60 for
# every submittal after it (subsequent drafts and adopted elements).
FIRST_DAYS = 90
LATER_DAYS = 60
DISAGREE_DAYS = 7


def has_letter(x):
    """HCD posted the letter and we have the PDF: "downloaded", or "downloaded_scanned" (no text layer, so the
    letter's own dates are missing but the Download Tool can still date the round)."""
    return (x.get("status") or "").startswith("downloaded")


def same_cycle(a, b):
    """Two cycles match when they're equal or either is blank (unknown)."""
    return not a or not b or a == b


def letter_cycles(L, he):
    """Set x["_cycle"]: HCD's cycle label, or the Download Tool's cycle when the letter's received date matches a
    Tool submittal (within 14 days) only in another cycle."""
    for x in L:
        cyc = str(x.get("cycle") or "")
        x["_cycle"] = cyc
        rd = d(x.get("received_date"))
        if not cyc or not rd or not has_letter(x):
            continue
        k = norm(x["jurisdiction"]); k = ALIASES.get(k, k)
        near = sorted((abs((t - rd).days), r["planning_period"]) for t, r in he.get(k, []) if abs((t - rd).days) <= 14)
        if near and not any(p == cyc for _, p in near):
            x["_cycle"] = near[0][1]
            x["cycle_from_tool"] = near[0][1]


def cycle_of(x):
    return x["_cycle"] if "_cycle" in x else str(x.get("cycle") or "")


def d(s):
    try:
        return date.fromisoformat(str(s)[:10]) if s else None
    except ValueError:
        return None


def review_rounds(L, he):
    """Add round fields to each downloaded letter in L (list of dicts with jurisdiction, reviewed, status, type,
    cycle, received_date, first_received_date). `he` maps a normalized jurisdiction to [(received date, row)]."""
    letters = collections.defaultdict(list)          # (date, cycle) of every letter to the jurisdiction, any status/type
    for x in L:
        ld = d(x.get("reviewed"))
        if ld:
            k = norm(x["jurisdiction"]); letters[ALIASES.get(k, k)].append((ld, cycle_of(x)))
    for k in letters:
        letters[k].sort()
    for x in L:
        x.update(review_start_text=None, review_days_text=None, round_start_tool=None, round_start_tool_type=None,
                 round_submittals=None, review_limit_days=None, review_flags=None)
        letter = d(x.get("reviewed"))
        if not has_letter(x) or letter is None:
            continue
        k = norm(x["jurisdiction"]); k = ALIASES.get(k, k)
        cyc = cycle_of(x)
        # earlier letters close a round only within the same cycle (or when either cycle is blank)
        prev = max((t for t, c in letters.get(k, []) if t < letter and same_cycle(c, cyc)), default=None)
        # the letter's own dates after the previous letter: the earliest starts the clock
        named = [t for t in (d(x.get("first_received_date")), d(x.get("received_date"))) if t and t <= letter]
        after = [t for t in named if prev is None or t > prev]
        text = min(after) if after else (max(named) if named else None)
        # Download Tool submittals in the same cycle after the previous letter, up to this letter
        subs = sorted(((t, r) for t, r in he.get(k, []) if (not cyc or r["planning_period"] == cyc)
                       and (prev is None or t > prev) and t <= letter), key=lambda s: s[0])   # same-day uploads: keep order
        tool = subs[0] if subs else None
        flags = []
        # a letter that reviews no submittal: text with no received date, no Tool submittal, not an adopted element
        no_review = (tool is None and x.get("status") == "downloaded" and not x.get("received_date")
                     and not x.get("first_received_date") and not re.search(r"ad+opt", x.get("type") or "", re.I))
        if no_review:
            flags.append("no_submittal_reviewed")
        elif tool is None:
            flags.append("no_tool_submittal")
        if tool and text and abs((tool[0] - text).days) > DISAGREE_DAYS:
            flags.append("tool_text_disagree")
        start = tool[0] if tool else text
        days = (letter - start).days if start else None
        if days is not None and not 0 <= days <= 400:
            days = None
        # first submittal of the cycle: no HCD letter since the jurisdiction's earliest submittal in this cycle
        cycle_subs = [t for t, r in he.get(k, []) if (not cyc or r["planning_period"] == cyc)]
        first_of_cycle = min(cycle_subs) if cycle_subs else None
        first_round = prev is None or (first_of_cycle is not None and prev < first_of_cycle)
        limit = None if no_review else FIRST_DAYS if first_round else LATER_DAYS
        x["review_limit_days"] = limit
        if limit and days is not None and days > limit:
            flags.append("over_statutory_limit")
        x.update(review_start_text=text.isoformat() if text else None,
                 review_days_text=(letter - text).days if text and 0 <= (letter - text).days <= 400 else None,
                 round_start_tool=tool[0].isoformat() if tool else None,
                 round_start_tool_type=tool[1]["type"] if tool else None,
                 round_submittals=len(subs) if subs else 0,
                 submittal_date=start.isoformat() if start else None, review_days=days,
                 review_flags="; ".join(flags) or None)
        # The element reviewed is the round's first submittal: point he_* (the site's "Element" link) at it.
        if tool and tool[0].isoformat() != x.get("he_received_date"):
            x.update(he_received_date=tool[0].isoformat(), he_type=tool[1]["type"], he_cycle=tool[1]["planning_period"],
                     he_pdf_url=tool[1].get("pdf_url"), submittal_match="first submittal of the review round")


def match_elements(L, he):
    """he_* for each downloaded letter: the Tool document nearest the letter's received date (within 14 days), or,
    when the letter names no date, the latest one in the 150 days before it. Only Tool rows in the letter's cycle
    count when the letter has a cycle; with no match he_* stay blank. review_rounds() then points he_* at the round's
    first submittal when there is one."""
    for x in L:
        x.update(he_received_date=None, he_type=None, he_cycle=None, he_pdf_url=None, submittal_match=None, submittal_date=None)
        if not has_letter(x) or not x.get("reviewed"):
            continue
        k = norm(x["jurisdiction"]); k = ALIASES.get(k, k)
        cyc = cycle_of(x)
        docs = [t for t in he.get(k, []) if not cyc or t[1]["planning_period"] == cyc]
        letter = date.fromisoformat(x["reviewed"])
        best = None
        if x.get("received_date"):
            rd = date.fromisoformat(x["received_date"])
            near = [t for t in docs if abs((t[0] - rd).days) <= 14]
            if near:
                best = min(near, key=lambda t: abs((t[0] - rd).days))
                dd = (best[0] - rd).days
                x["submittal_match"] = "same date" if dd == 0 else f"{dd:+d} days from letter's received date"
        else:
            prior = [t for t in docs if letter - timedelta(days=150) <= t[0] <= letter]
            if prior:
                best = max(prior, key=lambda t: t[0])
                x["submittal_match"] = "latest submittal before letter (letter states no date)"
        if best:
            x.update(he_received_date=best[0].isoformat(), he_type=best[1]["type"], he_cycle=best[1]["planning_period"], he_pdf_url=best[1]["pdf_url"])


def main(letters_json, he_csv, out_json, out_csv):
    L = json.load(open(letters_json))
    he = collections.defaultdict(list)
    for r in csv.DictReader(open(he_csv, encoding="utf-8")):
        try:
            k = norm(r["jurisdiction"])
            he[ALIASES.get(k, k)].append((date.fromisoformat(r["received_date"]), r))
        except ValueError:
            pass
    letter_cycles(L, he)
    match_elements(L, he)
    review_rounds(L, he)
    json.dump(L, open(out_json, "w"))
    cols = ["county","jurisdiction","type","cycle","reviewed","finding","finding_source","submittal_date","review_days",
            "received_date","first_received_date","adopted_date","last_revision_date","statutory_due_date",
            "review_start_text","review_days_text","round_start_tool","round_start_tool_type","round_submittals",
            "review_limit_days","review_flags","cycle_from_tool",
            "he_received_date","he_type","he_pdf_url","submittal_match","linktext","status","fetched_from","pdf_url"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["letter_date" if c == "reviewed" else c for c in cols])
        for x in L: w.writerow([x.get(c) if x.get(c) is not None else "" for c in cols])
    D = [x for x in L if has_letter(x)]
    print("downloaded", len(D), "submittal_date", sum(1 for x in D if x["submittal_date"]),
          "linked to HE doc", sum(1 for x in D if x["he_pdf_url"]),
          "flags", collections.Counter(f for x in D for f in (x["review_flags"] or "").split("; ") if f))

if __name__ == "__main__":
    main(*sys.argv[1:])
