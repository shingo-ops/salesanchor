#!/bin/bash
# record-baseline.sh — 登録された全ファイルを「実行済み」として ledger に記録だけ入れる（実行はしない）。
# ADR-1005 段階2 の baseline（Alembic の stamp に当たる 1 回限りの操作）。
#
# 使い方:
#   bash scripts/migration-ledger/record-baseline.sh                       # dry-run（既定。DB に触れない）
#   bash scripts/migration-ledger/record-baseline.sh --commit --expect-sha <デプロイ済みの main の SHA>
#
# 必ず守る前提（満たさないと --commit は拒否する）:
#   1. ADR-1007 段3 の PR（#3978、#4018、#4017）が、すべてマージされ、デプロイ済みであること。
#      → scripts/migration-ledger/step3-neutralized.list の全ファイルに「NEUTRALIZED (ADR-」の印があること。
#      （無効化の前に baseline を取ると、無効化の書き換えが、すべてチェックサム不一致になる）
#   2. 段階1（テナントの正本を 1 つに）が済んでいること（ADR-1005）。
#   3. 作業ツリーが、デプロイ済みの main のコミットと一致していること（--expect-sha で確かめる）。
# 本番の ledger への書き込みなので、PO の「psql write」チケットが要る（CLAUDE.md の不可逆操作）。
# このスクリプトは、DRY-RUN → COMMIT の 2 段で使う。手順は docs/handoff/migration-ledger/design.md。

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

MODE="dry-run"
REGISTRATION="${REPO_ROOT}/scripts/run_all_migrations.sh"
STEP3_LIST="${SCRIPT_DIR}/step3-neutralized.list"
EXPECT_SHA=""
REPO_DIR="${REPO_DIR:-${REPO_ROOT}}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) MODE="dry-run" ;;
    --commit) MODE="commit" ;;
    --registration) REGISTRATION="$2"; shift ;;
    --repo-dir) REPO_DIR="$2"; shift ;;
    --step3-files) STEP3_LIST="$2"; shift ;;
    --expect-sha) EXPECT_SHA="$2"; shift ;;
    *) echo "不明な引数: $1" >&2; exit 2 ;;
  esac
  shift
done

BACKEND="${BACKEND:-astro-webapp-backend-1}"
POSTGRES="${POSTGRES:-astro-webapp-postgres-1}"
PSQL="${PSQL:-psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1}"
STEP=0
TOTAL=0
# shellcheck disable=SC1091
. "${REPO_ROOT}/scripts/lib/migration_ledger.sh"

# 前提 3: コミットの一致
if [ -n "${EXPECT_SHA}" ]; then
  HEAD_SHA="$(git -C "${REPO_DIR}" rev-parse HEAD)"
  if [ "${HEAD_SHA}" != "${EXPECT_SHA}" ]; then
    echo "ERROR: 作業ツリーの HEAD (${HEAD_SHA}) が --expect-sha (${EXPECT_SHA}) と違います" >&2
    exit 1
  fi
  export LEDGER_GIT_SHA="${HEAD_SHA}"
elif [ "${MODE}" = "commit" ]; then
  echo "ERROR: --commit には --expect-sha（デプロイ済みの main の SHA）が必要です" >&2
  exit 1
fi

# 前提 1: 段3 の無効化の印
MISSING=""
if [ ! -f "${STEP3_LIST}" ]; then
  echo "ERROR: 段3 の一覧が見つかりません: ${STEP3_LIST}" >&2
  exit 1
fi
while read -r path; do
  case "${path}" in ''|'#'*) continue ;; esac
  if [ ! -f "${REPO_DIR}/${path}" ] || ! grep -q 'NEUTRALIZED (ADR-' "${REPO_DIR}/${path}"; then
    MISSING="${MISSING} ${path}"
  fi
done < "${STEP3_LIST}"
if [ -n "${MISSING}" ]; then
  echo "ERROR: 次のファイルに「NEUTRALIZED (ADR-」の印がありません（段3 の無効化が未反映）:" >&2
  for path in ${MISSING}; do echo "      ${path}" >&2; done
  if [ "${MODE}" = "commit" ]; then
    echo "baseline は記録しません。#3978・#4018・#4017 をマージしてデプロイしてから、やり直してください。" >&2
    exit 1
  fi
  echo "（dry-run なので続行します。--commit はここで拒否されます）"
fi

# 登録されたファイルの一覧（重複は 1 件にする）と、存在の確認
LIST="$(mktemp)"
ledger_registered_files "${REGISTRATION}" | sort -u -k2,2 > "${LIST}"
N_SQL="$(awk '$1 == "run_sql"' "${LIST}" | wc -l | tr -d ' ')"
N_PY="$(awk '$1 == "run_py"' "${LIST}" | wc -l | tr -d ' ')"
N_ALL="$(wc -l < "${LIST}" | tr -d ' ')"
ABSENT=""
while read -r cmd path; do
  [ -f "${REPO_DIR}/${path}" ] || ABSENT="${ABSENT} ${path}"
done < "${LIST}"
if [ -n "${ABSENT}" ]; then
  echo "ERROR: 登録されているが存在しないファイル:${ABSENT}" >&2
  rm -f "${LIST}"
  exit 1
fi

if [ "${MODE}" = "dry-run" ]; then
  echo "DRY-RUN: 記録する件数 ${N_ALL}（run_sql ${N_SQL}、run_py ${N_PY}）。DB には何も書きません。手順は 1 件も実行しません。"
  head -3 "${LIST}" | while read -r cmd path; do
    echo "  例: ${path}  sha256=$(ledger_sha256 "${REPO_DIR}/${path}")"
  done
  rm -f "${LIST}"
  exit 0
fi

# --commit: ledger の表を用意し（無ければ作成の migration だけ実行）、全件を status=baseline で記録する
ledger_ensure_table
ledger_load
RECORDED=0
SKIPPED=0
while read -r cmd path; do
  kind="sql"; [ "${cmd}" = "run_py" ] && kind="py"
  if [ -n "$(ledger_cached_sum "${path}")" ]; then SKIPPED=$((SKIPPED + 1)); continue; fi
  ledger_record "${kind}" "${path}" "$(ledger_sha256 "${REPO_DIR}/${path}")" 0 baseline
  RECORDED=$((RECORDED + 1))
done < "${LIST}"
rm -f "${LIST}"
echo "COMMIT: baseline を記録した ${RECORDED} 件（既に記録済みで飛ばした ${SKIPPED} 件、登録 ${N_ALL} 件）。手順は 1 件も実行していません。"
