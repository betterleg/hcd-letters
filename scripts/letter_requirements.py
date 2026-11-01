"""
Tie each housing element review letter's findings to the statutory requirement they fall under,
then ask: what does HCD find on 1st, 2nd, 3rd and later reviews; what keeps coming back; what
appears only once an element is in compliance; and which programs HCD requires.

    python3 scripts/letter_requirements.py      # -> he_letters/requirements.csv, programs.csv, REQUIREMENTS.md

How a letter is read
  HCD's appendix repeats one pattern: a statutory requirement quoted from Gov. Code § 65583
  (or § 65588), ending in its citation, e.g. "...(Gov. Code, § 65583, subd. (a)(3).)", followed by
  HCD's findings on it. Most findings start with a topic label ("Realistic Capacity:",
  "Suitability of Nonvacant Sites:", "Program 4.C (Transitional and Supportive Housing):").
  This script splits the letter at each quoted requirement, files every paragraph under it, and
  tags each paragraph with its topic label (labels are normalized, e.g. "Land-Use Controls" and
  "Land Use Controls" become one). Unlabeled paragraphs inherit the topic before them.

Review round: the letter's place among that jurisdiction's 6th-cycle reviews by date (1st, 2nd,
3rd, 4th+), counting every review on the dashboard, including "Contact HCD" ones with no text.

Outputs
  requirements.csv  one row per letter x requirement x topic: jurisdiction, letter_date, type,
                    cycle, round, finding, requirement (code cite), requirement_label, topic,
                    program (when the topic names a program), words, text (first 600 characters)
  letter_outcomes.csv  one row per letter: round, compliance (In compliance / Out of compliance / No
                    finding), kind of letter in plain words ("Revisions needed", "Meets requirements,
                    rezoning not done (AB 1398)", "Other"...), number of findings, requirements and
                    issues HCD wrote about, program commitments HCD asks for
  programs.csv      programs named in compliance letters ("must continue timely and effective
                    implementation of all programs including...") with a category
  REQUIREMENTS.md   the summary tables
"""
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HE = ROOT / "he_letters"
CYCLES = ("6", "7")

# Requirement keys from the citation that closes HCD's quote of the statute.
REQ_LABELS = {
    "65588": "Review and revision of the prior element",
    "65583(a)(1)": "Population, employment and housing needs (incl. ELI)",
    "65583(a)(2)": "Household characteristics (overpayment, overcrowding, conditions)",
    "65583(a)(3)": "Sites inventory and analysis",
    "65583(a)(4)": "Zoning for emergency shelters and other housing types",
    "65583(a)(5)": "Governmental constraints",
    "65583(a)(6)": "Nongovernmental constraints",
    "65583(a)(7)": "Special housing needs",
    "65583(a)(8)": "Energy conservation",
    "65583(a)(9)": "At-risk assisted housing",
    "65583(b)": "Quantified objectives",
    "65583(c)": "Programs: schedule of actions, timelines and objectives",
    "65583(c)(1)": "Program: adequate sites / rezoning",
    "65583(c)(2)": "Program: assist housing for lower- and moderate-income households",
    "65583(c)(3)": "Program: remove governmental and nongovernmental constraints",
    "65583(c)(4)": "Program: conserve and improve existing housing",
    "65583(c)(5)": "Affirmatively furthering fair housing (programs)",
    "65583(c)(6)": "Program: preserve at-risk housing",
    "65583(c)(7)": "Program: ADUs affordable to lower-income households",
    "65583(c)(8)": "Program: general plan consistency",
    "65583(c)(9)": "Public participation",
    "65583(c)(10)": "Affirmatively furthering fair housing (assessment)",
    "65583(c)(10)(A)": "Affirmatively furthering fair housing (assessment)",
    "65583(d)": "Programs (other)",
    "65583(e)": "Programs (other)",
    "65583(f)": "Programs (other)",
    "65583(g)": "Programs (other)",
    "65583(h)": "Programs (other)",
}
GROUP_OF = {  # requirement -> the appendix section HCD files it under
    "65588": "A. Review and revision",
    **{k: "B. Needs, resources and constraints" for k in REQ_LABELS if k.startswith("65583(a)")},
    "65583(c)(10)": "B. Needs, resources and constraints", "65583(c)(10)(A)": "B. Needs, resources and constraints",
    "65583(b)": "D. Quantified objectives",
    "65583(c)(9)": "E. Public participation",
    "65583(c)(8)": "F. Consistency with general plan",
}
RX_REQ_END = re.compile(r"\(\s*Gov(?:ernment|\.)?\s*Code,?\s*(?:§§?|sections?)\s*(65583|65588)(?![.\d]\d)\s*,?\s*"
                        r"(?:subds?\.?|subdivisions?)?\s*((?:\(\s*[a-z0-9]+\s*\)\s*)*)", re.I)
