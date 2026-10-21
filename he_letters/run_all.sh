#!/usr/bin/env bash
# Pull HCD's housing element review letters table, the Housing Element Download Tool table
# (submittals each letter is matched to) and the Review and Compliance Report.
# Usage: bash run_all.sh   -> letters.csv, housing_elements.csv, compliance.csv
set -euo pipefail
cd "$(dirname "$0")"
for r in letters housing_elements compliance; do
  echo "== $r"
  node scrape_report.js --report "$r"
  node decode_report.js --in "${r}_raw.json"
done
echo
echo "Next: python3 extract_letters.py --dry-run, then parse_letters.py and link_submittals.py (see README)"
