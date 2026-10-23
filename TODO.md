# To do: future changes

Add items at the bottom of **Open**. Move them to **Done** with the date when they ship.

## Open

### 7. Review the citation parser against HCD's tags

After the first weekly HAU run, check the agreement figure at the top of `hau/CITATIONS.md` and spot-check about 50 letters. Tune `scripts/parse_citations.py` where it misses.

### 13. Restyle the website so it looks hand-made, not generated

The site uses a common pattern (serif headline, card grid, teal accent, uppercase eyebrow labels, KPI tiles) that reads as AI-built. Give it its own identity:

- A distinct look: e.g. a planning-document or civic-report style (strong grid, rules instead of rounded cards, a restrained palette tied to HCD/California planning documents, real typographic hierarchy), or match Ascent's own report style.
- Drop the generic elements: rounded card shadows, uppercase eyebrows, pill badges, KPI tiles with big serif numbers, "dek" subtitle under the title.
- Charts: one consistent chart style with direct labels instead of legends where possible.
- Copy: shorter, plainer headings and notes written the way you'd write them.
- Decide with a mockup or two before changing the CSS.

### 14. Default to the 6th and 7th cycles everywhere

Every tab, chart, table and report (website and the `*.md` reports) starts with the 6th and 7th cycles. A cycle control on each lets you:

- see the 6th cycle only, the 7th cycle only, or both together (the default);
- bring in earlier cycles (5th, 4th, and letters with no cycle listed), each alone or with the others.

HAU letters have no cycle; they stay in their own views, with a date range instead. The choice is kept in the page address so it can be shared. Done so far: the Requirements tab (6th and 7th, each or together).

### 15. Show totals together, split trends

- **Counts and overall topics** (letter frequency, most-cited requirements, issues, statutes, keywords): show one combined table, with the number of letters and the breakdown by cycle (and by source, HAU vs. review letters) side by side in the same row.
- **Analysis and trends over time:** split by cycle, and by source, as separate series or small multiples, so 6th- and 7th-cycle patterns (and HAU vs. review letters) aren't blended.
- **Search** stays combined, since it can already be narrowed to HAU letters, review letters, or a cycle.

### 16. Show requested PDFs in the browser

Only for the PDFs in `requested/` (letters obtained from HCD by request and kept on GitHub); the PDF links to HCD's own site already open in the browser. GitHub doesn't display these PDFs in place: its page shows a preview inside GitHub, and the raw file downloads. Show them in a viewer on the site instead, e.g. PDF.js reading the file from GitHub, in the letter reader next to the text, with a fallback link to the file on GitHub.

## Merge migration

### Phase 1. Link citations to the Housing Laws Navigator

Each standardized citation (`65915(o)(8)`) can open the matching section in the Housing Laws Navigator once its link format is known (an anchor or URL parameter per section). Add it in `site/app.js` where the Statutes tab and search results show codes.


## Wish list

### AI extraction of what each letter requires (Claude API)

The rules-based analysis files findings by requirement and topic but can't say *what* HCD asked for in plain terms. Add a step that sends each new letter's findings (only the paragraphs HCD wrote for that jurisdiction, from `requirements.csv`) to Claude with a fixed JSON schema, and saves the answers to `he_letters/ai_findings.csv`:

- `requirement` (Gov. Code cite, checked against the rules-based one), `issue` (fixed list, e.g. nonvacant sites, realistic capacity, AFFH metrics), `deficiency` (one sentence: what is missing), `required_action` (analysis to add, or program commitment, with any deadline or number), `program_ref` (program named, if any), `severity` (new / repeated from prior review / carried over unchanged), `quote` (the sentence it came from, so every answer can be checked).
- Run on new letters only in the weekly job; backfill the ~2,000 6th-cycle letters once. Needs an `ANTHROPIC_API_KEY` repository secret. Cache by letter so nothing is re-sent.
- Check quality first on ~50 letters against a hand review; keep the rules-based numbers as the baseline.
- Then: "what HCD asked for" tables by round and requirement, and per-letter summaries on the website and in the weekly issue.


## Done

- 2026-10-23: **Analysis** workflow (manual) to rebuild citations, standard language and requirements without a dashboard pull; analysis steps in the weekly jobs can no longer block saving new letters; numpy installed from Ubuntu packages.
- 2026-10-23: Search and the letter reader work on older iPhones (iOS before 16.4): removed a JavaScript feature those versions of Safari can't read.
- 2026-10-22: **#9 Language tab** (standard paragraphs with use by year, each wording with changes marked, the letters using it, recurring headings). **#11 plain letter-kind labels** (compliance as its own field). **#12 Requirements tab and charts** (reviews to compliance, kinds of letters by round, requirements / issues / commitments by round with staying power, last hurdles, programs in compliance letters; cycle and county controls) and **sortable, filterable tables with CSV download on every tab**, with sort and filters kept in the page address. **#16 (text part) letter reader**: every "Read" link opens the letter on the site, with find-in-letter, search words highlighted, HCD's standard sentences dimmed, and a shareable link.
- 2026-10-22: Dropped: request the five missing review letters from HCD (was #4).
- 2026-10-22: **Requirements analysis** (`scripts/letter_requirements.py` → `he_letters/REQUIREMENTS.md`): findings tied to the statutory requirement they answer, by review round, staying power, last hurdles before compliance, program commitments, programs named in compliance letters.
- 2026-10-22: **Standard-language analysis** (`scripts/letter_patterns.py` → `PATTERNS.md`, `patterns.csv` in both folders, weekly): recurring headings, boilerplate paragraphs and their variants.
- 2026-10-22: **#8 California date on the website**: the "Updated …" stamp shows the date in Pacific time (it was the UTC date, so evening builds showed tomorrow).
- 2026-10-22: **#3 letter-trends analyses**: closed; the trends analyses were built fresh as part of this project (the website's Trends, Statutes and Compliance tabs) rather than brought over from the separate project.
- 2026-10-22: **#1 statute citations** (`scripts/parse_citations.py` → `hau/citations.csv`, `he_letters/citations.csv`, `CITATIONS.md`; subdivision "(o)" kept as the letter o, as written in the statute). **#2 ADU grouping** (checkbox on the Statutes tab). **#5 search** (Search tab: words and exact phrases, code sections at any depth, city or county, filters, CSV download, shareable links; built with no outside service by `scripts/build_search_index.py`). **Keyword cleanup** (`scripts/clean_keywords.py` → `hau/keyword_map.csv`).
- 2026-10-22: `requested/` folder for letters obtained from HCD by request: text (with OCR), auto-matching to dashboard rows, indexes, website tag, and a workflow that runs on upload.
- 2026-10-20: HAU and housing element review-letter weekly jobs, issue-size fix, Node 22 update, HCD Letter Tracker website.
