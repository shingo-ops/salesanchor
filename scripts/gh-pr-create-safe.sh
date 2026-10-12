#!/bin/bash
# gh-pr-create-safe.sh — --base ガード付き PR 作成
#
# 目的: gh pr create の --base 指定漏れによる main への誤マージを防ぐ
#       - --base 未指定時は main を自動付与
#       - --base main かつ head が release/*・hotfix/* 以外 → ハードブロック
#
# 使用方法: bash scripts/gh-pr-create-safe.sh [gh pr create オプション...]
#           例: bash scripts/gh-pr-create-safe.sh --title "..." --body "..."
#
# 呼び出し元:
#   - ~/.claude/agents/generator.md（gh pr create の代わりに必須）
#   - ~/.claude/agents/manager.md（同上）
#
# 参考: scripts/gh-pr-merge-safe.sh（同パターン）
#       docs/adr/ADR-074-worktree-agent-enforcement.md

set -euo pipefail

fail() {
  echo "🚫 gh-pr-create-safe: $*" >&2
  exit 1
}

BASE_VALUE=""
HEAD_VALUE=""
BODY_VALUE=""
BODY_FILE=""
BODY_COUNT=0
TITLE_VALUE=""
TITLE_COUNT=0
BASE_COUNT=0
HEAD_COUNT=0
ARGS=("$@")

