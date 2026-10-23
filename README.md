# HCD letters

This repo keeps two sets of California HCD letters up to date, with their full text, using scheduled GitHub Actions.

| Folder | Source | Schedule |
|---|---|---|
| `hau/` | **HAU letters**: the Housing Accountability Unit's technical assistance, inquiry, ordinance findings and enforcement letters, from the [Technical Assistance and Enforcement Letters Dashboard](https://www.hcd.ca.gov/hau/enforcement-letters) | Mondays 15:23 UTC |
| `he_letters/` | **Housing element review letters**: HCD's findings on draft and adopted housing elements, from the review-letter page of the [Housing Element Download Tool](https://www.hcd.ca.gov/housing-open-data-tools/housing-element-download-tool) | Mondays 15:53 UTC |

Each job does the following:

1. Pulls the dashboard.
2. Compares it with last week and stops if the letter count suddenly drops, which means the dashboard changed.
3. Downloads newly posted PDFs and saves their text.
4. Rebuilds the indexes and commits everything.
5. Opens an issue listing the new letters, which GitHub emails to you.

## Website: HCD Letter Tracker

`site/` is a public web page built from this repo's data and published on GitHub Pages at **https://<your-user>.github.io/hcd-letters/** (for this repo, https://betterleg.github.io/hcd-letters/). It has eight tabs:

- **Overview:** totals, the latest letters, and HAU letters by quarter.
- **Search:** one search across both letter sets. Search by words or an "exact phrase" in the letter text, a code section at any depth (`65915` finds every subdivision, `65915(o)` only (o) and below, `66310-66342` a range, `HSC 17021.5` other codes), a city or county (a county name finds every jurisdiction in it), and filters for source, letter type, housing law, keyword, cycle, finding and dates. Results show a highlighted snippet, can be downloaded as CSV, and every search has its own shareable address. The masthead box searches from any tab.
- **Requirements:** what HCD requires in housing element review letters (6th and 7th cycles, each or together, by county): how many reviews it took to reach compliance, what kind of letter each round brings, the requirements, issues and program commitments HCD raises in each round and which keep coming back, the last hurdles before compliance, and the programs HCD names when it finds compliance. Click any row for its letters.
- **Language:** HCD's standard paragraphs, how many letters use each, how the wording changed over time (changes marked), and which letters use each wording; plus recurring headings.
- **Trends:** HAU letters per quarter by letter type, filterable by housing law; housing element review letters per quarter by finding, filterable by cycle; and a table of housing laws by year.
- **Statutes & keywords:** three rankings, each with a sparkline and a click-through to the letters: HCD's statute tags on HAU letters; **citations found in the letter text** of both sets, at section, subdivision or full depth; and HCD's keywords with spelling variants grouped. A checkbox groups the ADU Law sections (66310–66342) into one row.
- **Compliance:** current status counts from HCD's Review and Compliance Report, 6th-cycle findings by year, days from submittal to letter against the 60- and 90-day review periods, and the jurisdictions out of compliance today.
- **Jurisdiction lookup:** every HAU and review letter for a city or county, with links to the text in this repo and to HCD's PDFs.

Every table can be sorted by clicking a column, filtered, and downloaded as CSV; the page address keeps the sort and filters, so a view can be shared. **Read** opens a letter's text on the site, with a find box, the search words highlighted, and HCD's standard sentences dimmed so its findings for that place stand out; the reader has its own shareable address too.

The **Website** workflow rebuilds the page after each Monday data job, so it stays current on its own. `scripts/build_site_data.py` turns the CSVs into `site/data/*.json`, and `scripts/build_search_index.py` builds the search index in `site/search/`, at build time; neither is committed. The search runs entirely in the browser (no outside service): the index is split into 512 small files, so a search downloads only the pieces for its own words, and snippets load each letter's text from this repo.

