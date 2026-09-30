#!/bin/bash
# is-ledger-done-pr.sh — 「台帳 DONE化 PR」かどうかの判定（判定条件の唯一の置き場所）
#
# 使い方: bash scripts/ci/is-ledger-done-pr.sh <PR番号>
# 終了コード: 0=台帳 DONE化 PR / 1=該当しない（理由は stderr）/ 2=使い方・取得の誤り
#
# 次の4条件をすべて満たすときだけ exit 0:
#   1. head ブランチ名が release/ledger-done- で始まる
#   2. タイトルが「chore(ledger): ... DONE 化（自動）」の形
#   3. 変更ファイルが1件以上あり、すべて .claude-pipeline/active-work.d/ の下（.. を含まない）
#   4. 作成者が LEDGER_PR_AUTHOR である
#
# 変更ファイルは pulls/{n}/files を --paginate で全件取る（gh pr view --json files は
# 100件で打ち切られるため）。取れた件数が changedFiles と合わなければ exit 2。
#
# 呼び出し元: ledger-auto-done-main.yml（予約前）/ auto-merge-guard.yml（見張り）
# 設計: docs/handoff/ledger-auto-done-main/design.md
set -u

# 台帳PRを作るアカウント（PIPELINE_PAT の持ち主）。ここ1か所だけに置く。
LEDGER_PR_AUTHOR="shingo-ops"
BRANCH_PREFIX="release/ledger-done-"
TITLE_REGEX='^chore\(ledger\): .*DONE 化（自動）$'
FILES_PREFIX=".claude-pipeline/active-work.d/"

PR="${1:-}"
if [ -z "${PR}" ]; then
  echo "usage: is-ledger-done-pr.sh <PR番号>" >&2
  exit 2
fi

if ! JSON="$(gh pr view "${PR}" --json headRefName,title,author,changedFiles)"; then
  echo "PR #${PR} の情報を取得できない" >&2
  exit 2
fi

REPO="${GH_REPO:-}"
if [ -z "${REPO}" ] && ! REPO="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"; then
  echo "リポジトリ名を取得できない" >&2
  exit 2
fi

if ! FILES_LIST="$(gh api --paginate "repos/${REPO}/pulls/${PR}/files" --jq '.[].filename')"; then
  echo "PR #${PR} の変更ファイル一覧を取得できない" >&2
  exit 2
fi

BRANCH="$(jq -r '.headRefName // ""' <<<"${JSON}")"
TITLE="$(jq -r '.title // ""' <<<"${JSON}")"
AUTHOR="$(jq -r '.author.login // ""' <<<"${JSON}")"
EXPECTED_COUNT="$(jq -r '.changedFiles // -1' <<<"${JSON}")"

FILE_COUNT=0
BAD_FILES=()
while IFS= read -r F; do
  [ -n "${F}" ] || continue
  FILE_COUNT=$((FILE_COUNT + 1))
  if [[ "${F}" != "${FILES_PREFIX}"* || "${F}" == *..* ]]; then
    BAD_FILES+=("${F}")
  fi
done <<<"${FILES_LIST}"

if [ "${FILE_COUNT}" -ne "${EXPECTED_COUNT}" ]; then
  echo "変更ファイル数が合わない: 取得=${FILE_COUNT} changedFiles=${EXPECTED_COUNT}" >&2
  exit 2
fi

REASONS=()
[[ "${BRANCH}" == "${BRANCH_PREFIX}"* ]] || REASONS+=("head ブランチ名が ${BRANCH_PREFIX} で始まらない (${BRANCH})")
[[ "${TITLE}" =~ ${TITLE_REGEX} ]] || REASONS+=("タイトルが台帳DONE化の形でない (${TITLE})")
[ "${FILE_COUNT}" -ge 1 ] || REASONS+=("変更ファイルが0件")
[ "${#BAD_FILES[@]}" -eq 0 ] || REASONS+=("台帳ディレクトリ外のファイルを含む (${BAD_FILES[0]} ほか計${#BAD_FILES[@]}件)")
[ "${AUTHOR}" = "${LEDGER_PR_AUTHOR}" ] || REASONS+=("作成者が ${LEDGER_PR_AUTHOR} でない (${AUTHOR})")

if [ "${#REASONS[@]}" -gt 0 ]; then
  printf '%s\n' "${REASONS[@]}" | paste -sd ';' - >&2
  exit 1
fi
exit 0
