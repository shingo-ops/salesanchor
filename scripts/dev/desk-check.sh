#!/usr/bin/env bash
# scripts/dev/desk-check.sh
# 始業3点確認: ①今どこか表示 ②本店(MAINリポジトリ)ならSTOP ③起点が最新mainから離れていれば警告
# 使い方: 机(worktree)のrootで ./scripts/dev/desk-check.sh
# 終了コード: OK=0 / 本店STOP=1
set -uo pipefail

MAIN_REPO="/Users/tanizawashingo/salesanchor"   # 本店(ここでは作業しない)
HERE="$(pwd -P)"
BR="$(git branch --show-current 2>/dev/null || echo '?')"

echo "== desk-check =="
echo "  ディレクトリ : $HERE"
echo "  ブランチ     : $BR"

# ① 本店判定(厳密にパス一致)
if [ "$HERE" = "$MAIN_REPO" ]; then
  echo "  [STOP] ここは本店(MAINリポジトリ)です。作業机(worktree)へ移動してください。"
  exit 1
fi

# ② 起点の鮮度(最新mainからどれだけ離れているか)
git fetch origin --quiet 2>/dev/null
MAIN_TIP="$(git rev-parse origin/main 2>/dev/null || echo '')"
if [ -z "$MAIN_TIP" ]; then
  echo "  [warn] origin/main を取得できません。ネット/認証を確認してください。"
else
  BASE="$(git merge-base HEAD "$MAIN_TIP" 2>/dev/null || echo '')"
  if [ "$BASE" = "$MAIN_TIP" ]; then
    echo "  [OK]   起点は最新mainに追いついています。"
  else
    BEHIND="$(git rev-list --count "${BASE}..${MAIN_TIP}" 2>/dev/null || echo '?')"
    echo "  [warn] 起点が最新mainより ${BEHIND} コミット古いです。最新を取り直してから始めるのを推奨。"
  fi
fi

echo "  [OK]   本店ではありません。作業を開始できます。"
exit 0
