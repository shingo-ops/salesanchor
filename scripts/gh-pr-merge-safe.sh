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

set -e

# CI環境はスキップ（GitHub Actions は自分専用のPRを自分で管理する）
if [ -n "${GITHUB_ACTIONS}" ]; then
  exit 0
fi

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
# 所有権確認済み → マージ実行
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "✅ PR所有権確認: PR #${OWNED_PR} (ブランチ: ${CURRENT_BRANCH})"
echo "   gh pr merge ${OWNED_PR} $*"
echo ""

# --- MERGE_RETRY: not up to date 自動追従（最大2回・正規手順の機械化） ---
merge_with_retry() {
  local attempt out
  for attempt in 0 1 2; do
    if [ "${attempt}" -gt 0 ]; then
      echo "[MERGE_RETRY] 追従を実行します（試行 ${attempt}/2）"
      git fetch --prune --quiet
      if ! git merge origin/main --no-edit; then
        echo "[MERGE_RETRY] STOP: コンフリクト。自動解決はしません。git status を確認してください。"
        git status --porcelain
        return 1
      fi
      git push || return 1
      echo "[MERGE_RETRY] 最新HEADのchecks全緑を待ちます"
      gh pr checks "${OWNED_PR}" --watch --required || {
        echo "[MERGE_RETRY] STOP: checksにfailあり。--log-failed を確認してください。"
        return 1
      }
    fi
    out="$(gh pr merge "${OWNED_PR}" "$@" 2>&1)" && { echo "${out}"; return 0; }
    echo "${out}"
    # 拒否種別を判定
    if echo "${out}" | grep -q "not up to date"; then
      : # 従来どおり: 次ループ冒頭で追従する
    elif echo "${out}" | grep -qE "cannot be cleanly created|merge conflict"; then
      echo "[MERGE_RETRY] STOP: コンフリクト。自動解決はしません。手動確認してください。"
      return 1
    elif echo "${out}" | grep -qE "rule violations|required status check|is not mergeable"; then
      # RULE_WAIT: 判定待ち（GitHubの再判定が追いついていない）。追従はせず、判定確定を待って同一HEADで再マージ
      echo "[MERGE_RETRY][RULE_WAIT] 判定待ちの可能性。確定を待って再マージします（最大3回・各30秒）"
      rw_ok=0
      for rw in 1 2 3; do
        sleep 30
        MSTATE="$(gh pr view "${OWNED_PR}" --json mergeStateStatus -q .mergeStateStatus 2>/dev/null)"
        echo "[MERGE_RETRY][RULE_WAIT] 試行 ${rw}/3 mergeStateStatus=${MSTATE}"
        if [ "${MSTATE}" = "BEHIND" ]; then
          echo "[MERGE_RETRY][RULE_WAIT] BEHIND を検出。待機せず追従フローへ戻ります"
          break
        fi
        rwout="$(gh pr merge "${OWNED_PR}" "$@" 2>&1)"
        if [ $? -eq 0 ]; then echo "${rwout}"; rw_ok=1; break; fi
        echo "${rwout}"
        # 待っても種別が変わった（not up to date化＝main前進）なら外ループの追従へ委ねる
        if echo "${rwout}" | grep -q "not up to date"; then
          echo "[MERGE_RETRY][RULE_WAIT] main前進を検知。追従フローへ戻ります"
          break
        fi
        # コンフリクト化したら即停止
        if echo "${rwout}" | grep -qE "cannot be cleanly created|merge conflict"; then
          echo "[MERGE_RETRY] STOP: 判定待ち中にコンフリクト化。手動確認してください。"
          return 1
        fi
      done
      [ "${rw_ok}" -eq 1 ] && return 0
      # 3回待っても通らず、not up to dateでもない → 恒久的な必須チェック不足等。停止して人へ
      if ! echo "${rwout}" | grep -q "not up to date"; then
        echo "[MERGE_RETRY] STOP: 判定待ちリトライ後も拒否。必須チェック不足等の可能性。手動確認してください。"
        return 1
      fi
    else
      echo "[MERGE_RETRY] STOP: 未知の拒否。安全のため停止します。"
      echo "${out}"
      return 1
    fi
  done
  echo "[MERGE_RETRY] STOP: 2回の追従でも拒否。mainの前進が速すぎます。手動確認してください。"
  return 1
}

merge_with_retry "$@"

# ── マージ成功後: worktreeを自動クリーンアップ ───────────────────────────────
CLEANUP_SCRIPT="${MAIN_REPO_ROOT}/scripts/cleanup-worktree.sh"
if [ -f "${CLEANUP_SCRIPT}" ]; then
  bash "${CLEANUP_SCRIPT}" "${CURRENT_BRANCH}" "${WORKTREE_DIR}" "${MAIN_REPO_ROOT}"
fi
