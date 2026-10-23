# To do: future changes

Add items at the bottom of **Open**. Move them to **Done** with the date when they ship.

## Open

### 3. Add analyses from the HCD letter-trends project

Bring that project's charts and metrics into the website once its files are shared.

### 4. Request the five missing review letters from HCD

These are listed as `failed` in `he_letters/letters_index.csv`:

- Calistoga, 10/9/2023
- Arroyo Grande, 12/10/2020
- Arcata, 10/28/2020
- Portola Valley revocation, 3/2024
- St. Helena revocation, 3/2024

Also confirm the Alturas and San Diego (6/16/2020) letters that `url_overrides.csv` matched by file name only.

When HCD sends them, upload them to `requested/`; they match like any requested letter.

### 6. Link citations to the Housing Laws Navigator

Each standardized citation (`65915(o)(8)`) can open the matching section in the Housing Laws Navigator once its link format is known (an anchor or URL parameter per section). Add it in `site/app.js` where the Statutes tab and search results show codes.

### 7. Review the citation parser against HCD's tags

After the first weekly HAU run, check the agreement figure at the top of `hau/CITATIONS.md` and spot-check about 50 letters. Tune `scripts/parse_citations.py` where it misses.

## Done

- 2026-10-22: **#1 statute citations** (`scripts/parse_citations.py` → `hau/citations.csv`, `he_letters/citations.csv`, `CITATIONS.md`; subdivision "(o)" kept as the letter o, as written in the statute). **#2 ADU grouping** (checkbox on the Statutes tab). **#5 search** (Search tab: words and exact phrases, code sections at any depth, city or county, filters, CSV download, shareable links; built with no outside service by `scripts/build_search_index.py`). **Keyword cleanup** (`scripts/clean_keywords.py` → `hau/keyword_map.csv`).
- 2026-10-22: `requested/` folder for letters obtained from HCD by request: text (with OCR), auto-matching to dashboard rows, indexes, website tag, and a workflow that runs on upload.
- 2026-10-20: HAU and housing element review-letter weekly jobs, issue-size fix, Node 22 update, HCD Letter Tracker website.
