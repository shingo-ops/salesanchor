#!/bin/bash
# new-worktree.sh — Git Worktree 標準起動スクリプト
#
# 使い方:
#   bash scripts/new-worktree.sh <ブランチ名>
#   bash scripts/new-worktree.sh <ブランチ名> --claude  # Claude Code も同時起動
#
# 例:
#   bash scripts/new-worktree.sh feature/morimoto/new-feature
#   bash scripts/new-worktree.sh feature/morimoto/new-feature --claude
#
# 効果:
#   ~/worktrees/salesanchor/<ブランチ名>/ に独立した作業ディレクトリを作成
#   → 別ターミナルのブランチ切り替えに影響を受けない
#
# 参考: docs/PARALLEL_TERMINAL_GUIDE.md (P5)
#       https://incident.io/blog/shipping-faster-with-claude-code-and-git-worktrees

set -e

BRANCH="${1}"
WITH_CLAUDE="${2}"

# ledger-guard G2.1: どこから実行しても本店そのものを測る
HONTEN_GIT_DIR=$(git rev-parse --git-common-dir 2>/dev/null || echo "")
if [ -n "${HONTEN_GIT_DIR}" ]; then
  HONTEN_ROOT=$(dirname "${HONTEN_GIT_DIR}")
  G2_CURRENT_BRANCH="${G2_TEST_BRANCH:-$(git -C "${HONTEN_ROOT}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)}"
  if [ "${G2_CURRENT_BRANCH}" != "main" ]; then
    echo ""
    echo "WARNING: 本店が main 以外（${G2_CURRENT_BRANCH}）に居ます。作業は続行しますが、"
    echo "         本店を main へ戻すことを推奨: git checkout main && git pull --ff-only origin main"
    echo ""
  fi
fi

if [ -z "${BRANCH}" ]; then
  echo ""
  echo "使い方: bash scripts/new-worktree.sh <ブランチ名> [--claude]"
  echo ""
  echo "例:"
  echo "  bash scripts/new-worktree.sh feature/morimoto/my-feature"
  echo "  bash scripts/new-worktree.sh feature/morimoto/my-feature --claude"
  echo ""
  exit 1
fi

# リポジトリルートを取得
REPO_ROOT="$(git rev-parse --show-toplevel)"
REPO_NAME="$(basename "${REPO_ROOT}")"

