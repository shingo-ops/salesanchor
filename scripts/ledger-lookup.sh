#!/bin/bash
# ledger-lookup.sh — 台帳の窓口（読み）: ブランチ名で登録行を引く
# 使い方: bash scripts/ledger-lookup.sh <branch>
# 検索順: active-work.d/<セーフ形>.md → active-work.md（本体）
# exit 0=見つかった(行を出力) / 1=未登録 / 2=セーフ形衝突（別ブランチのファイル）
# 設計: docs/specs/ledger-guard/design-phase2.md §2
set -u
BRANCH="${1:-}"
[ -z "${BRANCH}" ] && { echo "使い方: ledger-lookup.sh <branch>" >&2; exit 1; }
GIT_COMMON_DIR="$(git rev-parse --git-common-dir 2>/dev/null)"
if [[ "${GIT_COMMON_DIR}" = /* ]]; then MAIN_REPO_ROOT="$(dirname "${GIT_COMMON_DIR}")"; else MAIN_REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; fi
LEDGER_FILE="${ACTIVE_WORK_FILE:-${MAIN_REPO_ROOT}/.claude-pipeline/active-work.md}"
LEDGER_DIR="${ACTIVE_WORK_DIR:-${MAIN_REPO_ROOT}/.claude-pipeline/active-work.d}"
SAFE="${BRANCH//\//-}"
DFILE="${LEDGER_DIR}/${SAFE}.md"
if [ -f "${DFILE}" ]; then
  DECLARED="$(grep -m1 '^branch: ' "${DFILE}" | sed 's/^branch: //')"
  if [ "${DECLARED}" != "${BRANCH}" ]; then
    echo "衝突: ${DFILE} は branch: ${DECLARED} の登録です（要求: ${BRANCH}）" >&2
    exit 2
  fi
  ROW="$(awk -F'|' -v b="${BRANCH}" 'NF>=4{f=$2; gsub(/^ +| +$/,"",f); if(f==b){print; exit}}' "${DFILE}")"
  [ -n "${ROW}" ] && { echo "${ROW}"; exit 0; }
  echo "登録ファイルはあるが行が見つからない: ${DFILE}" >&2; exit 1
fi
if [ -f "${LEDGER_FILE}" ]; then
  ROW="$(awk -F'|' -v b="${BRANCH}" 'NF>=4{f=$2; gsub(/^ +| +$/,"",f); if(f==b){print; exit}}' "${LEDGER_FILE}")"
  [ -n "${ROW}" ] && { echo "${ROW}"; exit 0; }
fi
exit 1
