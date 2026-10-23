# Letters requested from HCD

PDFs of letters that HCD's dashboards list as "Contact HCD for a copy", obtained by request. Each weekly job (and any push to this folder) extracts their text, matches them to the dashboard and adds them to the indexes and the website, marked *requested from HCD*. Instructions are at the bottom of this page.

**5 PDFs**: 4 matched to a dashboard letter, 1 to check. Updated 2026-10-23.

## Need a look

Fix these in [`manifest.csv`](manifest.csv) (see below).

| File | Status | What the script found |
|---|---|---|
| [Beverly-Hills-SB-79-Review-050826 (1).pdf](Beverly-Hills-SB-79-Review-050826%20%281%29.pdf) | no_match | no dashboard row for a jurisdiction named in it within 3 days of 2026-05-08 |

## All requested letters

| File | Source | Jurisdiction | Letter date | Type / task | Match | Text |
|---|---|---|---|---|---|---|
| [oceanside-hau-3630-sb-79-out-101526.pdf](oceanside-hau-3630-sb-79-out-101526.pdf) | HAU | Oceanside | 2026-10-15 | CSTASK0027553 | auto | [text](../hau/letters/Oceanside_SB_79_Ordinance-Alternative_Plan_Finding_2026-10-15_HAU0003630__requested.txt) |
| [palo alto-hau-3614-sb-79-in-101326 (1).pdf](palo%20alto-hau-3614-sb-79-in-101326%20%281%29.pdf) | HAU | Palo Alto | 2026-10-13 | CSTASK0027530 | auto | [text](../hau/letters/Palo_Alto_SB_79_Ordinance-Alternative_Plan_Finding_2026-10-13_HAU0003614__requested.txt) |
| [culver-city-sb79-101226.pdf](culver-city-sb79-101226.pdf) | HAU | Culver City | 2026-10-12 | CSTASK0027480 | auto | [text](../hau/letters/Culver_City_SB_79_Ordinance-Alternative_Plan_Finding_2026-10-12_HAU0003603__requested.txt) |
| [Pasadena-3572-sb-79-out-092526.pdf](Pasadena-3572-sb-79-out-092526.pdf) | HAU | Pasadena | 2026-09-25 | CSTASK0027329 | auto | [text](../hau/letters/Pasadena_SB_79_Ordinance-Alternative_Plan_Finding_2026-09-25_HAU0003572__requested.txt) |
| [Beverly-Hills-SB-79-Review-050826 (1).pdf](Beverly-Hills-SB-79-Review-050826%20%281%29.pdf) |  |  |  |  | no_match | [text](text/Beverly-Hills-SB-79-Review-050826%20%281%29.txt) |

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
