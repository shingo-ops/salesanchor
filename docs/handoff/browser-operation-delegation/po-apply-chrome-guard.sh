#!/bin/bash
# po-apply-chrome-guard.sh — ADR-1085 便1（画面操作の見張り chrome-op-guard）を本物（~/.claude/scripts/chrome-op-guard）へ反映する（PO が `!` で実行する）
#
# 流れ: バックアップ → 試作の試験 → 置き場へ写す（権限 555）→ settings.json に登録2件を足す → T16（本物の置き場での自己試験）→ 不合格なら自動で戻す（ROLLED BACK）
# このスクリプトを実行するまで、本物は変わらない。取り消しは po-rollback-chrome-guard.sh。
# `--update`: 反映済みの Mac で、試作と本物の中身が違うファイルだけを入れ替える（settings.json は触らない。T16 不合格ならその入れ替えだけ戻す）。
# 同意の判定は既に取り付け済みの ~/.claude/scripts/consent_check.py（ADR-1033）を使う。
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
W="$(cd "$HERE/../../.." && pwd)"
SRC="$HERE/hooks"
CONSENT_SRC="$HERE/../conversation-consent/hooks"
SCRIPTS="$HOME/.claude/scripts"
DST="$SCRIPTS/chrome-op-guard"
SETTINGS="$HOME/.claude/settings.json"
TEST="$W/scripts/dev/chrome-guard-tests.py"
HELPER="$HERE/po_chrome_settings.py"
ROLLBACK="$HERE/po-rollback-chrome-guard.sh"
TS="$(date +%Y%m%d%H%M%S)"
BK="$SCRIPTS/.backup/chrome-$TS"
DEPLOY_FILES=(chrome_op_guard.py chrome_op_record.py chrome_common.py tiers.json)

UPDATE=""
if [ "$#" -gt 1 ] || { [ "$#" -eq 1 ] && [ "$1" != "--update" ]; }; then
  echo "使い方: po-apply-chrome-guard.sh [--update]"
  exit 2
fi
[ "${1:-}" = "--update" ] && UPDATE=1

registered() { python3 "$HELPER" check "$SETTINGS" >/dev/null 2>&1; }

if [ -z "$UPDATE" ] && [ -f "$DST/chrome_op_guard.py" ] && registered; then
  echo "反映済み（$DST と settings.json の登録2件がある）。何も変更しません。"
  exit 0
fi
if [ -n "$UPDATE" ] && [ ! -f "$DST/chrome_op_guard.py" ]; then
  echo "中止: $DST/chrome_op_guard.py が無い。初回は --update なしで実行してください。"
  exit 1
fi

echo "== ADR-1085 便1 反映 $TS =="
echo "試作: $SRC"
echo "本物: $DST"

[ -f "$HOME/.claude/VOICEVOX_MUTED" ] || { echo "中止: $HOME/.claude/VOICEVOX_MUTED が無い（試験で通知が鳴るため）"; exit 1; }
[ -f "$SETTINGS" ] || { echo "中止: settings.json が無い"; exit 1; }
[ -f "$SCRIPTS/consent_check.py" ] || { echo "中止: $SCRIPTS/consent_check.py が無い（ADR-1033 の取り付けが先）"; exit 1; }

# 許可券が1つでも残っていれば、何も変えずに中止する
if ls "$HOME/.claude/permits"/danger-permit-*.json >/dev/null 2>&1; then
  echo "中止: 許可券のフォルダに danger-permit-*.json がある。"
  ls "$HOME/.claude/permits"/danger-permit-*.json
  exit 1
fi

# 1. バックアップ
mkdir -p "$BK" || { echo "中止: バックアップ先を作れない"; exit 1; }
cp -p "$SETTINGS" "$BK/settings.json" && cmp "$SETTINGS" "$BK/settings.json" || { echo "中止: settings.json のバックアップ失敗"; exit 1; }
if [ -n "$UPDATE" ]; then
  for f in "${DEPLOY_FILES[@]}"; do
    if [ -f "$DST/$f" ]; then
      cp -p "$DST/$f" "$BK/$f" && cmp "$DST/$f" "$BK/$f" || { echo "中止: $f のバックアップ失敗"; exit 1; }
    fi
  done
