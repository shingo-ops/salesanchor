#!/bin/bash
# ledger-update.sh — 台帳の窓口（書き）: 登録行の状態またはPR#を更新する
# 使い方: bash scripts/ledger-update.sh <branch> --status <S> | --pr <N>
# 更新先は行の所在側（.d優先→本体）。exit 0=更新 / 1=未登録 / 2=衝突
# 設計: docs/specs/ledger-guard/design-phase2.md §2
set -u
BRANCH="${1:-}"; MODE="${2:-}"; VALUE="${3:-}"
{ [ -z "${BRANCH}" ] || [ -z "${VALUE}" ]; } && { echo "使い方: ledger-update.sh <branch> --status <S> | --pr <N>" >&2; exit 1; }
case "${MODE}" in --status|--pr) ;; *) echo "不明なオプション: ${MODE}" >&2; exit 1;; esac
GIT_COMMON_DIR="$(git rev-parse --git-common-dir 2>/dev/null)"
if [[ "${GIT_COMMON_DIR}" = /* ]]; then MAIN_REPO_ROOT="$(dirname "${GIT_COMMON_DIR}")"; else MAIN_REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; fi
LEDGER_FILE="${ACTIVE_WORK_FILE:-${MAIN_REPO_ROOT}/.claude-pipeline/active-work.md}"
LEDGER_DIR="${ACTIVE_WORK_DIR:-${MAIN_REPO_ROOT}/.claude-pipeline/active-work.d}"
SAFE="${BRANCH//\//-}"
DFILE="${LEDGER_DIR}/${SAFE}.md"
TARGET=""
if [ -f "${DFILE}" ]; then
  DECLARED="$(grep -m1 '^branch: ' "${DFILE}" | sed 's/^branch: //')"
  [ "${DECLARED}" != "${BRANCH}" ] && { echo "衝突: ${DFILE} は branch: ${DECLARED} の登録です" >&2; exit 2; }
  TARGET="${DFILE}"
elif bash "$(dirname "$0")/ledger-lookup.sh" "${BRANCH}" > /dev/null 2>&1; then
  TARGET="${LEDGER_FILE}"
else
  echo "未登録: ${BRANCH}" >&2; exit 1
fi
python3 - "${TARGET}" "${BRANCH}" "${MODE}" "${VALUE}" << 'PYEOF'
import sys
path, branch, mode, value = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
idx = 4 if mode == "--status" else 5
out, hit = [], 0
for line in open(path, encoding="utf-8").read().splitlines(keepends=True):
    if line.lstrip().startswith("|"):
        parts = line.rstrip("\n").split("|")
        if len(parts) >= 8 and parts[1].strip() == branch and hit == 0:
            parts[idx] = f" {value} "
            line = "|".join(parts) + "\n"
            hit = 1
            print("更新:", line.rstrip())
    out.append(line)
if hit == 0:
    print(f"行が見つからない: {branch}", file=sys.stderr)
    sys.exit(1)
open(path, "w", encoding="utf-8").write("".join(out))
PYEOF
exit $?
