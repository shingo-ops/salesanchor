#!/bin/bash
# check-migration-immutability.sh — 実行済み（登録済み）の migration の書き換えを CI で止める（ADR-1005 段階2）。
#
# 登録（scripts/run_all_migrations.sh の run_sql / run_py）されたファイルのうち、base（main）に
# 既にあるものが head で変わっていたら失敗する。直したいときは新しい手順を足す。
# 例外: 毎回実行リスト（scripts/migration-ledger/every-run.list）のファイル。
# 新しく追加したファイル（base に無いもの）は対象外（PR の中で直してよい）。
#
# 使い方:
#   BASE_SHA=<sha> HEAD_SHA=<sha> bash scripts/check-migration-immutability.sh
#   bash scripts/check-migration-immutability.sh --base <sha> --head <sha> [--repo-dir D] [--registration F] [--every-run-list F]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REGISTRATION=""
EVERY_RUN_LIST=""
BASE="${BASE_SHA:-}"
HEAD_REF="${HEAD_SHA:-HEAD}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --base) BASE="$2"; shift ;;
    --head) HEAD_REF="$2"; shift ;;
    --repo-dir) REPO_DIR="$2"; shift ;;
    --registration) REGISTRATION="$2"; shift ;;
    --every-run-list) EVERY_RUN_LIST="$2"; shift ;;
    *) echo "不明な引数: $1" >&2; exit 2 ;;
  esac
  shift
done

[ -n "${REGISTRATION}" ] || REGISTRATION="${REPO_DIR}/scripts/run_all_migrations.sh"
[ -n "${EVERY_RUN_LIST}" ] || EVERY_RUN_LIST="${REPO_DIR}/scripts/migration-ledger/every-run.list"

if [ -z "${BASE}" ]; then
  echo "ERROR: --base（または BASE_SHA）が必要です" >&2
  exit 2
fi

is_every_run() {
  [ -f "${EVERY_RUN_LIST}" ] || return 1
  grep -v '^[[:space:]]*#' "${EVERY_RUN_LIST}" | grep -qxF "$1"
}

BAD=""
CHECKED=0
LIST="$(mktemp)"
grep -E '^run_(sql|py)[[:space:]]' "${REGISTRATION}" | awk '{print $2}' | sort -u > "${LIST}"
while read -r path; do
  # base に無いファイルは「新規追加」なので対象外
  if ! git -C "${REPO_DIR}" cat-file -e "${BASE}:${path}" 2>/dev/null; then continue; fi
  CHECKED=$((CHECKED + 1))
  if is_every_run "${path}"; then continue; fi
  if ! git -C "${REPO_DIR}" diff --quiet "${BASE}" "${HEAD_REF}" -- "${path}"; then
    BAD="${BAD} ${path}"
  fi
done < "${LIST}"
rm -f "${LIST}"

if [ -n "${BAD}" ]; then
  echo "ERROR: 実行済み（登録済み）の migration が書き換えられています:" >&2
  for path in ${BAD}; do echo "      ${path}" >&2; done
  echo "直したい場合は、新しい migration を足してください（ADR-1005 段階2）。" >&2
  echo "毎回実行が必要なファイルだけ scripts/migration-ledger/every-run.list に載せられます（設計担当の判断）。" >&2
  exit 1
fi
echo "OK: 登録済みで base に既にある ${CHECKED} 件のファイルは、書き換えられていません。"
