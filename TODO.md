# To do: future changes

Add items at the bottom of **Open**. Move them to **Done** with the date when they ship.

## Open

### 7. Review the citation parser against HCD's tags

`hau/CITATIONS.md` now sorts every HCD tag the parser didn't find into: covered by a range the letter cites, **number in the text but missed by the parser**, or not in the letter at all (HCD tagged the topic). Only the middle group is a parser problem; the report lists the most frequent ones with an example each. After the next weekly HAU run, fix those patterns in `scripts/parse_citations.py`. (Oct 2026 run: 47% of tags found before this breakdown existed.)
### 16. Show requested PDFs in the browser

Only for the PDFs in `requested/` (letters obtained from HCD by request and kept on GitHub); the PDF links to HCD's own site already open in the browser. GitHub doesn't display these PDFs in place: its page shows a preview inside GitHub, and the raw file downloads. Show them in a viewer on the site instead, e.g. PDF.js reading the file from GitHub, in the letter reader next to the text, with a fallback link to the file on GitHub.

## Merge migration

### Phase 1. Link citations to the Housing Laws Navigator

Each standardized citation (`65915(o)(8)`) can open the matching section in the Housing Laws Navigator once its link format is known (an anchor or URL parameter per section). Add it in `site/app.js` where the Statutes tab, the Requirements tab and search results show codes.

## Wish list

### AI extraction of what each letter requires (AI model API)

The rules-based analysis files findings by requirement and topic but can't say *what* HCD asked for in plain terms. Add a step that sends each new letter's findings (only the paragraphs HCD wrote for that jurisdiction, from `requirements.csv`) to an AI model with a fixed JSON schema, and saves the answers to `he_letters/ai_findings.csv`:

- `requirement` (Gov. Code cite, checked against the rules-based one), `issue` (fixed list, e.g. nonvacant sites, realistic capacity, AFFH metrics), `deficiency` (one sentence: what is missing), `required_action` (analysis to add, or program commitment, with any deadline or number), `program_ref` (program named, if any), `severity` (new / repeated from prior review / carried over unchanged), `quote` (the sentence it came from, so every answer can be checked).
- Run on new letters only in the weekly job; backfill the ~2,000 6th-cycle letters once. Needs an API key stored as a repository secret. Cache by letter so nothing is re-sent.
- Check quality first on ~50 letters against a hand review; keep the rules-based numbers as the baseline.
- Then: "what HCD asked for" tables by round and requirement, and per-letter summaries on the website and in the weekly issue.


## Done

- 2026-11-09: **Review rounds.** `link_submittals.py`: HCD's previous letter to a jurisdiction (any status or cycle) closes a review round; the first submittal after it starts the clock, and revisions during the review don't reset it. `submittal_date`/`review_days` use the Download Tool date when there is one, else the letter's; the letter-based count is kept in `review_days_text`. New columns `review_start_text`, `review_days_text`, `round_start_tool`, `round_start_tool_type`, `round_submittals`, `review_limit_days` (Gov. Code 65585: 90 for the first submittal of the cycle, 60 after), `review_flags`. Scanned letters (no text layer) are dated from the Tool too; Tool rows use the same name aliases as letters. The "Element" link (`he_pdf_url`) points at the round's first submittal. Tests: `tests/test_link_submittals.py` (weekly job and full re-parse). Site: the timeline marks each review's statutory period; Days over the limit show in red.
- 2026-11-05: HAU letters job runs daily (15:23 UTC) instead of Mondays. It commits only when something changed and opens an issue only when there are new letters; the website redeploys after each run. Review letters stay weekly.
- 2026-11-05: Overview: Latest letters full width, HAU-by-quarter chart below. Jurisdiction lookup: timeline and letters merged into one table (letters and milestones, with a mark matching the timeline; Read/PDF on every row; milestone rows open the letter that names them); hovering a row or mark highlights its match, clicking a mark jumps to its row. "In the letter" column dropped (wording stays in the timeline tooltip). Plainer styling: heavy rules over sections, ink text links, mono dates, underlined table filters.
- 2026-11-05: **Jurisdiction timelines.** `scripts/letter_milestones.py` → `he_letters/milestones.csv`: each letter's milestones in HCD's wording (submittal received for review, revisions received during review, other material received, adopted, posted for public review, meetings with HCD, statutory due date, the HCD letter, Download Tool postings). The Jurisdiction lookup shows them on a timeline with each review period running from the submittal HCD reviewed (60- and 90-day marks from that date; revisions don't restart it), plus a sortable table.
- 2026-11-05: **#14 cycles:** a Cycles menu in the header (6th + 7th by default; 6th, 7th, all, or 5th and earlier) applies to every view of review letters and is remembered. **#15:** count tables break totals down by HAU and cycle in the same row; review-letter trends are drawn one chart per cycle. **#13 restyle:** report style with one sans typeface, ruled sections instead of cards, plain figures instead of tiles, colored markers instead of pills, navy accent.
- 2026-11-05: **#7 diagnostics** added to `hau/CITATIONS.md` (see #7 above for the remaining review).
- 2026-11-05: **Letter–submittal pairing fix** for integration: letters on later modifications pair with the modification submittal (latest "received for review" date); new `first_received_date` and `statutory_due_date` columns in `letters_analysis.csv`; tests in `tests/test_parse_letters.py`.
- 2026-11-01: Fresh-repo fixes: workflows and scripts skip cleanly before any letters are downloaded; runners pinned to Ubuntu 24.04; `setup-python` v6; privacy-check terms match whole words only.
- 2026-11-01: **#18 Fresh repo:** old repo and its history deleted; rebuilt from the current code with one clean first commit. Letter text and data are re-downloaded by the first workflow runs; requested PDFs re-uploaded to `requested/`.
- 2026-10-25: **Privacy:** personal details removed from the repo's files; commits use the GitHub no-reply address; `.env` and key files ignored; `scripts/check_public.py` blocks secrets and `PRIVATE_TERMS` before every commit (hook and Actions) and every deploy.
- 2026-10-24: **#17 Search tab navigation fixed.** Clicking a tab (or Back/Forward) always shows it; returning to Search keeps your results; returning to Requirements, Language and other tabs restores their filters in the address. New `tests/nav_test.py` clicks through every tab on desktop and phone sizes, and the Website workflow runs it before each deploy.
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