# shared な台帳とフックが見ている本店ルート（worktree 間で共通）
GIT_COMMON_DIR="$(git rev-parse --git-common-dir 2>/dev/null)"
if [[ "${GIT_COMMON_DIR}" = /* ]]; then
  MAIN_REPO_ROOT="$(dirname "${GIT_COMMON_DIR}")"
else
  MAIN_REPO_ROOT="$(git rev-parse --show-toplevel)"
fi

# worktree の配置先（~/worktrees/<リポジトリ名>/<ブランチ名の/を-に置換>）
BRANCH_SAFE="${BRANCH//\//-}"
WORKTREE_DIR="${HOME}/worktrees/${REPO_NAME}/${BRANCH_SAFE}"

# ── マージ済みworktreeを先に回収してから上限チェック（ADR-114）────────────────
REAPER_SCRIPT="${REPO_ROOT}/scripts/reaper-worktree.sh"
if [ -f "${REAPER_SCRIPT}" ]; then
  bash "${REAPER_SCRIPT}" --execute 2>/dev/null || true
fi

# 並行 worktree 数の上限チェック（メインリポジトリ除く）
WORKTREE_COUNT=$(git worktree list | tail -n +2 | wc -l | tr -d ' ')
# ADR-114 §6: 上限はセーフティネット化（自動回収で減り続けるため、異常検知の閾値として設定）
WORKTREE_LIMIT="${WORKTREE_LIMIT:-100}"
if [ "${WORKTREE_COUNT}" -ge "${WORKTREE_LIMIT}" ]; then
  UNSAVED_COUNT=0
  if [ -f "${REAPER_SCRIPT}" ]; then
    UNSAVED_COUNT=$(bash "${REAPER_SCRIPT}" 2>/dev/null | grep -c "未保存あり" || echo "0")
  fi
  echo ""
  echo "⚠️  worktree が上限（${WORKTREE_LIMIT}個）に達しています（現在 ${WORKTREE_COUNT} 個）。"
  echo "   マージ済みworktreeを回収して空きを作ってください。"
  echo "   → 回収実行: bash scripts/reaper-worktree.sh --execute"
  if [ "${UNSAVED_COUNT}" -gt 0 ]; then
    echo "   → 未保存あり ${UNSAVED_COUNT} 件は人の判断が必要（自動回収対象外）"
  fi
  echo ""
  exit 1
fi

# main から最新化してブランチ作成（branch-operations §3-3 の正規入口）
git fetch origin

BASE_BRANCH="origin/main"

# すでに worktree が存在する場合はスキップ
if git worktree list | grep -q "${WORKTREE_DIR}"; then
  echo "ℹ️  worktree はすでに存在します: ${WORKTREE_DIR}"
else
  echo "🌿 worktree を作成しています..."
  echo "   ブランチ: ${BRANCH}"
  echo "   ベース  : ${BASE_BRANCH}"
  echo "   場所    : ${WORKTREE_DIR}"
  echo ""

  mkdir -p "$(dirname "${WORKTREE_DIR}")"
  git worktree add -b "${BRANCH}" "${WORKTREE_DIR}" "${BASE_BRANCH}"

  echo ""
  echo "✅ worktree を作成しました: ${WORKTREE_DIR}"

  # ── pre-push フックを worktree で有効化 ──────────────────────────────────────
  # husky の prepare スクリプトが core.hooksPath を frontend/.husky/_ に上書きするため、
  # worktree 固有の設定で frontend/.husky を直接指定する（npm install の影響を受けない）
  git -C "${WORKTREE_DIR}" config core.hooksPath frontend/.husky

  # ── UUID ライフサイクル管理（.worktree-id を発行）────────────────────────────
  WORKTREE_UUID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
  CREATED_AT="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  python3 - "${WORKTREE_DIR}/.worktree-id" "${WORKTREE_UUID}" "${BRANCH}" "${CREATED_AT}" "${WORKTREE_DIR}" <<'PYEOF'
import sys, json
out_file, uuid_val, branch, created_at, worktree_path = \
    sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
worktree_id = {
    "uuid": uuid_val,
    "branch": branch,
    "created_at": created_at,
    "worktree_path": worktree_path,
}
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(worktree_id, f, ensure_ascii=False, indent=2)
print(f"🔑 UUID発行: {uuid_val}")
PYEOF

  # Active Work Registry に自動登録（分割台帳 SSoT: .claude-pipeline/active-work.d/）
  LEDGER_DIR="${MAIN_REPO_ROOT}/.claude-pipeline/active-work.d"
  mkdir -p "${LEDGER_DIR}"
  DFILE="${LEDGER_DIR}/${BRANCH_SAFE}.md"
  if [ -f "${DFILE}" ]; then
    DECLARED="$(grep -m1 '^branch: ' "${DFILE}" | sed 's/^branch: //')"
    if [ "${DECLARED}" != "${BRANCH}" ]; then
      echo "🚫 衝突: ${DFILE} は branch: ${DECLARED} の登録です（要求: ${BRANCH}）。登録せず中止しました。人の判断を仰いでください。"
    else
      echo "ℹ️  active-work.d に既存登録あり（重複登録をスキップ）"
    fi
  else
    STARTED_AT="$(date '+%Y-%m-%d %H:%M')"
    {
      echo "branch: ${BRANCH}"
      echo ""
      echo "| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |"
      echo "|-----------|--------------|---------|------|-----|------|------|"
      echo "| ${BRANCH} | （記入してください） | ${STARTED_AT} | IN_PROGRESS | | | |"
    } > "${DFILE}"
    echo "📋 active-work.d に登録しました（担当機能エリアを記入してください）"
  fi
fi

echo ""
echo "📂 移動コマンド:"
echo "   cd ${WORKTREE_DIR}"
echo ""

# --claude フラグで Claude Code を起動
if [ "${WITH_CLAUDE}" = "--claude" ]; then
  echo "🤖 Claude Code を起動しています..."
  cd "${WORKTREE_DIR}"
  claude
fi

echo "🗑️  作業完了後のクリーンアップ:"
echo "   git worktree remove ${WORKTREE_DIR}"
echo "   git branch -d ${BRANCH}"
echo ""
