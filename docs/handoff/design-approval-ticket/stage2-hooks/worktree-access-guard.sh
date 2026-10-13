#!/bin/bash
# worktree-access-guard.sh — TTYベースのworktreeアクセス制御（PreToolUse）
#
# 別TTYセッションが所有するworktreeへのRead/Edit/Write/Glob/Grep/Bashをブロックする。
#
# exit 0: アクセス許可
# exit 1: アクセスブロック
#
# エスケープハッチ: WORKTREE_ACCESS_OVERRIDE=1 で強制通過

CLAIMS_FILE=""

# claims.json を探す（git-common-dir で全worktreeから同一ファイルを参照）
# 修正: git rev-parse --show-toplevel はworktree内でworktreeパスを返すため共有不可
#       → git-common-dir は常にメインリポジトリの .git を指すため共有可能
COMMON_GIT=$(git rev-parse --git-common-dir 2>/dev/null)
if [[ "$COMMON_GIT" = /* ]]; then
  # worktree内からの実行: COMMON_GIT はメインリポジトリの .git への絶対パス
  REPO_ROOT=$(dirname "$COMMON_GIT")
elif [ -n "$COMMON_GIT" ]; then
  # メインリポジトリからの実行: COMMON_GIT は相対パス (.git)
  REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
fi
if [ -n "$REPO_ROOT" ]; then
  CLAIMS_FILE="${REPO_ROOT}/.claude-pipeline/claims.json"
fi

if [ ! -f "$CLAIMS_FILE" ]; then
  exit 0
fi

# 現在のセッション ID
if [ -n "${TERM_SESSION_ID}" ]; then
  MY_SESSION="${TERM_SESSION_ID}"
elif tty >/dev/null 2>&1; then
  MY_SESSION="$(tty | sed 's|/dev/||')"
else
  MY_SESSION="$(hostname -s)-$$"
fi

# stdin からツール入力を読む
INPUT=$(cat)

# ターゲットパスを抽出
TARGET_PATH=$(echo "$INPUT" | python3 -c "
import sys, json, os, re

try:
    data = json.load(sys.stdin)
    tool_name = data.get('tool_name', '')
    tool_input = data.get('tool_input', {})

    path = ''
    if tool_name in ('Read', 'Edit', 'Write'):
        path = tool_input.get('file_path', '')
    elif tool_name in ('Glob', 'Grep'):
        path = tool_input.get('path', '') or ''
    elif tool_name == 'Bash':
        cmd = tool_input.get('command', '')
        worktree_base = os.path.expanduser('~/worktrees')
        if worktree_base in cmd:
            matches = re.findall(re.escape(worktree_base) + r'/[^\s;|&<>\'\"]+', cmd)
            path = matches[0] if matches else ''

    if path:
        print(os.path.abspath(os.path.expanduser(path)))
except:
    pass
" 2>/dev/null)

if [ -z "$TARGET_PATH" ]; then
  exit 0
fi

# claims.json と照合
RESULT=$(python3 - "$CLAIMS_FILE" "$MY_SESSION" "$TARGET_PATH" <<'PYEOF'
import sys, json, os

claims_file, my_session, target_path = sys.argv[1], sys.argv[2], sys.argv[3]

try:
    with open(claims_file, encoding='utf-8') as f:
        claims = json.load(f)
except:
    sys.exit(0)

for branch, claim in claims.items():
    worktree_path = claim.get('worktree_path', '')
    if not worktree_path:
        continue
    worktree_path = os.path.abspath(os.path.expanduser(worktree_path))

    if target_path.startswith(worktree_path + '/') or target_path == worktree_path:
        owner = claim.get('session', '')
        if owner and owner != my_session:
            print(f"BLOCKED|{branch}|{owner}")
            sys.exit(0)

sys.exit(0)
PYEOF
)

if [[ "$RESULT" == BLOCKED* ]]; then
  IFS='|' read -r _ BRANCH OWNER <<< "$RESULT"

  EVENTS_LOG="$HOME/.claude/logs/agent-events.jsonl"
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  printf '{"type":"access_blocked","session":"%s","branch":"%s","owner":"%s","path":"%s","ts":"%s"}\n' \
    "$MY_SESSION" "$BRANCH" "$OWNER" "$TARGET_PATH" "$TIMESTAMP" >> "$EVENTS_LOG" 2>/dev/null

  if [ "${WORKTREE_ACCESS_OVERRIDE}" = "1" ]; then
    echo "⚠️  WORKTREE_ACCESS_OVERRIDE=1 により強制通過。" >&2
    exit 0
  fi

  echo "" >&2
  echo "🚫 BLOCKED: 別セッションのworktreeへのアクセスは禁止されています。" >&2
  echo "   パス    : $TARGET_PATH" >&2
  echo "   ブランチ: $BRANCH" >&2
  echo "   オーナー: $OWNER" >&2
  echo "   自分    : $MY_SESSION" >&2
  echo "" >&2
  echo "   → しんごさんに確認してください。" >&2
  echo "   → 緊急時: WORKTREE_ACCESS_OVERRIDE=1 bash scripts/..." >&2
  exit 2
fi

exit 0
