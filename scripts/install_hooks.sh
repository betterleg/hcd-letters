#!/usr/bin/env bash
# Run once in a codespace or clone (the devcontainer runs it for you):
#  - commits use your GitHub no-reply address instead of a personal email
#  - a pre-commit hook runs scripts/check_public.py on what you're about to commit
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
user="${GITHUB_USER:-$(git config user.name || true)}"
if [ -n "$user" ]; then
  git config user.name "$user"
  git config user.email "${user}@users.noreply.github.com"
fi
git config pull.rebase true
cat > .git/hooks/pre-commit <<'HOOK'
#!/usr/bin/env bash
exec python3 scripts/check_public.py --staged
HOOK
chmod +x .git/hooks/pre-commit
echo "Commits will be signed as: $(git config user.name) <$(git config user.email)>; privacy check hook installed."
