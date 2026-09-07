#!/usr/bin/env bash
# =============================================================================
# sync-executor-rules.sh
# SSOT (docs/rules/executor-behavior.md) の内容を AGENTS.md のマーカー区間に展開する。
#
# 使い方:
#   bash scripts/sync-executor-rules.sh           # 通常実行
#   bash scripts/sync-executor-rules.sh --check   # dry-run (差分があれば非ゼロ終了)
# =============================================================================

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SSOT="$REPO_ROOT/docs/rules/executor-behavior.md"
AGENTS_MD="$REPO_ROOT/AGENTS.md"
START_MARKER="<!-- EXECUTOR_BEHAVIOR_START -->"
END_MARKER="<!-- EXECUTOR_BEHAVIOR_END -->"
CHECK_MODE="${1:-}"

if [[ ! -f "$SSOT" ]]; then
  echo "❌ SSOT が見つかりません: $SSOT" >&2
  exit 1
fi

if [[ ! -f "$AGENTS_MD" ]]; then
  echo "❌ AGENTS.md が見つかりません: $AGENTS_MD" >&2
  exit 1
fi

# マーカーの存在確認
if ! grep -q "$START_MARKER" "$AGENTS_MD"; then
  echo "❌ AGENTS.md に '$START_MARKER' が見つかりません" >&2
  echo "   AGENTS.md に以下を追加してください:" >&2
  echo "   $START_MARKER" >&2
  echo "   $END_MARKER" >&2
  exit 1
fi

if ! grep -q "$END_MARKER" "$AGENTS_MD"; then
  echo "❌ AGENTS.md に '$END_MARKER' が見つかりません" >&2
  exit 1
fi

# SSOT の内容を読み込む
SSOT_CONTENT="$(cat "$SSOT")"

# マーカー区間を SSOT で置換（Python で安全に処理）
UPDATED="$(python3 - "$AGENTS_MD" "$START_MARKER" "$END_MARKER" "$SSOT_CONTENT" <<'PYEOF'
import sys

agents_path = sys.argv[1]
start_marker = sys.argv[2]
end_marker = sys.argv[3]
ssot_content = sys.argv[4]

with open(agents_path, "r") as f:
    content = f.read()

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    sys.exit(1)

end_of_start = start_idx + len(start_marker)
new_content = (
    content[:end_of_start]
    + "\n"
    + ssot_content
    + "\n"
    + content[end_idx:]
)
print(new_content, end="")
PYEOF
)"

if [[ "$CHECK_MODE" == "--check" ]]; then
  CURRENT="$(cat "$AGENTS_MD")"
  if [[ "$CURRENT" == "$UPDATED" ]]; then
    echo "✅ AGENTS.md は executor-behavior.md と同期しています"
    exit 0
  else
    echo "❌ AGENTS.md が executor-behavior.md と同期していません"
    echo "   bash scripts/sync-executor-rules.sh を実行してください"
    diff <(echo "$CURRENT") <(echo "$UPDATED") || true
    exit 1
  fi
fi

echo "$UPDATED" > "$AGENTS_MD"
echo "✅ AGENTS.md を executor-behavior.md で更新しました"
