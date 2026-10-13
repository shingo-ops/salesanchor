#!/bin/bash
# PO 用: settings.json の autoMode.allow から「private repo 前提の許可」1件だけを取り除く。
# - 対象がちょうど1件のときだけ、settings.json.bak-<日時> に写してから取り除く
# - 取り除いた文の全文は ~/.claude/logs/removed-allow-<日時>.txt に保存（リポジトリの外）
# - 2回目は「対象なし」で変化なし。対象が2件以上なら何も変えず止まる
# 第1引数で settings.json のパス、第2引数でログ置き場を差し替えられる（試験用。省略時は本物）
set -euo pipefail

SETTINGS="${1:-/Users/tanizawashingo/.claude/settings.json}"
LOG_DIR="${2:-/Users/tanizawashingo/.claude/logs}"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "${SETTINGS}" ]; then
  echo "ERROR: ${SETTINGS} が見つかりません。" >&2
  exit 1
fi

python3 -I "${HERE}/po_remove_private_repo_rule.py" "${SETTINGS}" "${LOG_DIR}"
