#!/usr/bin/env bash
# SessionStart 鮮度チェック（MTG決定 C / ADR-042）。
# 役割: ローカルの開発ルール（CLAUDE.md / STANDARD-WORKFLOW.md 等）が origin/develop より
#       遅れていれば「pull を推奨」と警告する。stdout は SessionStart で Claude のコンテキストに注入される。
# 原則: 非破壊（fetch のみ・自動 pull しない）／非ブロッキング（常に exit 0）／fail-open（失敗は黙ってスキップ）。
set -uo pipefail

# リポ外なら何もしない
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -n "$ROOT" ] || exit 0
cd "$ROOT" || exit 0

# 非破壊 fetch。低速/オフラインは 5 秒で打ち切り（macOS に timeout(1) が無いため git 側で上限）。
# 失敗（ネット無し等）は黙ってスキップ。
git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=5 fetch origin develop --quiet 2>/dev/null || exit 0

# origin/develop が取れなければ何もしない
git rev-parse --verify --quiet origin/develop >/dev/null || exit 0

# 開発ルールの正本。HEAD と origin/develop の共通祖先（merge-base）時点の各ファイルと、
# origin/develop 時点の各ファイルの blob を直接比較する。差があれば「merge-base 以降に
# origin/develop 側でルールが更新された」＝こちらが遅れている。
# blob 直比較なので①history simplification の影響を受けず②このブランチ自身がルールを
# 編集していても誤警告しない（merge-base 起点で develop 側の前進だけを見る）。
RULES="CLAUDE.md docs/STANDARD-WORKFLOW.md backend/CLAUDE.md frontend/CLAUDE.md"
BASE="$(git merge-base HEAD origin/develop 2>/dev/null)" || exit 0
[ -n "$BASE" ] || exit 0

stale_files=""
for f in $RULES; do
  base_blob="$(git rev-parse --quiet --verify "$BASE:$f" 2>/dev/null || true)"
  dev_blob="$(git rev-parse --quiet --verify "origin/develop:$f" 2>/dev/null || true)"
  # develop 側に存在し、base と blob が異なる → そのファイルは更新されている
  if [ -n "$dev_blob" ] && [ "$base_blob" != "$dev_blob" ]; then
    stale_files="${stale_files}${stale_files:+, }${f}"
  fi
done

if [ -n "$stale_files" ]; then
  echo "⚠️ 開発ルールが origin/develop より新しいです（更新ファイル: ${stale_files}）。"
  echo "   着手前に最新を取り込んでください: git pull --ff-only origin develop"
  echo "   （worktree 運用なら最新 develop から新規 worktree を作成）。"
  echo "   ※このフックは自動 pull しません（作業中の変更との衝突を避けるため・fetch のみ）。"
  echo "   EN: Dev rules updated on origin/develop (${stale_files}). Pull before starting; this hook does not auto-pull."
fi

exit 0
