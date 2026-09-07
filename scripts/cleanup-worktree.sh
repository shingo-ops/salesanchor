#!/bin/bash
# cleanup-worktree.sh — PRマージ後のworktree自動クリーンアップ
#
# 目的: gh-pr-merge-safe.sh がマージ成功した後に呼び出され、
#       使用済みworktreeとブランチを自動削除する
#
# 使用方法: bash scripts/cleanup-worktree.sh <ブランチ名> <worktreeパス> <メインリポジトリルート>
#
# 呼び出し元: scripts/gh-pr-merge-safe.sh（マージ成功後に自動実行）

set -e

BRANCH="${1}"
WORKTREE_DIR="${2}"
MAIN_REPO_ROOT="${3}"

if [ -z "${BRANCH}" ] || [ -z "${WORKTREE_DIR}" ] || [ -z "${MAIN_REPO_ROOT}" ]; then
  echo "使い方: bash scripts/cleanup-worktree.sh <ブランチ名> <worktreeパス> <メインリポジトリルート>"
  exit 1
fi

# ── メインリポジトリ自体は削除しない ─────────────────────────────────────────
if [ "${WORKTREE_DIR}" = "${MAIN_REPO_ROOT}" ]; then
  echo "ℹ️  メインリポジトリのためworktreeクリーンアップをスキップ"
  exit 0
fi

echo ""
echo "🗑️  worktreeをクリーンアップしています..."
echo "   ブランチ: ${BRANCH}"
echo "   パス    : ${WORKTREE_DIR}"
echo ""

# ── .worktree-id を削除（UUID解放）─────────────────────────────────────────
WORKTREE_ID_FILE="${WORKTREE_DIR}/.worktree-id"
if [ -f "${WORKTREE_ID_FILE}" ]; then
  UUID_VAL="$(python3 -c "import json; d=json.load(open('${WORKTREE_ID_FILE}')); print(d.get('uuid','unknown'))" 2>/dev/null || echo 'unknown')"
  echo "🔓 UUID解放: ${UUID_VAL}"
  rm -f "${WORKTREE_ID_FILE}"
fi

# ── worktree 削除（メインリポジトリから実行）─────────────────────────────────
git -C "${MAIN_REPO_ROOT}" worktree remove --force "${WORKTREE_DIR}" 2>/dev/null && \
  echo "✅ worktree削除完了: ${WORKTREE_DIR}" || \
  echo "⚠️  worktree削除スキップ（既に存在しない可能性あり）"

# ── ローカルブランチ削除 ─────────────────────────────────────────────────────
git -C "${MAIN_REPO_ROOT}" branch -D "${BRANCH}" 2>/dev/null && \
  echo "✅ ブランチ削除完了: ${BRANCH}" || \
  echo "⚠️  ブランチ削除スキップ（既に存在しない可能性あり）"

# ── active-work.md のエントリを DONE に更新（ADR-114: 行は消さず残す）────────
ROWC="$(bash "$(dirname "$0")/ledger-lookup.sh" "${BRANCH}" 2>/dev/null || true)"
if echo "${ROWC}" | grep -q "IN_PROGRESS"; then
  bash "$(dirname "$0")/ledger-update.sh" "${BRANCH}" --status DONE > /dev/null \
    && echo "✅ active-work.md → DONE に更新しました: ${BRANCH}" \
    || echo "⚠️  active-work.md DONE 更新失敗: ${BRANCH}"
else
  echo "ℹ️  active-work.md 更新不要（既に DONE または行なし）: ${BRANCH}"
fi

# ── worktree prune ───────────────────────────────────────────────────────────
git -C "${MAIN_REPO_ROOT}" worktree prune 2>/dev/null || true

echo ""
echo "✅ クリーンアップ完了"
echo ""
