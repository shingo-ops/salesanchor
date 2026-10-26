#!/bin/bash
# po-apply-consent.sh — ADR-1033（会話での同意）のフックを本物（~/.claude/scripts）へ反映する（PO が `!` で実行する）
#
# 流れ: バックアップ → 試作の試験 → 本物へ反映（settings.json に登録を1件足す）→ 本物の試験 → 不合格なら自動で戻す（ROLLED BACK）
# このスクリプトを実行するまで、本物のフックは変わらない。取り消しは po-rollback-consent.sh。
# `--update`: 反映済みの Mac で、試作と本物の中身が違うファイルだけを入れ替える（settings.json は触らない。試験不合格ならその入れ替えだけ戻す）。
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
W="$(cd "$HERE/../../.." && pwd)"
SRC="$HERE/hooks"
DST="$HOME/.claude/scripts"
SETTINGS="$HOME/.claude/settings.json"
BRIDGE="$HOME/.codex/salesanchor/permit_bridge.py"
TEST="$W/scripts/dev/test-agent-hooks.sh"
HELPER="$HERE/po_settings_matcher.py"
ROLLBACK="$HERE/po-rollback-consent.sh"
TS="$(date +%Y%m%d%H%M%S)"
BK="$DST/.backup/$TS"

# 元からある4ファイル（バックアップ・復元の対象）と、反映する5ファイル（consent_check.py は新規）
ORIG_FILES=(agent-danger-hook.sh worktree-only-guard.sh pr-body-guard.sh danger_sanitize.py)
DEPLOY_FILES=(agent-danger-hook.sh worktree-only-guard.sh pr-body-guard.sh danger_sanitize.py consent_check.py)

UPDATE=""
[ "${1:-}" = "--update" ] && UPDATE=1

if [ -z "$UPDATE" ] && [ -f "$DST/consent_check.py" ]; then
  echo "反映済み（$DST/consent_check.py が既にある）。何も変更しません。"
  exit 0
fi
if [ -n "$UPDATE" ] && [ ! -f "$DST/consent_check.py" ]; then
  echo "中止: $DST/consent_check.py が無い。初回は --update なしで実行してください。"
  exit 1
fi

echo "== ADR-1033 反映 $TS =="
echo "試作: $SRC"
echo "本物: $DST"

[ -f "$HOME/.claude/VOICEVOX_MUTED" ] || { echo "中止: $HOME/.claude/VOICEVOX_MUTED が無い（試験で通知が鳴るため）"; exit 1; }
[ -f "$SETTINGS" ] || { echo "中止: settings.json が無い"; exit 1; }
[ -f "$BRIDGE" ] || { echo "中止: permit_bridge.py が無い（バックアップできない）"; exit 1; }

# 本物の試験は使い捨て許可券を消費しかねない。1つでも残っていれば、何も変えずに中止する。
if ls "$HOME/.claude/permits"/danger-permit-*.json >/dev/null 2>&1; then
  echo "中止: 許可券のフォルダに danger-permit-*.json がある（本物の試験が消費しかねない）。"
  ls "$HOME/.claude/permits"/danger-permit-*.json
  exit 1
fi

# 1. バックアップ
mkdir -p "$BK" || { echo "中止: バックアップ先を作れない"; exit 1; }
for f in "${ORIG_FILES[@]}"; do
  cp -p "$DST/$f" "$BK/$f" || { echo "中止: バックアップ失敗 $f"; exit 1; }
  cmp "$DST/$f" "$BK/$f" || { echo "中止: バックアップが一致しない $f"; exit 1; }
done
cp -p "$SETTINGS" "$BK/settings.json" && cmp "$SETTINGS" "$BK/settings.json" || { echo "中止: settings.json のバックアップ失敗"; exit 1; }
cp -p "$BRIDGE" "$BK/permit_bridge.py" && cmp "$BRIDGE" "$BK/permit_bridge.py" || { echo "中止: permit_bridge.py のバックアップ失敗"; exit 1; }
if [ -n "$UPDATE" ]; then
  cp -p "$DST/consent_check.py" "$BK/consent_check.py" && cmp "$DST/consent_check.py" "$BK/consent_check.py" || { echo "中止: consent_check.py のバックアップ失敗"; exit 1; }
fi
date -u +%Y-%m-%dT%H:%M:%SZ > "$BK/CONSENT_BACKUP"
echo "[1] バックアップ完了: ${BK}（フック4・settings.json・permit_bridge.py 一致）"