RX_LABEL = re.compile(r"^((?:Program[s]?\s+[A-Z0-9][\w.\-]*\s*(?:\([^)]{2,80}\))?)|(?:[A-Z][A-Za-z0-9’'&/(),\- ]{2,80}?)):\s+(?=\S)")
RX_PAGEHDR = re.compile(r"^\s*Page \d+\s*$")
SKIP_LABELS = {"source", "general", "note", "for example", "re", "dear", "example", "examples", "cc", "and", "including",
               "for your information", "in addition", "however", "please note", "please be aware", "reminder"}

TOPIC_SYNONYMS = [
    (r"^land ?use controls?$", "Land use controls"),
    (r"^electronic sites? inventory$", "Electronic sites inventory"),
    (r"^(sites? inventory|parcel listing|site inventory)$", "Sites inventory / parcel listing"),
    (r"^(suitability of )?nonvacant sites$|^previously identified nonvacant", "Nonvacant sites"),
    (r"^realistic capacity$", "Realistic capacity"),
    (r"^(small|large|small and large) sites$", "Small and large sites"),
    (r"^contributing factors( to fair housing issues)?$", "AFFH: contributing factors"),
    (r"^goals,? (priorities|actions),? (metrics,? )?and milestones$|^goals and actions$", "AFFH: goals, actions, metrics and milestones"),
    (r"^local data and knowledge,? (and )?other relevant factors$|^local data and knowledge$|^other relevant factors$", "AFFH: local data, knowledge and other factors"),
    (r"^(fair housing )?enforcement( and outreach)?( capacity)?$|^outreach$", "AFFH: fair housing enforcement and outreach"),
    (r"^integration and segregation", "AFFH: integration and segregation"),
    (r"^(disparities in )?access to opportunit", "AFFH: access to opportunity"),
    (r"^disproportionate housing needs", "AFFH: disproportionate needs and displacement"),
    (r"^racial.*(concentrat|r/ecap)", "AFFH: R/ECAPs and areas of affluence"),
    (r"^(local )?processing and permit procedures$", "Processing and permit procedures"),
    (r"^fees and exactions?$", "Fees and exactions"),
    (r"^(zoning and fees transparency|zoning, development standards and fees)$", "Zoning and fees transparency"),
    (r"^(constraints on )?housing for persons with disabilities$", "Housing for persons with disabilities"),
    (r"^(availability of |suitability and availability of )?infrastructure$", "Infrastructure"),
    (r"^accessory dwelling units", "ADUs"),
    (r"^zoning for a variety of housing types|^emergency shelters$", "Zoning for a variety of housing types / shelters"),
    (r"^extremely low.income", "Extremely low-income households"),
    (r"^(city|county|publicly).owned sites$", "Publicly owned sites"),
    (r"^progress in meeting the (rhna|regional housing need)", "Progress in meeting the RHNA"),
    (r"^sites identified in prior planning periods$", "Sites identified in prior planning periods"),
    (r"^codes and enforcement$", "Codes and enforcement"),
    (r"^on/off.site improvements$", "On/off-site improvements"),
    (r"^environmental constraints$", "Environmental constraints"),
    (r"^replacement housing", "Replacement housing"),
    (r"^programs?$", "Programs (general)"),
]
PROGRAM_CATEGORIES = [  # first match wins
    ("ADUs", r"accessory (dwelling )?units?|\badus?\b|jadu|second units?"),
    ("Fair housing, mobility and anti-displacement", r"fair housing|affh|mobility|displacement|tenant|place.based|revitaliz|opportunit|equity|segregat|environmental justice|neighborhood improvement|access to resources|grocery|economic development"),
    ("Special needs, homelessness and shelters", r"homeless|unhoused|shelter|supportive|transitional|navigation|special (housing )?needs|disabilit|farmworker|senior|elderly|reasonable accommodation|employee housing|group homes?|residential care|community care|single room|\bsro\b|universal design"),
    ("Rezoning and adequate sites", r"rezon|adequate sites|sites? inventory|by.right|overlay|upzon|lot consolidation|large lot|small lot|lot splits?|residential land|land use (policy|designation)|specific plan|no net loss|mid.cycle|surplus land|publicly.owned|city.owned|county.owned"),
    ("Zoning code amendments and housing types", r"zoning (code|ordinance)|code amendment|municipal code|variety of housing types|missing middle|mixed.use|adaptive reuse|manufactured|mobile ?home|definition of family|family definition|shared housing|general plan (update|amend)|amend the general plan"),
    ("Remove constraints and streamline", r"constraint|streamlin|objective (design )?standards|design review|permit|parking|fees?\b|process|development standards|transparen|growth management"),
    ("Affordable housing assistance and incentives", r"affordab|inclusionary|incentive|density bonus|extremely low|lower.income|funding|subsid|land trust|partnership|housing trust|voucher|section 8|rental assistance|first.time|homebuyer|down ?payment"),
    ("Infrastructure, water and sewer", r"water|sewer|wastewater|infrastructure|capital improvement|utilit"),
    ("Conserve, rehabilitate and preserve", r"rehabilit|conserv|preserv|at.risk|code enforcement|repair|weatheriz|energy|hazard"),
    ("Outreach, education and collaboration", r"outreach|education|collaborat|regional|working group|engagement|partner"),
    ("Monitoring and reporting", r"monitor|annual|report|replacement|implementation"),
]


