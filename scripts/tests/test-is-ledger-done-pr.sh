#!/bin/bash
# test-is-ledger-done-pr.sh — scripts/ci/is-ledger-done-pr.sh の判定テスト（gh をスタブ化）
#
# 検証項目:
#   [合格]     4条件をすべて満たす PR は exit 0
#   [条件1欠] head ブランチ名が release/ledger-done- で始まらない → exit 1
#   [条件2欠] タイトルが規定の形でない → exit 1
#   [条件3欠] 台帳ディレクトリ外のファイルを含む／パス脱出（..）を含む → exit 1
#   [条件4欠] 作成者が shingo-ops でない → exit 1
#   [files空] 変更ファイルが 0 件 → exit 1
#   [引数無]  PR番号なし → exit 2
#
# 実行方法: bash scripts/tests/test-is-ledger-done-pr.sh
# 終了コード: 0=全PASS / 1=FAILあり
set -u

HERE="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${HERE}/ci/is-ledger-done-pr.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT

PASS=0; FAIL=0
ok(){ echo "PASS: $1"; PASS=$((PASS+1)); }
ng(){ echo "FAIL: $1"; FAIL=$((FAIL+1)); }

# gh スタブ: `gh pr view <N> --json ...` に対し FAKE_PR_JSON を返す
mkdir -p "${TMP}/bin"
cat > "${TMP}/bin/gh" <<'STUB'
#!/bin/bash
printf '%s\n' "${FAKE_PR_JSON}"
STUB
chmod +x "${TMP}/bin/gh"

GOOD_BRANCH="release/ledger-done-3845"
GOOD_TITLE="chore(ledger): PR #3845 を DONE 化（自動）"
GOOD_FILE=".claude-pipeline/active-work.d/release-foo.md"
GOOD_AUTHOR="shingo-ops"

# make_json <branch> <title> <files_json_array> <author>
make_json() {
  jq -n --arg b "$1" --arg t "$2" --argjson f "$3" --arg a "$4" \
    '{headRefName:$b, title:$t, files:$f, author:{login:$a}}'
}
files_of() { jq -n --arg p "$1" '[{path:$p}]'; }

# run_case <name> <expected_rc> <json>
run_case() {
  local name="$1" want="$2" json="$3" out rc
  out="$(FAKE_PR_JSON="${json}" PATH="${TMP}/bin:${PATH}" bash "${TARGET}" 3845 2>&1)"; rc=$?
  if [ "${rc}" -eq "${want}" ]; then
    if [ "${want}" -ne 0 ] && [ -z "${out}" ]; then
      ng "${name}: 理由が stderr に出ていない"
    else
      ok "${name} (rc=${rc})"
    fi
  else
    ng "${name}: rc=${rc} 期待=${want} out=${out}"
  fi
}

run_case "合格: 4条件すべて満たす" 0 \
  "$(make_json "${GOOD_BRANCH}" "${GOOD_TITLE}" "$(files_of "${GOOD_FILE}")" "${GOOD_AUTHOR}")"

run_case "条件1欠: ブランチ名が違う" 1 \
  "$(make_json "release/other-3845" "${GOOD_TITLE}" "$(files_of "${GOOD_FILE}")" "${GOOD_AUTHOR}")"

run_case "条件2欠: タイトルが違う" 1 \
  "$(make_json "${GOOD_BRANCH}" "feat: something DONE 化（自動）" "$(files_of "${GOOD_FILE}")" "${GOOD_AUTHOR}")"

run_case "条件3欠: 台帳外のファイルを含む" 1 \
  "$(make_json "${GOOD_BRANCH}" "${GOOD_TITLE}" "$(jq -n --arg a "${GOOD_FILE}" '[{path:$a},{path:"backend/app/main.py"}]')" "${GOOD_AUTHOR}")"

run_case "条件3欠: パス脱出（..）を含む" 1 \
  "$(make_json "${GOOD_BRANCH}" "${GOOD_TITLE}" "$(files_of ".claude-pipeline/active-work.d/../../backend/x.py")" "${GOOD_AUTHOR}")"

run_case "条件4欠: 作成者が違う" 1 \
  "$(make_json "${GOOD_BRANCH}" "${GOOD_TITLE}" "$(files_of "${GOOD_FILE}")" "someone-else")"

run_case "files 0件" 1 \
  "$(make_json "${GOOD_BRANCH}" "${GOOD_TITLE}" "[]" "${GOOD_AUTHOR}")"

OUT_NOARG="$(PATH="${TMP}/bin:${PATH}" bash "${TARGET}" 2>&1)"; RC_NOARG=$?
if [ "${RC_NOARG}" -eq 2 ]; then ok "引数無: exit 2"; else ng "引数無: rc=${RC_NOARG} out=${OUT_NOARG}"; fi

echo "----"
echo "PASS=${PASS} FAIL=${FAIL}"
[ "${FAIL}" -eq 0 ]
