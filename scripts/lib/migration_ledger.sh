#!/bin/bash
# scripts/lib/migration_ledger.sh — 実行済み記録（ledger）の関数（ADR-1005 段階2）
#
# scripts/run_all_migrations.sh から source される。run_sql / run_py はここで定義する
# （本番と試験 scripts/tests/test-migration-ledger.sh が同じ関数を使うため）。
#
# 方針:
#   - 記録の置き場所は専用スキーマ ops の表 ops.migration_ledger
#     （public と違い、salesanchor_app に DML が自動で付かない）。作成は migrations/ の構造だけの migration。
#   - 通常: ledger に無い手順だけを登録順に実行し、成功したものだけ記録する。
#   - 記録済みファイルの内容（sha256、改行は LF に正規化）が変わっていたら、何も実行せずに失敗する。
#   - 全件やり直しモード: --full（または MIGRATION_FULL_RERUN=1）。記録を無視して全件実行し、記録を更新する。
#   - 毎回実行リスト: scripts/migration-ledger/every-run.list（1 ファイル）。載っているものは毎回実行する。
#
# 呼び出し元が用意する変数: REPO_DIR, BACKEND, POSTGRES, PSQL, TOTAL, STEP
# 試験用: LEDGER_HOOKS_FILE に shell ファイルを指定すると、末尾で source して関数を差し替えられる。

: "${LEDGER_SCOPE:=public}"
: "${LEDGER_DDL_FILE:=migrations/20261007_100000_create_migration_ledger.sql}"
: "${LEDGER_EVERY_RUN_LIST:=${REPO_DIR:-.}/scripts/migration-ledger/every-run.list}"
LEDGER_CACHE=""

# --- DB と実行（本番の既定。試験は hooks で差し替える）-----------------------------------------
# SQL を標準入力で受け、タブ区切り・見出しなしで結果を返す。
ledger_psql() {
  docker exec -i "${POSTGRES}" ${PSQL} -tA -F "$(printf '\t')"
}

ledger_exec_sql() {
  local file="$1"
  echo ">>> [${STEP}/${TOTAL:-?}] psql < ${file}"
  docker exec -i "${POSTGRES}" ${PSQL} < "${REPO_DIR}/${file}"
}

ledger_exec_py() {
  local script="$1"
  shift
  echo ">>> [${STEP}/${TOTAL:-?}] python ${script} $*"
  # SA-18 Phase2: Python マイグレーションは DDL を含むため ADMIN_DATABASE_URL で実行。
  # ADMIN_DATABASE_URL 未設定時は DATABASE_URL にフォールバック（後方互換）。
  docker exec \
    -e DATABASE_URL="${ADMIN_DATABASE_URL:-$DATABASE_URL}" \
    "$@" -w /app "${BACKEND}" python "${script}"
}

# --- 登録行の入口（run_all_migrations.sh の登録行がこれを呼ぶ）----------------------------------
run_sql() {
  STEP=$((STEP + 1))
  ledger_step sql "$1" ledger_exec_sql "$1"
}

run_py() {
  STEP=$((STEP + 1))
  ledger_step py "$1" ledger_exec_py "$@"
}

# --- 部品 ------------------------------------------------------------------------------------
# sha256（改行コードの違いで不一致にならないよう、CR を除いてから計算する）
ledger_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    tr -d '\r' < "$1" | sha256sum | cut -d' ' -f1
  else
    tr -d '\r' < "$1" | shasum -a 256 | cut -d' ' -f1
  fi
}

# SQL に埋め込む値の検査（英数字・_ . / - だけを許す）
ledger_valid_token() {
  case "$1" in
    "") return 1 ;;
    *[!A-Za-z0-9_./-]*) return 1 ;;
  esac
  return 0
}

ledger_is_every_run() {
  [ -f "${LEDGER_EVERY_RUN_LIST}" ] || return 1
  grep -v '^[[:space:]]*#' "${LEDGER_EVERY_RUN_LIST}" | grep -qxF "$1"
}

ledger_git_sha() {
  if [ -n "${LEDGER_GIT_SHA:-}" ]; then
    echo "${LEDGER_GIT_SHA}"
  else
    git -C "${REPO_DIR}" rev-parse HEAD 2>/dev/null || echo unknown
  fi
}

# 登録された手順の一覧（"run_sql path" または "run_py path" の行）。引数: 登録のスクリプト
ledger_registered_files() {
  grep -E '^run_(sql|py)[[:space:]]' "$1" | awk '{print $1, $2}'
}

ledger_table_exists() {
  local found
  found="$(printf "SELECT to_regclass('ops.migration_ledger');\n" | ledger_psql)" || return 2
  [ -n "${found}" ]
}

ledger_ensure_table() {
  if ledger_table_exists; then return 0; fi
  echo ">>> [ledger] ops.migration_ledger が無いので、作成の migration を実行する: ${LEDGER_DDL_FILE}"
  ledger_exec_sql "${LEDGER_DDL_FILE}" || return 1
  if ! ledger_table_exists; then
    echo ">>> ERROR [ledger] 作成の後も ops.migration_ledger が見つからない" >&2
    return 1
  fi
}