def norm_topic(label):
    s = re.sub(r"\s+", " ", label).strip(" .:")
    k = s.lower().replace("’", "'").replace("-", " ")
    if k in SKIP_LABELS or len(k) < 3 or len(k.split()) > 9:
        return None
    for rx, canon in TOPIC_SYNONYMS:
        if re.search(rx, k):
            return canon
    return s[0].upper() + s[1:]


def program_name(label):
    m = re.match(r"Programs?\s+([A-Z0-9][\w.\-]*)\s*(?:\(([^)]+)\))?", label)
    return (m.group(2) or m.group(1)).strip() if m else ""


def clean_program(name):
    """'Program 1 (Alameda Point)' / 'Program H-2: Rezoning' / 'Accessory Dwelling Units' -> name."""
    n = re.sub(r"\s+", " ", name).strip(" ;,.")
    m = re.match(r"^Programs?\s+[\w.\-]+\s*\((.+?)\)?$", n)
    if m:
        return m.group(1).strip(" ()")
    return re.sub(r"^(Programs?\s+)?[A-Z]{0,3}[\-.]?\d+[\w.\-]*\s*[:–—-]?\s*", "", n).strip(" ()") or n


def category(text):
    t = text.lower()
    for name, rx in PROGRAM_CATEGORIES:
        if re.search(rx, t):
            return name
    return "Other"


RX_PAGE_ANY = re.compile(r"\bPage \d{1,2}\b")
RX_BULLET = re.compile(r"^[•▪●◦\uf0b7\uf0a7\-–]\s+")


def clean_lines(text):
    """Drop running page headers ("Name, Title" + "Page 3", or "City's Draft Housing Element Page 4 <date>")."""
    lines = text.splitlines()
    drop = set()
    for i, ln in enumerate(lines):
        if RX_PAGEHDR.match(ln) or (RX_PAGE_ANY.search(ln) and len(ln.strip()) < 140):
            drop.add(i)
            if i > 0 and lines[i - 1].strip() and len(lines[i - 1].strip()) < 90 and not lines[i - 1].rstrip().endswith((".", ":", ";")):
                drop.add(i - 1)
            if i + 1 < len(lines) and re.match(r"^\s*[A-Z][a-z]+ \d{1,2},? \d{4}\s*$", lines[i + 1]):
                drop.add(i + 1)
    return [ln for i, ln in enumerate(lines) if i not in drop]


def paragraphs(lines):
    paras, cur = [], []
    for ln in lines:
        s = RX_BULLET.sub("", ln.strip())
        starts_item = bool(re.match(r"^(\d{1,2}|[A-H])\.\s+\S", s))
        starts_label = bool(RX_LABEL.match(s)) and not cur[-1].endswith((",", "-", "and", "or")) if cur else False
        if not s or starts_item or starts_label:
            if cur:
                paras.append(" ".join(cur))
            cur = [s] if s else []
        else:
            cur.append(s)
    if cur:
        paras.append(" ".join(cur))
    merged = []
    for p in (re.sub(r"\s+", " ", p) for p in paras if p):
        # re-join a paragraph split by a page break: previous one is mid-sentence and this one continues in lower case
        if merged and not re.search(r"[.:;)\"”]$", merged[-1]) and re.match(r"^[a-z(]", p):
            merged[-1] += " " + p
        else:
            merged.append(p)
    return [p for p in merged if not re.match(r"^[A-H]\.\s+[A-Z][A-Za-z ,&]{2,60}$", p)]  # drop bare section headings


def req_key(code, path):
    toks = re.findall(r"\(\s*([a-z0-9]+)\s*\)", path or "")
    if code == "65588":
        return "65588"
    for depth in (3, 2, 1):
        k = code + "".join(f"({t})" for t in toks[:depth])
        if k in REQ_LABELS:
            return k
    return code + "".join(f"({t})" for t in toks[:2]) if toks else code


OPENINGS = {}  # first words of a quoted requirement -> requirement key, learned from quotes that end in a citation


def opening(p):
    return " ".join(re.findall(r"[a-z]+", re.sub(r"^((\d{1,2}|[A-H])\.\s+)", "", p).lower())[:9])


def learn_openings(texts):
    seen = defaultdict(Counter)
    for text in texts:
        for p in paragraphs(clean_lines(text)):
            m = None
            for m in RX_REQ_END.finditer(p):
                pass
            if m and len(p) - m.end() < 40 and len(p.split()) >= 9:
                seen[opening(p)][req_key(m.group(1), m.group(2))] += 1
    OPENINGS.clear()
    OPENINGS.update({o: c.most_common(1)[0][0] for o, c in seen.items() if sum(c.values()) >= 5})


