#!/usr/bin/env bash
# Commit a job's output and push it, surviving other jobs that pushed in the meantime.
#
#   bash scripts/commit_and_push.sh "commit message" "rebuild command" path [path...]
#
# Everything these jobs commit is generated (CSVs, indexes, letter text). If another job
# (the other weekly job, Requested letters, or a manual run) pushed changes to the same files
# while this one ran, a plain rebase conflicts. Then this script keeps this run's version of
# each conflicting file and re-runs the rebuild command, which regenerates the indexes from
# the merged inputs, so both jobs' changes end up in the result.
set -uo pipefail
msg=$1; rebuild=$2; shift 2

git config user.name "github-actions[bot]"
git config user.email "41898283+github-actions[bot]@users.noreply.github.com"
git add -A "$@"
if git diff --cached --quiet; then
  echo "No changes to commit."
  exit 0
fi
git commit -q -m "$msg"

for attempt in 1 2 3 4; do
  if ! git pull --rebase -q; then
    echo "Conflict with a newer commit on main (another job pushed meanwhile). Keeping this run's files and rebuilding."
    git rebase --abort
    if ! git pull --rebase -q -X theirs; then
      git rebase --abort
      echo "::error::Could not merge with newer commits on main; re-run this workflow."
      exit 1
    fi
    bash -c "$rebuild" || exit 1
    git add -A "$@"
    git diff --cached --quiet || git commit -q -m "Rebuild indexes after merging newer commits ($(date -u +%F))"
  fi
  if git push -q; then
    echo "Pushed."
    exit 0
  fi
  echo "Push rejected (main moved again); retrying in $((attempt * 15))s."
  sleep $((attempt * 15))
done
echo "::error::Could not push after 4 tries; re-run this workflow."
exit 1
