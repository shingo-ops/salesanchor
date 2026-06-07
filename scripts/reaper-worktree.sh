#!/bin/bash
# reaper-worktree.sh — マージ済み worktree の自動回収（ADR-114）
#
# 安全条件（非交渉・すべて満たした部屋だけ削除）:
#   ① active-work.md が DONE、または gh で PR がマージ済み（base=develop）
#   ② 未コミット・未push がゼロ
#   ③ IN_PROGRESS でない
#
# 既定: dry-run（削除予定の一覧表示のみ）
# 実削除: --execute フラグが必須
#
# テスト用オーバーライド環境変数:
#   REAPER_WORKTREES_DIR      — 走査するディレクトリ（既定: ~/worktrees/salesanchor）
#   REAPER_ACTIVE_WORK_FILE   — active-work.md のパス（既定: <repo>/.claude-pipeline/active-work.md）
#   REAPER_REPO_NAME          — gh コマンドに使うリポジトリ名（既定: shingo-ops/salesanchor）
#
# 使用方法:
#   bash scripts/reaper-worktree.sh            # dry-run（削除予定の一覧のみ）
#   bash scripts/reaper-worktree.sh --execute  # 実削除

EXECUTE=0
if [ "${1:-}" = "--execute" ]; then
  EXECUTE=1
fi