def parse_letter(text):
    """[(requirement, topic, program, paragraph)] for the findings part of the letter."""
    paras = paragraphs(clean_lines(text))
    out, req, topic, prog = [], None, None, ""
    for p in paras:
        if len(p.split()) >= 9 and opening(p) in OPENINGS and not RX_LABEL.match(p):
            req, topic, prog = OPENINGS[opening(p)], None, ""
            continue
        m = None
        for m in RX_REQ_END.finditer(p):
            pass
        is_quote = m is not None and len(p) - m.end() < 40 and re.match(r"^((\d{1,2}|[A-H])\.\s+)?[A-Z]", p) and (
            re.match(r"^((\d{1,2}|[A-H])\.\s+)?(An?|The|Include|Identify|Address|Promote|Analyze|Develop|Establish|Local|Review|Conserve|Preserve|Assist|Affirmatively|Housing|Make|Shall|Describe|Each)\b", p))
        if is_quote:
            req, topic, prog = req_key(m.group(1), m.group(2)), None, ""
            continue
        if req is None:
            continue
        if re.match(r"^(Sincerely|We are committed|HCD appreciates|Public participation in the development|Several federal, state)", p):
            req = None
            continue
        lm = RX_LABEL.match(p)
        if lm:
            pn = program_name(lm.group(1))
            if pn:
                topic, prog = "Specific programs", pn
            else:
                t = norm_topic(lm.group(1))
                if t:
                    topic, prog = t, ""
        out.append((req, topic or "(no topic label)", prog, p))
    return out


def compliance_programs(text):
    """Program names listed after '...implementation of all programs including but not limited to the following:'"""
    flat = re.sub(r"\s+", " ", "\n".join(clean_lines(text)))
    m = re.search(r"implementation of all programs,? including,? but not limited to,? the following:?(.{0,6000}?)(?:The \w+ must monitor|As part of|HCD|Please|$)", flat, re.I)
    if not m:
        return []
    items = re.split(r"\s*[•▪●◦]\s*|\s+(?=Program\s+[A-Z0-9][\w.\-]*\s*\()", m.group(1))
    out = []
    for it in items:
        it = it.strip(" ;,.")
        if 4 < len(it) < 160 and re.search(r"[A-Za-z]{3}", it):
            out.append(it)
    return out


