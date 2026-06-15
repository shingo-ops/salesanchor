#!/bin/bash
# test-manifest-generation.sh — auto-release-pr.yml manifest 生成ロジックのテスト
#
# 検証項目:
#   [1] squash merge 形式のコミットでも PR 番号が manifest に入ること
#       （--merges なし git log で #NNNN を拾えること）
#   [2] 既存 release PR がある状態で develop が進んだ場合、
#       PR 本文の manifest ブロックとテーブルが更新されること
#
# 実行方法: bash scripts/tests/test-manifest-generation.sh
# 終了コード: 0=全PASS / 1=FAIL あり

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PASS=0
FAIL=0

TMPDIR_TEST=$(mktemp -d /tmp/manifest-test.XXXXXX)
trap 'rm -rf "${TMPDIR_TEST}"' EXIT

# ── モック gh コマンド ────────────────────────────────────────────────────────
MOCK_BIN="${TMPDIR_TEST}/mock-bin"
mkdir -p "${MOCK_BIN}"

# gh の動作:
#   gh pr view <num> --json headRefName -q .headRefName → "feature/test/pr-<num>"
#   gh pr view <num> --json body -q .body              → fake PR body（テスト2用）
#   gh pr edit <num> --body <body>                      → body を temp ファイルに書く
FAKE_PR_BODY_FILE="${TMPDIR_TEST}/current-pr-body.txt"
UPDATED_PR_BODY_FILE="${TMPDIR_TEST}/updated-pr-body.txt"

cat > "${MOCK_BIN}/gh" << 'GHEOF'
#!/bin/bash
# 引数をスペース結合して簡易マッチ
ARGS="$*"

if [[ "$ARGS" == *"--json headRefName"* ]]; then
  # pr view <num> --json headRefName -q .headRefName
  num=$(echo "$ARGS" | grep -oE '[0-9]+' | head -1)
  echo "feature/test/pr-${num}"
  exit 0
fi

if [[ "$ARGS" == *"--json body"* ]]; then
  # pr view <existing> --json body -q .body → 既存 PR 本文
  cat "${FAKE_PR_BODY_FILE}"
  exit 0
fi

if [[ "$ARGS" == *"pr edit"* ]]; then
  # gh pr edit <num> --body <body>
  # --body の次の引数が本文
  body=""
  capture_next=false
  for arg in "$@"; do
    if $capture_next; then
      body="$arg"
      break
    fi
    if [ "$arg" = "--body" ]; then
      capture_next=true
    fi
  done
  echo "$body" > "${UPDATED_PR_BODY_FILE}"
  exit 0
fi

echo ""
exit 0
GHEOF
chmod +x "${MOCK_BIN}/gh"

export PATH="${MOCK_BIN}:${PATH}"

# ── テスト 1: squash merge コミットでも PR 番号を抽出できること ──────────────

# 一時 git リポジトリを作成
FAKE_REPO="${TMPDIR_TEST}/fake-repo"
git init "${FAKE_REPO}" -q 2>/dev/null
git -C "${FAKE_REPO}" config user.email "test@test.com"
git -C "${FAKE_REPO}" config user.name "test"

# "main" 相当のベースコミット
touch "${FAKE_REPO}/base.txt"
git -C "${FAKE_REPO}" add .
git -C "${FAKE_REPO}" commit -m "init" -q 2>/dev/null
git -C "${FAKE_REPO}" branch -M main 2>/dev/null || true

# origin/main として参照できるよう bare リポジトリを作成してリモート追加
FAKE_REMOTE="${TMPDIR_TEST}/fake-remote.git"
git init --bare "${FAKE_REMOTE}" -q 2>/dev/null
git -C "${FAKE_REPO}" remote add origin "${FAKE_REMOTE}"
git -C "${FAKE_REPO}" push origin main -q 2>/dev/null

# squash merge スタイルのコミット（--merges では拾えない形式）
echo "squash1" > "${FAKE_REPO}/f1.txt"
git -C "${FAKE_REPO}" add .
git -C "${FAKE_REPO}" commit -m "feat: 機能追加A (#2300)" -q 2>/dev/null

echo "squash2" > "${FAKE_REPO}/f2.txt"
git -C "${FAKE_REPO}" add .
git -C "${FAKE_REPO}" commit -m "fix: バグ修正B (#2301)" -q 2>/dev/null

# 通常マージコミット（--merges でも拾える形式）
git -C "${FAKE_REPO}" checkout -b feature-x -q 2>/dev/null
echo "merge1" > "${FAKE_REPO}/f3.txt"
git -C "${FAKE_REPO}" add .
git -C "${FAKE_REPO}" commit -m "feat: マージ用コミット (#2302)" -q 2>/dev/null
git -C "${FAKE_REPO}" checkout main -q 2>/dev/null
git -C "${FAKE_REPO}" merge --no-ff feature-x -m "Merge pull request #2302 from feature-x" -q 2>/dev/null

# manifest 生成コマンドを実行（--merges なし）
PR_NUMBERS=$(git -C "${FAKE_REPO}" log origin/main..HEAD --oneline \
  | grep -oE '#[0-9]+' | tr -d '#' | sort -un || true)

# 検証: 3件すべての PR 番号が含まれること
MISSING=""
for expected in 2300 2301 2302; do
  if ! echo "${PR_NUMBERS}" | grep -qx "${expected}"; then
    MISSING="${MISSING} ${expected}"
  fi
done

if [ -z "${MISSING}" ]; then
  echo "✅ PASS [squash-merge対応]: PR 2300, 2301, 2302 がすべて抽出されました"
  PASS=$(( PASS + 1 ))