**One-time setup:** go to **Settings** → **Pages** → **Build and deployment** → **Source** and choose **GitHub Actions**. Then go to **Actions** → **Website** → **Run workflow**. The page goes live in a minute or two. (GitHub Pages on a private repo needs a paid GitHub plan; on a public repo it's free.)

To preview it in a codespace: `python3 scripts/build_site_data.py && python3 scripts/build_search_index.py && python3 -m http.server -d site 8000`, then open port 8000 from the Ports tab.

## Letters requested from HCD (`requested/`)

Letters the dashboards list as "Contact HCD for a copy" can be added once you have them. Upload the PDFs into `requested/` (on GitHub: **Add file** → **Upload files**; subfolders are fine) and commit. The **Requested letters** workflow then:

1. extracts each PDF's text, using OCR for scans;
2. matches it to its dashboard row: HAU letters by task number (`CSTASK…`) or case number, any letter by jurisdiction + letter date;
3. saves the text with the public letters (`hau/letters/`, `he_letters/letters/`, file names ending `__requested`) and marks that row in `letters_index.csv` as downloaded, `fetched_from` = `requested_from_hcd`;
4. updates the findings, indexes and website, where these letters show a **Requested** tag and a PDF link into this repo.

`requested/README.md` lists every PDF and what it matched, with a **To check** list for any the matcher couldn't place. Fix those in `requested/manifest.csv` (instructions at the bottom of that README). The weekly jobs re-apply the folder after every dashboard pull, so a letter HCD lists later is picked up then. This also covers the five review letters missing from HCD's site (`TODO.md` #4). The repo is public, so anything in `requested/` is public.

## Where to start reading

- `hau/LETTERS.md`: HAU letters by year, letter type, housing law and most-cited statute.
- `he_letters/LETTERS.md`: housing element review letters by year, type and cycle, with HCD's findings and review times.
- `*/index/<year>.md`: every letter that year, with links to its text in this repo, HCD's PDF and, for review letters, the housing element it reviewed.
- `*/CHANGES.md`: what changed in the latest run.

- `he_letters/REQUIREMENTS.md`: what HCD requires, from the 6th-cycle review letters: each finding filed under the statutory requirement it answers (Gov. Code § 65583 subdivisions), what HCD raises on 1st, 2nd, 3rd and later reviews, the issues that keep coming back, the last hurdles before compliance, the program commitments HCD asks for, and the programs it names in compliance letters. Data in `requirements.csv`, `letter_outcomes.csv` and `programs.csv`.
- `*/PATTERNS.md`: HCD's standard language: recurring section headings, boilerplate paragraphs, how many letters use each, and how the wording has changed.
- `*/CITATIONS.md`: the most-cited sections, subdivisions and full citations found in the letter text; for HAU letters, how well they agree with HCD's own tags.

To search the text, use the website's Search tab, or GitHub's search box with "In this repository", e.g. `65915(v) path:hau/letters` or `"sites inventory" path:he_letters/letters`.

### Data files

**`hau/`**

| File | Contents |
|---|---|
| `hau_letters.csv` | One row per letter: task, case number, date, jurisdiction, letter type, housing laws, statutes, keywords, PDF link. |
| `hau_statutes.csv`, `hau_keywords.csv`, `hau_laws.csv` | One row per letter–tag pair, joined on `task`. |
| `citations.csv` | Statute citations found in each letter's text (also in `he_letters/`; see below). |
| `keyword_map.csv` | HCD's raw keywords and the grouped keyword each one counts under on the website. Edit a row's `clean` and set `rule` to `manual` to change a grouping. |
| `letters_index.csv` | Each letter's download status; `local_pdf` points to a PDF in `requested/` for letters requested from HCD. |

**`he_letters/`**

| File | Contents |
|---|---|
| `letters.csv` | The dashboard's letters table. |
| `letters_analysis.csv` | One row per letter, plus these added columns: `finding` (In or Out), `submittal_date`, `review_days`, `he_pdf_url` (the housing element reviewed), and more. |
| `housing_elements.csv` | Every housing element document on the Download Tool. |
| `compliance.csv` | Each jurisdiction's current compliance status, from the Review and Compliance Report. |
| `url_overrides.csv` | Corrected links for broken dashboard links; add rows as you find them. |
| `citations.csv` | Statute citations found in each letter's text. |

**Citation format** (`citations.csv`, both folders): one row per letter and citation, written the same way everywhere so it can be grouped or linked to a code-section tool. `Gov. Code, § 65915, subd. (o)(8)` becomes `65915(o)(8)`; other codes get a prefix (`HSC 17021.5`, `PRC`, `CIV`, `CCP`, `WIC`…). Columns: `normalized`, `level_section` (65915), `level_subdivision` (65915(o)), `count` (mentions in that letter), `in_footnote`, `code_inferred` (true when the letter gave only "section 65583.2"), `raw` (as written) and a `snippet`. The parser handles "§§", lists, "subd./subdivision", "paragraph (2) of subdivision (c) of section…", ranges, "et seq." and "Id."/"Ibid."

## Set it up (one time, about 15 minutes)

1. **Create the repo.** On github.com, go to **+** → **New repository** and name it, e.g., `hcd-letters`. Choose **Private** or **Public**, leave "Add a README" unchecked, and click **Create repository**.
2. **Add the files from a codespace.** On the new repo's page, click **Code** → **Codespaces** → **Create codespace on main**. Drag `hcd-letters_2026-10-20.zip` onto the file list, then in the terminal:
   ```bash
   unzip -o hcd-letters_2026-10-20.zip -d /tmp/x && cp -r /tmp/x/hcd-letters/. . && rm hcd-letters_2026-10-20.zip
   ```
3. **Optional: reuse the review letters you already downloaded.** This saves the first run about 30 minutes. Drag your `letters_out.zip` onto the file list, then:
   ```bash
   unzip -o letters_out.zip -d he_letters/ && rm letters_out.zip
   ```
   This puts `letters/`, `letters.csv` and `letters_index.csv` into `he_letters/`. The first run then fetches only letters that are new since your October download.
4. **Push.**
   ```bash
   git add -A && git commit -m "HCD letters toolkit" && git push
   ```
5. **Let the Actions commit.** Go to **Settings** → **Actions** → **General** → **Workflow permissions**, choose **Read and write permissions**, and click **Save**.
6. **Run each job once by hand.** Go to the **Actions** tab, choose **HAU letters**, and click **Run workflow** → **Run workflow**. Then do the same for **Housing element review letters**. First runs take about 20–40 minutes each, or less if you did step 3; later runs take a few minutes.
7. **Check the results.** Open `hau/LETTERS.md` and `he_letters/LETTERS.md`, and look under **Issues** for the new-letter lists.

To change a schedule, edit the `cron:` line in `.github/workflows/hau-letters.yml` or `he-letters.yml`. The time is in UTC.

## Re-running the analysis

**Actions** → **Analysis** → **Run workflow** rebuilds the citations, standard-language and requirements files from the letter text already in the repo (no dashboard pull, a few minutes), then the website. Use it after changing an analysis script, or to fill the Requirements and Language tabs the first time.

## Notifications

- **New letters:** each job opens an issue listing them, and GitHub emails you if you're watching the repo. To turn the issues off, set `OPEN_ISSUE: "false"` in that workflow.
- **Failures:** GitHub emails you when a scheduled run fails, most likely because HCD republished a dashboard. See below.
- **Inactive repos:** in a public repo with no commits for 60 days, GitHub pauses scheduled runs. Click **Enable workflow** on the Actions tab to restart them.

## When HCD changes a dashboard

The saved queries (`*_template.json`) are tied to each dashboard's internal IDs. When a run fails with "letters fell from…" or a query error, recapture the query in a codespace. The codespace comes with Node, Python and pdftotext installed.

**HAU letters:**

```bash
cd hau && npm install puppeteer
node scrape_report.js --report hau --capture && node make_link_templates.js && bash run_all.sh
```

**Housing element review letters**, Download Tool documents or Compliance Report:

```bash
cd he_letters && npm install puppeteer
node scrape_report.js --report letters --capture            # review letters (page 2)
node scrape_report.js --report housing_elements --capture   # Download Tool documents (page 1)
node scrape_report.js --report compliance --capture         # Review and Compliance Report
bash run_all.sh
```

Add `--list` to any capture command to see the queries on the page first. When the counts look right, commit and push, then run the Action again.

## Running things by hand in a codespace

```bash
cd hau && bash run_all.sh && python3 extract_letters.py --law "Density Bonus" --dry-run
cd he_letters && bash run_all.sh && python3 extract_letters.py --cycle 6 --county "San Diego" --dry-run
```

`extract_letters.py --help` lists each folder's filters.

## Notes

- **HAU letters:** "Contact HCD for a copy" letters have no public PDF; you can request them from HAUportal@hcd.ca.gov and add them to `requested/`. Surplus Land Act and Affordable Housing Preservation Law letters aren't on this dashboard.
- **Housing element review letters, broken links:** about 5% of the dashboard's PDF links are broken. The downloader retries the same file name in two HCD website folders and applies `url_overrides.csv`, which together recovered 98 of 102 broken links in October 2026.
- **Housing element review letters, "Contact HCD":** 3,434 of these letters, mostly before 2019, are listed as "Contact HCD" with no public copy.
- **Cost:** GitHub Actions is free and unlimited for public repos. A private repo uses your account's monthly Actions minutes; two weekly runs of a few minutes each use very little.