def main():
    analysis = list(csv.DictReader(open(HE / "letters_analysis.csv", encoding="utf-8")))
    index = list(csv.DictReader(open(HE / "letters_index.csv", encoding="utf-8")))
    text_of = {(r["jurisdiction"], r["reviewed"], r["type"]): r["text_file"] for r in index
               if r.get("status", "").startswith("downloaded") and r.get("text_file")}
    # review round within each jurisdiction's 6th (or 7th) cycle, counting every review on the dashboard
    by_j = defaultdict(list)
    for r in analysis:
        if r.get("cycle") in CYCLES and r.get("letter_date"):
            by_j[(r["jurisdiction"], r["cycle"])].append(r)
    rnd, first_in = {}, {}
    for key, rs in by_j.items():
        rs.sort(key=lambda r: r["letter_date"])
        for i, r in enumerate(rs, 1):
            rnd[id(r)] = i
        ins = [rnd[id(r)] for r in rs if r.get("finding") == "In"]
        first_in[key] = min(ins) if ins else None

    texts = {}
    for rs in by_j.values():
        for r in rs:
            tf = text_of.get((r["jurisdiction"], r["letter_date"], r["type"]))
            if tf and (HE / tf).exists():
                texts[tf] = (HE / tf).read_text(encoding="utf-8", errors="replace")
    learn_openings(texts.values())
    rows, progs, letters, pending = [], [], [], []
    for (j, cyc), rs in by_j.items():
        for r in rs:
            tf = text_of.get((r["jurisdiction"], r["letter_date"], r["type"]))
            if tf not in texts:
                continue
            text = texts[tf]
            found = parse_letter(text)
            kind = letter_kind(text, r.get("finding", ""), bool(found))
            ftext = " ".join(x[3] for x in found)
            commits = [name for name, rx in COMMITMENTS if re.search(rx, ftext, re.I)] if r.get("finding") == "Out" else []
            info = dict(jurisdiction=j, county=r.get("county", ""), letter_date=r["letter_date"], type=r["type"], cycle=cyc,
                        round=rnd[id(r)], finding=r.get("finding", ""), compliance=compliance_of(r.get("finding", "")),
                        kind=kind, text_file=tf)
            letters.append(dict(info, reqs={x[0] for x in found}, topics={x[1] for x in found}, commits=commits,
                                n_findings=len(found), words=len(ftext.split())))
            pending.append((len(letters) - 1, [(x[0], x[1], sentences(x[3], names=(j, r.get("county", "")))) for x in found]))
            for req, topic, prog, p in found:
                rows.append(dict(info, requirement=req, requirement_label=REQ_LABELS.get(req, req), topic=topic, program=prog,
                                 words=len(p.split()), text=p[:600]))
            if r.get("finding") == "In":
                for name in compliance_programs(text):
                    nm = clean_program(name)
                    progs.append(dict(info, program=nm, category=category(nm)))
    # Standard sentences: the same normalized sentence in BOILER_MIN or more letters. A commitment counts as
    # "specific" only when it appears in a sentence HCD wrote for that letter.
    freq = Counter(k for _, paras in pending for k in {k for _, _, ss in paras for k, _ in ss})
    for li, paras in pending:
        own_paras = [(q, t, " ".join(x for k, x in ss if freq[k] < BOILER_MIN)) for q, t, ss in paras]
        own = " ".join(o for _, _, o in own_paras)
        letters[li]["commits_specific"] = [n for n, rx in COMMITMENTS if re.search(rx, own, re.I)] if letters[li]["finding"] == "Out" else []
        letters[li]["specific_words"] = len(own.split())
        # a requirement or issue counts as "specific" when HCD wrote 25+ words of its own about it in this letter
        wq, wt = Counter(), Counter()
        for q, t, o in own_paras:
            wq[q] += len(o.split())
            wt[t] += len(o.split())
        letters[li]["reqs_specific"] = {q for q, n in wq.items() if n >= 25}
        letters[li]["topics_specific"] = {t for t, n in wt.items() if n >= 25}
    cols = ["jurisdiction", "county", "letter_date", "type", "cycle", "round", "finding", "compliance", "kind", "requirement", "requirement_label",
            "topic", "program", "words", "text_file", "text"]
    with open(HE / "requirements.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    with open(HE / "programs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["jurisdiction", "county", "letter_date", "type", "cycle", "round", "program", "category", "text_file"], extrasaction="ignore")
        w.writeheader()
        w.writerows(progs)
    with open(HE / "letter_outcomes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["jurisdiction", "county", "letter_date", "type", "cycle", "round", "compliance", "kind", "findings", "finding_words",
                    "specific_words", "requirements", "requirements_specific", "issues_specific", "commitments",
                    "commitments_specific", "text_file"])
        for l in letters:
            w.writerow([l["jurisdiction"], l["county"], l["letter_date"], l["type"], l["cycle"], l["round"], l["compliance"], l["kind"],
                        l["n_findings"], l["words"], l.get("specific_words", 0), " | ".join(sorted(l["reqs"])),
                        " | ".join(sorted(l.get("reqs_specific", ()))),
                        " | ".join(sorted(set(l.get("topics_specific", ())) - {"(no topic label)"})),
                        " | ".join(l["commits"]), " | ".join(l.get("commits_specific", ())), l["text_file"]])
    report([l for l in letters if l["cycle"] == "6"], [r for r in rows if r["cycle"] == "6"],
           [p for p in progs if p.get("cycle") == "6"], {k[0]: v for k, v in first_in.items() if k[1] == "6"},
           n7=sum(1 for l in letters if l["cycle"] == "7"))
    print(f"he_letters/requirements.csv: {len(rows):,} findings from {len(letters):,} 6th-cycle letters; programs.csv: {len(progs):,} program mentions")


BOILER_MIN = 25


def sentences(text, names=()):
    """[(normalized key, original sentence)]; names, dates and numbers are blanked so standard sentences compare equal."""
    out = []
    for t in re.split(r"(?<=[.;:])\s+(?=[A-Z(•])", text):
        k = t.lower()
        for n in names:
            if n:
                k = k.replace(n.lower().replace(" county", ""), " ")
        k = re.sub(r"\b(city|county|town)('s|’s)?\b", " ", k)
        k = re.sub(r"[\d,]+(\.\d+)?", "#", k)
        k = re.sub(r"[^a-z#]+", " ", k).strip()
        if len(k) > 30:
            out.append((k, t))
    return out


RX_REZONE_PENDING = re.compile(r"cannot be found in (?:substantial |full )?compliance until[^.]{0,200}rezon", re.I)


COMPLIANCE = {"In": "In compliance", "Out": "Out of compliance"}


def compliance_of(finding):
    return COMPLIANCE.get(finding, "No finding")


