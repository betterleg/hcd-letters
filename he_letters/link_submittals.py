"""Attach the Housing Element submittal each letter reviewed, from the HE Download Tool CSV."""
import csv, json, re, sys, collections
from datetime import date, timedelta

ALIASES = {"sanbuenaventura": "ventura", "sanluisobispoco": "sanluisobispocounty",
           "ranchostmargarita": "ranchosantamargarita", "amadorcity": "amador"}
norm = lambda s: re.sub(r"[^a-z]", "", (s or "").lower())

def main(letters_json, he_csv, out_json, out_csv):
    L = json.load(open(letters_json))
    he = collections.defaultdict(list)
    for r in csv.DictReader(open(he_csv, encoding="utf-8")):
        try:
            he[norm(r["jurisdiction"])].append((date.fromisoformat(r["received_date"]), r))
        except ValueError:
            pass
    for x in L:
        x.update(he_received_date=None, he_type=None, he_cycle=None, he_pdf_url=None, submittal_match=None, submittal_date=None)
        if x["status"] != "downloaded":
            continue
        k = norm(x["jurisdiction"]); k = ALIASES.get(k, k)
        docs = he.get(k, [])
        letter = date.fromisoformat(x["reviewed"])
        best = None
        if x["received_date"]:
            rd = date.fromisoformat(x["received_date"])
            near = [t for t in docs if abs((t[0] - rd).days) <= 14]
            if near:
                best = min(near, key=lambda t: abs((t[0] - rd).days))
                d = (best[0] - rd).days
                x["submittal_match"] = "same date" if d == 0 else f"{d:+d} days from letter's received date"
        else:
            prior = [t for t in docs if letter - timedelta(days=150) <= t[0] <= letter]
            if prior:
                best = max(prior, key=lambda t: t[0])
                x["submittal_match"] = "latest submittal before letter (letter states no date)"
        if best:
            x.update(he_received_date=best[0].isoformat(), he_type=best[1]["type"], he_cycle=best[1]["planning_period"], he_pdf_url=best[1]["pdf_url"])
        x["submittal_date"] = x["received_date"] or x["he_received_date"]
        if x["submittal_date"]:
            d = (letter - date.fromisoformat(x["submittal_date"])).days
            x["review_days"] = d if 0 <= d <= 400 else None
    json.dump(L, open(out_json, "w"))
    cols = ["county","jurisdiction","type","cycle","reviewed","finding","finding_source","submittal_date","review_days",
            "received_date","adopted_date","last_revision_date","he_received_date","he_type","he_pdf_url","submittal_match",
            "linktext","status","fetched_from","pdf_url"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["letter_date" if c == "reviewed" else c for c in cols])
        for x in L: w.writerow([x.get(c) if x.get(c) is not None else "" for c in cols])
    D = [x for x in L if x["status"] == "downloaded"]
    print("downloaded", len(D), "submittal_date", sum(1 for x in D if x["submittal_date"]),
          "linked to HE doc", sum(1 for x in D if x["he_pdf_url"]), collections.Counter((x["submittal_match"] or "none").split(" (")[0] if "latest" in (x["submittal_match"] or "") else ("same" if x["submittal_match"]=="same date" else ("off" if x["submittal_match"] else "none")) for x in D))

if __name__ == "__main__":
    main(*sys.argv[1:])
