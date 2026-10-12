#!/bin/bash
# PO 用: 段1の PermissionDenied 記録フックを settings.json に登録する。
# - permission-denied-log.sh が無ければエラーで止まる
# - settings.json を settings.json.bak-<日時> に写してから、hooks.PermissionDenied を1件足す
# - 同じものが登録済みなら何もしない
set -euo pipefail

HOOK_SCRIPT="/Users/tanizawashingo/.claude/scripts/permission-denied-log.sh"
SETTINGS="/Users/tanizawashingo/.claude/settings.json"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "$HOOK_SCRIPT" ]; then
  echo "ERROR: $HOOK_SCRIPT が見つかりません。登録を中止します。" >&2
  exit 1
fi

BACKUP="${SETTINGS}.bak-$(date +%Y%m%d%H%M%S)"
cp -p "$SETTINGS" "$BACKUP"
echo "backup: $BACKUP"

python3 "$HERE/po_register_stage1.py" "$SETTINGS"

echo "--- hooks.PermissionDenied (登録後) ---"
python3 -c "import json,sys; print(json.dumps(json.load(open(sys.argv[1])).get('hooks',{}).get('PermissionDenied'), ensure_ascii=False, indent=2))" "$SETTINGS"
