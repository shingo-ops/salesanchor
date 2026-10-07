#!/bin/bash
# 実行済み記録（ledger）付きランナーの論理を、DB なし・docker なしで検証する（ADR-1005 段階2）。
# 本物の psql の代わりに「偽の psql」（砂場の hooks.sh が ledger_psql を差し替える）を使い、
# 記録を一時ファイルに持つ。検証するのは scripts/lib/migration_ledger.sh の関数
# （本番の run_sql／run_py と同じもの）、scripts/migration-ledger/record-baseline.sh、
# scripts/check-migration-immutability.sh。
#
# 実行: bash scripts/tests/test-migration-ledger.sh

set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${HERE}/../.." && pwd)"
LIB="${REPO_ROOT}/scripts/lib/migration_ledger.sh"
BASELINE="${REPO_ROOT}/scripts/migration-ledger/record-baseline.sh"
IMMUTABLE="${REPO_ROOT}/scripts/check-migration-immutability.sh"

FAIL=0
PASS=0
pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }
assert_eq() { if [ "$1" = "$2" ]; then pass "$3"; else fail "$3 (期待: '$2' / 実際: '$1')"; fi; }
assert_contains() { case "$1" in *"$2"*) pass "$3";; *) fail "$3 ('$2' が出力に無い)";; esac; }
assert_not_contains() { case "$1" in *"$2"*) fail "$3 ('$2' が出力にある)";; *) pass "$3";; esac; }
nonzero() { if [ "$1" -ne 0 ]; then echo nonzero; else echo zero; fi; }

SANDBOXES=""
cleanup() { for d in ${SANDBOXES}; do rm -r "${d}" 2>/dev/null || true; done; }
trap cleanup EXIT

# --- 砂場: repo（migrations と scripts）、偽の ledger、実行ログ、差し替え用の hooks.sh --------------
new_sandbox() {
  SB="$(mktemp -d)"
  SANDBOXES="${SANDBOXES} ${SB}"
  mkdir -p "${SB}/repo/migrations" "${SB}/repo/scripts"
  : > "${SB}/exec.log"
  : > "${SB}/every-run.list"
  printf 'SELECT 1;\n' > "${SB}/repo/migrations/001_a.sql"
  printf 'SELECT 2;\n' > "${SB}/repo/migrations/002_b.sql"
  printf 'print(3)\n'  > "${SB}/repo/scripts/p.py"
  printf 'CREATE SCHEMA IF NOT EXISTS ops;\n' > "${SB}/repo/migrations/20261007_100000_create_migration_ledger.sql"
  # 登録の見本（run_all_migrations.sh と同じ「run_sql <path>」「run_py <path>」の形）
  cat > "${SB}/repo/scripts/run_fixture.sh" <<'REG'
run_sql migrations/001_a.sql
run_sql migrations/002_b.sql
run_py  scripts/p.py
REG
  # 偽の psql と偽の実行（ライブラリを source した「後」に source して、関数を差し替える）
  cat > "${SB}/hooks.sh" <<'HOOKS'
ledger_psql() {
  local sql; sql="$(cat)"
  case "${sql}" in
    *to_regclass*)
      if [ -f "${LEDGER_TABLE_MARK}" ]; then echo "ops.migration_ledger"; fi ;;
    *"INSERT INTO ops.migration_ledger"*)
      local row fn
      row="$(printf '%s' "${sql}" | sed -n "s/.*VALUES ('\([^']*\)','\([^']*\)','\([^']*\)','\([^']*\)','\([^']*\)'.*/\1	\3	\4	\5/p")"
      fn="$(printf '%s' "${row}" | cut -f2)"
      if [ -f "${LEDGER_DB}" ]; then grep -v "	${fn}	" "${LEDGER_DB}" > "${LEDGER_DB}.new" || true; mv "${LEDGER_DB}.new" "${LEDGER_DB}"; fi
      printf '%s\n' "${row}" >> "${LEDGER_DB}" ;;
    *"FROM ops.migration_ledger"*)
      if [ -f "${LEDGER_DB}" ]; then cat "${LEDGER_DB}"; fi ;;
  esac
}
ledger_exec_sql() {
  echo "RAN sql $1" >> "${LEDGER_EXEC_LOG}"
  case "$1" in *create_migration_ledger*) : > "${LEDGER_TABLE_MARK}";; esac
  if [ "$1" = "${FAIL_FILE:-}" ]; then return 1; fi
  return 0
}
ledger_exec_py() {
  echo "RAN py $1" >> "${LEDGER_EXEC_LOG}"
  if [ "$1" = "${FAIL_FILE:-}" ]; then return 1; fi
  return 0
}
HOOKS
}

