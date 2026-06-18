#!/bin/bash
# test-reaper-safety.sh — reaper-worktree.sh の安全条件テスト（ADR-114）
#
# 検証項目:
#   [1] IN_PROGRESS の部屋は dry-run で削除対象に出ない
#   [2] REVIEW の部屋は dry-run で削除対象に出ない
#   [3] 未保存の作業がある部屋（DONE+未コミット）は dry-run で削除対象に出ない
#   [4] DONE かつ未保存なし の部屋は dry-run で削除対象に出る
#   [5] active-work.md に行がない(NOT_FOUND)かつ gh が 0 件を返す部屋は削除対象に出ない
#   [6] DONE + upstream未設定 + origin/<branch>なし → 削除対象に出る（upstream未設定だけで保護しない）
#   [7] DONE + upstream未設定 + origin/<branch>あり + 未pushコミットあり → 削除対象に出ない
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

# ── モック gh コマンド ────────────────────────────────────────────────────
# MOCK_GH_MERGED_BRANCH (カンマ区切り) に含まれるブランチは 1 を返す、それ以外は 0
# MOCK_GH_MAIN_MERGED (カンマ区切り) に含まれるブランチは main マージとして 1 を返す
MOCK_BIN="${TMPDIR_TEST}/mock-bin"
mkdir -p "${MOCK_BIN}"
cat > "${MOCK_BIN}/gh" << 'GHEOF'
#!/bin/bash
# モック gh: --state merged クエリに応答
if [[ "$*" == *"--state merged"* ]]; then
  if [ -n "${MOCK_GH_MERGED_BRANCH:-}" ]; then
    IFS=',' read -ra _MERGED <<< "${MOCK_GH_MERGED_BRANCH}"
    for _b in "${_MERGED[@]}"; do
      for arg in "$@"; do
        if [ "${arg}" = "${_b}" ]; then
          echo "1"
          exit 0
        fi
      done
    done
  fi
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

# active-work.md のヘッダー（7列: branch | area | date | status | pr | main | note）
cat > "${FAKE_ACTIVE_WORK}" << 'AWEOF'
# Active Work Registry

## 現在進行中の作業

| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |
|-----------|--------------|---------|------|-----|------|------|
AWEOF

run_reaper_dry() {
  REAPER_WORKTREES_DIR="${FAKE_WORKTREES}" \
  REAPER_ACTIVE_WORK_FILE="${FAKE_ACTIVE_WORK}" \
  REAPER_REPO_NAME="test/test" \
  bash "${REAPER}" 2>&1
}

run_reaper_dry_with_merged() {
  local merged_branches="${1:-}"
  REAPER_WORKTREES_DIR="${FAKE_WORKTREES}" \
  REAPER_ACTIVE_WORK_FILE="${FAKE_ACTIVE_WORK}" \
  REAPER_REPO_NAME="test/test" \
  MOCK_GH_MERGED_BRANCH="${merged_branches}" \
  bash "${REAPER}" 2>&1
}

