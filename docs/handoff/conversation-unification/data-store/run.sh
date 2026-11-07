#!/bin/bash
# 会話の一本化 便1: 名簿 id 10・11・12（phone・in_person・whatsapp）の会話の置き場を meta_messages にする。
# 設計 docs/handoff/conversation-unification/design.md §4 便1・card-bin1.md §11。
# PO が ! で流す。manual-only 鍵を使う（エージェントは流さない）。便1 の本番反映の後に流す。
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