for ((i = 0; i < ${#ARGS[@]}; i++)); do
  arg="${ARGS[$i]}"
  case "$arg" in
    --title)
      ((i + 1 < ${#ARGS[@]})) || fail "${arg} の値がありません"
      TITLE_VALUE="${ARGS[$((i + 1))]}"; TITLE_COUNT=$((TITLE_COUNT + 1)); i=$((i + 1)) ;;
    --title=*) TITLE_VALUE="${arg#--title=}"; TITLE_COUNT=$((TITLE_COUNT + 1)) ;;
    --base)
      ((i + 1 < ${#ARGS[@]})) || fail "${arg} の値がありません"
      BASE_VALUE="${ARGS[$((i + 1))]}"; BASE_COUNT=$((BASE_COUNT + 1)); i=$((i + 1)) ;;
    --base=*) BASE_VALUE="${arg#--base=}"; BASE_COUNT=$((BASE_COUNT + 1)) ;;
    --head)
      ((i + 1 < ${#ARGS[@]})) || fail "${arg} の値がありません"
      HEAD_VALUE="${ARGS[$((i + 1))]}"; HEAD_COUNT=$((HEAD_COUNT + 1)); i=$((i + 1)) ;;
    --head=*) HEAD_VALUE="${arg#--head=}"; HEAD_COUNT=$((HEAD_COUNT + 1)) ;;
    --body)
      ((i + 1 < ${#ARGS[@]})) || fail "${arg} の値がありません"
      BODY_VALUE="${ARGS[$((i + 1))]}"; BODY_COUNT=$((BODY_COUNT + 1)); i=$((i + 1)) ;;
    --body=*) BODY_VALUE="${arg#--body=}"; BODY_COUNT=$((BODY_COUNT + 1)) ;;
    --body-file)
      ((i + 1 < ${#ARGS[@]})) || fail "${arg} の値がありません"
      BODY_FILE="${ARGS[$((i + 1))]}"; BODY_COUNT=$((BODY_COUNT + 1)); i=$((i + 1)) ;;
    --body-file=*) BODY_FILE="${arg#--body-file=}"; BODY_COUNT=$((BODY_COUNT + 1)) ;;
    *) fail "許可されていない引数です: ${arg}" ;;
  esac
done

[[ "$TITLE_COUNT" -eq 1 ]] || fail "--title を1つだけ指定してください"
[[ -n "$TITLE_VALUE" ]] || fail "PRタイトルが空です"
[[ "$BODY_COUNT" -eq 1 ]] || fail "--body または --body-file を1つだけ指定してください"
[[ "$BASE_COUNT" -le 1 ]] || fail "--base は重複指定できません"
[[ "$HEAD_COUNT" -le 1 ]] || fail "--head は重複指定できません"
[[ "$BASE_COUNT" -eq 0 || -n "$BASE_VALUE" ]] || fail "--base の明示空値は許可されていません"
[[ "$HEAD_COUNT" -eq 0 || -n "$HEAD_VALUE" ]] || fail "--head の明示空値は許可されていません"
if [[ -n "$BODY_FILE" ]]; then
  [[ "$BODY_FILE" != "-" ]] || fail "--body-file - は許可されていません"
  if ! PR_BODY_WITH_SENTINEL="$(python3 - "$BODY_FILE" <<'PYEOF'
import os
import stat
import sys

path = sys.argv[1]
try:
    mode = os.stat(path).st_mode
    if not stat.S_ISREG(mode):
        raise ValueError("not a regular file")
    data = open(path, "rb").read()
    if not data:
        raise ValueError("empty body")
    if b"\x00" in data:
        raise ValueError("NUL byte")
    data.decode("utf-8")
except (OSError, UnicodeDecodeError, ValueError) as exc:
    print(f"invalid body file: {exc}", file=sys.stderr)
    raise SystemExit(1)
sys.stdout.buffer.write(data + b"\x1e")
PYEOF
)"; then
    fail "body fileをUTF-8本文として読めません: ${BODY_FILE}"
  fi
  PR_BODY="${PR_BODY_WITH_SENTINEL%$'\x1e'}"
else
  PR_BODY="$BODY_VALUE"
fi
[[ -n "$PR_BODY" ]] || fail "PR本文が空です"

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || fail "git worktreeを確認できません"
cd "$REPO_ROOT"
CURRENT_BRANCH="$(git branch --show-current)"
ACTUAL_HEAD="${HEAD_VALUE:-$CURRENT_BRANCH}"
BASE_VALUE="${BASE_VALUE:-main}"

[[ "$BASE_VALUE" == "main" ]] || fail "baseはmainだけが許可されています: ${BASE_VALUE}"
[[ "$ACTUAL_HEAD" == "$CURRENT_BRANCH" ]] || fail "headは現在branchだけが許可されています: ${ACTUAL_HEAD}"
[[ "$ACTUAL_HEAD" =~ ^(release|hotfix)/ ]] || fail "main向けheadはrelease/*またはhotfix/*だけです: ${ACTUAL_HEAD}"

ORIGIN_URL="$(git config --get remote.origin.url 2>/dev/null)" || fail "originを確認できません"
case "$ORIGIN_URL" in
  https://github.com/shingo-ops/salesanchor|https://github.com/shingo-ops/salesanchor.git|git@github.com:shingo-ops/salesanchor.git|ssh://git@github.com/shingo-ops/salesanchor.git) ;;
  *) fail "originはshingo-ops/salesanchorではありません" ;;
esac

AUTH_LOGIN="$(env GH_HOST=github.com GH_REPO=github.com/shingo-ops/salesanchor \
  gh api user --hostname github.com --jq .login 2>/dev/null)" || fail "GitHub認証作者を取得できません"
case "$AUTH_LOGIN" in shingo-cc|Hikky-dev) ;; *) fail "PR作者 ${AUTH_LOGIN} は許可されていません" ;; esac

git fetch origin main "$ACTUAL_HEAD" --quiet || fail "origin/mainまたはorigin/${ACTUAL_HEAD}を取得できません"
LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse "refs/remotes/origin/${ACTUAL_HEAD}" 2>/dev/null)" || fail "push済みheadを確認できません"
BASE_SHA="$(git rev-parse refs/remotes/origin/main 2>/dev/null)" || fail "origin/mainが存在しません"
SHA_PATTERN='^[0-9a-fA-F]{40}$'
[[ "$LOCAL_SHA" =~ $SHA_PATTERN ]] || fail "local HEADが40桁SHAではありません"
[[ "$REMOTE_SHA" =~ $SHA_PATTERN ]] || fail "origin headが40桁SHAではありません"
[[ "$BASE_SHA" =~ $SHA_PATTERN ]] || fail "origin/mainが40桁SHAではありません"
[[ "$LOCAL_SHA" == "$REMOTE_SHA" ]] || fail "local HEADとorigin headが一致しません"

printf '%s' "$PR_BODY" | env -u PR_BODY_VALIDATE_SKIP bash scripts/dev/validate-pr-body.sh

echo "✅ PR作成前検査通過: ${ACTUAL_HEAD} → main (${LOCAL_SHA})"
env GH_HOST=github.com GH_REPO=github.com/shingo-ops/salesanchor \
  gh pr create --repo github.com/shingo-ops/salesanchor \
  --title "$TITLE_VALUE" --body "$PR_BODY" --base "$BASE_VALUE" --head "$ACTUAL_HEAD"
env -u GITHUB_ACTIONS GH_HOST=github.com GH_REPO=github.com/shingo-ops/salesanchor \
  bash "$(dirname "$0")/register-pr.sh" || echo "⚠️  .pr-number の登録に失敗しました（PR作成は成功しています）"