# .worktree-id なしの旧 worktree を作る（git init + ブランチ設定）
make_worktree_dir_no_id() {
  local name="$1"
  local branch="$2"
  local dir="${FAKE_WORKTREES}/${name}"
  mkdir -p "${dir}"
  git init "${dir}" -q 2>/dev/null
  git -C "${dir}" checkout -b "${branch}" -q 2>/dev/null
  echo "${dir}"
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
echo "| ${BRANCH_IP} | テスト | 2026-06-06 | IN_PROGRESS | | | |" >> "${FAKE_ACTIVE_WORK}"

# ── テスト 2: REVIEW → 削除対象に出ない ─────────────────────────────────────
BRANCH_REVIEW="feature/test/review-open"
make_worktree_dir "wt-review" "${BRANCH_REVIEW}" > /dev/null
echo "| ${BRANCH_REVIEW} | テスト | 2026-06-06 | REVIEW | #777 | | |" >> "${FAKE_ACTIVE_WORK}"

# ── テスト 4: DONE かつ未保存なし → 削除対象に出る ──────────────────────────
BRANCH_DONE="feature/test/done-clean"
DONE_DIR=$(make_worktree_dir "wt-done" "${BRANCH_DONE}")
echo "| ${BRANCH_DONE} | テスト | 2026-06-06 | DONE | #999 | | |" >> "${FAKE_ACTIVE_WORK}"
# git initして「未保存なし」状態を作る（git rev-parse HEAD が失敗→ unsaved=0 扱い）

# ── テスト 5: NOT_FOUND かつ gh=0 → 削除対象に出ない ────────────────────────
BRANCH_UNKNOWN="feature/test/unknown-no-pr"
make_worktree_dir "wt-unknown" "${BRANCH_UNKNOWN}" > /dev/null
# active-work.md に行なし + gh mock は 0 を返す

# ── dry-run 実行（テスト 1,2,4,5 をまとめて確認） ───────────────────────────
OUTPUT=$(run_reaper_dry)

echo ""
echo "=== reaper dry-run 出力（round 1） ==="
echo "${OUTPUT}"
echo ""
echo "=== テスト結果 ==="

assert_not_in_delete "IN_PROGRESS保護"   "${BRANCH_IP}"      "${OUTPUT}"
assert_not_in_delete "REVIEW保護"        "${BRANCH_REVIEW}"  "${OUTPUT}"
assert_in_delete     "DONE削除候補"       "${BRANCH_DONE}"    "${OUTPUT}"
assert_not_in_delete "NOT_FOUND+gh0保護" "${BRANCH_UNKNOWN}" "${OUTPUT}"

# ── テスト 3: DONE + 未コミットあり → 削除対象に出ない ──────────────────────
BRANCH_DONE_UNSAVED="feature/test/done-unsaved"
DONE_UNSAVED_DIR=$(make_worktree_dir "wt-done-unsaved" "${BRANCH_DONE_UNSAVED}")
echo "| ${BRANCH_DONE_UNSAVED} | テスト | 2026-06-06 | DONE | #998 | | |" >> "${FAKE_ACTIVE_WORK}"

# git init + 未コミットファイルを作って git status --porcelain で検出させる
git init "${DONE_UNSAVED_DIR}" -q 2>/dev/null
touch "${DONE_UNSAVED_DIR}/unsaved.txt"

OUTPUT3=$(run_reaper_dry)
assert_not_in_delete "DONE+未保存あり保護" "${BRANCH_DONE_UNSAVED}" "${OUTPUT3}"

# ── テスト 6: DONE + upstream未設定 + origin/<branch>なし → 削除対象に出る ──
# upstream未設定だけを理由に未push扱いしないことを確認する
BRANCH_DONE_NO_UPSTREAM="feature/test/done-no-upstream"
DONE_NO_UPSTREAM_DIR=$(make_worktree_dir "wt-done-no-upstream" "${BRANCH_DONE_NO_UPSTREAM}")
echo "| ${BRANCH_DONE_NO_UPSTREAM} | テスト | 2026-06-06 | DONE | #997 | | |" >> "${FAKE_ACTIVE_WORK}"
# git init + コミットあり + upstream なし + origin/<branch> もなし
git init "${DONE_NO_UPSTREAM_DIR}" -q 2>/dev/null
git -C "${DONE_NO_UPSTREAM_DIR}" config user.email "test@test.com"
git -C "${DONE_NO_UPSTREAM_DIR}" config user.name "test"
touch "${DONE_NO_UPSTREAM_DIR}/committed.txt"
git -C "${DONE_NO_UPSTREAM_DIR}" add .
git -C "${DONE_NO_UPSTREAM_DIR}" commit -m "init" -q 2>/dev/null
# upstream未設定・origin/<branch>なし → UNSAVED=0 → 削除候補になるべき

OUTPUT6=$(run_reaper_dry)
assert_in_delete "DONE+upstream未設定+originなし→削除候補" "${BRANCH_DONE_NO_UPSTREAM}" "${OUTPUT6}"

# ── テスト 7: DONE + upstream未設定 + origin/<branch>あり + 未push → 保護 ───
BRANCH_DONE_UNPUSHED="feature/test/done-unpushed"
DONE_UNPUSHED_DIR=$(make_worktree_dir "wt-done-unpushed" "${BRANCH_DONE_UNPUSHED}")
echo "| ${BRANCH_DONE_UNPUSHED} | テスト | 2026-06-06 | DONE | #996 | | |" >> "${FAKE_ACTIVE_WORK}"

# bare リポジトリを「リモート」として作成（古い状態を持つ）
FAKE_REMOTE="${TMPDIR_TEST}/fake-remote.git"
git init --bare "${FAKE_REMOTE}" -q 2>/dev/null
git init "${DONE_UNPUSHED_DIR}" -q 2>/dev/null
git -C "${DONE_UNPUSHED_DIR}" config user.email "test@test.com"
git -C "${DONE_UNPUSHED_DIR}" config user.name "test"
git -C "${DONE_UNPUSHED_DIR}" remote add origin "${FAKE_REMOTE}"

# リモートに最初のコミットを push
touch "${DONE_UNPUSHED_DIR}/base.txt"
git -C "${DONE_UNPUSHED_DIR}" add .
git -C "${DONE_UNPUSHED_DIR}" commit -m "base" -q 2>/dev/null
git -C "${DONE_UNPUSHED_DIR}" push origin HEAD:"refs/heads/${BRANCH_DONE_UNPUSHED}" -q 2>/dev/null
# リモートの refs を fetch してローカルに origin/<branch> を作る
git -C "${DONE_UNPUSHED_DIR}" fetch origin -q 2>/dev/null

# ローカルにだけ追加コミット（未push）
touch "${DONE_UNPUSHED_DIR}/local-only.txt"
git -C "${DONE_UNPUSHED_DIR}" add .
git -C "${DONE_UNPUSHED_DIR}" commit -m "local only" -q 2>/dev/null
# upstream は設定しない（@{u} は使えない状態）

OUTPUT7=$(run_reaper_dry)
assert_not_in_delete "DONE+upstream未設定+origin有+未push→保護" "${BRANCH_DONE_UNPUSHED}" "${OUTPUT7}"

# ── テスト 8: active-work.md に行なし → 新規行が --- より上に挿入される ────
# auto-review / auto-done ワークフローの not-found 挿入ロジックをテストする
BRANCH_NEW="feature/test/brand-new-branch"
NEW_ACTIVE_WORK="${TMPDIR_TEST}/active-work-insert-test.md"
cat > "${NEW_ACTIVE_WORK}" << 'AWEOF2'
# Active Work Registry

## 現在進行中の作業

| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |
|-----------|--------------|---------|------|-----|------|------|
| feature/test/existing | テスト | 2026-06-06 | IN_PROGRESS | | | |
---

## 記入例

```
| feature/morimoto/example | サンプル | 2026-06-06 | IN_PROGRESS | | | |
```
AWEOF2

python3 - <<'INSERT_PYEOF' "${NEW_ACTIVE_WORK}" "${BRANCH_NEW}" "9999"
import sys, os
from datetime import datetime, timezone

filepath   = sys.argv[1]
branch     = sys.argv[2]
pr_number  = sys.argv[3]

with open(filepath, encoding="utf-8") as f:
    content = f.read()

lines = content.splitlines(keepends=True)
new_lines = []
found = False

for line in lines:
    if branch in line and line.strip().startswith("|"):
        parts = line.rstrip("\n").split("|")
        cols = parts[1:-1]
        if len(cols) == 7 and cols[0].strip() == branch:
            found = True
    new_lines.append(line)

if not found:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    new_row = f"| {branch} | （自動登録・要補完） | {now} | REVIEW | #{pr_number} | | 自動登録 |\n"
    inserted = False
    for i, l in enumerate(new_lines):
        if l.rstrip() == "---":
            j = i + 1
            while j < len(new_lines) and new_lines[j].strip() == "":
                j += 1
            if j < len(new_lines) and new_lines[j].startswith("## 記入例"):
                new_lines.insert(i, new_row)
                inserted = True
                break
    if not inserted:
        print("ERROR: パターンが見つかりません", file=sys.stderr)
        sys.exit(1)

with open(filepath, "w", encoding="utf-8") as f:
    f.write("".join(new_lines))
INSERT_PYEOF

# 検証: --- の前に新規行があり、--- の後に新規行がないこと
INSERT_RESULT=$(python3 - <<'VERIFY_PYEOF' "${NEW_ACTIVE_WORK}" "${BRANCH_NEW}"
import sys

filepath = sys.argv[1]
branch   = sys.argv[2]

with open(filepath, encoding="utf-8") as f:
    lines = f.readlines()

sep_index  = next((i for i, l in enumerate(lines) if l.rstrip() == "---"), None)
row_index  = next((i for i, l in enumerate(lines) if branch in l), None)

if sep_index is None:
    print("NO_SEP")
elif row_index is None:
    print("NO_ROW")
elif row_index < sep_index:
    print("OK_BEFORE_SEP")
else:
    print("FAIL_AFTER_SEP")
VERIFY_PYEOF
)

if [ "${INSERT_RESULT}" = "OK_BEFORE_SEP" ]; then
  echo "✅ PASS [新規行テーブル内挿入]: 新規行が --- より上に挿入されました"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [新規行テーブル内挿入]: 期待=OK_BEFORE_SEP 実際=${INSERT_RESULT}"
  FAIL=$(( FAIL + 1 ))
fi

# ── テスト 9-12: IN_PROGRESS/REVIEW + merged/no-merge ────────────────────────
# 判定順: 未保存チェック → PR merged 判定 → IN_PROGRESS/REVIEW チェック
# マージ済みなら IN_PROGRESS/REVIEW でも削除候補になること
BRANCH_IP_MERGED="feature/test/in-progress-merged"
make_worktree_dir "wt-ip-merged" "${BRANCH_IP_MERGED}" > /dev/null
echo "| ${BRANCH_IP_MERGED} | テスト | 2026-06-16 | IN_PROGRESS | | | |" >> "${FAKE_ACTIVE_WORK}"

BRANCH_REVIEW_MERGED="feature/test/review-merged"
make_worktree_dir "wt-review-merged" "${BRANCH_REVIEW_MERGED}" > /dev/null
echo "| ${BRANCH_REVIEW_MERGED} | テスト | 2026-06-16 | REVIEW | | | |" >> "${FAKE_ACTIVE_WORK}"

BRANCH_REVIEW_NO_MERGE="feature/test/review-no-merge"
make_worktree_dir "wt-review-no-merge" "${BRANCH_REVIEW_NO_MERGE}" > /dev/null
echo "| ${BRANCH_REVIEW_NO_MERGE} | テスト | 2026-06-16 | REVIEW | | | |" >> "${FAKE_ACTIVE_WORK}"

BRANCH_IP_NO_MERGE="feature/test/in-progress-no-merge"
make_worktree_dir "wt-ip-no-merge" "${BRANCH_IP_NO_MERGE}" > /dev/null
echo "| ${BRANCH_IP_NO_MERGE} | テスト | 2026-06-16 | IN_PROGRESS | | | |" >> "${FAKE_ACTIVE_WORK}"

OUTPUT_M=$(run_reaper_dry_with_merged "${BRANCH_IP_MERGED},${BRANCH_REVIEW_MERGED}")

echo ""
echo "=== テスト 9-12 dry-run 出力 ==="
echo "${OUTPUT_M}"
echo ""
echo "=== テスト 9-12 結果 ==="

assert_in_delete     "IN_PROGRESS+merged削除候補"   "${BRANCH_IP_MERGED}"       "${OUTPUT_M}"
assert_in_delete     "REVIEW+merged削除候補"         "${BRANCH_REVIEW_MERGED}"   "${OUTPUT_M}"
assert_not_in_delete "REVIEW+未マージ保護"           "${BRANCH_REVIEW_NO_MERGE}" "${OUTPUT_M}"
assert_not_in_delete "IN_PROGRESS+未マージ保護"      "${BRANCH_IP_NO_MERGE}"     "${OUTPUT_M}"

# ── テスト 13-14: .worktree-id なし（旧 worktree）────────────────────────────
# .worktree-id がなくても git branch --show-current でブランチを取得して処理する

BRANCH_LEGACY_MERGED="feature/test/legacy-merged-no-id"
LEGACY_MERGED_DIR=$(make_worktree_dir_no_id "wt-legacy-merged" "${BRANCH_LEGACY_MERGED}")
# active-work.md に行なし（NOT_FOUND 扱い）→ gh merged で判定する

BRANCH_LEGACY_NO_MERGE="feature/test/legacy-no-merge-no-id"
LEGACY_NO_MERGE_DIR=$(make_worktree_dir_no_id "wt-legacy-no-merge" "${BRANCH_LEGACY_NO_MERGE}")

OUTPUT_LEGACY=$(run_reaper_dry_with_merged "${BRANCH_LEGACY_MERGED}")

echo ""
echo "=== テスト 13-14 dry-run 出力 ==="
echo "${OUTPUT_LEGACY}"
echo ""
echo "=== テスト 13-14 結果 ==="

assert_in_delete     ".worktree-idなし+merged削除候補"   "${BRANCH_LEGACY_MERGED}"   "${OUTPUT_LEGACY}"
assert_not_in_delete ".worktree-idなし+未マージ保護"      "${BRANCH_LEGACY_NO_MERGE}" "${OUTPUT_LEGACY}"

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
