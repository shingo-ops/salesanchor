#!/bin/bash
# backfill-active-work-done.sh — IN_PROGRESS 行の一括棚卸し（ADR-114 一度きりの後始末）
#
# 目的:
#   active-work.md に IN_PROGRESS と記録されているが、
#   実際には develop へのマージが完了しているブランチを DONE に更新する。
#   「自動DONE（未来）＋棚卸し（過去）でひと揃い」の「過去」を担う。
#
# 判定基準（ADR-114 §3 マージ判定切り分け）:
#   - gh で merged かつ base=develop → DONE に更新
#   - closed（未マージ）→ 更新しない（安全側）
#   - PR なし → 更新しない（確証なし）
#
# 使用方法:
#   bash scripts/backfill-active-work-done.sh            # dry-run（変更なし・一覧表示のみ）
#   bash scripts/backfill-active-work-done.sh --execute  # 実際に DONE に更新

EXECUTE=0
if [ "${1:-}" = "--execute" ]; then
  EXECUTE=1
fi

REPO_NAME="${BACKFILL_REPO_NAME:-shingo-ops/salesanchor}"

# ── メインリポジトリルート取得 ──────────────────────────────────────────────
GIT_COMMON_DIR="$(git rev-parse --git-common-dir 2>/dev/null || echo "")"
if [[ "${GIT_COMMON_DIR}" = /* ]]; then
  MAIN_REPO_ROOT="$(dirname "${GIT_COMMON_DIR}")"
else
  MAIN_REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
fi

ACTIVE_WORK_FILE="${BACKFILL_ACTIVE_WORK_FILE:-${MAIN_REPO_ROOT}/.claude-pipeline/active-work.md}"

if [ ! -f "${ACTIVE_WORK_FILE}" ]; then
  echo "⚠️  active-work.md が見つかりません: ${ACTIVE_WORK_FILE}"
  exit 1
fi

echo "🔍 IN_PROGRESS 行を棚卸し中: ${ACTIVE_WORK_FILE}"
echo ""

# ── IN_PROGRESS ブランチを取得 ────────────────────────────────────────────
mapfile -t IN_PROGRESS_BRANCHES < <(python3 - "${ACTIVE_WORK_FILE}" <<'PYEOF'
import sys, re
filepath = sys.argv[1]
content = open(filepath, encoding="utf-8").read()
for line in content.splitlines():
    m = re.match(r'\|\s*(\S+)\s*\|.*\|\s*IN_PROGRESS\s*\|', line)
    if m:
        print(m.group(1).strip())
PYEOF
2>/dev/null)

if [ "${#IN_PROGRESS_BRANCHES[@]}" -eq 0 ]; then
  echo "✅ IN_PROGRESS エントリなし"
  exit 0
fi

echo "IN_PROGRESS エントリ: ${#IN_PROGRESS_BRANCHES[@]} 件"
echo ""

WILL_UPDATE=()
SKIP_NOT_MERGED=()
SKIP_ERROR=()

for BRANCH in "${IN_PROGRESS_BRANCHES[@]}"; do
  # gh で develop へのマージ済みを確認
  MERGED_COUNT=$(gh pr list \
    --repo "${REPO_NAME}" \
    --state merged \
    --base develop \
    --head "${BRANCH}" \
    --json number \
    --jq length 2>/dev/null || echo "0")

  if [ "${MERGED_COUNT:-0}" -gt 0 ]; then
    WILL_UPDATE+=("${BRANCH}")
  else
    SKIP_NOT_MERGED+=("${BRANCH}")
  fi
done

# ── サマリ表示 ────────────────────────────────────────────────────────────
if [ "${#SKIP_NOT_MERGED[@]}" -gt 0 ]; then
  echo "🔄 未マージ（更新しない）: ${#SKIP_NOT_MERGED[@]} 件"
  for B in "${SKIP_NOT_MERGED[@]}"; do echo "   - ${B}"; done
  echo ""
fi

if [ "${#WILL_UPDATE[@]}" -eq 0 ]; then
  echo "✅ DONE 更新対象なし"
  exit 0
fi

echo "✅ DONE 更新対象（マージ済み）: ${#WILL_UPDATE[@]} 件"
for B in "${WILL_UPDATE[@]}"; do echo "   - ${B}"; done
echo ""

if [ "${EXECUTE}" -eq 0 ]; then
  echo "ℹ️  dry-run モード（上記は更新候補の一覧です）"
  echo "   実際に更新するには: bash scripts/backfill-active-work-done.sh --execute"
  exit 0
fi

# ── 実際に DONE に更新 ────────────────────────────────────────────────────
echo "✏️  DONE に更新しています..."
UPDATED=0

for BRANCH in "${WILL_UPDATE[@]}"; do
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
if updated:
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(''.join(new_lines))
    print(f"  ✅ DONE: {branch}")
else:
    print(f"  ℹ️  行なし（スキップ）: {branch}")
PYEOF
  UPDATED=$(( UPDATED + 1 ))
done

echo ""
echo "✅ 棚卸し完了: ${UPDATED} 件を DONE に更新"
