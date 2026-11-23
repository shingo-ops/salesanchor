#!/bin/bash
# 会社006（審査用）に Meta 審査用の印を付ける（ADR-1055 What 11）。
# 設計 docs/handoff/auth-new-device-approval/review-exempt-design.md 3-10。
# PO が ! で流すか、PO が permit-danger.sh で許した回に Opus が manual-only 鍵で流す。
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
