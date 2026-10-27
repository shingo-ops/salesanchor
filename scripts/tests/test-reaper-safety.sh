#!/bin/bash
# test-reaper-safety.sh — reaper-worktree.sh の安全条件テスト（ADR-114）
#
# 検証項目:
#   [1] IN_PROGRESS の部屋は dry-run で削除対象に出ない
#   [2] REVIEW の部屋は dry-run で削除対象に出ない
#   [3] 未保存の作業がある部屋（DONE+未コミット）は dry-run で削除対象に出ない
#   [4] DONE かつ未保存なし の部屋は dry-run で削除対象に出る
#   [5] active-work.md に行がない(NOT_FOUND)かつ gh が 0 件を返す部屋は削除対象に出ない
#   [6] DONE + upstream未設定 + origin/<branch>なし + コミットはローカルのみ → 削除対象に出ない（GitHub から取り戻せないため保護。R8）
#   [7] DONE + upstream未設定 + origin/<branch>あり + 未pushコミットあり → 削除対象に出ない
#   [R8-a] DONE + upstream=origin/main + origin/<branch>なし + mainに無いローカルのみコミット → 保護
#   [R8-b] DONE + upstream未設定 + 全コミットが origin の別ブランチ(main)にある → 削除対象に出る
#   [R8-c] DONE + git init のみ（コミット無し・未コミット無し）→ 削除対象に出る
#   [R8-d] fetch 失敗時は削除しない（存在しない remote 名で呼ぶ。ネットワーク・本体 ref には触れない）
#   [R9-a] マージ済み + 未追跡の pr-body.md（全行が PR 本文にある）→ 削除候補
#   [R9-b] 下書きに PR 本文に無い行が1行ある → 保護
#   [R9-c] マージ済み + 未追跡の notes.md（下書きでない）→ 保護
#   [R9-d] 下書きはあるがマージ済み PR が無い → 保護
#   [R9-e] gh の本文取得に失敗 → 保護
#   [R9-f] .scratch/pr-body.md（サブフォルダ・全行が本文にある）→ 削除候補
#   [R9-g] --execute で下書きが .git/reaper-drafts/ に控えられ、部屋が消える
#   [B-a] REAPER_BASE_BRANCH=staging → gh の PR 行き先判定が staging（main ではない）
#   [B-b] REAPER_BASE_BRANCH 未指定 → gh の PR 行き先判定は main（既定）
#   [B-c] ブランチ名が main・develop・REAPER_BASE_BRANCH と同じ部屋は DONE でも削除対象に出ない（本体ブランチ保護）
#   [B-d] 上の保護の対照: 通常ブランチの DONE の部屋は削除対象に出る
#   [G1] 部屋の core.fsmonitor に仕込んだ印の台本が reaper の dry-run で動かない（対照: 上書きなしの git status では動く）
#   [G2] 入れ子のリポジトリ（mode 160000）がある部屋は残し理由を出す（対照: 入れ子なしは削除候補）
#   [G3] git-safe.sh を読めないとき終了コード 1・何も消さない
#   [G3b] git-safe.sh が空のときも終了コード 1・何も消さない
#   [G4] worktree の commondir を偽の置き場へ向けた部屋は、印が動かず「git の繋がりが本店と合わない」に入り削除候補に入らない（対照あり）
#   [G5] worktree の .git ファイルを偽の gitdir へ向けた部屋も同じ
#   [G6] 正しい worktree は「合わない」に入らず、今の判定どおり
#   [G7] 本店の .git がシンボリックリンクなら終了コード 1・何も消さない
#   [G8] 本店の .git/commondir が偽の置き場なら、rev-parse 段で印が動かず終了コード 1・何も消さない（対照あり）
#   [G9] 本番の走査を worktree の中（本店の最上位でない cwd）で動かすと終了コード 1・何も消さない
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
# 他セッション・ランナーの本物の reaper が /tmp のロックを持っていても影響されないよう、ロックを試験専用にする
export REAPER_LOCK_DIR="${TMPDIR_TEST}/default.lock.d"
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
[ -n "${MOCK_GH_ARGS_LOG:-}" ] && echo "$*" >> "${MOCK_GH_ARGS_LOG}"
# 本文取得クエリ（--json baseRefName,body）: MOCK_GH_BODY_DIR/<ブランチの/を-に>.txt を返す。
#   ファイルが無ければ空（マージ済み PR なし相当）。MOCK_GH_BODY_FAIL=1 なら非0で終了。
if [[ "$*" == *"--state merged"* && "$*" == *"body"* ]]; then
  [ "${MOCK_GH_BODY_FAIL:-0}" = "1" ] && exit 1
  for arg in "$@"; do
    _f="${MOCK_GH_BODY_DIR:-/nonexistent}/${arg//\//-}.txt"
    if [ -f "${_f}" ]; then cat "${_f}"; exit 0; fi
  done
  exit 0
fi
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
  REAPER_SKIP_FETCH=1 \
  bash "${REAPER}" 2>&1
}