sandbox_env() {
  export REPO_DIR="${SB}/repo"
  export LEDGER_DB="${SB}/ledger.tsv"
  export LEDGER_TABLE_MARK="${SB}/table.mark"
  export LEDGER_EXEC_LOG="${SB}/exec.log"
  export LEDGER_EVERY_RUN_LIST="${SB}/every-run.list"
  export LEDGER_DDL_FILE="migrations/20261007_100000_create_migration_ledger.sql"
  export LEDGER_GIT_SHA="testsha"
  export LEDGER_HOOKS_FILE="${SB}/hooks.sh"
}

# 砂場の repo を git リポジトリにして、HEAD の SHA を SB_SHA に入れる
init_sandbox_git() {
  git -C "${SB}/repo" init -q . >/dev/null 2>&1
  git -C "${SB}/repo" add -A >/dev/null 2>&1
  git -C "${SB}/repo" -c user.email=t@t -c user.name=t commit -q -m base >/dev/null 2>&1
  SB_SHA="$(git -C "${SB}/repo" rev-parse HEAD)"
}

# ランナーを実行する。引数: normal | full
run_runner() {
  local mode="$1"
  (
    set -e
    sandbox_env
    BACKEND="backend"; POSTGRES="postgres"; PSQL="psql"; TOTAL=3; STEP=0
    if [ "${mode}" = "full" ]; then MIGRATION_FULL_RERUN=1; fi
    # shellcheck disable=SC1090
    . "${LIB}"
    ledger_init "${SB}/repo/scripts/run_fixture.sh"
    # shellcheck disable=SC1090
    . "${SB}/repo/scripts/run_fixture.sh"
  )
}

# ======================================================================================
echo "=== 前提: ライブラリ・スクリプト・リストと ledger の作成 migration が存在する ==="
for f in "${LIB}" "${BASELINE}" "${IMMUTABLE}" "${REPO_ROOT}/scripts/migration-ledger/every-run.list" \
         "${REPO_ROOT}/scripts/migration-ledger/step3-neutralized.list" \
         "${REPO_ROOT}/migrations/20261007_100000_create_migration_ledger.sql"; do
  if [ -f "${f}" ]; then pass "存在: ${f#"${REPO_ROOT}"/}"; else fail "存在しない: ${f#"${REPO_ROOT}"/}"; fi
done
if [ ! -f "${LIB}" ]; then echo "ライブラリが無いので、以降の試験は実行しない"; echo "結果: ${PASS} 件 PASS / ${FAIL} 件 FAIL"; exit 1; fi

echo "=== T1: 未記録の手順は実行され、成功したものだけ記録される ==="
new_sandbox
out="$(run_runner normal 2>&1)"; rc=$?
assert_eq "${rc}" "0" "T1 終了コード 0"
assert_eq "$(grep -c '^RAN ' "${SB}/exec.log")" "4" "T1 実行は 4 件（ledger 作成 1 ＋ 手順 3）"
assert_eq "$(wc -l < "${SB}/ledger.tsv" | tr -d ' ')" "3" "T1 記録は 3 件"
assert_contains "$(cat "${SB}/ledger.tsv")" "migrations/001_a.sql" "T1 001_a.sql が記録された"
assert_contains "$(cat "${SB}/ledger.tsv")" "applied" "T1 状態は applied"

