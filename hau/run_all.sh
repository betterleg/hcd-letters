#!/usr/bin/env bash
# Pull HCD's Technical Assistance and Enforcement Letters Dashboard and build hau_letters.csv.
# Usage: bash run_all.sh
set -euo pipefail
cd "$(dirname "$0")"
for r in hau hau_statutes hau_keywords hau_laws; do
  echo "== $r"
  node scrape_report.js --report "$r"
  node decode_report.js --in "${r}_raw.json"
done
python3 merge_hau.py
echo
echo "Next: python3 extract_letters.py --dry-run   (downloads the letter PDFs as text)"