run_reaper_dry_with_merged() {
  local merged_branches="${1:-}"
  REAPER_WORKTREES_DIR="${FAKE_WORKTREES}" \
  REAPER_ACTIVE_WORK_FILE="${FAKE_ACTIVE_WORK}" \
  REAPER_REPO_NAME="test/test" \
  MOCK_GH_MERGED_BRANCH="${merged_branches}" \
  REAPER_SKIP_FETCH=1 \
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

# ── テスト 6: DONE + upstream未設定 + origin/<branch>なし + ローカルのみコミット → 保護（R8） ──
# 旧: 削除候補（穴）。R8: GitHub に無いコミットは取り戻せないので保護する
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
# upstream未設定・origin/<branch>なし・コミットは origin のどの ref からも到達できない → 保護

OUTPUT6=$(run_reaper_dry)
assert_not_in_delete "DONE+upstream未設定+originなし+ローカルのみ→保護(R8)" "${BRANCH_DONE_NO_UPSTREAM}" "${OUTPUT6}"

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

# ── テスト 15: DONE + upstream=共用側(origin/main) + 専用棚一致 + きれい → 削除候補（本バグ再現） ──
# @{u} が origin/main を指し @{u}..HEAD に差分が出るが、HEAD==origin/<branch>（push済み）。
# 旧コード=未push誤検出で保護／修正後=専用棚一致でpush済みとみなし②完了(DONE)へ進み削除候補。
BRANCH_DONE_SHARED="feature/test/done-shared-upstream"
DONE_SHARED_DIR=$(make_worktree_dir "wt-done-shared" "${BRANCH_DONE_SHARED}")
echo "| ${BRANCH_DONE_SHARED} | テスト | 2026-06-06 | DONE | #997 | | |" >> "${FAKE_ACTIVE_WORK}"

FAKE_REMOTE_15="${TMPDIR_TEST}/fake-remote-15.git"
git init --bare "${FAKE_REMOTE_15}" -q 2>/dev/null
git init "${DONE_SHARED_DIR}" -q 2>/dev/null
git -C "${DONE_SHARED_DIR}" config user.email "test@test.com"
git -C "${DONE_SHARED_DIR}" config user.name "test"
git -C "${DONE_SHARED_DIR}" remote add origin "${FAKE_REMOTE_15}"

# base → origin/main（共用側の物差しを作る）
touch "${DONE_SHARED_DIR}/base.txt"
git -C "${DONE_SHARED_DIR}" add .
git -C "${DONE_SHARED_DIR}" commit -m "base" -q 2>/dev/null
git -C "${DONE_SHARED_DIR}" push origin HEAD:"refs/heads/main" -q 2>/dev/null

# feature → origin/<branch>（専用棚＝HEADと一致）
touch "${DONE_SHARED_DIR}/feature.txt"
git -C "${DONE_SHARED_DIR}" add .
git -C "${DONE_SHARED_DIR}" commit -m "feature work" -q 2>/dev/null
git -C "${DONE_SHARED_DIR}" push origin HEAD:"refs/heads/${BRANCH_DONE_SHARED}" -q 2>/dev/null

git -C "${DONE_SHARED_DIR}" fetch origin -q 2>/dev/null
# @{u} を共用側 origin/main に向ける（設定漏れの再現）
git -C "${DONE_SHARED_DIR}" branch --set-upstream-to=origin/main -q 2>/dev/null

OUTPUT15=$(run_reaper_dry)
assert_in_delete "DONE+共用upstream+専用棚一致+きれい→削除候補(本バグ)" "${BRANCH_DONE_SHARED}" "${OUTPUT15}"

# ── テスト R8-a: DONE + upstream=origin/main + origin/<branch>なし + ローカルのみコミット → 保護 ──
BRANCH_R8A="feature/test/r8a-local-only"
R8A_DIR=$(make_worktree_dir "wt-r8a" "${BRANCH_R8A}")
echo "| ${BRANCH_R8A} | テスト | 2026-06-06 | DONE | #990 | | |" >> "${FAKE_ACTIVE_WORK}"
FAKE_REMOTE_R8A="${TMPDIR_TEST}/fake-remote-r8a.git"
git init --bare "${FAKE_REMOTE_R8A}" -q 2>/dev/null
git init "${R8A_DIR}" -q 2>/dev/null
git -C "${R8A_DIR}" config user.email "test@test.com"
git -C "${R8A_DIR}" config user.name "test"
git -C "${R8A_DIR}" remote add origin "${FAKE_REMOTE_R8A}"
touch "${R8A_DIR}/base.txt"
git -C "${R8A_DIR}" add .
git -C "${R8A_DIR}" commit -m "base" -q 2>/dev/null
git -C "${R8A_DIR}" push origin HEAD:"refs/heads/main" -q 2>/dev/null
git -C "${R8A_DIR}" fetch origin -q 2>/dev/null
git -C "${R8A_DIR}" branch --set-upstream-to=origin/main -q 2>/dev/null
touch "${R8A_DIR}/local-only.txt"
git -C "${R8A_DIR}" add .
git -C "${R8A_DIR}" commit -m "local only" -q 2>/dev/null
OUTPUT_R8A=$(run_reaper_dry)
assert_not_in_delete "R8-a DONE+upstream=main+origin専用棚なし+ローカルのみ→保護" "${BRANCH_R8A}" "${OUTPUT_R8A}"

# ── テスト R8-b: DONE + upstream未設定 + 全コミットが origin の別ブランチ(main)にある → 削除候補 ──
BRANCH_R8B="feature/test/r8b-all-on-origin"
R8B_DIR=$(make_worktree_dir "wt-r8b" "${BRANCH_R8B}")
echo "| ${BRANCH_R8B} | テスト | 2026-06-06 | DONE | #991 | | |" >> "${FAKE_ACTIVE_WORK}"
FAKE_REMOTE_R8B="${TMPDIR_TEST}/fake-remote-r8b.git"
git init --bare "${FAKE_REMOTE_R8B}" -q 2>/dev/null
git init "${R8B_DIR}" -q 2>/dev/null
git -C "${R8B_DIR}" config user.email "test@test.com"
git -C "${R8B_DIR}" config user.name "test"
git -C "${R8B_DIR}" remote add origin "${FAKE_REMOTE_R8B}"
touch "${R8B_DIR}/base.txt"
git -C "${R8B_DIR}" add .
git -C "${R8B_DIR}" commit -m "base" -q 2>/dev/null
git -C "${R8B_DIR}" push origin HEAD:"refs/heads/main" -q 2>/dev/null
git -C "${R8B_DIR}" fetch origin -q 2>/dev/null
OUTPUT_R8B=$(run_reaper_dry)
assert_in_delete "R8-b DONE+upstream未設定+全コミットがoriginにある→削除候補" "${BRANCH_R8B}" "${OUTPUT_R8B}"

# ── テスト R8-c: DONE + git init のみ（コミット無し・未コミット無し）→ 削除候補 ──
# 既存 [4] の wt-done は git init すらしない部屋。R8-c は git 管理下でコミット0件の部屋（HEAD なし）。
BRANCH_R8C="feature/test/r8c-no-commits"
R8C_DIR=$(make_worktree_dir "wt-r8c" "${BRANCH_R8C}")
echo "| ${BRANCH_R8C} | テスト | 2026-06-06 | DONE | #992 | | |" >> "${FAKE_ACTIVE_WORK}"
git init "${R8C_DIR}" -q 2>/dev/null
echo ".worktree-id" > "${R8C_DIR}/.git/info/exclude"
OUTPUT_R8C=$(run_reaper_dry)
assert_in_delete "R8-c DONE+コミット無し→削除候補" "${BRANCH_R8C}" "${OUTPUT_R8C}"

# ── テスト R8-d: fetch 失敗時は削除しない ──────────────────────────────────
# REAPER_SKIP_FETCH を付けず、存在しない remote 名で fetch を失敗させる（ネットワークにも本体の ref にも触れない）
# 上の R8-b / R8-c は fetch 成功時なら削除候補になる部屋。ここでは1件も出てはいけない。
OUTPUT_R8D=$(
  REAPER_WORKTREES_DIR="${FAKE_WORKTREES}" \
  REAPER_ACTIVE_WORK_FILE="${FAKE_ACTIVE_WORK}" \
  REAPER_REPO_NAME="test/test" \
  REAPER_FETCH_REMOTE="__reaper_test_no_such_remote__" \
  bash "${REAPER}" 2>&1
)
assert_not_in_delete "R8-d fetch失敗時はDONEきれい(R8-c)も削除しない" "${BRANCH_R8C}" "${OUTPUT_R8D}"
assert_not_in_delete "R8-d fetch失敗時はDONEきれい(R8-b)も削除しない" "${BRANCH_R8B}" "${OUTPUT_R8D}"
if echo "${OUTPUT_R8D}" | grep -q "git fetch に失敗しました" && echo "${OUTPUT_R8D}" | grep -q "fetch 失敗のため"; then
  echo "✅ PASS [R8-d fetch失敗の警告]: 警告2種が出力されています"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [R8-d fetch失敗の警告]: 警告が出力されていません"
  FAIL=$(( FAIL + 1 ))
fi

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

# ── テスト R9: PR 本文の下書き（*pr-body*.md）だけが残ったマージ済みの部屋 ──────
# 下書きの全行がマージ済み PR（main）の本文にあるときだけ、未保存扱いしない。
MOCK_GH_BODY_DIR="${TMPDIR_TEST}/pr-bodies"
export MOCK_GH_BODY_DIR
mkdir -p "${MOCK_GH_BODY_DIR}"
BODY_TEXT=$'## 概要\n\n- 変更点その1\n- 変更点その2\n\n### 標準ワークフロー確認'

# 空コミットの git 部屋を作る（HEAD なし。.worktree-id は exclude して未追跡に数えない）
make_r9_room() {
  local name="$1" branch="$2"
  local dir
  dir=$(make_worktree_dir "${name}" "${branch}")
  git init "${dir}" -q 2>/dev/null
  echo ".worktree-id" > "${dir}/.git/info/exclude"
  echo "${dir}"
}
set_pr_body() {  # <branch> <本文>
  printf '%s\n' "$2" > "${MOCK_GH_BODY_DIR}/${1//\//-}.txt"
}

BRANCH_R9A="feature/test/r9a-draft-ok"
R9A_DIR=$(make_r9_room "wt-r9a" "${BRANCH_R9A}")
set_pr_body "${BRANCH_R9A}" "${BODY_TEXT}"
printf '## 概要\n\n- 変更点その1\n- 変更点その2\n' > "${R9A_DIR}/pr-body.md"

BRANCH_R9B="feature/test/r9b-draft-extra-line"
R9B_DIR=$(make_r9_room "wt-r9b" "${BRANCH_R9B}")
set_pr_body "${BRANCH_R9B}" "${BODY_TEXT}"
printf '## 概要\n- 本文に無い行\n' > "${R9B_DIR}/pr-body.md"

BRANCH_R9C="feature/test/r9c-notes-md"
R9C_DIR=$(make_r9_room "wt-r9c" "${BRANCH_R9C}")
set_pr_body "${BRANCH_R9C}" "${BODY_TEXT}"
printf '## 概要\n' > "${R9C_DIR}/notes.md"

BRANCH_R9D="feature/test/r9d-draft-no-merged-pr"
R9D_DIR=$(make_r9_room "wt-r9d" "${BRANCH_R9D}")
printf '## 概要\n' > "${R9D_DIR}/pr-body.md"   # 本文ファイルなし = マージ済み PR なし

BRANCH_R9E="feature/test/r9e-body-fetch-fail"
R9E_DIR=$(make_r9_room "wt-r9e" "${BRANCH_R9E}")
set_pr_body "${BRANCH_R9E}" "${BODY_TEXT}"
printf '## 概要\n' > "${R9E_DIR}/pr-body.md"

BRANCH_R9F="feature/test/r9f-subfolder-draft"
R9F_DIR=$(make_r9_room "wt-r9f" "${BRANCH_R9F}")
set_pr_body "${BRANCH_R9F}" "${BODY_TEXT}"
mkdir -p "${R9F_DIR}/.scratch"
printf '## 概要\r\n\r\n- 変更点その1\r\n' > "${R9F_DIR}/.scratch/pr-body.md"   # CRLF でも一致扱い

R9_MERGED="${BRANCH_R9A},${BRANCH_R9B},${BRANCH_R9C},${BRANCH_R9E},${BRANCH_R9F}"
OUTPUT_R9=$(run_reaper_dry_with_merged "${R9_MERGED}")
echo ""
echo "=== テスト R9 dry-run 出力 ==="
echo "${OUTPUT_R9}"
echo ""
echo "=== テスト R9 結果 ==="
assert_in_delete     "R9-a マージ済み+pr-body.md全行が本文にある→削除候補"   "${BRANCH_R9A}" "${OUTPUT_R9}"
assert_not_in_delete "R9-b 下書きに本文に無い行→保護"                      "${BRANCH_R9B}" "${OUTPUT_R9}"
assert_not_in_delete "R9-c notes.md(下書きでない)→保護"                    "${BRANCH_R9C}" "${OUTPUT_R9}"
assert_not_in_delete "R9-d 下書きあり+マージ済みPRなし→保護"               "${BRANCH_R9D}" "${OUTPUT_R9}"
assert_in_delete     "R9-f .scratch/pr-body.md(サブフォルダ・CRLF)→削除候補" "${BRANCH_R9F}" "${OUTPUT_R9}"

OUTPUT_R9E=$(MOCK_GH_BODY_FAIL=1 run_reaper_dry_with_merged "${R9_MERGED}")
assert_not_in_delete "R9-e 本文取得失敗→保護"                              "${BRANCH_R9E}" "${OUTPUT_R9E}"
assert_not_in_delete "R9-e 本文取得失敗→R9-aも保護"                        "${BRANCH_R9A}" "${OUTPUT_R9E}"

# ── テスト R9-g: --execute で控えができ、部屋が消える ──────────────────────────
# 実際の worktree 登録が要るので、一時の本体リポジトリ（+bare の origin）を作り、cwd をそこにして実行する。
# 本物の .git には一切触れない。
R9G_MAIN="${TMPDIR_TEST}/r9g-main"
R9G_REMOTE="${TMPDIR_TEST}/r9g-remote.git"
R9G_ROOMS="${TMPDIR_TEST}/r9g-rooms"
BRANCH_R9G="release/r9g-exec"
git init --bare "${R9G_REMOTE}" -q 2>/dev/null
git init "${R9G_MAIN}" -q -b main 2>/dev/null
git -C "${R9G_MAIN}" config user.email "test@test.com"
git -C "${R9G_MAIN}" config user.name "test"
git -C "${R9G_MAIN}" remote add origin "${R9G_REMOTE}"
touch "${R9G_MAIN}/base.txt"
git -C "${R9G_MAIN}" add .
git -C "${R9G_MAIN}" commit -m "base" -q 2>/dev/null
git -C "${R9G_MAIN}" push origin HEAD:refs/heads/main -q 2>/dev/null
git -C "${R9G_MAIN}" fetch origin -q 2>/dev/null
mkdir -p "${R9G_ROOMS}"
git -C "${R9G_MAIN}" worktree add -q -b "${BRANCH_R9G}" "${R9G_ROOMS}/room" HEAD 2>/dev/null
printf '## 概要\n\n- 変更点その1\n' > "${R9G_ROOMS}/room/pr-body.md"
mkdir -p "${R9G_ROOMS}/room/.scratch"
printf '%s\n' '- 変更点その1' > "${R9G_ROOMS}/room/.scratch/pr-body-2.md"
set_pr_body "${BRANCH_R9G}" "${BODY_TEXT}"
OUTPUT_R9G=$(cd "${R9G_MAIN}" && \
  REAPER_WORKTREES_DIR="${R9G_ROOMS}" \
  REAPER_ACTIVE_WORK_FILE="${FAKE_ACTIVE_WORK}" \
  REAPER_REPO_NAME="test/test" \
  REAPER_LOCK_DIR="${TMPDIR_TEST}/r9g.lock.d" \
  MOCK_GH_MERGED_BRANCH="${BRANCH_R9G}" \
  REAPER_SKIP_FETCH=1 \
  bash "${REAPER}" --execute 2>&1)
echo ""
echo "=== テスト R9-g --execute 出力 ==="
echo "${OUTPUT_R9G}"
R9G_BK="${R9G_MAIN}/.git/reaper-drafts/release-r9g-exec"
if [ ! -d "${R9G_ROOMS}/room" ] \
   && [ "$(cat "${R9G_BK}/pr-body.md" 2>/dev/null)" = $'## 概要\n\n- 変更点その1' ] \
   && [ -f "${R9G_BK}/.scratch/pr-body-2.md" ] \
   && echo "${OUTPUT_R9G}" | grep -q "📝 下書きを控えました"; then
  echo "✅ PASS [R9-g --execute]: 控え2件ができ、部屋が消えました"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [R9-g --execute]: 控え不足または部屋が残っています"
  FAIL=$(( FAIL + 1 ))
fi

# ── テスト B: REAPER_BASE_BRANCH と本体ブランチ保護 ─────────────────────────
BASE_ROOMS="${TMPDIR_TEST}/base-rooms"
mkdir -p "${BASE_ROOMS}"
_mk_base_room() {
  local name="$1" branch="$2"
  mkdir -p "${BASE_ROOMS}/${name}"
  python3 -c "
import json
json.dump({'branch': '${branch}', 'uuid': 'test-uuid', 'created_at': '2026-06-06T00:00:00Z', 'worktree_path': '${BASE_ROOMS}/${name}'}, open('${BASE_ROOMS}/${name}/.worktree-id', 'w'))
"
}
_mk_base_room "wt-b-main" "main"
_mk_base_room "wt-b-develop" "develop"
_mk_base_room "wt-b-staging" "staging"
_mk_base_room "wt-b-normal" "feature/test/base-normal"
{
  echo "| main | テスト | 2026-06-06 | DONE | | | |"
  echo "| develop | テスト | 2026-06-06 | DONE | | | |"
  echo "| staging | テスト | 2026-06-06 | DONE | | | |"
  echo "| feature/test/base-normal | テスト | 2026-06-06 | DONE | | | |"
} >> "${FAKE_ACTIVE_WORK}"

run_reaper_base() {
  local base_value="$1" log="$2"
  : > "${log}"
  if [ -n "${base_value}" ]; then
    REAPER_BASE_BRANCH="${base_value}" \
    REAPER_WORKTREES_DIR="${BASE_ROOMS}" \
    REAPER_ACTIVE_WORK_FILE="${FAKE_ACTIVE_WORK}" \
    REAPER_REPO_NAME="test/test" \
    REAPER_SKIP_FETCH=1 \
    REAPER_LOCK_DIR="${TMPDIR_TEST}/base.lock.d" \
    MOCK_GH_ARGS_LOG="${log}" \
    bash "${REAPER}" 2>&1
  else
    REAPER_WORKTREES_DIR="${BASE_ROOMS}" \
    REAPER_ACTIVE_WORK_FILE="${FAKE_ACTIVE_WORK}" \
    REAPER_REPO_NAME="test/test" \
    REAPER_SKIP_FETCH=1 \
    REAPER_LOCK_DIR="${TMPDIR_TEST}/base.lock.d" \
    MOCK_GH_ARGS_LOG="${log}" \
    bash "${REAPER}" 2>&1
  fi
}

# gh を呼ばせるため、台帳に行のないブランチの部屋を別に用意する
_mk_base_room "wt-b-nogh" "feature/test/base-nogh"
BASE_LOG_DEV="${TMPDIR_TEST}/gh-args-develop.log"
BASE_LOG_DEF="${TMPDIR_TEST}/gh-args-default.log"
OUTPUT_B_DEV=$(run_reaper_base "staging" "${BASE_LOG_DEV}")
echo ""
echo "=== テスト B（REAPER_BASE_BRANCH=staging）出力 ==="
echo "${OUTPUT_B_DEV}"

# B-c / B-d: staging を行き先にした実行で、main・develop・staging の部屋は保護、通常ブランチは候補
if echo "${OUTPUT_B_DEV}" | grep -q "本体ブランチ（削除しない）: 3 件"; then
  echo "✅ PASS [B-c]: main・develop・REAPER_BASE_BRANCH の3部屋が本体ブランチとして保護されました"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [B-c]: 本体ブランチ 3 件の保護表示がありません"
  FAIL=$(( FAIL + 1 ))
fi
if echo "${OUTPUT_B_DEV}" | grep -A 20 "🗑️  削除対象" | grep -q "feature/test/base-normal" \
   && ! echo "${OUTPUT_B_DEV}" | grep -A 20 "🗑️  削除対象" | grep -qE "^   - (main|develop|staging)$"; then
  echo "✅ PASS [B-d]: 通常ブランチの DONE は削除対象、main/develop/staging は削除対象にない"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [B-d]: 削除対象の内訳が期待と違います"
  FAIL=$(( FAIL + 1 ))
fi

# B-a: 行き先が staging（main ではない）で gh が呼ばれている
if grep -q 'baseRefName == "staging"' "${BASE_LOG_DEV}" && ! grep -q 'baseRefName == "main"' "${BASE_LOG_DEV}"; then
  echo "✅ PASS [B-a]: REAPER_BASE_BRANCH=staging で gh の行き先判定が staging になりました"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [B-a]: gh 呼び出しの行き先が staging になっていません"
  sed 's/^/    /' "${BASE_LOG_DEV}"
  FAIL=$(( FAIL + 1 ))
fi

# B-b: 未指定なら main
run_reaper_base "" "${BASE_LOG_DEF}" > /dev/null
if grep -q 'baseRefName == "main"' "${BASE_LOG_DEF}" && ! grep -q 'baseRefName == "staging"' "${BASE_LOG_DEF}"; then
  echo "✅ PASS [B-b]: 未指定の既定は main のままです"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [B-b]: 既定の行き先が main になっていません"
  sed 's/^/    /' "${BASE_LOG_DEF}"
  FAIL=$(( FAIL + 1 ))
fi

# ── G: git の守り（ADR-1039・scripts/git-safe.sh）──────────────────────────
# G1: 部屋の config に仕込まれた core.fsmonitor の台本が、reaper の git で動かない
# G2: 入れ子のリポジトリ（mode 160000）がある部屋は、ほかが消す条件でも残る（理由つき）
# G3: git-safe.sh を読めないとき、終了コード 1 で何も消さない
G_MARK="${TMPDIR_TEST}/g1-mark"
G_SCRIPT="${TMPDIR_TEST}/g1-fsmonitor.sh"
cat > "${G_SCRIPT}" << GEOF
#!/bin/bash
touch "${G_MARK}"
exit 0
GEOF
chmod +x "${G_SCRIPT}"

# G1
BRANCH_G1="feature/test/g1-fsmonitor"
G1_DIR=$(make_worktree_dir "wt-g1" "${BRANCH_G1}")
echo "| ${BRANCH_G1} | テスト | 2026-06-06 | DONE | #990 | | |" >> "${FAKE_ACTIVE_WORK}"
git init "${G1_DIR}" -q 2>/dev/null
echo ".worktree-id" > "${G1_DIR}/.git/info/exclude"
git -C "${G1_DIR}" config core.fsmonitor "${G_SCRIPT}"
rm -f "${G_MARK}"
git -C "${G1_DIR}" status >/dev/null 2>&1 || true
if [ -e "${G_MARK}" ]; then
  echo "✅ PASS [G1-対照]: 上書きなしの git status では印の台本が動く（仕込みが効く作りだと確認）"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [G1-対照]: 上書きなしでも印ができません（この作りでは fsmonitor が呼ばれない）"
  FAIL=$(( FAIL + 1 ))
fi
rm -f "${G_MARK}"
OUTPUT_G1=$(run_reaper_dry)
if [ ! -e "${G_MARK}" ]; then
  echo "✅ PASS [G1]: reaper の dry-run で印の台本が動きませんでした"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [G1]: reaper の dry-run で印の台本が動きました"
  FAIL=$(( FAIL + 1 ))
fi
assert_in_delete "G1+上書きしても判定は変わらない（DONE+未保存なしは削除候補）" "${BRANCH_G1}" "${OUTPUT_G1}"

# G2: 入れ子のリポジトリ。対照（入れ子なし）と並べる
G_REMOTE="${TMPDIR_TEST}/g2-remote.git"
git init --bare "${G_REMOTE}" -q 2>/dev/null
make_g2_room() {
  local name="$1" branch="$2" nested="$3" dir
  dir=$(make_worktree_dir "${name}" "${branch}")
  echo "| ${branch} | テスト | 2026-06-06 | DONE | #991 | | |" >> "${FAKE_ACTIVE_WORK}"
  git init "${dir}" -q 2>/dev/null
  echo ".worktree-id" > "${dir}/.git/info/exclude"
  git -C "${dir}" config user.email "test@test.com"
  git -C "${dir}" config user.name "test"
  git -C "${dir}" remote add origin "${G_REMOTE}"
  touch "${dir}/base.txt"
  git -C "${dir}" add base.txt
  if [ "${nested}" = "1" ]; then
    mkdir -p "${dir}/inner"
    git init "${dir}/inner" -q 2>/dev/null
    git -C "${dir}/inner" config user.email "test@test.com"
    git -C "${dir}/inner" config user.name "test"
    touch "${dir}/inner/x.txt"
    git -C "${dir}/inner" add x.txt
    git -C "${dir}/inner" commit -m "inner" -q 2>/dev/null
    git -C "${dir}" add inner 2>/dev/null
  fi
  git -C "${dir}" commit -m "base" -q 2>/dev/null
  git -C "${dir}" push origin HEAD:"refs/heads/${branch}" -q 2>/dev/null
  git -C "${dir}" fetch origin -q 2>/dev/null
  echo "${dir}"
}
BRANCH_G2_CTRL="feature/test/g2-plain"
BRANCH_G2="feature/test/g2-nested"
make_g2_room "wt-g2-plain" "${BRANCH_G2_CTRL}" 0 >/dev/null
G2_DIR=$(make_g2_room "wt-g2-nested" "${BRANCH_G2}" 1)
if git -C "${G2_DIR}" ls-files --stage | grep -q '^160000 '; then
  echo "✅ PASS [G2-前提]: 作り物の部屋に mode 160000 がある"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [G2-前提]: mode 160000 の行がありません"
  FAIL=$(( FAIL + 1 ))
fi
OUTPUT_G2=$(run_reaper_dry)
assert_in_delete     "G2-対照: 入れ子なしの同じ作りの部屋は削除候補" "${BRANCH_G2_CTRL}" "${OUTPUT_G2}"
assert_not_in_delete "G2: 入れ子のリポジトリがある部屋は残す"       "${BRANCH_G2}"      "${OUTPUT_G2}"
if echo "${OUTPUT_G2}" | grep -A 20 "未保存あり" | grep -q "${BRANCH_G2}（入れ子のリポジトリがある（残す））"; then
  echo "✅ PASS [G2-理由]: 理由「入れ子のリポジトリがある（残す）」が出ています"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [G2-理由]: 理由が出ていません"
  FAIL=$(( FAIL + 1 ))
fi

# G3: git-safe.sh が無い写しで動かす → 終了コード 1・何も消さない
G3_COPY="${TMPDIR_TEST}/g3-copy"
mkdir -p "${G3_COPY}"
cp "${REAPER}" "${G3_COPY}/reaper-worktree.sh"
G3_RC=0
G3_OUT=$(REAPER_WORKTREES_DIR="${FAKE_WORKTREES}" \
  REAPER_ACTIVE_WORK_FILE="${FAKE_ACTIVE_WORK}" \
  REAPER_REPO_NAME="test/test" REAPER_SKIP_FETCH=1 \
  bash "${G3_COPY}/reaper-worktree.sh" 2>&1) || G3_RC=$?
if [ "${G3_RC}" -eq 1 ] && echo "${G3_OUT}" | grep -q "git の守りを読めない" && ! echo "${G3_OUT}" | grep -q "削除対象"; then
  echo "✅ PASS [G3]: git-safe.sh を読めないとき、終了コード 1・削除対象なしで終わりました"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [G3]: 終了コード=${G3_RC}"
  echo "${G3_OUT}" | sed 's/^/    /'
  FAIL=$(( FAIL + 1 ))
fi

# G3b: git-safe.sh が空（配列を作らない）の写しで動かす → 終了コード 1・何も消さない
G3B_COPY="${TMPDIR_TEST}/g3b-copy"
mkdir -p "${G3B_COPY}"
cp "${REAPER}" "${G3B_COPY}/reaper-worktree.sh"
: > "${G3B_COPY}/git-safe.sh"
G3B_RC=0
G3B_OUT=$(REAPER_WORKTREES_DIR="${FAKE_WORKTREES}" \
  REAPER_ACTIVE_WORK_FILE="${FAKE_ACTIVE_WORK}" \
  REAPER_REPO_NAME="test/test" REAPER_SKIP_FETCH=1 \
  bash "${G3B_COPY}/reaper-worktree.sh" 2>&1) || G3B_RC=$?
if [ "${G3B_RC}" -eq 1 ] && echo "${G3B_OUT}" | grep -q "git の守りを読めない" && ! echo "${G3B_OUT}" | grep -q "削除対象"; then
  echo "✅ PASS [G3b]: git-safe.sh が空のとき、終了コード 1・削除対象なしで終わりました"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [G3b]: 終了コード=${G3B_RC}"
  echo "${G3B_OUT}" | sed 's/^/    /'
  FAIL=$(( FAIL + 1 ))
fi

# ── G4〜G9: git の繋がりの確かめ（ADR-1039 便2b-2・scripts/git-safe.sh の git_safe_link_ok / git_safe_main_ok）──
# 本番の走査（REAPER_WORKTREES_DIR を空）で dry-run。作り物の元のリポジトリを cwd にする。
# 作り物はすべて TMPDIR_TEST の下（終了時の既存の後片付けに任せる）。
# 偽の置き場は、元の .git から worktrees を最初から写さない作り（rsync --exclude）。
LK_MARK="${TMPDIR_TEST}/lk-mark"
LK_MAIN="${TMPDIR_TEST}/linkcheck-main-${RANDOM}${RANDOM}"
LK_REMOTE="${TMPDIR_TEST}/lk-remote.git"
LK_ROOMS="${TMPDIR_TEST}/lk-rooms"
LK_EVIL="${TMPDIR_TEST}/lk-evil-gitdir"
LK_LOCK="${TMPDIR_TEST}/lk.lock.d"
BRANCH_G4="feature/test/lk-g4-commondir"
BRANCH_G5="feature/test/lk-g5-gitdir"
BRANCH_G6="feature/test/lk-g6-legit"
git init --bare "${LK_REMOTE}" -q 2>/dev/null
git init "${LK_MAIN}" -q -b main 2>/dev/null
git -C "${LK_MAIN}" config user.email "test@test.com"
git -C "${LK_MAIN}" config user.name "test"
git -C "${LK_MAIN}" remote add origin "${LK_REMOTE}"
printf '1\n' > "${LK_MAIN}/f.txt"
git -C "${LK_MAIN}" add f.txt
git -C "${LK_MAIN}" commit -m "base" -q 2>/dev/null
git -C "${LK_MAIN}" push origin HEAD:refs/heads/main -q 2>/dev/null
git -C "${LK_MAIN}" fetch origin -q 2>/dev/null
mkdir -p "${LK_ROOMS}"
git -C "${LK_MAIN}" worktree add -q -b "${BRANCH_G4}" "${LK_ROOMS}/g4" HEAD 2>/dev/null
git -C "${LK_MAIN}" worktree add -q -b "${BRANCH_G5}" "${LK_ROOMS}/g5" HEAD 2>/dev/null
git -C "${LK_MAIN}" worktree add -q -b "${BRANCH_G6}" "${LK_ROOMS}/g6" HEAD 2>/dev/null
{
  echo "| ${BRANCH_G4} | テスト | 2026-06-06 | DONE | #992 | | |"
  echo "| ${BRANCH_G5} | テスト | 2026-06-06 | DONE | #993 | | |"
  echo "| ${BRANCH_G6} | テスト | 2026-06-06 | DONE | #994 | | |"
} >> "${FAKE_ACTIVE_WORK}"
# 偽の置き場: 元の .git を worktrees 抜きで写し、filter の命令を仕込む
mkdir -p "${LK_EVIL}"
rsync -a --exclude=/worktrees "${LK_MAIN}/.git/" "${LK_EVIL}/"
printf '[filter "evil"]\n\tclean = touch %s; cat\n' "${LK_MARK}" >> "${LK_EVIL}/config"
mkdir -p "${LK_EVIL}/info"
printf '*.txt filter=evil\n' >> "${LK_EVIL}/info/attributes"

# G4: worktree の commondir を偽の置き場へ。f.txt は同じ長さ（1\n → 2\n）で変える
printf '2\n' > "${LK_ROOMS}/g4/f.txt"
G4_GD="$(git -C "${LK_MAIN}" rev-parse --absolute-git-dir)/worktrees/g4"
printf '%s\n' "${LK_EVIL}" > "${G4_GD}/commondir"
rm -f "${LK_MARK}"
git -C "${LK_ROOMS}/g4" -c core.fsmonitor=false -c core.hooksPath=/dev/null status --porcelain --ignore-submodules=all >/dev/null 2>&1 || true
if [ -e "${LK_MARK}" ]; then
  echo "✅ PASS [G4-対照]: 偽の置き場を読む worktree では、上書き付きの git status でも印ができる（仕込みが効く作りだと確認）"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [G4-対照]: 印ができません（この作りでは filter が呼ばれない）"
  FAIL=$(( FAIL + 1 ))
fi
rm -f "${LK_MARK}"

# G5: worktree の .git ファイルを偽の gitdir（.git/worktrees/g5 の写しで commondir を偽の置き場へ）へ
LK_FAKE_GD="${TMPDIR_TEST}/lk-fake-gitdir-g5"
mkdir -p "${LK_FAKE_GD}"
rsync -a "$(git -C "${LK_MAIN}" rev-parse --absolute-git-dir)/worktrees/g5/" "${LK_FAKE_GD}/"
printf '%s\n' "${LK_EVIL}" > "${LK_FAKE_GD}/commondir"
printf 'gitdir: %s\n' "${LK_FAKE_GD}" > "${LK_ROOMS}/g5/.git"
printf '2\n' > "${LK_ROOMS}/g5/f.txt"

run_lk() { # <cwd> [引数...]。終了コードは LK_RC に入る
  local cwd="$1"; shift
  LK_RC=0
  LK_OUT=$(cd "${cwd}" && env -u REAPER_WORKTREES_DIR \
    REAPER_ACTIVE_WORK_FILE="${FAKE_ACTIVE_WORK}" \
    REAPER_REPO_NAME="test/test" \
    REAPER_SKIP_FETCH=1 \
    REAPER_LOCK_DIR="${LK_LOCK}" \
    bash "${REAPER}" "$@" 2>&1) || LK_RC=$?
}
lk_in_mismatch() { # <ブランチ> : 「git の繋がりが本店と合わない」の欄に入っているか
  echo "${LK_OUT}" | sed -n '/git の繋がりが本店と合わない/,/^$/p' | grep -q "$1"
}

run_lk "${LK_MAIN}"
echo ""
echo "=== テスト G4〜G6 本番の走査 dry-run 出力 ==="
echo "${LK_OUT}"
if [ "${LK_RC}" -eq 0 ] && echo "${LK_OUT}" | grep -q "=== reaper 結果 ==="; then
  echo "✅ PASS [G4-6 前提]: 本番の走査が終了コード 0 で最後まで動いた（ロックで飛ばされていない）"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [G4-6 前提]: 終了コード=${LK_RC}"
  FAIL=$(( FAIL + 1 ))
fi
if [ ! -e "${LK_MARK}" ]; then
  echo "✅ PASS [G4]: reaper の dry-run で印の台本が動きませんでした（commondir 偽装）"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [G4]: reaper の dry-run で印の台本が動きました"
  FAIL=$(( FAIL + 1 ))
fi
rm -f "${LK_MARK}"
if lk_in_mismatch "${BRANCH_G4}"; then
  echo "✅ PASS [G4-合わない欄]: 偽の commondir の部屋が「git の繋がりが本店と合わない」に入った"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [G4-合わない欄]: 入っていません"
  FAIL=$(( FAIL + 1 ))
fi
assert_not_in_delete "G4 偽の commondir の部屋は削除候補に入らない" "${BRANCH_G4}" "${LK_OUT}"
if lk_in_mismatch "${BRANCH_G5}"; then
  echo "✅ PASS [G5-合わない欄]: 偽の gitdir の部屋が「git の繋がりが本店と合わない」に入った"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [G5-合わない欄]: 入っていません"
  FAIL=$(( FAIL + 1 ))
fi
assert_not_in_delete "G5 偽の gitdir の部屋は削除候補に入らない" "${BRANCH_G5}" "${LK_OUT}"
if ! lk_in_mismatch "${BRANCH_G6}"; then
  echo "✅ PASS [G6-合わない欄に入らない]: 正しい worktree は「合わない」に入っていない"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [G6-合わない欄に入らない]: 正しい worktree が「合わない」に入った"
  FAIL=$(( FAIL + 1 ))
fi
assert_in_delete "G6 正しい worktree は今の判定どおり（DONE+未保存なしは削除候補）" "${BRANCH_G6}" "${LK_OUT}"

# G9: cwd が worktree（正しい G6）→ 終了コード 1・何も消さない
run_lk "${LK_ROOMS}/g6"
if [ "${LK_RC}" -eq 1 ] && echo "${LK_OUT}" | grep -q "何も消さない" && ! echo "${LK_OUT}" | grep -q "削除対象"; then
  echo "✅ PASS [G9]: cwd が worktree のとき、終了コード 1・「何も消さない」で終わりました"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [G9]: 終了コード=${LK_RC}"
  echo "${LK_OUT}" | sed 's/^/    /'
  FAIL=$(( FAIL + 1 ))
fi

# G7: 元のリポジトリの .git がシンボリックリンク → 終了コード 1・何も消さない
LK_LINKMAIN="${TMPDIR_TEST}/linkcheck-symlink-${RANDOM}${RANDOM}"
mkdir -p "${LK_LINKMAIN}"
ln -s "${LK_MAIN}/.git" "${LK_LINKMAIN}/.git"
run_lk "${LK_LINKMAIN}"
if [ "${LK_RC}" -eq 1 ] && echo "${LK_OUT}" | grep -q "何も消さない" && ! echo "${LK_OUT}" | grep -q "削除対象"; then
  echo "✅ PASS [G7]: 本店の .git がシンボリックリンクのとき、終了コード 1・何も消さずに終わりました"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [G7]: 終了コード=${LK_RC}"
  echo "${LK_OUT}" | sed 's/^/    /'
  FAIL=$(( FAIL + 1 ))
fi

# G8: 本店の .git/commondir を偽の置き場へ。:66・:70 の rev-parse で命令が動かないこと
printf '2\n' > "${LK_MAIN}/f.txt"
printf '%s\n' "${LK_EVIL}" > "${LK_MAIN}/.git/commondir"
rm -f "${LK_MARK}"
git -C "${LK_MAIN}" -c core.fsmonitor=false -c core.hooksPath=/dev/null diff --no-ext-diff --no-textconv --ignore-submodules=all --numstat >/dev/null 2>&1 || true
if [ -e "${LK_MARK}" ]; then
  echo "✅ PASS [G8-対照]: 本店の commondir を偽の置き場に向けると、上書き付きの git diff でも印ができる（仕込みが効く作りだと確認）"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [G8-対照]: 印ができません（この作りでは filter が呼ばれない）"
  FAIL=$(( FAIL + 1 ))
fi
rm -f "${LK_MARK}"
run_lk "${LK_MAIN}"
rm -f "${LK_MAIN}/.git/commondir"
printf '1\n' > "${LK_MAIN}/f.txt"
if [ "${LK_RC}" -eq 1 ] && echo "${LK_OUT}" | grep -q "何も消さない" && ! echo "${LK_OUT}" | grep -q "削除対象"; then
  echo "✅ PASS [G8]: 本店の commondir が仕込まれているとき、終了コード 1・何も消さずに終わりました"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [G8]: 終了コード=${LK_RC}"
  echo "${LK_OUT}" | sed 's/^/    /'
  FAIL=$(( FAIL + 1 ))
fi
if [ ! -e "${LK_MARK}" ]; then
  echo "✅ PASS [G8-印]: reaper の rev-parse 段で印の台本が動きませんでした"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [G8-印]: reaper の rev-parse 段で印の台本が動きました"
  FAIL=$(( FAIL + 1 ))
fi
rm -f "${LK_MARK}"

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