ledger_load() {
  LEDGER_CACHE="$(mktemp)"
  printf "SELECT scope, filename, checksum, status FROM ops.migration_ledger WHERE scope = '%s' ORDER BY id;\n" \
    "${LEDGER_SCOPE}" | ledger_psql > "${LEDGER_CACHE}"
}

ledger_cached_sum() {
  awk -F'\t' -v f="$1" '$2 == f {print $3; exit}' "${LEDGER_CACHE}"
}

# 記録済みファイルのチェックサムの検査（何も実行する前に、全件を調べる）。引数: 登録のスクリプト
ledger_preflight() {
  local reg="$1" list bad="" cmd path cached cur
  list="$(mktemp)"
  ledger_registered_files "${reg}" > "${list}"
  while read -r cmd path; do
    [ -f "${REPO_DIR}/${path}" ] || continue
    if ledger_is_every_run "${path}"; then continue; fi
    cached="$(ledger_cached_sum "${path}")"
    [ -n "${cached}" ] || continue
    cur="$(ledger_sha256 "${REPO_DIR}/${path}")"
    if [ "${cached}" != "${cur}" ]; then bad="${bad} ${path}"; fi
  done < "${list}"
  rm -f "${list}"
  if [ -n "${bad}" ]; then
    echo ">>> ERROR [ledger] 実行済みの手順の内容が変わっています（チェックサム不一致）。何も実行せずに止めます:" >&2
    for path in ${bad}; do echo "      ${path}" >&2; done
    echo ">>> 直したい場合は新しい手順を足してください。緊急時の全件やり直しは --full（MIGRATION_FULL_RERUN=1）。" >&2
    return 1
  fi
}

# 初期化。引数: 登録のスクリプト（通常は "$0"）
ledger_init() {
  local reg="$1"
  if [ "${MIGRATION_FULL_RERUN:-0}" = "1" ]; then
    echo ">>> [ledger] 全件やり直しモード: 記録を無視して全件を実行し、記録を更新する"
  fi
  ledger_ensure_table || return 1
  ledger_load || return 1
  if [ "${MIGRATION_FULL_RERUN:-0}" = "1" ]; then return 0; fi
  ledger_preflight "${reg}"
}

# 1 件の記録（成功したあとだけ呼ぶ）。引数: 種類 ファイル チェックサム 所要ミリ秒 [状態]
ledger_record() {
  local kind="$1" file="$2" sum="$3" ms="$4" status="${5:-applied}" sha
  sha="$(ledger_git_sha)"
  ledger_valid_token "${kind}" && ledger_valid_token "${file}" && ledger_valid_token "${sum}" \
    && ledger_valid_token "${status}" && ledger_valid_token "${sha}" || {
    echo ">>> ERROR [ledger] 記録する値に使えない文字がある: ${file}" >&2
    return 1
  }
  case "${ms}" in ''|*[!0-9]*) ms=0 ;; esac
  printf "INSERT INTO ops.migration_ledger (scope, kind, filename, checksum, status, duration_ms, git_sha) VALUES ('%s','%s','%s','%s','%s',%s,'%s') ON CONFLICT (scope, filename) DO UPDATE SET kind = EXCLUDED.kind, checksum = EXCLUDED.checksum, status = EXCLUDED.status, applied_at = NOW(), duration_ms = EXCLUDED.duration_ms, git_sha = EXCLUDED.git_sha;\n" \
    "${LEDGER_SCOPE}" "${kind}" "${file}" "${sum}" "${status}" "${ms}" "${sha}" | ledger_psql > /dev/null
}

# 1 手順の実行。引数: 種類 ファイル 実行のコマンド…
ledger_step() {
  local kind="$1" file="$2" cached cur t0 t1
  shift 2
  ledger_valid_token "${file}" || { echo ">>> ERROR [ledger] 登録名に使えない文字がある: ${file}" >&2; return 1; }
  cur="$(ledger_sha256 "${REPO_DIR}/${file}")" || return 1
  if [ "${MIGRATION_FULL_RERUN:-0}" != "1" ] && ! ledger_is_every_run "${file}"; then
    cached="$(ledger_cached_sum "${file}")"
    if [ -n "${cached}" ]; then
      if [ "${cached}" = "${cur}" ]; then
        echo ">>> [${STEP}/${TOTAL:-?}] skip (recorded) ${file}"
        return 0
      fi
      echo ">>> ERROR [ledger] チェックサム不一致: ${file}" >&2
      return 1
    fi
  fi
  t0="$(date +%s)"
  "$@" || return 1
  t1="$(date +%s)"
  ledger_record "${kind}" "${file}" "${cur}" "$(( (t1 - t0) * 1000 ))"
}

# 試験用の差し替え（本番では指定しない）
if [ -n "${LEDGER_HOOKS_FILE:-}" ] && [ -f "${LEDGER_HOOKS_FILE}" ]; then
  # shellcheck disable=SC1090
  . "${LEDGER_HOOKS_FILE}"
fi