echo "=== T2: 記録済み（チェックサム一致）は飛ばされる ==="
: > "${SB}/exec.log"
out="$(run_runner normal 2>&1)"; rc=$?
assert_eq "${rc}" "0" "T2 終了コード 0"
assert_eq "$(grep -c '^RAN ' "${SB}/exec.log")" "0" "T2 実行は 0 件"
assert_contains "${out}" "skip" "T2 skip と表示される"

echo "=== T3: 記録済みファイルのチェックサムが変わっていたら、何も実行せず失敗する ==="
printf 'SELECT 22;\n' > "${SB}/repo/migrations/002_b.sql"
: > "${SB}/exec.log"
out="$(run_runner normal 2>&1)"; rc=$?
assert_eq "$(nonzero "${rc}")" "nonzero" "T3 終了コードが 0 でない"
assert_eq "$(grep -c '^RAN ' "${SB}/exec.log")" "0" "T3 実行は 0 件（実行前に止まる）"
assert_contains "${out}" "migrations/002_b.sql" "T3 不一致のファイル名が表示される"

echo "=== T4: 全件やり直しモードは、記録と不一致でも全件を実行し、記録を更新する ==="
: > "${SB}/exec.log"
out="$(run_runner full 2>&1)"; rc=$?
assert_eq "${rc}" "0" "T4 終了コード 0"
assert_eq "$(grep -c '^RAN ' "${SB}/exec.log")" "3" "T4 実行は 3 件"
: > "${SB}/exec.log"
out="$(run_runner normal 2>&1)"; rc=$?
assert_eq "${rc}" "0" "T4 更新後の通常モードは成功（チェックサムが更新された）"
assert_eq "$(grep -c '^RAN ' "${SB}/exec.log")" "0" "T4 更新後の通常モードは実行 0 件"

echo "=== T5: 途中で失敗した手順は記録されず、以降は実行されない ==="
new_sandbox
FAIL_FILE="migrations/002_b.sql" run_runner normal > "${SB}/out.txt" 2>&1; rc=$?
assert_eq "$(nonzero "${rc}")" "nonzero" "T5 終了コードが 0 でない"
assert_contains "$(cat "${SB}/ledger.tsv")" "migrations/001_a.sql" "T5 成功した 001_a.sql は記録された"
assert_not_contains "$(cat "${SB}/ledger.tsv")" "migrations/002_b.sql" "T5 失敗した 002_b.sql は記録されない"
assert_not_contains "$(cat "${SB}/exec.log")" "RAN py scripts/p.py" "T5 失敗の後の p.py は実行されない"
: > "${SB}/exec.log"
run_runner normal > "${SB}/out.txt" 2>&1; rc=$?
assert_eq "${rc}" "0" "T5 直したあとの再実行は成功"
assert_eq "$(grep -c '^RAN ' "${SB}/exec.log")" "2" "T5 再実行は続きの 2 件だけ（002_b と p.py）"

echo "=== T6: 毎回実行リストのファイルは、記録済みでも毎回実行される ==="
new_sandbox
run_runner normal > "${SB}/out.txt" 2>&1
printf '# 見本\nmigrations/001_a.sql\n' > "${SB}/every-run.list"
printf 'SELECT 11;\n' > "${SB}/repo/migrations/001_a.sql"   # 内容を変えても、毎回実行のものは失敗しない
: > "${SB}/exec.log"
run_runner normal > "${SB}/out.txt" 2>&1; rc=$?
assert_eq "${rc}" "0" "T6 終了コード 0（毎回実行のものはチェックサム不一致でも止まらない）"
assert_eq "$(grep -c '^RAN sql migrations/001_a.sql' "${SB}/exec.log")" "1" "T6 001_a.sql が実行される"
assert_eq "$(grep -c '^RAN ' "${SB}/exec.log")" "1" "T6 実行は 1 件だけ"

