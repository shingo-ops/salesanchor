#!/bin/bash
# po-rollback-chrome-guard.sh — ADR-1085 便1（chrome-op-guard）の反映を取り消す（PO が `!` で実行する）
#
# 使い方: bash po-rollback-chrome-guard.sh [バックアップのフォルダ]
#   引数なし: ~/.claude/scripts/.backup の中で、po-apply-chrome-guard.sh が作った一番新しいもの（CHROME_BACKUP の印つき）
# 戻すもの: settings.json の登録2件を外し、置き場 ~/.claude/scripts/chrome-op-guard を消す。
#           settings.json が「登録2件以外は変わっていない」ことをバックアップと比べて確かめる。
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS="$HOME/.claude/scripts"
DST="$SCRIPTS/chrome-op-guard"
SETTINGS="$HOME/.claude/settings.json"
HELPER="$HERE/po_chrome_settings.py"
DEPLOY_FILES=(chrome_op_guard.py chrome_op_record.py chrome_common.py tiers.json)

[ -f "$HOME/.claude/VOICEVOX_MUTED" ] || { echo "中止: $HOME/.claude/VOICEVOX_MUTED が無い"; exit 1; }
if ls "$HOME/.claude/permits"/danger-permit-*.json >/dev/null 2>&1; then
  echo "中止: 許可券のフォルダに danger-permit-*.json がある。"
  exit 1
fi

BK="${1:-}"
if [ -z "$BK" ]; then
  BK="$(ls -1d "$SCRIPTS"/.backup/*/ 2>/dev/null | while read -r d; do [ -f "${d}CHROME_BACKUP" ] && echo "${d%/}"; done | sort | tail -1)"
fi
if [ -z "$BK" ] || [ ! -f "$BK/CHROME_BACKUP" ]; then
  echo "中止: 戻し元のバックアップ（CHROME_BACKUP の印つき）が見つからない。"
  exit 1
fi
echo "== ADR-1085 便1 取り消し =="
echo "戻し元: $BK"

failed=""

# 登録2件を外す
if [ -f "$SETTINGS" ]; then
  smode="$(stat -f %Lp "$SETTINGS" 2>/dev/null || echo 600)"
  chmod u+w "$SETTINGS" 2>/dev/null
  if python3 "$HELPER" remove "$SETTINGS"; then
    chmod "$smode" "$SETTINGS" 2>/dev/null
  else
    echo "ROLLBACK FAILED: settings.json の登録を外せない"
    failed=1
  fi
  # 登録以外が変わっていないことを確かめる（バックアップから登録を外した形と、今の形を、中身で比べる）
  if [ -f "$BK/settings.json" ]; then
    if python3 - "$BK/settings.json" "$SETTINGS" <<'PYEOF'
import json, sys
def strip(d):
    hooks = d.get("hooks", {})
    for ev in ("PreToolUse", "PostToolUse"):
        if ev in hooks:
            hooks[ev] = [e for e in hooks[ev] if "/chrome-op-guard/" not in json.dumps(e)]
    return d
a = strip(json.load(open(sys.argv[1], encoding="utf-8")))
b = strip(json.load(open(sys.argv[2], encoding="utf-8")))
def norm(d):
    h = d.get("hooks", {})
    for ev in list(h):
        if h[ev] == []:
            del h[ev]
    return json.dumps(d, sort_keys=True, ensure_ascii=False)
sys.exit(0 if norm(a) == norm(b) else 1)
PYEOF
    then
      echo "  確認 settings.json は登録2件以外が変わっていない"
    else
      echo "ROLLBACK FAILED: settings.json が登録以外も変わっている。バックアップ $BK/settings.json と見比べてください"
      failed=1
    fi
  fi
else
  echo "  settings.json が無い（飛ばす）"
fi

# 置き場を消す（ファイルを1つずつ消してから空のフォルダを消す）
if [ -d "$DST" ]; then
  for f in "${DEPLOY_FILES[@]}"; do
    chmod u+w "$DST/$f" 2>/dev/null
    rm -f "$DST/$f"
    if [ -e "$DST/$f" ]; then echo "ROLLBACK FAILED: $f（削除できない）"; failed=1; else echo "  削除 $f"; fi
  done
  rm -f "$DST"/*.pyc 2>/dev/null
  rmdir "$DST" 2>/dev/null
  if [ -e "$DST" ]; then echo "ROLLBACK FAILED: $DST に想定外のファイルが残っている"; failed=1; else echo "  削除 $DST"; fi
else
  echo "  置き場は既に無い"
fi

if [ -n "$failed" ]; then
  echo "バックアップ: $BK から手で戻してください。"
  exit 3
fi
echo "ROLLED BACK"
exit 0
