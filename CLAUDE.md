# CLAUDE.md: hcd-letters

Context for Claude Code sessions on this repo. Owner: Matt Gelbman (AICP, Senior Urban Planner, Ascent Environmental), who works in California housing law. Write for a planner, not a developer: say what changed and what to check, not how the code works.

## What this repo is

This repo holds weekly scrapes of three of HCD's Power BI dashboards, the full text of every public letter, and a public website built from them.

| Folder | Source | Weekly job |
|---|---|---|
| `hau/` | Technical Assistance and Enforcement Letters Dashboard (Housing Accountability Unit). One row per letter, plus statute, keyword and housing-law tags. | `.github/workflows/hau-letters.yml` (Mon 15:23 UTC) |
| `he_letters/` | Housing Element Download Tool: review letters (page 2), housing element documents (page 1), and the Review and Compliance Report. | `.github/workflows/he-letters.yml` (Mon 15:53 UTC) |
| `site/` | HCD Letter Tracker website on GitHub Pages (betterleg.github.io/hcd-letters) | `.github/workflows/pages.yml` (after each data job) |
| `requested/` | PDFs Matt obtained from HCD by request ("Contact HCD" letters), plus `manifest.csv` (match per PDF) and a generated `README.md` | `.github/workflows/requested-letters.yml` (on push to `requested/`); also re-applied by both weekly jobs |
| (analysis) | Citations, standard language, requirements, rebuilt from text in the repo | `.github/workflows/analysis.yml` (manual) |
| `scripts/` | Run comparison and issue body (`compare_runs.py`), Markdown indexes (`build_index.py`, `build_he_index.py`), citations (`parse_citations.py`), keyword grouping (`clean_keywords.py`), requested letters, site data (`build_site_data.py`) and search index (`build_search_index.py`), safe push (`commit_and_push.sh`) | used by the workflows |

`TODO.md` is the backlog. Update it when items ship: move them to **Done** with the date.

## How the scrapers work

- **No browser.** Each `*_template.json` is a saved Power BI query. `scrape_report.js` sends it to `wabi-us-gov-iowa-api.analysis.usgovcloudapi.net/public/reports/querydata` with the report's `X-PowerBI-ResourceKey` and pages through the results 500 rows at a time. `decode_report.js` turns the response into CSV.
- **Decoding rules:**
  - Columns are mapped by their position in the response (G0…, M0) through the response `descriptor`. Never map them by position on screen.
  - The `R` bitmask means "repeat the value from the previous row"; the `Ø` bitmask means null.
  - Value dictionaries are per page.
  - Dates are wall-clock times stored as UTC epoch milliseconds.
  - The first row of each later page repeats the previous page's last row and is flagged `RF`. Skip it.