echo "=== T7: ledger の表が無い場合は、作成の migration を先に実行してから進む ==="
new_sandbox
run_runner normal > "${SB}/out.txt" 2>&1
assert_eq "$(head -1 "${SB}/exec.log")" "RAN sql migrations/20261007_100000_create_migration_ledger.sql" "T7 最初の実行は ledger の作成"

echo "=== T8: baseline は dry-run が既定で、何も記録しない（実行もしない）==="
new_sandbox
printf -- '-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07)\nSELECT 1;\n' > "${SB}/repo/migrations/001_a.sql"
printf 'migrations/001_a.sql\n' > "${SB}/step3.list"
( sandbox_env; : > "${LEDGER_TABLE_MARK}"; bash "${BASELINE}" --registration "${SB}/repo/scripts/run_fixture.sh" --repo-dir "${SB}/repo" --step3-files "${SB}/step3.list" > "${SB}/out.txt" 2>&1 ); rc=$?
out="$(cat "${SB}/out.txt")"
assert_eq "${rc}" "0" "T8 dry-run は終了コード 0"
assert_contains "${out}" "DRY-RUN" "T8 DRY-RUN と表示される"
assert_contains "${out}" "3" "T8 記録する件数 3 を表示する"
assert_eq "$([ -f "${SB}/ledger.tsv" ] && echo exists || echo none)" "none" "T8 dry-run は何も記録しない"
assert_eq "$(grep -c '^RAN ' "${SB}/exec.log")" "0" "T8 手順は 1 件も実行しない"

echo "=== T9: baseline は、段3 の無効化の印が無いファイルがあると、記録を拒否する ==="
new_sandbox
printf 'migrations/001_a.sql\n' > "${SB}/step3.list"        # 001_a.sql に印が無い
init_sandbox_git
( sandbox_env; : > "${LEDGER_TABLE_MARK}"; bash "${BASELINE}" --commit --expect-sha "${SB_SHA}" --registration "${SB}/repo/scripts/run_fixture.sh" --repo-dir "${SB}/repo" --step3-files "${SB}/step3.list" > "${SB}/out.txt" 2>&1 ); rc=$?
out="$(cat "${SB}/out.txt")"
assert_eq "$(nonzero "${rc}")" "nonzero" "T9 終了コードが 0 でない"
assert_contains "${out}" "NEUTRALIZED" "T9 無効化の印が無いことを説明する"
assert_eq "$([ -f "${SB}/ledger.tsv" ] && echo exists || echo none)" "none" "T9 何も記録しない"

echo "=== T10: baseline --commit は、全登録ファイルを status=baseline で記録し、実行しない ==="
new_sandbox
printf -- '-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07)\nSELECT 1;\n' > "${SB}/repo/migrations/001_a.sql"
printf 'migrations/001_a.sql\n' > "${SB}/step3.list"
init_sandbox_git
( sandbox_env; : > "${LEDGER_TABLE_MARK}"; bash "${BASELINE}" --commit --expect-sha "${SB_SHA}" --registration "${SB}/repo/scripts/run_fixture.sh" --repo-dir "${SB}/repo" --step3-files "${SB}/step3.list" > "${SB}/out.txt" 2>&1 ); rc=$?
assert_eq "${rc}" "0" "T10 終了コード 0"
assert_eq "$(wc -l < "${SB}/ledger.tsv" | tr -d ' ')" "3" "T10 記録は 3 件"
assert_eq "$(grep -c 'baseline' "${SB}/ledger.tsv")" "3" "T10 すべて status=baseline"
assert_eq "$(grep -c '^RAN ' "${SB}/exec.log")" "0" "T10 手順は 1 件も実行しない"
: > "${SB}/exec.log"
run_runner normal > "${SB}/out.txt" 2>&1; rc=$?
assert_eq "${rc}" "0" "T10 baseline の後の通常実行は成功"
assert_eq "$(grep -c '^RAN ' "${SB}/exec.log")" "0" "T10 baseline の後の通常実行は 0 件（すべて飛ばす）"

