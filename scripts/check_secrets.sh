#!/usr/bin/env bash
# Scan tracked and staged files for things that look like committed secrets.
# Usage: scripts/check_secrets.sh      (exit 1 if anything suspicious is found)
set -euo pipefail
cd "$(dirname "$0")/.."

status=0

if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  echo "ERROR: .env is tracked by git. Remove it with: git rm --cached .env"
  status=1
fi

patterns=(
  'AIza[0-9A-Za-z_-]{35}'                               # Google / Gemini API key
  'sk-[A-Za-z0-9]{20,}'                                 # OpenAI-style key (Whisper)
  '-----BEGIN [A-Z ]*PRIVATE KEY-----'
  '(GEMINI|MOCK_GOV)_API_KEY=[A-Za-z0-9_-]{8,}'           # a filled-in key line
)

files=$(git ls-files --cached --others --exclude-standard | grep -v -E '(^|/)(package-lock\.json)$' || true)
for pattern in "${patterns[@]}"; do
  matches=$(echo "$files" | xargs -r grep -I -n -E -- "$pattern" 2>/dev/null | grep -v 'scripts/check_secrets.sh' || true)
  if [[ -n "$matches" ]]; then
    echo "Possible secret matching /$pattern/:"
    echo "$matches"
    status=1
  fi
done

if [[ $status -eq 0 ]]; then
  echo "Secrets check passed: no secrets found in tracked or unignored files."
fi
exit $status
