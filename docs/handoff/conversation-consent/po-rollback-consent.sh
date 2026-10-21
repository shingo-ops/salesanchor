#!/bin/bash
# po-rollback-consent.sh — ADR-1033（会話での同意）の反映を取り消し、バックアップから全部戻す（PO が `!` で実行する）
#
# 使い方: bash po-rollback-consent.sh [バックアップのフォルダ]
#   引数なし: ~/.claude/scripts/.backup の中で、po-apply-consent.sh が作った一番新しいもの（CONSENT_BACKUP の印つき）
# 戻すもの: 元からあった4ファイル（agent-danger-hook.sh / worktree-only-guard.sh / pr-body-guard.sh / danger_sanitize.py）、
#           settings.json（MultiEdit|NotebookEdit の登録が消える）、permit_bridge.py（念のための写し）。
#           consent_check.py は新規ファイルなので削除する。danger_sanitize.py は反映前から有ったものを戻す。
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DST="$HOME/.claude/scripts"
SETTINGS="$HOME/.claude/settings.json"
BRIDGE="$HOME/.codex/salesanchor/permit_bridge.py"

ORIG_FILES=(agent-danger-hook.sh worktree-only-guard.sh pr-body-guard.sh danger_sanitize.py)

BK="${1:-}"
if [ -z "$BK" ]; then
  BK="$(ls -1d "$DST"/.backup/*/ 2>/dev/null | while read -r d; do [ -f "${d}CONSENT_BACKUP" ] && echo "${d%/}"; done | sort | tail -1)"
fi
if [ -z "$BK" ] || [ ! -f "$BK/CONSENT_BACKUP" ]; then
  echo "中止: 戻し元のバックアップ（CONSENT_BACKUP の印つき）が見つからない。"
  exit 1
fi
echo "== ADR-1033 取り消し =="
echo "戻し元: $BK"

failed=""
for f in "${ORIG_FILES[@]}"; do
  if [ ! -f "$BK/$f" ]; then
    # 反映前に無かったファイルは取り除く
    chmod u+w "$DST/$f" 2>/dev/null
    rm -f "$DST/$f"
    if [ -e "$DST/$f" ]; then echo "ROLLBACK FAILED: $f（削除できない）"; failed=1; else echo "  削除 $f（反映前は無かった）"; fi
    continue
  fi
  chmod u+w "$DST/$f" 2>/dev/null
  if cp -p "$BK/$f" "$DST/$f" && cmp "$BK/$f" "$DST/$f"; then
    echo "  復元 $f"
  else
    echo "ROLLBACK FAILED: $f"
    failed=1
  fi
done

# 新規ファイル consent_check.py を取り除く
chmod u+w "$DST/consent_check.py" 2>/dev/null
rm -f "$DST/consent_check.py"
if [ -e "$DST/consent_check.py" ]; then echo "ROLLBACK FAILED: consent_check.py"; failed=1; else echo "  削除 consent_check.py"; fi

# settings.json（登録の追加を取り消す。バックアップの写しで丸ごと戻す）
if [ -f "$BK/settings.json" ]; then
  smode="$(stat -f %Lp "$SETTINGS" 2>/dev/null || echo 600)"
  chmod u+w "$SETTINGS" 2>/dev/null
  if cp -p "$BK/settings.json" "$SETTINGS" && cmp "$BK/settings.json" "$SETTINGS"; then
    chmod "$smode" "$SETTINGS" 2>/dev/null
    echo "  復元 settings.json"
  else
    echo "ROLLBACK FAILED: settings.json"
    failed=1
  fi
fi

# permit_bridge.py は変えていないが、写しと違っていれば戻す
if [ -f "$BK/permit_bridge.py" ] && ! cmp -s "$BK/permit_bridge.py" "$BRIDGE"; then
  bmode="$(stat -f %Lp "$BRIDGE" 2>/dev/null || echo 644)"
  chmod u+w "$BRIDGE" 2>/dev/null
  if cp -p "$BK/permit_bridge.py" "$BRIDGE" && cmp "$BK/permit_bridge.py" "$BRIDGE"; then
    chmod "$bmode" "$BRIDGE" 2>/dev/null
    echo "  復元 permit_bridge.py"
  else
    echo "ROLLBACK FAILED: permit_bridge.py"
    failed=1
  fi
fi

if [ -n "$failed" ]; then
  echo "バックアップ: $BK から手で戻してください。"
  exit 3
fi
echo "ROLLED BACK"
exit 0
