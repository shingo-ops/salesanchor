#!/bin/bash
# worktree-only-guard.sh — feature ブランチ作業の worktree 強制（v2）
#
# 配布原本: docs/specs/ledger-guard/artifacts/worktree-only-guard.v2.sh
# 適用先: ~/.claude/scripts/worktree-only-guard.sh（手作業カードでcp・diff検収）
#
# ブロック対象:
#   1. feature/fix/release/main ブランチにいる + worktree 外
#      → Edit/Write / git push / gh pr merge / git commit
#   2. どのブランチにいても + worktree 外 → feature/* 宛ての git push
#
# exit 0: 許可 / exit 1: ブロック / エスケープハッチ: WORKTREE_BYPASS=1

BRANCH=$(git -C "$PWD" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
WORKTREE_BASE="${HOME}/worktrees"

# worktree 内なら常に許可
if [[ "$PWD" == "${WORKTREE_BASE}"/* ]]; then
  exit 0
fi

# stdin を一度だけ読む
INPUT=$(cat 2>/dev/null || true)
TOOL_NAME=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('tool_name', ''))
except:
    print('')
" 2>/dev/null)

COMMAND=""
if [ "$TOOL_NAME" = "Bash" ]; then
  COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('tool_input', {}).get('command', ''))
except:
    print('')
" 2>/dev/null)
fi

SHOULD_BLOCK=0
BLOCK_BRANCH="$BRANCH"

# ルール1: feature/fix/release/main ブランチにいる
#   → Edit/Write または git push / gh pr merge / git commit をブロック
if [[ "$BRANCH" == feature/* ]] || [[ "$BRANCH" == fix/* ]] || [[ "$BRANCH" == release/* ]] || [[ "$BRANCH" == "main" ]]; then
  if [ "$TOOL_NAME" = "Bash" ]; then
    if echo "$COMMAND" | grep -qE '(git push|gh pr merge|git commit)'; then
      SHOULD_BLOCK=1
    fi
  else
    # Edit / Write
    SHOULD_BLOCK=1
  fi
fi

# ルール2: どのブランチにいても、feature/* 宛ての git push はブロック
if [ "$TOOL_NAME" = "Bash" ] && [ "$SHOULD_BLOCK" -eq 0 ]; then
  PUSH_TARGET=$(echo "$COMMAND" | python3 -c "
import sys, re
cmd = sys.stdin.read()
m = re.search(r'git push\s+\S+\s+((?:feature|fix|release)/\S+)', cmd)
print(m.group(1) if m else '')
" 2>/dev/null)
  if [ -n "$PUSH_TARGET" ]; then
    SHOULD_BLOCK=1
    BLOCK_BRANCH="$PUSH_TARGET"
  fi
fi

if [ "$SHOULD_BLOCK" -eq 0 ]; then
  exit 0
fi

# エスケープハッチ
if [ "${WORKTREE_BYPASS:-0}" = "1" ]; then
  echo "⚠️  WORKTREE_BYPASS=1 により強制通過（ブランチ: ${BLOCK_BRANCH}）" >&2
  exit 0
fi

# ── 自動リカバリー ─────────────────────────────────────────────────────────────
EVENTS_LOG="$HOME/.claude/logs/agent-events.jsonl"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
REPO_ROOT=$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null || echo "$PWD")
REPO_NAME=$(basename "$REPO_ROOT")
BRANCH_SAFE="${BLOCK_BRANCH//\//-}"
WORKTREE_DIR="${HOME}/worktrees/${REPO_NAME}/${BRANCH_SAFE}"

# mainブランチの本店ブロック: 自動作成は試みず、専用案内のみ
if [ "$BRANCH" = "main" ]; then
  echo "" >&2
  echo "🚫 BLOCKED: 本店（メインリポジトリ）では編集・commitできません。" >&2
  echo "   作業は worktree で行ってください:" >&2
  echo "   bash scripts/new-worktree.sh <ブランチ名>" >&2
  echo "   緊急時: WORKTREE_BYPASS=1 で強制通過（ログに記録されます）" >&2
  printf '{"type":"main_repo_write_blocked","session":"%s","branch":"%s","pwd":"%s","ts":"%s"}\n' \
    "$(basename "$PWD")" "$BLOCK_BRANCH" "$PWD" "$TIMESTAMP" >> "$EVENTS_LOG" 2>/dev/null
  exit 1
fi

# ケース1: このブランチの worktree がすでに存在する → 移動先を案内
EXISTING_WORKTREE=$(git -C "$REPO_ROOT" worktree list 2>/dev/null \
  | grep " \[${BLOCK_BRANCH}\]$" | awk '{print $1}' \
  | grep -v "^${REPO_ROOT}$" | head -1)

if [ -n "$EXISTING_WORKTREE" ]; then
  echo "" >&2
  echo "🔄 worktree は作成済みです。以下のパスに移動して作業してください:" >&2
  echo "   cd ${EXISTING_WORKTREE}" >&2
  echo "" >&2
  printf '{"type":"worktree_redirect","session":"%s","branch":"%s","worktree":"%s","ts":"%s"}\n' \
    "$(basename "$PWD")" "$BLOCK_BRANCH" "$EXISTING_WORKTREE" "$TIMESTAMP" >> "$EVENTS_LOG" 2>/dev/null
  exit 1
fi

# ケース2: worktree が存在しない → 自動作成を試みる（fetch なし・軽量）
mkdir -p "$(dirname "$WORKTREE_DIR")" 2>/dev/null
if git -C "$REPO_ROOT" worktree add "$WORKTREE_DIR" "$BLOCK_BRANCH" 2>/dev/null; then
  git -C "$WORKTREE_DIR" config core.hooksPath frontend/.husky 2>/dev/null || true
  echo "" >&2
  echo "✅ Worktree を自動作成しました。以下のパスに移動して作業してください:" >&2
  echo "   cd ${WORKTREE_DIR}" >&2
  echo "" >&2
  printf '{"type":"worktree_auto_created","session":"%s","branch":"%s","worktree":"%s","ts":"%s"}\n' \
    "$(basename "$PWD")" "$BLOCK_BRANCH" "$WORKTREE_DIR" "$TIMESTAMP" >> "$EVENTS_LOG" 2>/dev/null
  exit 1
fi

# ケース3: ブランチがメインリポジトリでチェックアウト済みのため自動作成不可
echo "" >&2
echo "🚫 BLOCKED: worktree の外から feature ブランチへの操作は禁止されています。" >&2
echo "" >&2
echo "   ブランチ '${BLOCK_BRANCH}' はメインリポジトリでチェックアウト済みのため" >&2
echo "   自動作成できませんでした。以下の手順で解決してください:" >&2
echo "" >&2
echo "   1. git checkout main" >&2
echo "   2. bash scripts/new-worktree.sh ${BLOCK_BRANCH} --claude" >&2
echo "" >&2
echo "   緊急時: WORKTREE_BYPASS=1 で強制通過" >&2
printf '{"type":"worktree_bypass_blocked","session":"%s","branch":"%s","pwd":"%s","ts":"%s"}\n' \
  "$(basename "$PWD")" "$BLOCK_BRANCH" "$PWD" "$TIMESTAMP" >> "$EVENTS_LOG" 2>/dev/null
exit 1