echo "=== T11: 実行済みファイルの書き換えを CI で検出する ==="
new_sandbox
G="${SB}/repo"
git -C "${G}" init -q . >/dev/null 2>&1
git -C "${G}" add -A >/dev/null 2>&1
git -C "${G}" -c user.email=t@t -c user.name=t commit -q -m base >/dev/null 2>&1
BASE_SHA="$(git -C "${G}" rev-parse HEAD)"
printf 'SELECT 99;\n' > "${G}/migrations/001_a.sql"
git -C "${G}" -c user.email=t@t -c user.name=t commit -q -am edit >/dev/null 2>&1
HEAD_EDIT="$(git -C "${G}" rev-parse HEAD)"
out="$(bash "${IMMUTABLE}" --repo-dir "${G}" --registration "${G}/scripts/run_fixture.sh" --every-run-list "${SB}/every-run.list" --base "${BASE_SHA}" --head "${HEAD_EDIT}" 2>&1)"; rc=$?
assert_eq "$(nonzero "${rc}")" "nonzero" "T11 登録済みファイルの書き換えは失敗"
assert_contains "${out}" "migrations/001_a.sql" "T11 書き換えられたファイル名が表示される"
printf '# 見本\nmigrations/001_a.sql\n' > "${SB}/every-run.list"
out="$(bash "${IMMUTABLE}" --repo-dir "${G}" --registration "${G}/scripts/run_fixture.sh" --every-run-list "${SB}/every-run.list" --base "${BASE_SHA}" --head "${HEAD_EDIT}" 2>&1)"; rc=$?
assert_eq "${rc}" "0" "T11 毎回実行リストのファイルの書き換えは許可"
: > "${SB}/every-run.list"
git -C "${G}" -c user.email=t@t -c user.name=t checkout -q "${BASE_SHA}" -- migrations/001_a.sql >/dev/null 2>&1
printf 'SELECT 100;\n' > "${G}/migrations/003_new.sql"
printf 'run_sql migrations/003_new.sql\n' >> "${G}/scripts/run_fixture.sh"
git -C "${G}" add -A >/dev/null 2>&1
git -C "${G}" -c user.email=t@t -c user.name=t commit -q -m add-new >/dev/null 2>&1
HEAD_NEW="$(git -C "${G}" rev-parse HEAD)"
out="$(bash "${IMMUTABLE}" --repo-dir "${G}" --registration "${G}/scripts/run_fixture.sh" --every-run-list "${SB}/every-run.list" --base "${BASE_SHA}" --head "${HEAD_NEW}" 2>&1)"; rc=$?
assert_eq "${rc}" "0" "T11 新しいファイルの追加（既存は未変更）は成功"