- **Templates must be recaptured when HCD republishes a dashboard** (`--capture`, needs puppeteer):
  - `hau`: `node scrape_report.js --report hau --capture && node make_link_templates.js`. The statute, keyword and law templates are built from the main one, because those fields only exist as filters on the dashboard.
  - `he_letters`: `--report letters` (page 2), `--report housing_elements` (page 1; clicks the disclaimer and keeps the table's built-in filter), `--report compliance` (page 3).
- **`extract_letters.py`** downloads PDFs into memory and keeps text only.
  - It is resumable: existing `.txt`/`.json` pairs are skipped.
  - It writes `letters_index.csv`, a status for every row.
  - Review letters with a broken dashboard link fall back to `url_overrides.csv`, then two hcd.ca.gov folders. These recovered 98 of 102 broken links in October 2026.
  - "Contact HCD" rows have no public PDF.
- **`he_letters` analysis:**
  - `parse_letters.py` finds each letter's In/Out finding (from HCD's file-name label, else the letter's wording; about 97% agreement) and its received, adopted and revision dates.
  - `link_submittals.py` matches each letter to its Download Tool submittal (`submittal_date`, `review_days`).

- **`scripts/requested_letters.py`** runs after `extract_letters.py` (which rewrites `letters_index.csv` each week) and re-applies every PDF in `requested/`:
  - Text via pdftotext, or tesseract OCR when there's no text layer.
  - Matching: HAU task/case number in the file name or text; else jurisdiction named in the file name/text + a date within 3 days of the dashboard date. Ties or misses go to `needs_review` / `no_match` in `manifest.csv`.
  - `manual`, `not_on_dashboard` and `ignore` manifest rows are never changed by the script. Unmatched text goes to `requested/text/`.
  - Matched rows get `status=downloaded`, `fetched_from=requested_from_hcd`, `text_file`, and `local_pdf` (repo path). The site and index builders key these on jurisdiction + date + type (review letters) or task (HAU), since they have no public URL.

- **`scripts/parse_citations.py hau|he`** writes `citations.csv` and `CITATIONS.md` in each folder from the letter text (format `65915(o)(8)`, other codes prefixed `HSC 17021.5`). Runs after the text download in both weekly jobs and in Requested letters. Bare "section 65583.2" gets `code_inferred=true` (the letter's own explicit code for that section if any, else HSC for 17000s/50000–53999, else GOV). Test cases are in the module docstring; on 2,043 review letters about 99% of 6xxxx section numbers in the text are captured.
- **`scripts/clean_keywords.py`** writes `hau/keyword_map.csv` (raw keyword → grouped). Rows with `rule=manual` are Matt's and are never overwritten. Raw tags in `hau_letters.csv` stay as HCD wrote them.
- **Search** (`scripts/build_search_index.py`, Website job only): unigram + bigram inverted index in 512 fnv1a-hashed shards under `site/search/`. The tokenizer and hash in `site/app.js` (`toks`, `fnv1a`) must match the Python. Snippets fetch letter text from raw.githubusercontent.com, so the repo must stay public for snippets to work.

- **`scripts/letter_patterns.py hau|he`** (weekly; needs numpy) writes `PATTERNS.md` and `patterns.csv`: recurring headings and near-duplicate paragraph groups (MinHash on 5-word shingles, Jaccard 0.5; variants at 0.85) after replacing names, dates and numbers with placeholders. On the Oct 2026 review letters: 92 paragraph groups in 25+ letters, about 75 seconds.

- **`scripts/letter_requirements.py`** (review letters, weekly, after `letter_patterns.py`) splits each 6th-cycle letter at HCD's quoted requirements (quotes ending "(Gov. Code, § 65583, subd. (x)(n).)"; quotes without a cite are recognized from openings learned from cited ones), files each paragraph under that requirement, and tags it with HCD's topic label ("Realistic Capacity:", normalized via `TOPIC_SYNONYMS`). Round = order among the jurisdiction's 6th-cycle reviews. "Specific" counts ignore sentences that appear in 25+ letters. Writes `REQUIREMENTS.md`, `requirements.csv`, `letter_outcomes.csv`, `programs.csv`. Oct 2026: 29,051 findings from 2,012 letters. Careful: `65583.2` must not match as `65583` (see `RX_REQ_END`).

- **Website tabs added Oct 2026:** Requirements (`site/data/requirements.json` from `he_letters/letter_outcomes.csv` + `programs.csv`), Language (`site/data/language.json` from `*/patterns.json` + hashes of standard sentences; `sentence_key()` in `build_site_data.py` must match `sentenceKey()` in `app.js`), and the letter reader (`openReader()`). All tables use `dataTable()` in `app.js` (sort, filter, CSV, state in the page address via `params()`/`setParams()`).

## Baseline numbers (Oct 2026), for sanity-checking runs

- **HAU:** 1,376 letters, 1,320 with text, 55 Contact HCD.
  - Tags: 5,760 statute tags (537 distinct), 1,939 keyword tags, 1,535 housing-law tags.
- **Review letters:** 5,594 letters, 2,154 with text, 3,434 Contact HCD.
  - 5 PDFs are missing everywhere (listed in `TODO.md`).
- **Compliance report:** 539 jurisdictions. Statuses: In 521, Out 16, Enforcement Out 1, blank 1.

The workflows fail on purpose if the letter count drops more than 5% or by more than 25.

## Working rules

- **Never commit** raw `*_raw.json`, `*_captures.json` or `site/data/` (all in `.gitignore`). Do commit `letters/`, the CSVs and the `*.md` indexes.
- **Don't edit data by hand** in `hau/letters`, `he_letters/letters` or the CSVs. Change the scripts and let the Action regenerate.
- **The Actions also push to `main`.** Pull before committing; this repo uses `pull.rebase true`. The workflows commit through `scripts/commit_and_push.sh`: when another job pushed to the same files meanwhile, it keeps this run's version of the conflicting files and re-runs the rebuild steps, so indexes come out right.
- **Issue bodies are capped:** 100 rows per section and under 65,536 characters. First runs skip the issue.
- **Preview the site:** `python3 scripts/build_site_data.py && python3 scripts/build_search_index.py && python3 -m http.server -d site 8000`.
  - Site code is vanilla JS with d3 7.9.0 from cdnjs. Fonts are Newsreader, Public Sans and IBM Plex Mono. Colors are CSS tokens with light and dark themes.
- **Network:** HCD sites, Power BI, `hcdpowerbi.blob.core.windows.net` and the `wabi-…usgovcloudapi.net` API must be reachable. Ascent's Claude cloud workspace blocks them; GitHub Actions and Codespaces do not.

## Related

- Matt's Housing Laws Navigator (a claude.ai artifact of California housing statutes) is the likely target for statute links (TODO: Merge migration, Phase 1).
- The earlier one-off toolkits (`hcd_pipeline`, `hcd_letters_pipeline`, `hcd_hau_pipeline`) are superseded by this repo.
