#!/bin/bash
# 共用6行の投入（設計 docs/handoff/channel-master-shared/design.md §3・§6 の2・ADR-1007 決定1）。
# PO が ! で流す。manual-only 鍵を使う（エージェントは流さない）。
# 順番: precheck → dryrun → commit → verify（戻すとき: rollback。PR-B を戻した後だけ）
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
