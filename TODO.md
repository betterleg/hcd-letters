# To do: future changes

Add items at the bottom of **Open**. Move them to **Done** with the date when they ship.

## Open

### 1. Parse detailed statute citations from letter text

**Goal:** a citation dataset at the level of each subdivision, for both letter sets, using one standard format so each citation can link to a tool that displays that code section.

**Why:** HCD's Statutory Reference tags on the HAU dashboard stop at the section (`65915`), and housing element review letters have no tags at all. The letters themselves cite down to the subdivision, often in footnotes, e.g. *Gov. Code, § 65915, subd. (o)(8)*.

**Standard format:** `section(subdivision)(paragraph)(subparagraph)`, with letters kept lowercase and no spaces.

| As written in the letter | Standardized |
|---|---|
| Gov. Code, § 65915, subd. (o)(8) | `65915(o)(8)` |
| Government Code section 65583.2, subdivision (c) | `65583.2(c)` |
| Gov. Code, § 65583, subd. (c)(10)(A) | `65583(c)(10)(A)` |
| Gov. Code, §§ 65584.09, 65913.4 | `65584.09`, `65913.4` (two rows) |
| Gov. Code, § 65915, subds. (b) and (f) | `65915(b)`, `65915(f)` (two rows) |
| Health & Saf. Code, § 17021.5 | `HSC 17021.5` (prefix for anything other than the Government Code) |

- Keep the case as written inside the brackets: `(c)(10)(A)` has a capital A.
- Subdivision "(o)" is the letter o, not zero. The note that started this item wrote `65915(0)(8)`, so confirm before building.
- Other codes get short prefixes: `HSC` Health & Safety, `PRC` Public Resources, `CIV` Civil, `CCP` Code of Civil Procedure. Government Code citations get no prefix.

**Output:** a new `citations.csv` in each folder (`hau/`, `he_letters/`), one row per citation found:

| Column | Contents |
|---|---|
| letter key | `task` for HAU letters; PDF link for review letters |
| `code` | GOV, HSC, … |
| `section` | e.g. 65915 |
| `subdivision_path` | e.g. (o)(8) |
| `normalized` | e.g. 65915(o)(8) |
| `level_section` | 65915 |
| `level_subdivision` | 65915(o) |
| `raw` | the citation exactly as written |
| `in_footnote` | true/false, best effort |
| `snippet` | about 200 characters of surrounding text |

The three `level_*` columns let the site and the code-section tool group citations at any depth.

**Parsing notes:**

- Forms to handle:
  - "Gov. Code", "Government Code", "GC"
  - "§", "§§", "section", "sections"
  - "subd.", "subds.", "subdivision"
  - "para.", "paragraph"
  - "et seq."
  - ranges ("§§ 65580-65589.11")
  - lists joined by "and" or commas
  - "id." / "ibid." (point back to the previous citation)
- pdftotext puts footnotes at the bottom of each page. To flag `in_footnote`, use the line position on the page, or a footnote number at the start of the line.
- To check accuracy, compare section-level results with HCD's Statutory Reference tags on HAU letters, then spot-check about 50 letters by hand.

**Wire-in:**

- **Code:** add `parse_citations.py` to both folders, plus a step in each weekly workflow after the text download.
- **Site:** add a "Cited sections" view to the Statutes tab, at section, subdivision or full depth.
- **Links:** add each normalized citation as a link to the code-section tool (Housing Laws Navigator?). That needs that tool's URL or anchor format.

### 2. Group or hide the ADU section run in statute rankings

HCD tags every ADU ordinance letter with §§ 66310–66321, so they top the Statutes tab. Add an option to collapse them into one "ADU Law (66310–66342)" row, or to exclude ADU ordinance letters.

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

### 5. Search interface on the website

**Goal:** one search box on the HCD Letter Tracker that finds letters across both sets (HAU and housing element review). Results can be filtered and combined.

**Search by:**

- **Code section:** e.g. `65915`, `65915(o)`, `65915(o)(8)`. The search matches at the depth typed, so `65915` also finds every subdivision under it. This uses HCD's statute tags now, and `citations.csv` once item #1 ships.
- **Text in the letters:** words or exact phrases in the full letter text, e.g. `"sites inventory"`, `"no net loss"`, `parking`. Each result shows a highlighted snippet with the match.
- **Jurisdiction:** city or county, and county name to get every jurisdiction in it.
- **Other filters:**
  - letter source (HAU or housing element review)
  - letter type
  - housing law
  - cycle
  - HCD finding (In/Out)
  - keyword tag
  - date range
  - has public text or PDF

**Results:** a list showing date, jurisdiction, letter type, finding or law, matched code sections and a text snippet, with links to the text in the repo, HCD's PDF and the jurisdiction's page. Results can be sorted by date or relevance. The results can be downloaded as CSV, and the URL stores the search so it can be shared.

**How (to decide):**

- **Build:** a full-text index built weekly by the Website job from `hau/letters/*.txt`, `he_letters/letters/*.txt` and `requested/text/*.txt` (requested letters not on either dashboard). The text is about 50 MB, so the index needs to be split or compressed so the page stays fast. Options:
  - a client-side search library (MiniSearch or Lunr) with a sharded index
  - Pagefind, which builds a static, chunked index made for this kind of site
  - Check index size and load time before choosing.
- **Code search:** a small separate index from `citations.csv` or the statute tags, so code lookups load instantly.
- **Snippets:** store each letter's text alongside the index, or fetch it from the repo when a result is opened.

**Fit with the site:** a new "Search" tab, plus a search box in the masthead on every tab. Jurisdiction and statute links elsewhere on the site open pre-filled searches.

## Done

- 2026-10-22: `requested/` folder for letters obtained from HCD by request: text (with OCR), auto-matching to dashboard rows, indexes, website tag, and a workflow that runs on upload.
- 2026-10-20: HAU and housing element review-letter weekly jobs, issue-size fix, Node 22 update, HCD Letter Tracker website.