# ── メインリポジトリルート取得 ──────────────────────────────────────────────
GIT_COMMON_DIR="$(git rev-parse --git-common-dir 2>/dev/null || echo "")"
if [[ "${GIT_COMMON_DIR}" = /* ]]; then
  MAIN_REPO_ROOT="$(dirname "${GIT_COMMON_DIR}")"
else
  MAIN_REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
fi

WORKTREES_DIR="${REAPER_WORKTREES_DIR:-${HOME}/worktrees/salesanchor}"
ACTIVE_WORK_FILE="${REAPER_ACTIVE_WORK_FILE:-${MAIN_REPO_ROOT}/.claude-pipeline/active-work.md}"
REPO_NAME="${REAPER_REPO_NAME:-shingo-ops/salesanchor}"

# ── 分類バケット ────────────────────────────────────────────────────────────
WILL_DELETE=()
SKIP_IN_PROGRESS=()
SKIP_UNSAVED=()
SKIP_NOT_MERGED=()

if [ ! -d "${WORKTREES_DIR}" ]; then
  echo "📂 ${WORKTREES_DIR} が存在しません"
  exit 0
fi

echo "🔍 worktree を走査: ${WORKTREES_DIR}"
echo ""

# ── worktree 走査 ──────────────────────────────────────────────────────────
for WORKTREE_PATH in "${WORKTREES_DIR}"/*/; do
  [ -d "${WORKTREE_PATH}" ] || continue

  WORKTREE_ID_FILE="${WORKTREE_PATH}.worktree-id"
  [ -f "${WORKTREE_ID_FILE}" ] || continue

  BRANCH=$(python3 -c "
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    print(d.get('branch',''))
except Exception:
    print('')
" "${WORKTREE_ID_FILE}" 2>/dev/null || echo "")

  [ -z "${BRANCH}" ] && continue

  # ── チェック 1: active-work.md のステータス ──────────────────────────────
  ACTIVE_STATUS="NOT_FOUND"
  if [ -f "${ACTIVE_WORK_FILE}" ]; then
    ACTIVE_STATUS=$(python3 - "${ACTIVE_WORK_FILE}" "${BRANCH}" <<'PYEOF'
import sys
filepath, branch = sys.argv[1], sys.argv[2]
try:
    content = open(filepath, encoding="utf-8").read()
    for line in content.splitlines():
        if branch in line and line.strip().startswith('|'):
            cols = [c.strip() for c in line.split('|')]
            # 6列フォーマット: '' branch area date status pr note ''
            if len(cols) >= 6 and cols[1] == branch:
                print(cols[4])
                sys.exit(0)
    print("NOT_FOUND")
except Exception:
    print("ERROR")
PYEOF
2>/dev/null || echo "ERROR")
  fi

  # IN_PROGRESS → 絶対に消さない（最優先チェック）
  if [ "${ACTIVE_STATUS}" = "IN_PROGRESS" ]; then
    SKIP_IN_PROGRESS+=("${BRANCH}")
    continue
  fi

  # ── チェック 2: 未保存の作業がないか ────────────────────────────────────
  UNSAVED=0
  # git status は HEAD なしの fresh init でも動く（untracked files を検出可能）
  if git -C "${WORKTREE_PATH}" status >/dev/null 2>&1; then
    # 未コミット・未ステージ確認
    if [ -n "$(git -C "${WORKTREE_PATH}" status --porcelain 2>/dev/null)" ]; then
      UNSAVED=1
    fi
    # 未push 確認（upstream があれば）
    if [ "${UNSAVED}" -eq 0 ] && git -C "${WORKTREE_PATH}" rev-parse "@{u}" >/dev/null 2>&1; then
      if [ -n "$(git -C "${WORKTREE_PATH}" log --oneline "@{u}..HEAD" 2>/dev/null)" ]; then
        UNSAVED=1
      fi
    fi
  fi
  # git が存在しない場合（.git なし）は orphaned dir として UNSAVED=0 のまま（安全に削除可）

  if [ "${UNSAVED}" -eq 1 ]; then
    SKIP_UNSAVED+=("${BRANCH}")
    continue
  fi

  # ── チェック 3: DONE またはマージ済み ────────────────────────────────────
  IS_DONE=0
  [ "${ACTIVE_STATUS}" = "DONE" ] && IS_DONE=1

  if [ "${IS_DONE}" -eq 0 ]; then
    # gh で PR マージ済み確認（squash マージでも機能）
    # エラー時は 0 扱い（安全側）
    MERGED_COUNT=$(gh pr list \
      --repo "${REPO_NAME}" \
      --state merged \
      --base develop \
      --head "${BRANCH}" \
      --json number \
      --jq length 2>/dev/null || echo "0")
    [ "${MERGED_COUNT:-0}" -gt 0 ] && IS_DONE=1
  fi

  if [ "${IS_DONE}" -eq 0 ]; then
    SKIP_NOT_MERGED+=("${BRANCH}")
    continue
  fi

  # ── 全条件クリア → 削除候補 ──────────────────────────────────────────────
  WILL_DELETE+=("${BRANCH}::${WORKTREE_PATH}")
done

# ── サマリ表示 ────────────────────────────────────────────────────────────
echo "=== reaper 結果 ==="
echo ""

if [ "${#SKIP_IN_PROGRESS[@]}" -gt 0 ]; then
  echo "🔒 IN_PROGRESS（削除しない）: ${#SKIP_IN_PROGRESS[@]} 件"
  for B in "${SKIP_IN_PROGRESS[@]}"; do echo "   - ${B}"; done
  echo ""
fi

if [ "${#SKIP_UNSAVED[@]}" -gt 0 ]; then
  echo "⚠️  未保存あり（削除しない）: ${#SKIP_UNSAVED[@]} 件 ← 人の判断が必要"
  for B in "${SKIP_UNSAVED[@]}"; do echo "   - ${B}"; done
  echo ""
fi

if [ "${#SKIP_NOT_MERGED[@]}" -gt 0 ]; then
  echo "🔄 未マージ（削除しない）: ${#SKIP_NOT_MERGED[@]} 件"
  for B in "${SKIP_NOT_MERGED[@]}"; do echo "   - ${B}"; done
  echo ""
fi

if [ "${#WILL_DELETE[@]}" -eq 0 ]; then
  echo "✅ 削除対象なし"
  exit 0
fi

echo "🗑️  削除対象（安全条件クリア）: ${#WILL_DELETE[@]} 件"
for ENTRY in "${WILL_DELETE[@]}"; do
  BRANCH="${ENTRY%%::*}"
  echo "   - ${BRANCH}"
done
echo ""

if [ "${EXECUTE}" -eq 0 ]; then
  echo "ℹ️  dry-run モード（上記は削除候補の一覧です）"
  echo "   実削除するには: bash scripts/reaper-worktree.sh --execute"
  exit 0
fi

# ── 実削除 ────────────────────────────────────────────────────────────────
echo "🗑️  削除を実行します..."
DELETED=0

for ENTRY in "${WILL_DELETE[@]}"; do
  BRANCH="${ENTRY%%::*}"
  WPATH="${ENTRY#*::}"

  echo ""
  echo "  ▶ ${BRANCH}"

  # worktree フォルダ削除
  git -C "${MAIN_REPO_ROOT}" worktree remove --force "${WPATH}" 2>/dev/null && \
    echo "    ✅ フォルダ削除: ${WPATH}" || \
    echo "    ⚠️  フォルダ削除スキップ（既に存在しないか登録解除済み）"

  # ローカルブランチ削除
  git -C "${MAIN_REPO_ROOT}" branch -D "${BRANCH}" 2>/dev/null && \
    echo "    ✅ ブランチ削除: ${BRANCH}" || \
    echo "    ⚠️  ブランチ削除スキップ"

  # active-work.md を DONE に更新（行は消さず残す）
  if [ -f "${ACTIVE_WORK_FILE}" ]; then
    python3 - "${ACTIVE_WORK_FILE}" "${BRANCH}" <<'PYEOF'
import sys

filepath, branch = sys.argv[1], sys.argv[2]
with open(filepath, encoding="utf-8") as f:
    content = f.read()

lines = content.splitlines(keepends=True)
new_lines = []
updated = False
for line in lines:
    if branch in line and line.strip().startswith('|') and 'IN_PROGRESS' in line:
        line = line.replace('IN_PROGRESS', 'DONE', 1)
        updated = True
    new_lines.append(line)

new_content = ''.join(new_lines)
if updated:
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"    ✅ active-work.md → DONE: {branch}")
else:
    print(f"    ℹ️  active-work.md DONE 更新不要（既に DONE または行なし）: {branch}")
PYEOF
  fi

  DELETED=$(( DELETED + 1 ))
done

# worktree prune（参照のみ残っているゴミを掃除）
git -C "${MAIN_REPO_ROOT}" worktree prune 2>/dev/null || true

echo ""
echo "✅ reaper 完了: 削除 ${DELETED} 件"
if [ "${#SKIP_UNSAVED[@]}" -gt 0 ]; then
  echo "⚠️  未保存あり ${#SKIP_UNSAVED[@]} 件は保護済み（人が確認してください）"
fi