else
  echo "❌ FAIL [squash-merge対応]: 以下の PR 番号が抽出されませんでした:${MISSING}"
  echo "   git log 出力: $(git -C "${FAKE_REPO}" log origin/main..HEAD --oneline)"
  FAIL=$(( FAIL + 1 ))
fi

# --merges のみでは squash が漏れることの確認（参考テスト）
PR_NUMBERS_MERGES_ONLY=$(git -C "${FAKE_REPO}" log origin/main..HEAD --merges --oneline \
  | grep -oE '#[0-9]+' | tr -d '#' | sort -un || true)

if echo "${PR_NUMBERS_MERGES_ONLY}" | grep -qx "2300"; then
  echo "⚠️  NOTE [--merges限定]: squash PR 2300 が --merges でも拾えました（環境依存）"
else
  echo "✅ PASS [--merges限定]: --merges では squash PR 2300/2301 が漏れることを確認"
  PASS=$(( PASS + 1 ))
fi

# ── テスト 2: 既存 release PR がある場合に manifest ブロックとテーブルが更新される ──

# 既存 PR の本文（manifest ブロックあり・古い PR リスト）
cat > "${FAKE_PR_BODY_FILE}" << 'BODYEOF'
## リリース PR（自動起票）

develop ブランチが main より先行したため自動起票しました。

**しんごさん（PO）が内容確認後マージしてください。**

## migration 確認

✅ 本リリースに migration は含まれていません。

## 今回本番反映予定の PR（1 件）

| PR# | ブランチ |
|-----|--------|
| #2200 | feature/test/old-pr |

## マージ前チェックリスト

- [ ] develop の変更内容をすべて確認した

---

<!-- active-work-release-manifest
prs:
  - 2200
branches:
  - feature/test/old-pr
-->

*このPRは `develop` ブランチへのプッシュを検知して自動起票されました。*
BODYEOF

# 更新後の期待値（新しい PR 2300, 2301, 2302 が含まれる）
EXISTING_PR="9999"
PR_COUNT="3"
PR_YAML="  - 2300
  - 2301
  - 2302
"
BRANCH_YAML="  - feature/test/pr-2300
  - feature/test/pr-2301
  - feature/test/pr-2302
"
TABLE_ROWS="| #2300 | feature/test/pr-2300 |
| #2301 | feature/test/pr-2301 |
| #2302 | feature/test/pr-2302 |
"

# Python の更新ロジックを直接実行（auto-release-pr.yml から抽出）
export EXISTING_PR PR_COUNT PR_YAML BRANCH_YAML TABLE_ROWS FAKE_PR_BODY_FILE UPDATED_PR_BODY_FILE
python3 - <<'PYEOF'
import os, re, subprocess, sys

existing_pr = os.environ["EXISTING_PR"]
pr_count    = os.environ.get("PR_COUNT", "0")
pr_yaml     = os.environ.get("PR_YAML", "")
branch_yaml = os.environ.get("BRANCH_YAML", "")
table_rows  = os.environ.get("TABLE_ROWS", "")

# 既存 PR 本文を取得（モック gh 経由）
result = subprocess.run(
    ["gh", "pr", "view", existing_pr, "--json", "body", "-q", ".body"],
    capture_output=True, text=True, check=True,
)
body = result.stdout.rstrip("\n")

# manifest ブロック置換
new_manifest = (
    f"<!-- active-work-release-manifest\n"
    f"prs:\n{pr_yaml}branches:\n{branch_yaml}-->"
)
new_body = re.sub(
    r"<!-- active-work-release-manifest.*?-->",
    new_manifest,
    body,
    flags=re.DOTALL,
)

# テーブル置換
new_table = (
    f"## 今回本番反映予定の PR（{pr_count} 件）\n\n"
    f"| PR# | ブランチ |\n"
    f"|-----|--------|\n"
    f"{table_rows}"
)
new_body = re.sub(
    r"## 今回本番反映予定の PR（\d+ 件）\n\n"
    r"\| PR# \| ブランチ \|\n\|[^\n]+\n(?:\|[^\n]*\n)*",
    new_table,
    new_body,
)

if new_body == body:
    print("ERROR: 本文に変更なし", file=sys.stderr)
    sys.exit(1)

# モック gh pr edit に渡す
subprocess.run(
    ["gh", "pr", "edit", existing_pr, "--body", new_body],
    check=True,
)
print(f"updated: PR #{existing_pr}")
PYEOF

# 検証: 更新後の本文に新しい PR 番号が含まれ、古い PR が manifest ブロックにない
UPDATE_OK=true

for expected_pr in "2300" "2301" "2302"; do
  if ! grep -q "#${expected_pr}" "${UPDATED_PR_BODY_FILE}"; then
    echo "❌ FAIL [manifest更新]: #${expected_pr} が更新後の PR 本文に含まれていません"
    UPDATE_OK=false
  fi
done

if grep -q "#2200" "${UPDATED_PR_BODY_FILE}"; then
  # テーブルからは消えているが manifest ブロックも更新されているはず
  # 古い PR 2200 が manifest ブロック内に残っていたら失敗
  if grep -A 10 "active-work-release-manifest" "${UPDATED_PR_BODY_FILE}" | grep -q "2200"; then
    echo "❌ FAIL [manifest更新]: 古い PR #2200 が manifest ブロックに残っています"
    UPDATE_OK=false
  fi
fi

if $UPDATE_OK; then
  echo "✅ PASS [既存リリースPR manifest更新]: 新しい PR リストで manifest が更新されました"
  PASS=$(( PASS + 1 ))
else
  FAIL=$(( FAIL + 1 ))
fi

# ── 結果 ─────────────────────────────────────────────────────────────────────
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
