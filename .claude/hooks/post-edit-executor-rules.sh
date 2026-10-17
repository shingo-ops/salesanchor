#!/usr/bin/env bash
# =============================================================================
# post-edit-executor-rules.sh — PostToolUse hook
# docs/rules/executor-behavior.md を Write / Edit した直後に AGENTS.md を自動同期する。
#
# Claude Code settings.json の PostToolUse で呼び出される。
# stdout への出力は Claude のコンテキストに注入される。
# =============================================================================

set -uo pipefail

# tool_input は JSON で stdin に来る (PostToolUse)
# 編集対象のファイルパスを取り出す
TOOL_INPUT="${CLAUDE_TOOL_INPUT:-}"
TARGET_SUFFIX="docs/rules/executor-behavior.md"

# ファイルパスが対象か確認（JSON から file_path を grep）
if ! echo "${TOOL_INPUT}" | grep -q "$TARGET_SUFFIX"; then
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
SYNC_SCRIPT="$REPO_ROOT/scripts/sync-executor-rules.sh"

if [[ ! -f "$SYNC_SCRIPT" ]]; then
  exit 0
fi

echo "🔄 executor-behavior.md が更新されました。AGENTS.md を同期しています..."
if bash "$SYNC_SCRIPT" 2>&1; then
  echo "✅ AGENTS.md の同期完了"
else
  echo "❌ AGENTS.md の同期に失敗しました。手動で bash scripts/sync-executor-rules.sh を実行してください"
fi

exit 0
