#!/bin/bash
# 名簿の共通行 id 10・11（phone・in_person）を全社で外す（is_active=false）。
# 設計 docs/handoff/conversation-unification/phone-off/design.md・card.md。
# PO の委任を受けた Opus が manual-only 鍵で流す。
# 順番: precheck → dryrun → commit → verify（戻すとき: rollback）
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SSH=(ssh -F /dev/null -i "$HOME/.ssh/manual-only/id_ed25519" -o IdentitiesOnly=yes ubuntu@49.212.137.46)
PSQL="docker exec -i astro-webapp-postgres-1 psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1 -X"
step="${1:-}"
case "$step" in
  precheck|dryrun|commit|verify|rollback)
    "${SSH[@]}" "$PSQL" < "$HERE/$step.sql" ;;
  *) echo "使い方: bash run.sh precheck|dryrun|commit|verify|rollback" >&2; exit 2 ;;
esac
