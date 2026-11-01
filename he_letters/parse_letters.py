"""Parse HCD housing element review letters: received/adopted/revision dates and finding."""
import csv, json, re, sys, urllib.parse
from datetime import date, datetime
from pathlib import Path

MON = "January|February|March|April|May|June|July|August|September|October|November|December"
D = rf"((?:{MON})\.?\s+\d{{1,2}}\s*,?\s*\d{{4}})"
RX_RECEIVED = re.compile(rf"received\s+(?:for\s+(?:review\s+)?)?(?:on\s+)?{D}", re.I)
RX_ADOPTED = re.compile(rf"adopted\s+(?:on\s+)?{D}", re.I)
RX_REVISION = re.compile(rf"revisions?\s+(?:received\s+)?(?:on\s+)?(?:through\s+)?{D}", re.I)
IN_PH = [r"meets\s+(?:most\s+of\s+)?(?:all\s+)?(?:the\s+)?statutory\s+requirements", r"met\s+(?:the\s+)?statutory\s+requirements", r"in\s+(?:full|substantial)\s+compliance", r"substantially\s+compl(?:y|ies)\s+with", r"meets\s+the\s+statutory\s+requirements",
         r"pleased\s+to\s+find", r"complies\s+with\s+State\s+Housing\s+Element\s+Law", r"addresses\s+the\s+statutory\s+requirements"]
OUT_PH = [r"revisions\s+(?:will\s+be|are)\s+necessary", r"additional\s+revisions\s+are\s+(?:necessary|required)", r"does\s+not\s+(?:substantially\s+)?comply",
          r"not\s+in\s+(?:substantial\s+)?compliance", r"no\s+longer\s+(?:in\s+)?(?:substantial\s+)?compl", r"revok", r"has\s+failed\s+to"]
PENDING_PH = [r"(?:cannot|could\s+not|can\s+not|will\s+not)\s+be\s+found\s+in\s+(?:substantial\s+|full\s+)?compliance\s+until",
              r"upon\s+(?:adoption|completion)\s+of\s+the\s+(?:draft\s+)?(?:revisions|rezon)", r"until\s+the\s+(?:City|County|Town)\s+(?:has\s+)?complete[sd]?\s+(?:the\s+)?(?:necessary\s+)?rezon"]
RX_PENDING = re.compile("|".join(PENDING_PH), re.I)
RX_IN = re.compile("|".join(IN_PH), re.I)
RX_NOW_IN = re.compile(r"pleased\s+to\s+(?:find|report)|(?:is\s+)?now\s+in\s+(?:substantial|full)\s+compliance|HCD\s+finds\s+the\s+(?:adopted\s+)?(?:housing\s+)?element\s+in\s+(?:substantial|full)\s+compliance", re.I)
RX_OUT = re.compile("|".join(OUT_PH), re.I)


def to_date(s):
    s = re.sub(r"\s*,?\s*(\d{4})$", r", \1", re.sub(r"\.", "", s.strip()))
    s = re.sub(r"\s+", " ", s)
    try:
        d = datetime.strptime(s, "%B %d, %Y").date()
        return d.isoformat() if 1990 <= d.year <= 2035 else None
    except ValueError:
        return None


def parse(text):
    t = re.sub(r"\s+", " ", text)
    i = t.lower().find("thank you for")
    body = t[i:] if i >= 0 else t[300:]
    head = body[:1500]
    out = {}
    m = RX_RECEIVED.search(head)
    out["received_date"] = to_date(m.group(1)) if m else None
    m = RX_ADOPTED.search(head)
    out["adopted_date"] = to_date(m.group(1)) if m else None
    revs = [to_date(x) for x in RX_REVISION.findall(head)]
    revs = [r for r in revs if r]
    out["last_revision_date"] = max(revs) if revs else None
    finding_zone = body[:3500]
    mi, mo, mp = RX_IN.search(finding_zone), RX_OUT.search(finding_zone), RX_PENDING.search(finding_zone)
    now_in = RX_NOW_IN.search(finding_zone)
    if now_in and (not mo or now_in.start() < mo.start()):
        out["finding"] = "In"
    elif mp and (not mo or mp.start() < mo.start() or (mi and mi.start() < mo.start())):
        out["finding"] = "Meets requirements, pending action"
    elif mi and (not mo or mi.start() < mo.start()):
        out["finding"] = "In"
    elif mo:
        out["finding"] = "Out"
    else:
        out["finding"] = "Unclear"
    return out


RX_FN = re.compile(
    r"(?:(?<=^)|(?<=[-_ ]))(in|out)(?=[-_ ]|\d{6}|$)"            # -in-, -out-, -in120123
    r"|(?<=[a-z])(In|IN|Out|OUT)(?=\d{6}|[-_ ]|$)"                 # AdoptedIn122022, draftOUT0316
    r"|(?<=draft|adopt|opted|ezone)(in|out)(?=\d{6})",             # draftout031622
)


def filename_hint(url):
    """HCD's own in/out label in the letter's file name (last one wins, e.g. adopt-out-rezone-in)."""
    stem = Path(urllib.parse.unquote(urllib.parse.urlsplit(url).path)).stem
    hits = [next(g for g in m.groups() if g).lower() for m in RX_FN.finditer(stem)]
    return {"in": "In", "out": "Out"}.get(hits[-1]) if hits else None


if __name__ == "__main__":
    root = Path(sys.argv[1])
    rows = list(csv.DictReader(open(root / "letters_index.csv", encoding="utf-8")))
    recs = []
    for r in rows:
        rec = {k: r[k] for k in ("county", "jurisdiction", "type", "cycle", "reviewed", "linktext", "status", "fetched_from")}
        rec["pdf_url"] = r["weblink"] if r["weblink"].startswith("http") else ""
        rec.update(received_date=None, adopted_date=None, last_revision_date=None, finding=None, filename_hint=None, text_finding=None, finding_source=None, review_days=None)
        if r["status"] == "downloaded" and r["text_file"]:
            p = root / r["text_file"]
            if p.exists():
                rec.update(parse(p.read_text(encoding="utf-8", errors="replace")))
                rec["filename_hint"] = filename_hint(r["weblink"])
                rec["text_finding"] = rec["finding"]
                if rec["filename_hint"]:
                    rec["finding"], rec["finding_source"] = rec["filename_hint"], "HCD file name"
                else:
                    rec["finding_source"] = "letter text"
                if rec["received_date"] and r["reviewed"]:
                    d = (date.fromisoformat(r["reviewed"]) - date.fromisoformat(rec["received_date"])).days
                    rec["review_days"] = d if -5 <= d <= 400 else None
        recs.append(rec)
    json.dump(recs, open(sys.argv[2], "w"), indent=0)
    print(len(recs), "records")
