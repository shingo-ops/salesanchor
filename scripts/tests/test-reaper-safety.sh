#!/bin/bash
# test-reaper-safety.sh — reaper-worktree.sh の安全条件テスト（ADR-114）
#
# 検証項目:
#   [1] IN_PROGRESS の部屋は dry-run で削除対象に出ない
#   [2] 未保存の作業がある部屋は dry-run で削除対象に出ない
#   [3] DONE かつ未保存なし の部屋は dry-run で削除対象に出る
#   [4] active-work.md に行がない(NOT_FOUND)かつ gh が 0 件を返す部屋は削除対象に出ない
#
# 実行方法: bash scripts/tests/test-reaper-safety.sh
# 終了コード: 0=全PASS / 1=FAIL あり

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REAPER="${SCRIPT_DIR}/../reaper-worktree.sh"
PASS=0
FAIL=0

# ── テスト用一時ディレクトリ ────────────────────────────────────────────────
TMPDIR_TEST=$(mktemp -d /tmp/reaper-test.XXXXXX)
trap 'rm -rf "${TMPDIR_TEST}"' EXIT

FAKE_WORKTREES="${TMPDIR_TEST}/worktrees"
FAKE_ACTIVE_WORK="${TMPDIR_TEST}/active-work.md"

mkdir -p "${FAKE_WORKTREES}"

# ── モック gh コマンド（常に 0 件を返す）──────────────────────────────────
MOCK_BIN="${TMPDIR_TEST}/mock-bin"
mkdir -p "${MOCK_BIN}"
cat > "${MOCK_BIN}/gh" << 'GHEOF'
#!/bin/bash
# モック gh: pr list --jq length → 常に 0
if [[ "$*" == *"--jq length"* ]]; then
  echo "0"
else
  echo ""
fi
exit 0
GHEOF
chmod +x "${MOCK_BIN}/gh"

export PATH="${MOCK_BIN}:${PATH}"

# ── ヘルパー関数 ────────────────────────────────────────────────────────────
make_worktree_dir() {
  local name="$1"
  local branch="$2"
  local dir="${FAKE_WORKTREES}/${name}"
  mkdir -p "${dir}"
  python3 -c "
import json
json.dump({'branch': '${branch}', 'uuid': 'test-uuid', 'created_at': '2026-06-06T00:00:00Z', 'worktree_path': '${dir}'}, open('${dir}/.worktree-id', 'w'))
"
  echo "${dir}"
}

# active-work.md のヘッダー
cat > "${FAKE_ACTIVE_WORK}" << 'AWEOF'
# Active Work Registry

## 現在進行中の作業

| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | 備考 |
|-----------|--------------|---------|------|-----|------|
AWEOF

run_reaper_dry() {
  REAPER_WORKTREES_DIR="${FAKE_WORKTREES}" \
  REAPER_ACTIVE_WORK_FILE="${FAKE_ACTIVE_WORK}" \
  REAPER_REPO_NAME="test/test" \
  bash "${REAPER}" 2>&1
}

assert_not_in_delete() {
  local test_name="$1"
  local branch="$2"
  local output="$3"

  if echo "${output}" | grep -q "🗑️  削除対象" && echo "${output}" | grep "🗑️  削除対象" -A 50 | grep -q "${branch}"; then
    echo "❌ FAIL [${test_name}]: ${branch} が削除対象に含まれています（含まれてはいけない）"
    FAIL=$(( FAIL + 1 ))
  else
    echo "✅ PASS [${test_name}]: ${branch} は削除対象に含まれていません"
    PASS=$(( PASS + 1 ))
  fi
}

assert_in_delete() {
  local test_name="$1"
  local branch="$2"
  local output="$3"

  if echo "${output}" | grep -q "🗑️  削除対象" && echo "${output}" | grep -A 50 "🗑️  削除対象" | grep -q "${branch}"; then
    echo "✅ PASS [${test_name}]: ${branch} が削除対象に含まれています"
    PASS=$(( PASS + 1 ))
  else
    echo "❌ FAIL [${test_name}]: ${branch} が削除対象に含まれていません（含まれるべき）"
    FAIL=$(( FAIL + 1 ))
  fi
}

