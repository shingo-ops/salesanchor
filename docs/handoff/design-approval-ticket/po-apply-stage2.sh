#!/bin/bash
# po-apply-stage2.sh — 段2のフック修正版を本物（~/.claude/scripts）へ反映する（PO が `!` で実行する）
#
# 流れ: バックアップ → 試作の試験 → 本物へ反映 → 本物の試験 → 不合格なら自動で戻す（ROLLED BACK）
# このスクリプトを実行するまで、本物のフックは変わらない。
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
W="$(cd "$HERE/../../.." && pwd)"
SRC="$HERE/stage2-hooks"
DST="$HOME/.claude/scripts"
TEST="$W/scripts/dev/test-agent-hooks.sh"
TS="$(date +%Y%m%d%H%M%S)"
BK="$DST/.backup/$TS"

# 元からある5ファイル（バックアップ・復元の対象）と、反映する4ファイル
ORIG_FILES=(worktree-only-guard.sh agent-danger-hook.sh pr-body-guard.sh worktree-access-guard.sh extract-pr-body.py)
DEPLOY_FILES=(worktree-only-guard.sh agent-danger-hook.sh pr-body-guard.sh danger_sanitize.py)

echo "== 段2 反映 $TS =="
echo "試作: $SRC"
echo "本物: $DST"

[ -f "$HOME/.claude/VOICEVOX_MUTED" ] || { echo "中止: $HOME/.claude/VOICEVOX_MUTED が無い（試験で通知が鳴るため）"; exit 1; }

# 本物の試験は使い捨て許可チケットを消費しかねない。1つでも残っていれば、何も変えずに中止する。
if ls "$HOME/.claude/permits"/danger-permit-*.json >/dev/null 2>&1; then
  echo "中止: $HOME/.claude/permits/ に danger-permit-*.json がある（本物の試験が消費しかねない）。"
  ls "$HOME/.claude/permits"/danger-permit-*.json
  exit 1
fi

# 1. バックアップ
mkdir -p "$BK" || { echo "中止: バックアップ先を作れない"; exit 1; }
for f in "${ORIG_FILES[@]}"; do
  cp -p "$DST/$f" "$BK/$f" || { echo "中止: バックアップ失敗 $f"; exit 1; }
  cmp "$DST/$f" "$BK/$f" || { echo "中止: バックアップが一致しない $f"; exit 1; }
done
echo "[1] バックアップ完了: ${BK}（5ファイル一致）"

# 2. 試作の試験
echo "[2] 試作に対する試験"
if ! bash "$TEST" "$SRC"; then
  echo "中止: 試作の試験が不合格。本物は変えていない。"
  exit 1
fi

# 3. 本物へ反映（権限を記録 → chmod u+w → cp → 権限を戻す）
echo "[3] 本物へ反映"
for f in "${DEPLOY_FILES[@]}"; do
  if [ -e "$DST/$f" ]; then
    mode="$(stat -f %Lp "$DST/$f")"
    chmod u+w "$DST/$f"
  else
    mode="555"
  fi
  # danger_sanitize.py は agent-danger-hook.sh と同じ 555（r-xr-xr-x）にする
  [ "$f" = "danger_sanitize.py" ] && mode="555"
  cp "$SRC/$f" "$DST/$f" || { echo "反映失敗 $f"; BAD=1; }
  chmod "$mode" "$DST/$f"
  cmp "$SRC/$f" "$DST/$f" && echo "  反映 ${f}（権限 ${mode}）"
done

# 自動で戻す。cp・cmp の失敗を検出し、失敗したら ROLLBACK FAILED を表示して exit 3 で終える。
rollback() {
  echo
  echo "== 本物の試験が不合格（または試験できず）。自動で戻す =="
  local failed=""
  for f in "${ORIG_FILES[@]}"; do
    chmod u+w "$DST/$f" 2>/dev/null
    if cp -p "$BK/$f" "$DST/$f" && cmp "$BK/$f" "$DST/$f"; then
      echo "  復元 $f"
    else
      echo "ROLLBACK FAILED: $f"
      failed="1"
    fi
  done
  # 新規ファイル（元には無かった）は取り除く
  chmod u+w "$DST/danger_sanitize.py" 2>/dev/null
  if ! rm -f "$DST/danger_sanitize.py" || [ -e "$DST/danger_sanitize.py" ]; then
    echo "ROLLBACK FAILED: danger_sanitize.py"
    failed="1"
  fi
  if [ -n "$failed" ]; then
    echo "バックアップ: $BK から手で戻してください。"
    exit 3
  fi
  echo "ROLLED BACK"
  exit 1
}

# 4. 本物の試験
# (a) 使い捨て許可チケットが残っていれば、本物の試験が消費しかねないので中止する（再確認）
if ls "$HOME/.claude/permits"/danger-permit-*.json >/dev/null 2>&1; then
  echo "danger-permit-*.json が現れた。本物の試験を中止して戻す。"
  rollback
fi
# (b) 試験の開始・終了時刻を表示し、test-runs.log にも1行残す（段1の記録 agent-events.jsonl から試験分を除く目印）
echo "[4] 本物に対する試験"
T_START="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "  試験開始: $T_START"
bash "$TEST" "$DST" --real-home
TEST_RC=$?
T_END="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "  試験終了: $T_END"
mkdir -p "$HOME/.claude/logs"
echo "$T_START $T_END po-apply-stage2 real-home-test rc=$TEST_RC" >> "$HOME/.claude/logs/test-runs.log"

if [ "$TEST_RC" -eq 0 ] && [ -z "${BAD:-}" ]; then
  echo
  echo "== 結果: 反映成功（全件 PASS） =="
  echo "バックアップ: $BK"
  echo "次の手順: bash $HERE/po-register-stage2-allow.sh"
  exit 0
fi
rollback
