#!/bin/bash
# gh-pr-merge-safe.sh — PR所有権検証付きマージ
#
# 目的: Manager エージェントが誤って他エージェントのPRをマージするのを防ぐ
#       現在のworktreeに紐付いたPR番号のみマージを許可する
#
# 使用方法: bash scripts/gh-pr-merge-safe.sh [gh pr merge オプション...]
#           例: bash scripts/gh-pr-merge-safe.sh --squash --admin
#
# 呼び出し元:
#   - ~/.claude/agents/manager.md（gh pr merge の代わりに必須）
#   - 手動での安全なマージ操作
#
# 参考: docs/PARALLEL_TERMINAL_GUIDE.md
#       docs/adr/ADR-074-worktree-agent-enforcement.md

set -euo pipefail

# ── 中央設定ファイルを読み込む（validate-pr-ownership.sh と同パターン）─────────
GIT_COMMON_DIR="$(git rev-parse --git-common-dir 2>/dev/null)"
if [[ "${GIT_COMMON_DIR}" = /* ]]; then
  MAIN_REPO_ROOT="$(dirname "${GIT_COMMON_DIR}")"
else
  MAIN_REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
fi
CONFIG_FILE="${MAIN_REPO_ROOT}/.claude/agent-config.sh"
if [ -f "${CONFIG_FILE}" ]; then
  # shellcheck source=.claude/agent-config.sh
  source "${CONFIG_FILE}"
fi
AGENT_ACTIVE_WORK_REL="${AGENT_ACTIVE_WORK_REL:-.claude-pipeline/active-work.md}"
ACTIVE_WORK_FILE="${MAIN_REPO_ROOT}/${AGENT_ACTIVE_WORK_REL}"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
WORKTREE_DIR="$(git rev-parse --show-toplevel 2>/dev/null)"
PR_NUMBER_FILE="${WORKTREE_DIR}/.pr-number"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# チェック1: .pr-number ファイルの存在確認
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if [ ! -f "${PR_NUMBER_FILE}" ]; then
  echo ""
  echo "🚫 マージを中断しました: .pr-number ファイルが見つかりません。"
  echo ""
  echo "   このworktreeにPR番号が登録されていません。"
  echo "   Generator が gh pr create 後に以下を実行してください:"
  echo "   echo \"<PR番号>\" > ${PR_NUMBER_FILE}"
  echo ""
  exit 1
fi

OWNED_PR="$(cat "${PR_NUMBER_FILE}" | tr -d '[:space:]')"
if [ -z "${OWNED_PR}" ]; then
  echo ""
  echo "🚫 マージを中断しました: .pr-number ファイルが空です。"
  echo ""
  exit 1
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# チェック2: active-work.md との整合確認
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# awk でテーブルの PR# 列（6列目）を取得（macOS/BSD 互換）
if [ -f "${ACTIVE_WORK_FILE}" ]; then
  ACTIVE_PR="$(ACTIVE_WORK_FILE="${ACTIVE_WORK_FILE}" bash "$(dirname "$0")/ledger-lookup.sh" "${CURRENT_BRANCH}" 2>/dev/null | awk -F'|' '{gsub(/ /, "", $6); print $6}')"
  if [ -n "${ACTIVE_PR}" ] && [ "${ACTIVE_PR}" != "${OWNED_PR}" ]; then
    echo ""
    echo "🚫 マージを中断しました: PR番号の不一致。"
    echo ""
    echo "   .pr-number の PR#: ${OWNED_PR}"
    echo "   active-work.md の PR#: ${ACTIVE_PR}"
    echo "   ブランチ: ${CURRENT_BRANCH}"
    echo ""
    echo "   active-work.md の PR# 列を更新してから再実行してください。"
    echo ""
    exit 1
  fi
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 所有権確認済み → マージ前full gateと1回送信
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if ! [[ "${OWNED_PR}" =~ ^[1-9][0-9]*$ ]]; then
  echo "🚫 マージを中断しました: .pr-number が正の整数ではありません。" >&2
  exit 1
fi

if [ "$#" -ne 1 ] || [ "$1" != "--merge" ]; then
  echo "🚫 マージを中断しました: 許可引数は --merge だけです。" >&2
  echo "   --admin/--auto/--squash/--rebase/--repo/別PR指定は使用できません。" >&2
  exit 1
fi

echo "✅ PR所有権確認: PR #${OWNED_PR} (ブランチ: ${CURRENT_BRANCH})"
echo "   マージ前GO・HEAD・必須checksを検査します（自動追従・再送なし）"
echo ""

python3 "$(dirname "$0")/dev/check-pr-merge-ready.py" "${OWNED_PR}" "${CURRENT_BRANCH}"

# ── マージ成功後: worktreeを自動クリーンアップ ───────────────────────────────
CLEANUP_SCRIPT="${MAIN_REPO_ROOT}/scripts/cleanup-worktree.sh"
if [ -f "${CLEANUP_SCRIPT}" ]; then
  bash "${CLEANUP_SCRIPT}" "${CURRENT_BRANCH}" "${WORKTREE_DIR}" "${MAIN_REPO_ROOT}"
fi
