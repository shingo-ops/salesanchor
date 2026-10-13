#!/bin/bash
# PO 用: 段2の恒常許可（B2・B3・B4）を settings.json の autoMode.allow の末尾に追記する。
# - settings.json を settings.json.bak-<日時> に写してから追記する
# - 同じ文が既にあれば何もしない（2回実行しても変わらない）
# 第1引数で settings.json のパスを差し替えられる（試験用。省略時は本物）
set -euo pipefail

SETTINGS="${1:-/Users/tanizawashingo/.claude/settings.json}"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "$SETTINGS" ]; then
  echo "ERROR: $SETTINGS が見つかりません。" >&2
  exit 1
fi

BACKUP="${SETTINGS}.bak-$(date +%Y%m%d%H%M%S)"
cp -p "$SETTINGS" "$BACKUP"
echo "backup: $BACKUP"

python3 "$HERE/po_register_stage2_allow.py" "$SETTINGS"

python3 -c "import json,sys; a=json.load(open(sys.argv[1])).get('autoMode',{}).get('allow',[]); print('autoMode.allow entries:', len(a))" "$SETTINGS"
