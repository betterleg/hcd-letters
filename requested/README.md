# Letters requested from HCD

PDFs of letters that HCD's dashboards list as "Contact HCD for a copy", obtained by request. Each weekly job (and any push to this folder) extracts their text, matches them to the dashboard and adds them to the indexes and the website, marked *requested from HCD*. Instructions are at the bottom of this page.

**0 PDFs**: 0 matched to a dashboard letter, 0 to check. Updated 2026-10-22.

## All requested letters

| File | Source | Jurisdiction | Letter date | Type / task | Match | Text |
|---|---|---|---|---|---|---|

## How to add letters

1. Upload the PDFs into this folder: on GitHub, **Add file** → **Upload files**, or drag them into a codespace. Subfolders are fine; a `hau/` or `he/` subfolder tells the matcher which dashboard to look in.
2. Commit. The **Requested letters** workflow runs on its own, matches each PDF, saves its text and rebuilds the website.
3. Check **Need a look** above. File names that help the matcher: HCD's own (`sbd-adelanto-draft-out-051024.pdf`), or jurisdiction + date (`Adelanto 2014-03-05.pdf`). For HAU letters, the task number (`CSTASK0027569.pdf`).

## Fixing a match in manifest.csv

Edit the PDF's row and set `match` to `manual`:

- **HAU letter:** `source` = `hau`, `task` = the CSTASK number from `hau/hau_letters.csv`.
- **Review letter:** `source` = `he`, `jurisdiction` and `letter_date` exactly as in `he_letters/letters.csv` (`letter_date` is its `reviewed` date), plus `type` if that jurisdiction has two letters that day.
- **Not on either dashboard:** `match` = `not_on_dashboard`. Its text stays in `text/` and is searchable.
- **Skip a file:** `match` = `ignore`.

This repo is public, so anything here is public. Letters HCD sends on request are public records; don't add anything with personal information you wouldn't post.