def letter_kind(text, finding, has_findings):
    """What kind of letter this is, beyond In/Out."""
    flat = re.sub(r"\s+", " ", text)
    if finding == "Out":
        if re.search(r"(ordinance|resolution)[^.]{0,120}(submitted|received)[^.]{0,80}(verify|review)", flat, re.I) and not has_findings:
            return "Rezoning ordinance reviewed, still short"
        if RX_REZONE_PENDING.search(flat) and not has_findings:
            return "Meets requirements, rezoning not done (AB 1398)"
        if has_findings:
            return "Revisions needed"
        if re.search(r"revok|revocation", flat, re.I):
            return "Compliance revoked"
        return "Other"
    if finding == "In":
        if re.search(r"revised draft element meets|draft element meets the statutory requirements|will substantially comply[^.]{0,80}when it is adopted", flat, re.I):
            return "Draft meets requirements (adopt next)"
        if re.search(r"(complet|adopt)[^.]{0,80}rezon|rezon[^.]{0,80}complet", flat, re.I) and re.search(r"now in (substantial |full )?compliance|compliance (has been )?restored|is now in", flat, re.I):
            return "Rezoning completed, compliance restored"
        if re.search(r"full compliance", flat, re.I):
            return "Adopted, full compliance"
        if re.search(r"substantial compliance|substantially compl", flat, re.I):
            return "Adopted, substantial compliance"
        return "Other"
    return "Other"


# Commitments HCD asks programs to make. Each is counted once per Out letter whose findings mention it.
COMMITMENTS = [
    ("Rezone to meet the RHNA shortfall by a date", r"shortfall|rezon[^.]{0,80}(by|within|no later than)|65583\.2,? subd(ivision)?s?\.? \(h\)"),
    ("By-right approval for 20% lower-income projects (§ 65583.2(h)-(i))", r"by.right[^.]{0,200}20 percent|65583\.2,? subd(ivision)?s?\.? \(?[hi]\)?"),
    ("Replacement housing on sites with existing units", r"replacement housing"),
    ("No net loss monitoring (§ 65863)", r"no net loss|65863\b"),
    ("Mid-cycle review of sites / nonvacant assumptions", r"mid.cycle|(monitor|evaluat)[^.]{0,80}(nonvacant|redevelopment|realistic capacity)"),
    ("ADU monitoring and alternative actions if targets missed", r"(monitor|track)[^.]{0,120}(adu|accessory dwelling)[^.]{0,200}(alternative|additional) action"),
    ("Emergency shelters: zoning, capacity, standards (§ 65583(a)(4))", r"emergency shelter"),
    ("Low barrier navigation centers (§ 65660)", r"low.barrier navigation|65660"),
    ("Supportive housing by right (§ 65651)", r"65651|supportive housing[^.]{0,80}by.right"),
    ("Transitional and supportive housing as a residential use", r"transitional and supportive housing[^.]{0,200}(same|similar|residential use)"),
    ("Employee and farmworker housing (HSC 17021.5, 17021.6)", r"17021\.[568]|employee housing"),
    ("Group homes / residential care for 7+ persons", r"(group homes?|residential care)[^.]{0,120}(seven|7) or more|7\+"),
    ("Reasonable accommodation procedures", r"reasonable accommodation"),
    ("Density bonus law update (§ 65915)", r"density bonus|65915"),
    ("Objective standards / design review changes", r"objective (design )?standards|design review"),
    ("Parking standards", r"parking (standards|requirements|ratio)"),
    ("Fees: analysis, reduction or deferral", r"(reduce|waive|defer)[^.]{0,40}fees|fees? (study|reduction|waiver|deferral)"),
    ("Permit processing / streamlining (incl. SB 35)", r"streamlin|sb 35|65913\.4|permit processing"),
    ("Zoning, fee and standards transparency online (§ 65940.1)", r"65940\.1|transparen"),
    ("Water and sewer priority for affordable housing (§ 65589.7)", r"65589\.7|priority (water|sewer)"),
    ("Surplus Land Act / publicly owned sites", r"surplus land|54220|publicly.owned|city.owned|county.owned"),
    ("Lot consolidation / small sites incentives", r"lot consolidation|small sites?[^.]{0,80}incentiv"),
    ("Large sites: lot splits, phasing, specific plans", r"large sites?[^.]{0,120}(subdivi|split|phas|specific plan)"),
    ("Extremely low-income housing actions", r"extremely low.income"),
    ("AFFH: geographic targeting, metrics and milestones", r"geographic targeting|metrics|milestones|numerical targets"),
    ("AFFH: housing mobility / higher-opportunity areas", r"housing mobility|higher.(opportunity|resource|income) areas"),
    ("AFFH: anti-displacement / tenant protections", r"displacement|tenant protection"),
    ("AFFH: place-based revitalization", r"place.based|revitaliz"),
    ("Specific timelines (dates, not 'ongoing')", r"specific (timeline|commitment)|discrete timing|timelines?[^.]{0,60}(year|month|date)"),
]


def pct(a, b):
    return f"{a / b:.0%}" if b else ""


