"""
Privacy and secrets check for this public repo. Fails (exit 1) before anything is committed or deployed if:

  - a secrets file is tracked or about to be committed: .env, .env.*, *.pem, *.key, *.p12, *.pfx,
    id_rsa*, credentials*.json, secrets/ (".env.example" is allowed);
  - code, docs or settings contain something that looks like a secret: private keys, GitHub / Anthropic /
    OpenAI / AWS / Google tokens, or "API_KEY=..." / "TOKEN=..." / "PASSWORD=..." with a real value;
  - code, docs or settings contain a personal term you list in the PRIVATE_TERMS environment variable
    (comma-separated, e.g. your name and work email). Keep that list in a GitHub secret named PRIVATE_TERMS
    and in your codespace's secrets, never in the repo, so the list itself isn't published.

Letter text, CSVs and other data from HCD are not checked for personal terms: they are public records and
name city staff and consultants.

    python3 scripts/check_public.py            # every tracked file
    python3 scripts/check_public.py --staged   # only what is about to be committed (git hook, Actions)
"""
import os
import re
import subprocess
import sys

SECRET_FILES = re.compile(r"(^|/)(\.env(\..+)?|.+\.(pem|key|p12|pfx)|id_rsa.*|id_ed25519.*|credentials.*\.json|secrets/.*)$", re.I)
ALLOWED_FILES = re.compile(r"(^|/)\.env\.example$")
SECRET_TEXT = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"), "GitHub token"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}"), "GitHub token"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}"), "Anthropic API key"),
    (re.compile(r"\bsk-[A-Za-z0-9]{32,}"), "API key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"), "Google API key"),
    (re.compile(r"\b[A-Z0-9_]*(API_KEY|SECRET|TOKEN|PASSWORD)\s*[=:]\s*['\"]?(?!\$|\{\{|<|your|xxx|\*\*\*)[A-Za-z0-9_\-/+=]{12,}", re.I), "credential assignment"),
]
# Only code, docs and settings are checked for text; data folders are HCD's public records.
TEXT_FILES = re.compile(r"\.(py|js|mjs|sh|yml|yaml|json|md|html|css|toml|cfg|ini|txt)$|(^|/)\.[\w.-]+$", re.I)
# Generated reports in hau/ and he_letters/ (LETTERS.md, PATTERNS.md, patterns.json...) quote the letters, which can
# name consultants and staff, so they are treated as data too.
DATA_DIRS = re.compile(r"^(hau|he_letters)/(letters|index)/|^(hau|he_letters)/[^/]+\.(md|json)$|^requested/|^site/(data|search)/|_template\.json$|\.csv$")


def files(staged):
    cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"] if staged else ["git", "ls-files"]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return [f for f in out.splitlines() if f]


def main():
    staged = "--staged" in sys.argv
    terms = [t.strip().lower() for t in os.environ.get("PRIVATE_TERMS", "").split(",") if t.strip()]
    problems = []
    for f in files(staged):
        if SECRET_FILES.search(f) and not ALLOWED_FILES.search(f):
            problems.append(f"{f}: secrets file must not be committed (it's in .gitignore; run: git rm --cached '{f}')")
            continue
        if DATA_DIRS.search(f) or not TEXT_FILES.search(f) or not os.path.isfile(f):
            continue
        try:
            text = open(f, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for rx, what in SECRET_TEXT:
            m = rx.search(text)
            if m:
                line = text.count("\n", 0, m.start()) + 1
                problems.append(f"{f}:{line}: looks like a {what}")
        low = text.lower()
        for t in terms:
            # whole words only, so a short term does not match inside longer words
            m = re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", low)
            if m:
                problems.append(f"{f}:{low.count(chr(10), 0, m.start()) + 1}: contains a term from PRIVATE_TERMS")
    if problems:
        print("Privacy check failed. Nothing was committed or deployed.\n  " + "\n  ".join(problems))
        sys.exit(1)
    print(f"Privacy check OK ({'staged files' if staged else 'all tracked files'}"
          f"{', with PRIVATE_TERMS' if terms else ', no PRIVATE_TERMS set'}).")


if __name__ == "__main__":
    main()
