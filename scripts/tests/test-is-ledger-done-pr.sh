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
#   [101件]   101件すべて台帳なら合格／101件目だけ台帳外なら不合格（100件打ち切りの回帰）
#   [件数不一致] 取得した件数が changedFiles と合わない → exit 2
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

# gh スタブ:
#   gh pr view <N> --json ...  → FAKE_PR_JSON
#   gh api --paginate .../files --jq ... → FAKE_FILES（改行区切りのファイル名。--jq 適用後の形）
mkdir -p "${TMP}/bin"
cat > "${TMP}/bin/gh" <<'STUB'
#!/bin/bash
case "$1" in
  pr)  printf '%s\n' "${FAKE_PR_JSON}" ;;
  api) printf '%s' "${FAKE_FILES}" ;;
  *)   echo "unexpected gh call: $*" >&2; exit 9 ;;
esac
STUB
chmod +x "${TMP}/bin/gh"

GOOD_BRANCH="release/ledger-done-3845"
GOOD_TITLE="chore(ledger): PR #3845 を DONE 化（自動）"
GOOD_FILE=".claude-pipeline/active-work.d/release-foo.md"
GOOD_AUTHOR="shingo-ops"

# make_json <branch> <title> <author> <changedFiles>
make_json() {
  jq -n --arg b "$1" --arg t "$2" --arg a "$3" --argjson c "$4" \
    '{headRefName:$b, title:$t, author:{login:$a}, changedFiles:$c}'
}

# run_case <name> <expected_rc> <json> <files(改行区切り)>
run_case() {
  local name="$1" want="$2" json="$3" files="$4" out rc
  out="$(GH_REPO="o/r" FAKE_PR_JSON="${json}" FAKE_FILES="${files}" PATH="${TMP}/bin:${PATH}" bash "${TARGET}" 3845 2>&1)"; rc=$?
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

# 101件の台帳ファイル一覧
gen_files() {
  local i
  for i in $(seq 1 101); do printf '.claude-pipeline/active-work.d/release-%s.md\n' "${i}"; done
}

run_case "合格: 4条件すべて満たす" 0 \
  "$(make_json "${GOOD_BRANCH}" "${GOOD_TITLE}" "${GOOD_AUTHOR}" 1)" "${GOOD_FILE}"

run_case "条件1欠: ブランチ名が違う" 1 \
  "$(make_json "release/other-3845" "${GOOD_TITLE}" "${GOOD_AUTHOR}" 1)" "${GOOD_FILE}"

run_case "条件2欠: タイトルが違う" 1 \
  "$(make_json "${GOOD_BRANCH}" "feat: something DONE 化（自動）" "${GOOD_AUTHOR}" 1)" "${GOOD_FILE}"

run_case "条件3欠: 台帳外のファイルを含む" 1 \
  "$(make_json "${GOOD_BRANCH}" "${GOOD_TITLE}" "${GOOD_AUTHOR}" 2)" "$(printf '%s\n%s' "${GOOD_FILE}" "backend/app/main.py")"

run_case "条件3欠: パス脱出（..）を含む" 1 \
  "$(make_json "${GOOD_BRANCH}" "${GOOD_TITLE}" "${GOOD_AUTHOR}" 1)" ".claude-pipeline/active-work.d/../../backend/x.py"

run_case "条件4欠: 作成者が違う" 1 \
  "$(make_json "${GOOD_BRANCH}" "${GOOD_TITLE}" "someone-else" 1)" "${GOOD_FILE}"

run_case "files 0件" 1 \
  "$(make_json "${GOOD_BRANCH}" "${GOOD_TITLE}" "${GOOD_AUTHOR}" 0)" ""

run_case "101件すべて台帳: 合格" 0 \
  "$(make_json "${GOOD_BRANCH}" "${GOOD_TITLE}" "${GOOD_AUTHOR}" 101)" "$(gen_files)"

run_case "101件目だけ台帳外: 不合格" 1 \
  "$(make_json "${GOOD_BRANCH}" "${GOOD_TITLE}" "${GOOD_AUTHOR}" 101)" "$(gen_files | head -n 100; echo "backend/app/main.py")"

run_case "件数不一致（取得100件・changedFiles=101）" 2 \
  "$(make_json "${GOOD_BRANCH}" "${GOOD_TITLE}" "${GOOD_AUTHOR}" 101)" "$(gen_files | head -n 100)"

OUT_NOARG="$(PATH="${TMP}/bin:${PATH}" bash "${TARGET}" 2>&1)"; RC_NOARG=$?
if [ "${RC_NOARG}" -eq 2 ]; then ok "引数無: exit 2"; else ng "引数無: rc=${RC_NOARG} out=${OUT_NOARG}"; fi

echo "----"
echo "PASS=${PASS} FAIL=${FAIL}"
[ "${FAIL}" -eq 0 ]