fi
date -u +%Y-%m-%dT%H:%M:%SZ > "$BK/CHROME_BACKUP"
echo "[1] バックアップ完了: ${BK}"

# 2. 試作の試験（偽の HOME だけを使う）
echo "[2] 試作に対する試験"
TMPD="$(mktemp -d "${TMPDIR:-/tmp}/chrome-guard-apply.XXXXXX")" || { echo "中止: 一時フォルダを作れない"; exit 1; }
if ! python3 -I -B "$TEST" "$SRC" "$CONSENT_SRC" "$TMPD/unit"; then
  echo "中止: 試作の試験が不合格。本物は変えていない。"
  exit 1
fi

# T16: 本物の置き場の見張りに入力を流して確かめる（HOME は一時フォルダ。本物の台帳・記録は書かない）
t16() {
  local guard="$DST/chrome_op_guard.py" th rc ok=0
  th="$(mktemp -d "${TMPDIR:-/tmp}/chrome-guard-t16.XXXXXX")" || return 1
  mkdir -p "$th/.claude/projects/-p" "$th/.claude/logs"
  : > "$th/.claude/projects/-p/t16.jsonl"
  local nav3='{"tool_name":"mcp__claude-in-chrome__navigate","tool_input":{"url":"https://dash.cloudflare.com/abc/billing"},"session_id":"t16","transcript_path":"'"$th"'/.claude/projects/-p/t16.jsonl"}'
  local navok='{"tool_name":"mcp__claude-in-chrome__navigate","tool_input":{"url":"https://example.com/"},"session_id":"t16","transcript_path":"'"$th"'/.claude/projects/-p/t16.jsonl"}'
  local click='{"tool_name":"mcp__claude-in-chrome__computer","tool_input":{"action":"left_click","coordinate":[1,1],"action_summary":"自己試験の押す操作"},"session_id":"t16","transcript_path":"'"$th"'/.claude/projects/-p/t16.jsonl"}'
  printf '%s' "$nav3" | HOME="$th" python3 -B "$guard" >/dev/null 2>&1; rc=$?
  if [ "$rc" -eq 2 ]; then echo "  PASS T16-a 区分3の URL（cloudflare の請求）は exit 2"; else echo "  FAIL T16-a rc=$rc（2 のはず）"; ok=1; fi
  printf '%s' "$navok" | HOME="$th" python3 -B "$guard" >/dev/null 2>&1; rc=$?
  if [ "$rc" -eq 0 ]; then echo "  PASS T16-b 普通の URL は exit 0"; else echo "  FAIL T16-b rc=$rc（0 のはず）"; ok=1; fi
  printf '%s' "$click" | HOME="$th" python3 -B "$guard" >/dev/null 2>&1; rc=$?
  if [ "$rc" -eq 2 ]; then echo "  PASS T16-c 同意なしの押す操作は exit 2"; else echo "  FAIL T16-c rc=$rc（2 のはず）"; ok=1; fi
  rm -f "$th/.claude/projects/-p/t16.jsonl" "$th/.claude/logs"/*.jsonl "$th/.claude/logs"/*.json 2>/dev/null
  return "$ok"
}

# 更新（--update）: 中身が違うファイルだけ入れ替える。settings.json は触らない。
if [ -n "$UPDATE" ]; then
  echo "[3u] 更新: 試作と本物で中身が違うファイルを探す"
  CHANGED=()
  for f in "${DEPLOY_FILES[@]}"; do
    if [ ! -e "$DST/$f" ] || ! cmp -s "$SRC/$f" "$DST/$f"; then CHANGED+=("$f"); fi
  done
  if [ "${#CHANGED[@]}" -eq 0 ]; then
    echo "差なし（試作と本物は同じ）。何も入れ替えません。"
    exit 0
  fi
  UBAD=""
  for f in "${CHANGED[@]}"; do
    [ -e "$DST/$f" ] && chmod u+w "$DST/$f"
    cp "$SRC/$f" "$DST/$f" || { echo "入れ替え失敗 $f"; UBAD=1; }
    chmod 555 "$DST/$f"
    cmp "$SRC/$f" "$DST/$f" && echo "  入れ替え ${f}（権限 555）" || UBAD=1
  done
  if [ -z "$UBAD" ]; then
    echo "[4u] T16（本物の置き場）"
    t16 || UBAD=1
  fi
  if [ -z "$UBAD" ]; then
    echo
    echo "== 結果: 更新成功（入れ替え ${#CHANGED[@]} 件: ${CHANGED[*]}） =="
    echo "バックアップ: $BK"
    exit 0
  fi
  echo
  echo "== 更新が不合格。入れ替えたファイルだけバックアップから戻す =="
  RBF=""
  for f in "${CHANGED[@]}"; do
    if [ -f "$BK/$f" ]; then
      chmod u+w "$DST/$f" 2>/dev/null
      if cp -p "$BK/$f" "$DST/$f" && cmp "$BK/$f" "$DST/$f"; then chmod 555 "$DST/$f"; echo "  復元 $f"; else echo "ROLLBACK FAILED: $f"; RBF=1; fi
    else
      chmod u+w "$DST/$f" 2>/dev/null
      rm -f "$DST/$f"
      if [ -e "$DST/$f" ]; then echo "ROLLBACK FAILED: $f"; RBF=1; else echo "  削除 $f（更新前は無かった）"; fi
    fi
  done
  if [ -n "$RBF" ]; then echo "バックアップ: $BK から手で戻してください。"; exit 3; fi
  echo "ROLLED BACK（更新の入れ替えだけ）"
  exit 1
fi

# 3. 置き場へ写す（権限 555）
echo "[3] 本物へ反映"
BAD=""
mkdir -p "$DST" || { echo "中止: $DST を作れない"; exit 1; }
for f in "${DEPLOY_FILES[@]}"; do
  [ -e "$DST/$f" ] && chmod u+w "$DST/$f"
  cp "$SRC/$f" "$DST/$f" || { echo "反映失敗 $f"; BAD=1; }
  chmod 555 "$DST/$f"
  cmp "$SRC/$f" "$DST/$f" && echo "  反映 ${f}（権限 555）" || BAD=1
done

# settings.json に登録2件（PreToolUse・PostToolUse）を足す（既存の登録は変えない）
smode="$(stat -f %Lp "$SETTINGS")"
chmod u+w "$SETTINGS"
if python3 "$HELPER" add "$SETTINGS"; then
  python3 "$HELPER" check "$SETTINGS" >/dev/null || { echo "settings.json の登録を確認できない"; BAD=1; }
else
  echo "settings.json の登録に失敗"
  BAD=1
fi
chmod "$smode" "$SETTINGS"

# 4. T16
if ls "$HOME/.claude/permits"/danger-permit-*.json >/dev/null 2>&1; then
  echo "danger-permit-*.json が現れた。自己試験を中止して戻す。"
  bash "$ROLLBACK" "$BK"
  exit 1
fi
echo "[4] T16（本物の置き場に対する自己試験）"
t16 || BAD=1

if [ -z "$BAD" ]; then
  echo
  echo "== 結果: 反映成功（T16 全件 PASS） =="
  echo "バックアップ: $BK"
  echo "取り消し: bash $ROLLBACK"
  echo "次: Opus が tabs_context_mcp を1回呼び、chrome-ops.jsonl の tab_context_parsed が true か確かめる（T20）。"
  exit 0
fi

echo
echo "== 自己試験が不合格（または反映に失敗）。自動で戻す =="
bash "$ROLLBACK" "$BK"
RB=$?
[ "$RB" -eq 0 ] || exit 3
exit 1