# ── テスト 1: IN_PROGRESS → 削除対象に出ない ────────────────────────────────
BRANCH_IP="feature/test/in-progress"
make_worktree_dir "wt-ip" "${BRANCH_IP}" > /dev/null
echo "| ${BRANCH_IP} | テスト | 2026-06-06 | IN_PROGRESS | | |" >> "${FAKE_ACTIVE_WORK}"

# ── テスト 3: DONE かつ未保存なし → 削除対象に出る ──────────────────────────
BRANCH_DONE="feature/test/done-clean"
DONE_DIR=$(make_worktree_dir "wt-done" "${BRANCH_DONE}")
echo "| ${BRANCH_DONE} | テスト | 2026-06-06 | DONE | #999 | |" >> "${FAKE_ACTIVE_WORK}"
# git initして「未保存なし」状態を作る（git rev-parse HEAD が失敗→ unsaved=0 扱い）

# ── テスト 4: NOT_FOUND かつ gh=0 → 削除対象に出ない ────────────────────────
BRANCH_UNKNOWN="feature/test/unknown-no-pr"
make_worktree_dir "wt-unknown" "${BRANCH_UNKNOWN}" > /dev/null
# active-work.md に行なし + gh mock は 0 を返す

# ── dry-run 実行 ────────────────────────────────────────────────────────────
OUTPUT=$(run_reaper_dry)

echo ""
echo "=== reaper dry-run 出力 ==="
echo "${OUTPUT}"
echo ""
echo "=== テスト結果 ==="

assert_not_in_delete "IN_PROGRESS保護"    "${BRANCH_IP}"      "${OUTPUT}"
assert_in_delete     "DONE削除候補"        "${BRANCH_DONE}"    "${OUTPUT}"
assert_not_in_delete "NOT_FOUND+gh0保護"  "${BRANCH_UNKNOWN}" "${OUTPUT}"

# ── テスト 2: 未保存あり → 削除対象に出ない ─────────────────────────────────
# git init して未コミットファイルを作る
BRANCH_UNSAVED="feature/test/unsaved-changes"
UNSAVED_DIR=$(make_worktree_dir "wt-unsaved" "${BRANCH_UNSAVED}")
echo "| ${BRANCH_UNSAVED} | テスト | 2026-06-06 | IN_PROGRESS | | |" >> "${FAKE_ACTIVE_WORK}"

# active-work.md に IN_PROGRESS として登録済みなので、IN_PROGRESS チェックで先に引っかかる。
# 未保存チェックを直接テストするには IN_PROGRESS でない部屋が必要。
# ここでは DONE + 未保存ありの組み合わせでテスト。
BRANCH_DONE_UNSAVED="feature/test/done-unsaved"
DONE_UNSAVED_DIR=$(make_worktree_dir "wt-done-unsaved" "${BRANCH_DONE_UNSAVED}")
echo "| ${BRANCH_DONE_UNSAVED} | テスト | 2026-06-06 | DONE | #998 | |" >> "${FAKE_ACTIVE_WORK}"

# git init + 未コミットファイルを作って git status --porcelain で検出させる
git init "${DONE_UNSAVED_DIR}" -q 2>/dev/null
touch "${DONE_UNSAVED_DIR}/unsaved.txt"

OUTPUT2=$(run_reaper_dry)
assert_not_in_delete "DONE+未保存あり保護" "${BRANCH_DONE_UNSAVED}" "${OUTPUT2}"

# ── 結果 ────────────────────────────────────────────────────────────────────
echo ""
echo "=== 合計 ==="
echo "PASS: ${PASS}"
echo "FAIL: ${FAIL}"

if [ "${FAIL}" -gt 0 ]; then
  echo ""
  echo "❌ テスト失敗あり"
  exit 1
fi

echo ""
echo "✅ 全テスト PASS"
exit 0
