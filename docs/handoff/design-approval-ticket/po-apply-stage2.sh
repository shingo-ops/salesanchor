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

# 1. バックアップ
mkdir -p "$BK" || { echo "中止: バックアップ先を作れない"; exit 1; }
for f in "${ORIG_FILES[@]}"; do
  cp -p "$DST/$f" "$BK/$f" || { echo "中止: バックアップ失敗 $f"; exit 1; }
  cmp "$DST/$f" "$BK/$f" || { echo "中止: バックアップが一致しない $f"; exit 1; }
done
echo "[1] バックアップ完了: $BK（5ファイル一致）"

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
    mode="644"
  fi
  cp "$SRC/$f" "$DST/$f" || { echo "反映失敗 $f"; BAD=1; }
  chmod "$mode" "$DST/$f"
  cmp "$SRC/$f" "$DST/$f" && echo "  反映 $f（権限 $mode）"
done

# 4. 本物の試験
echo "[4] 本物に対する試験"
if bash "$TEST" "$DST" --real-home && [ -z "${BAD:-}" ]; then
  echo
  echo "== 結果: 反映成功（全件 PASS） =="
  echo "バックアップ: $BK"
  echo "次の手順: bash $HERE/po-register-stage2-allow.sh"
  exit 0
fi

# 5. 自動で戻す
echo
echo "== 本物の試験が不合格。自動で戻す =="
for f in "${ORIG_FILES[@]}"; do
  chmod u+w "$DST/$f" 2>/dev/null
  cp -p "$BK/$f" "$DST/$f"
  cmp "$BK/$f" "$DST/$f" && echo "  復元 $f"
done
# 新規ファイル（元には無かった）は取り除く
rm -f "$DST/danger_sanitize.py"
echo "ROLLED BACK"
exit 1