def report(letters, rows, progs, first_in, n7=0):
    bucket = lambda n: "4th+" if n >= 4 else ["1st", "2nd", "3rd"][n - 1]
    B = ["1st", "2nd", "3rd", "4th+"]
    out_l = [l for l in letters if l["finding"] == "Out"]
    full = [l for l in out_l if l["kind"] == "Revisions needed"]
    in_l = [l for l in letters if l["finding"] == "In"]
    n_b = Counter(bucket(l["round"]) for l in full)
    md = ["# What HCD requires: 6th-cycle housing element review letters", "",
          f"From {len(letters):,} 6th-cycle review letters with text ({len(out_l):,} Out, {len(in_l):,} In), by "
          "`scripts/letter_requirements.py`. Each finding is filed under the statutory requirement HCD quotes above it and "
          "tagged with HCD's topic label. *Round* is the letter's place among the jurisdiction's 6th-cycle reviews, counting "
          "every review on the dashboard. Data: [`requirements.csv`](requirements.csv) (one row per finding), "
          "[`letter_outcomes.csv`](letter_outcomes.csv) (one row per letter), [`programs.csv`](programs.csv). "
          + (f"The CSVs also cover {n7:,} 7th-cycle letters; this report waits until the 7th cycle has enough letters to compare." if n7 else ""), ""]

    reached = [v for v in first_in.values() if v]
    md += ["## How many reviews it takes", "",
           f"{len(reached):,} of {len(first_in):,} jurisdictions have an In letter in the 6th cycle. The review on which the first "
           "In letter came (6 = sixth or later):", "", "| Review | Jurisdictions | Share |", "|---|---|---|"]
    rc = Counter(min(v, 6) for v in reached)
    md += [f"| {k} | {v:,} | {pct(v, len(reached))} |" for k, v in sorted(rc.items())]

    kinds = defaultdict(Counter)
    for l in letters:
        kinds[(l["compliance"], l["kind"])][bucket(l["round"])] += 1
    nall = Counter(bucket(l["round"]) for l in letters)
    md += ["", "## What kind of letter each round brings", "",
           "Share of all letters in each round, grouped by HCD's finding. \"Revisions needed\" letters carry the appendix of "
           "findings; the AB 1398 letters find the element meets the law but hold compliance until rezoning is done.", "",
           "| Kind of letter | " + " | ".join(f"{b} ({nall[b]:,})" for b in B) + " |", "|---|" + "---|" * len(B)]
    for comp in ("In compliance", "Out of compliance", "No finding"):
        ks = [k for k in kinds if k[0] == comp]
        if not ks:
            continue
        tot = Counter()
        for k in ks:
            tot.update(kinds[k])
        md.append(f"| **{comp}** | " + " | ".join(f"**{pct(tot[b], nall[b])}**" for b in B) + " |")
        for k in sorted(ks, key=lambda k: (k[1] == "Other", -sum(kinds[k].values()))):
            md.append(f"| &nbsp;&nbsp;&nbsp;{k[1]} | " + " | ".join(pct(kinds[k][b], nall[b]) for b in B) + " |")

    md += ["", "## Requirements HCD finds unmet, by round", "",
           "Share of \"revisions needed\" letters in each round where HCD wrote at least 25 words of its own (not standard "
           f"sentences that appear in {BOILER_MIN}+ letters) under the requirement. The requirement is the statute HCD quotes as "
           "the heading of each finding.", "",
           "| Requirement | Code | " + " | ".join(f"{b} ({n_b[b]:,})" for b in B) + " |", "|---|---|" + "---|" * len(B)]
    req_by = defaultdict(Counter)
    for l in full:
        for q in l["reqs_specific"]:
            req_by[q][bucket(l["round"])] += 1
    for q in sorted(req_by, key=lambda q: -sum(req_by[q].values())):
        if sum(req_by[q].values()) >= 20:
            md.append(f"| {REQ_LABELS.get(q, q)} | {q} | " + " | ".join(pct(req_by[q][b], n_b[b]) for b in B) + " |")

    top_by = defaultdict(Counter)
    for l in full:
        for t in l["topics_specific"]:
            top_by[t][bucket(l["round"])] += 1
    md += ["", "## Issues HCD raises, by round", "",
           "HCD's topic labels within the findings, counted when HCD wrote 25+ words of its own on the topic, as a share of "
           "\"revisions needed\" letters in each round. *Staying power* "
           "is the share in 3rd-and-later letters divided by the share in 1st letters: near 1 or above means the issue "
           "keeps coming back.", "",
           "| Issue | " + " | ".join(B) + " | Staying power |", "|---|" + "---|" * (len(B) + 1)]
    late_n = n_b["3rd"] + n_b["4th+"]
    for t in sorted(top_by, key=lambda t: -sum(top_by[t].values()))[:40]:
        if t == "(no topic label)":
            continue
        sh = [top_by[t][b] / n_b[b] if n_b[b] else 0 for b in B]
        late = (top_by[t]["3rd"] + top_by[t]["4th+"]) / max(1, late_n)
        md.append(f"| {t} | " + " | ".join(f"{x:.0%}" for x in sh) + f" | {late / sh[0]:.2f} |" if sh[0] else
                  f"| {t} | " + " | ".join(f"{x:.0%}" for x in sh) + " | new later |")

    # last hurdles: issues in the last revisions-needed letter before a jurisdiction's first In
    lasts = []
    by_j = defaultdict(list)
    for l in letters:
        by_j[l["jurisdiction"]].append(l)
    for j, ls in by_j.items():
        fi = first_in.get(j)
        prior = [l for l in ls if l["kind"] == "Revisions needed" and (fi is None or l["round"] < fi)]
        if fi and prior:
            lasts.append(max(prior, key=lambda l: l["round"]))
    lt = Counter(t for l in lasts for t in l["topics_specific"] if t != "(no topic label)")
    lr = Counter(q for l in lasts for q in l["reqs_specific"])
    md += ["", "## The last hurdles before compliance", "",
           f"For the {len(lasts):,} jurisdictions that reached an In letter after at least one \"revisions needed\" letter: "
           "what HCD still raised in that last letter before the In.", "", "| Requirement | Share of last letters |", "|---|---|"]
    md += [f"| {REQ_LABELS.get(q, q)} ({q}) | {pct(v, len(lasts))} |" for q, v in lr.most_common(10)]
    md += ["", "| Issue | Share of last letters |", "|---|---|"]
    md += [f"| {t} | {pct(v, len(lasts))} |" for t, v in lt.most_common(15)]

    cm, cs = defaultdict(Counter), defaultdict(Counter)
    for l in full:
        for c in l["commits"]:
            cm[c][bucket(l["round"])] += 1
        for c in l.get("commits_specific", []):
            cs[c][bucket(l["round"])] += 1
    md += ["", "## Program commitments HCD asks for", "",
           "Share of \"revisions needed\" letters whose findings mention each commitment (keyword match). *Written for the letter* "
           f"counts only sentences HCD wrote for that jurisdiction, leaving out standard sentences that appear in {BOILER_MIN}+ letters; "
           "it is the better measure of what HCD actually asked that city or county to do. The round columns use it.", "",
           "| Commitment | Any mention | Written for the letter | " + " | ".join(B) + " |", "|---|---|---|" + "---|" * len(B)]
    for c in sorted(cm, key=lambda c: -sum(cs[c].values())):
        md.append(f"| {c} | {pct(sum(cm[c].values()), len(full))} | {pct(sum(cs[c].values()), len(full))} | "
                  + " | ".join(pct(cs[c][b], n_b[b]) for b in B) + " |")

    words = defaultdict(list)
    for l in full:
        words[bucket(l["round"])].append(l["words"])
    md += ["", "## How much HCD writes", "", "| Round | Revisions-needed letters | Median words of findings | Median words written for the letter |", "|---|---|---|---|"]
    for b in B:
        ws = sorted(words[b])
        sp = sorted(l["specific_words"] for l in full if bucket(l["round"]) == b)
        md.append(f"| {b} | {len(ws):,} | {ws[len(ws) // 2]:,} | {sp[len(sp) // 2]:,} |" if ws else f"| {b} | 0 | | |")

    cat = Counter(p["category"] for p in progs)
    n_in_with = len({p["text_file"] for p in progs})
    md += ["", "## Programs HCD names when it finds compliance", "",
           f"In {n_in_with:,} In letters HCD lists programs the jurisdiction \"must continue timely and effective implementation\" "
           f"of: {len(progs):,} program mentions, grouped by keywords in the program name.", "",
           "| Category | Programs named | Share |", "|---|---|---|"]
    md += [f"| {k} | {v:,} | {pct(v, len(progs))} |" for k, v in cat.most_common()]
    names = Counter(re.sub(r"\s+", " ", p["program"].lower()).strip() for p in progs)
    md += ["", "| Most common program names | Letters |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in names.most_common(30) if v >= 4]

    pf = [r for r in rows if r["finding"] == "Out" and r["topic"] == "Specific programs"]
    md += ["", "## Programs HCD asks to revise", "",
           f"{len(pf):,} findings in Out letters address a specific program by name, grouped by keywords in the program name:", "",
           "| Category | Findings |", "|---|---|"]
    md += [f"| {k} | {v:,} |" for k, v in Counter(category(r["program"]) for r in pf).most_common()]

    pat = HE / "patterns.csv"
    if pat.exists():
        g = [r for r in csv.DictReader(open(pat, encoding="utf-8")) if r.get("out_share") not in ("", None)]
        only_in = [r for r in g if float(r["out_share"]) <= 0.1]
        md += ["", "## Language that appears only when an element is in compliance", "",
               "Standard paragraphs (from `PATTERNS.md`) where 10% or fewer of the letters using them are Out findings.", ""]
        for r in only_in[:12]:
            md += [f"- **{int(r['letters']):,} letters, {r['first_year']}–{r['last_year']}:** {r['example'][:400]}{'…' if len(r['example']) > 400 else ''}"]
    (HE / "REQUIREMENTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