echo "=== T12: 本物の scripts/run_all_migrations.sh を、偽の docker で通しで動かす（配線の確認）==="
SB="$(mktemp -d)"; SANDBOXES="${SANDBOXES} ${SB}"
mkdir -p "${SB}/bin"
cat > "${SB}/bin/docker" <<'FAKEDOCKER'
#!/bin/bash
# 偽の docker: cp は何もしない。exec の中身で、ledger への問い合わせ・手順の実行・存在確認を見分ける。
echo "$*" >> "${FAKE_DOCKER_LOG}"
[ "$1" = "cp" ] && exit 0
args="$*"
case "${args}" in
  *"test -f"*) exit 0 ;;
  *" python "*) echo "RAN py" >> "${FAKE_EXEC_LOG}"; exit 0 ;;
  *"-tA"*)
    sql="$(cat)"
    case "${sql}" in
      *to_regclass*) if [ -f "${FAKE_TABLE_MARK}" ]; then echo "ops.migration_ledger"; fi ;;
      *"INSERT INTO ops.migration_ledger"*)
        row="$(printf '%s' "${sql}" | sed -n "s/.*VALUES ('\([^']*\)','\([^']*\)','\([^']*\)','\([^']*\)','\([^']*\)'.*/\1	\3	\4	\5/p")"
        fn="$(printf '%s' "${row}" | cut -f2)"
        if [ -f "${FAKE_LEDGER}" ]; then grep -v "	${fn}	" "${FAKE_LEDGER}" > "${FAKE_LEDGER}.new" || true; mv "${FAKE_LEDGER}.new" "${FAKE_LEDGER}"; fi
        printf '%s\n' "${row}" >> "${FAKE_LEDGER}" ;;
      *"FROM ops.migration_ledger"*) if [ -f "${FAKE_LEDGER}" ]; then cat "${FAKE_LEDGER}"; fi ;;
    esac ;;
  *)
    sql="$(cat)"
    echo "RAN sql" >> "${FAKE_EXEC_LOG}"
    case "${sql}" in *"CREATE TABLE IF NOT EXISTS ops.migration_ledger"*) : > "${FAKE_TABLE_MARK}" ;; esac ;;
esac
exit 0
FAKEDOCKER
chmod +x "${SB}/bin/docker"
: > "${SB}/docker.log"; : > "${SB}/exec.log"
real_runner() {
  ( PATH="${SB}/bin:${PATH}" REPO_DIR="${REPO_ROOT}" FAKE_DOCKER_LOG="${SB}/docker.log" FAKE_EXEC_LOG="${SB}/exec.log" \
    FAKE_LEDGER="${SB}/ledger.tsv" FAKE_TABLE_MARK="${SB}/table.mark" LEDGER_GIT_SHA=testsha \
    bash "${REPO_ROOT}/scripts/run_all_migrations.sh" "$@" )
}
N_REG="$(grep -cE '^run_(sql|py)[[:space:]]' "${REPO_ROOT}/scripts/run_all_migrations.sh")"
UNIQ_REG="$(grep -E '^run_(sql|py)[[:space:]]' "${REPO_ROOT}/scripts/run_all_migrations.sh" | awk '{print $2}' | sort -u | wc -l | tr -d ' ')"
out="$(real_runner 2>&1)"; rc=$?
assert_eq "${rc}" "0" "T12 1 回目（ledger が空）は終了コード 0"
assert_eq "$(wc -l < "${SB}/ledger.tsv" | tr -d ' ')" "${UNIQ_REG}" "T12 1 回目の記録は、登録ファイル数（重複を除く）と同じ"
assert_eq "$(grep -c '^RAN ' "${SB}/exec.log")" "$((N_REG + 1))" "T12 1 回目の実行は、登録行数 + ledger 作成の 1 件"
: > "${SB}/exec.log"
out="$(real_runner 2>&1)"; rc=$?
assert_eq "${rc}" "0" "T12 2 回目は終了コード 0"
assert_eq "$(grep -c '^RAN ' "${SB}/exec.log")" "0" "T12 2 回目は手順を 1 件も実行しない（全件を記録から飛ばす）"
assert_contains "${out}" "skip (recorded)" "T12 2 回目は skip と表示される"
: > "${SB}/exec.log"
out="$(real_runner --full 2>&1)"; rc=$?
assert_eq "${rc}" "0" "T12 --full は終了コード 0"
assert_eq "$(grep -c '^RAN ' "${SB}/exec.log")" "${N_REG}" "T12 --full は登録行数の全件を実行する"
assert_contains "${out}" "全件やり直しモード" "T12 --full のモードが表示される"

echo ""
echo "結果: ${PASS} 件 PASS / ${FAIL} 件 FAIL"
[ "${FAIL}" -eq 0 ]
