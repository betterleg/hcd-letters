#!/usr/bin/env bash
# Full re-parse of the letters already in this repo (no dashboard pull):
# requested letters, findings and submittal dates, milestones, citations, keywords,
# standard language, requirements, and the Markdown indexes.
#
#   bash scripts/reparse_all.sh
#
# Used by the Analysis workflow (Actions tab -> Analysis -> Run workflow). Safe to run in a Codespace too.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Requested letters"
python3 scripts/requested_letters.py

echo "== Review letters: findings, received/submittal dates, review time"
( cd he_letters
  python3 ../tests/test_parse_letters.py
  python3 ../tests/test_link_submittals.py
  python3 parse_letters.py . letters_parsed.json
  python3 link_submittals.py letters_parsed.json housing_elements.csv letters_linked.json letters_analysis.csv )

echo "== Citations and keywords"
python3 scripts/parse_citations.py hau
python3 scripts/parse_citations.py he
python3 scripts/clean_keywords.py

echo "== Standard language, requirements, milestones"
python3 scripts/letter_patterns.py he
python3 scripts/letter_patterns.py hau
python3 scripts/letter_requirements.py
python3 scripts/letter_milestones.py

echo "== Indexes"
python3 scripts/build_index.py hau
python3 scripts/build_he_index.py he_letters
