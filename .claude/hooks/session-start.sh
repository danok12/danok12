#!/bin/bash
# Ставит расчётные библиотеки из requirements.txt в облачной сессии Claude Code.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"

# Ставить заново, только если requirements.txt или этот скрипт изменились
# с последней успешной установки. Хеш лежит вне репозитория.
hashes="$HOME/.cache/danok12-session-start.sha256"
if ! sha256sum --check --status "$hashes" 2>/dev/null; then
  rm -f "$hashes"
  python3 -m pip install --quiet --disable-pip-version-check --root-user-action=ignore -r requirements.txt
  mkdir -p "$(dirname "$hashes")"
  sha256sum "$PWD/.claude/hooks/session-start.sh" "$PWD/requirements.txt" > "$hashes"
fi