# 2. 試作の試験
echo "[2] 試作に対する試験"
if ! bash "$TEST" "$SRC"; then
  echo "中止: 試作の試験が不合格。本物は変えていない。"
  exit 1
fi

# 更新（--update）: 中身が違うファイルだけ入れ替える。settings.json は触らない。初回の流れ（[3] 以降）には入らない。
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
    if [ -e "$DST/$f" ]; then
      mode="$(stat -f %Lp "$DST/$f")"
      chmod u+w "$DST/$f"
    else
      mode="555"
    fi
    cp "$SRC/$f" "$DST/$f" || { echo "入れ替え失敗 $f"; UBAD=1; }
    chmod "$mode" "$DST/$f"
    cmp "$SRC/$f" "$DST/$f" && echo "  入れ替え ${f}（権限 ${mode}）" || UBAD=1
  done

  if ls "$HOME/.claude/permits"/danger-permit-*.json >/dev/null 2>&1; then
    UBAD=1
    echo "danger-permit-*.json が現れた。本物の試験を中止して、入れ替えを戻す。"
  else
    echo "[4u] 本物に対する試験"
    T_START="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "  試験開始: $T_START"
    bash "$TEST" "$DST" --real-home
    TEST_RC=$?
    T_END="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "  試験終了: $T_END"
    mkdir -p "$HOME/.claude/logs"
    echo "$T_START $T_END po-apply-consent real-home-test rc=$TEST_RC" >> "$HOME/.claude/logs/test-runs.log"
    [ "$TEST_RC" -eq 0 ] || UBAD=1
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
      bmode="$(stat -f %Lp "$BK/$f")"
      chmod u+w "$DST/$f" 2>/dev/null
      if cp -p "$BK/$f" "$DST/$f" && cmp "$BK/$f" "$DST/$f"; then
        chmod "$bmode" "$DST/$f"
        echo "  復元 $f"
      else
        echo "ROLLBACK FAILED: $f"; RBF=1
      fi
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

# 3. 本物へ反映（権限を記録 → chmod u+w → cp → 権限を戻す）
echo "[3] 本物へ反映"
BAD=""
for f in "${DEPLOY_FILES[@]}"; do
  if [ -e "$DST/$f" ]; then
    mode="$(stat -f %Lp "$DST/$f")"
    chmod u+w "$DST/$f"
  else
    mode="555"
  fi
  cp "$SRC/$f" "$DST/$f" || { echo "反映失敗 $f"; BAD=1; }
  chmod "$mode" "$DST/$f"
  cmp "$SRC/$f" "$DST/$f" && echo "  反映 ${f}（権限 ${mode}）" || BAD=1
done

# settings.json に MultiEdit|NotebookEdit の登録を1件足す（既存の登録は変えない）
smode="$(stat -f %Lp "$SETTINGS")"
chmod u+w "$SETTINGS"
if python3 "$HELPER" add "$SETTINGS"; then
  python3 "$HELPER" check "$SETTINGS" >/dev/null || { echo "settings.json の登録を確認できない"; BAD=1; }
else
  echo "settings.json の登録に失敗"
  BAD=1
fi
chmod "$smode" "$SETTINGS"

# 4. 本物の試験
if ls "$HOME/.claude/permits"/danger-permit-*.json >/dev/null 2>&1; then
  echo "danger-permit-*.json が現れた。本物の試験を中止して戻す。"
  bash "$ROLLBACK" "$BK"
  exit 1
fi
echo "[4] 本物に対する試験"
T_START="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "  試験開始: $T_START"
bash "$TEST" "$DST" --real-home
TEST_RC=$?
T_END="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "  試験終了: $T_END"
mkdir -p "$HOME/.claude/logs"
echo "$T_START $T_END po-apply-consent real-home-test rc=$TEST_RC" >> "$HOME/.claude/logs/test-runs.log"

if [ "$TEST_RC" -eq 0 ] && [ -z "$BAD" ]; then
  echo
  echo "== 結果: 反映成功（全件 PASS） =="
  echo "バックアップ: $BK"
  echo "取り消し: bash $ROLLBACK"
  exit 0
fi

echo
echo "== 本物の試験が不合格（または反映に失敗）。自動で戻す =="
bash "$ROLLBACK" "$BK"
RB=$?
[ "$RB" -eq 0 ] || exit 3
exit 1
