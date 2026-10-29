#!/usr/bin/env bash
# 試験: scripts/run_all_migrations.sh の run_sql（ロック待ち1秒・流し直し）の挙動 T1〜T6（ADR-1037）。
# run_sql は本物を sed で抜き出して使う（写しは作らない）。使い捨て postgres:16 のみ。
# パスワードは試験専用の固定値（秘密ではない）。本番・secrets には触れない。リポジトリ直下で実行する。
set -uo pipefail

NAME=sb-retry-pg
SCRIPT=scripts/run_all_migrations.sh
DROP_SQL=migrations/20261002_170000_drop_discord_inventory_tables.sql
CREATE_SQL=migrations/20260604_120000_create_parse_logs.sql
VIEW_SQL=migrations/20260604_130000_create_supplier_parse_stats_view.sql
PSQL_ARR=(psql -U postgres -d postgres -v ON_ERROR_STOP=1)
OUT_DIR="$(mktemp -d)"
RESULT=0

dsql() { docker exec -i "$NAME" "${PSQL_ARR[@]}" -Atc "$1"; }

cleanup() {
  echo "--- docker logs (tail 40) ---"
  docker logs "$NAME" 2>&1 | tail -40 || true
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  rm -rf "$OUT_DIR"
}
trap cleanup EXIT

pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; RESULT=1; }

docker run -d --name "$NAME" -e POSTGRES_PASSWORD=sandbox postgres:16 >/dev/null
ready=0
for _ in $(seq 1 60); do
  if docker exec "$NAME" pg_isready -U postgres >/dev/null 2>&1; then ready=1; break; fi
  sleep 1
done
[ "$ready" = 1 ] || { echo "postgres did not become ready within 60s"; exit 1; }
sleep 3
for _ in $(seq 1 30); do dsql 'select 1' >/dev/null 2>&1 && break; sleep 1; done

# --- 本物の run_sql を抜き出して読み込む ---
EXTRACT="$(awk '/^SQL_LOCK_TIMEOUT=/{p=1} p{print} p&&/^run_sql\(\) \{/{r=1} r&&/^}/{exit}' "$SCRIPT")"
echo "extracted lines from ${SCRIPT}: $(printf '%s\n' "$EXTRACT" | wc -l | tr -d ' ')"
[ -n "$EXTRACT" ] || { echo "extract failed"; exit 1; }

POSTGRES="$NAME"
PSQL="psql -U postgres -d postgres -v ON_ERROR_STOP=1"
REPO_DIR="$(pwd)"
STEP=0
TOTAL=1

reset_defaults() {
  unset SQL_LOCK_TIMEOUT SQL_RETRY_MAX_ATTEMPTS SQL_RETRY_SLEEP_SEC SQL_RETRY_BUDGET
  eval "$EXTRACT"
  SQL_RETRY_USED=0
}
reset_defaults
echo "defaults: lock_timeout=${SQL_LOCK_TIMEOUT} max_attempts=${SQL_RETRY_MAX_ATTEMPTS} sleep=${SQL_RETRY_SLEEP_SEC} budget=${SQL_RETRY_BUDGET}"
# T7: 既定値の確認（ADR-1037 便1.1）
if [ "$SQL_RETRY_MAX_ATTEMPTS" = "40" ] && [ "$SQL_RETRY_BUDGET" = "40" ]; then
  pass "T7 defaults max_attempts=${SQL_RETRY_MAX_ATTEMPTS} budget=${SQL_RETRY_BUDGET}"
else
  fail "T7 defaults max_attempts=${SQL_RETRY_MAX_ATTEMPTS} budget=${SQL_RETRY_BUDGET}"
fi

setup_base() {
  dsql "CREATE TABLE IF NOT EXISTS public.products (id serial PRIMARY KEY, is_active bool);
        CREATE TABLE IF NOT EXISTS public.suppliers (id serial PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS public.ingestion_jobs (id serial PRIMARY KEY);" >/dev/null
  dsql "INSERT INTO public.products (is_active) SELECT true FROM generate_series(1,5);
        INSERT INTO public.suppliers DEFAULT VALUES; INSERT INTO public.suppliers DEFAULT VALUES;
        INSERT INTO public.ingestion_jobs DEFAULT VALUES;" >/dev/null
}

recreate_parse_logs() {
  docker exec -i "$NAME" "${PSQL_ARR[@]}" < "$CREATE_SQL" >/dev/null
  docker exec -i "$NAME" "${PSQL_ARR[@]}" < "$VIEW_SQL" >/dev/null
}

count_retry() { grep -c "lock conflict; retry [0-9]" "$1" || true; }

# 指定回数まで失敗する SQL を作る。$1=ファイル $2=sequence 名 $3=n
make_fail_sql() {
  cat > "$1" <<EOF
CREATE SEQUENCE IF NOT EXISTS $2;
DO \$\$
BEGIN
  IF nextval('$2') <= $3 THEN
    RAISE EXCEPTION USING ERRCODE = '40P01', MESSAGE = 'deadlock detected';
  END IF;
END
\$\$;
EOF
}

setup_base
recreate_parse_logs

# ===== T1/T2 =====
echo "=== T1/T2: A が products を6秒読み続ける間に本物の DROP migration を流す ==="
reset_defaults
docker exec -i "$NAME" "${PSQL_ARR[@]}" -c "BEGIN; SELECT count(*) FROM products; SELECT pg_sleep(6); COMMIT;" >"$OUT_DIR/A1.out" 2>&1 &
A_PID=$!
sleep 1
rm -f "$OUT_DIR/stop" "$OUT_DIR/c.txt"
(
  start=$(date +%s%N)
  while [ ! -f "$OUT_DIR/stop" ] && [ $(( ( $(date +%s%N) - start ) / 1000000 )) -lt 10000 ]; do
    s=$(date +%s%N)
    docker exec -i "$NAME" "${PSQL_ARR[@]}" -Atc 'SELECT count(*) FROM products' >/dev/null 2>&1
    e=$(date +%s%N)
    echo $(( (e - s) / 1000000 )) >> "$OUT_DIR/c.txt"
    sleep 0.5
  done
) &
C_PID=$!
run_sql "$DROP_SQL" >"$OUT_DIR/t1.log" 2>&1
T1_RC=$?
touch "$OUT_DIR/stop"
wait "$C_PID"
wait "$A_PID"
echo "--- run_sql log (T1) ---"; cat "$OUT_DIR/t1.log"
C_ALL="$(tr '\n' ' ' < "$OUT_DIR/c.txt")"
C_MAX="$(sort -n "$OUT_DIR/c.txt" | tail -1)"
echo "C measurements (ms): ${C_ALL}"
echo "C max (ms): ${C_MAX}"
if [ -n "$C_MAX" ] && [ "$C_MAX" -le 1500 ]; then pass "T1 C max ${C_MAX}ms <= 1500ms"; else fail "T1 C max '${C_MAX}'ms > 1500ms (all: ${C_ALL})"; fi
T1_RETRY="$(count_retry "$OUT_DIR/t1.log")"
GONE="$(dsql "SELECT coalesce(to_regclass('public.parse_logs')::text, 'gone')")"
if [ "$T1_RC" -eq 0 ] && [ "$T1_RETRY" -ge 1 ] && [ "$GONE" = "gone" ]; then
  pass "T2 rc=0 retry=${T1_RETRY} parse_logs=${GONE}"
else
  fail "T2 rc=${T1_RC} retry=${T1_RETRY} parse_logs=${GONE}"
fi

# ===== T3 =====
echo "=== T3: A が30秒読み続ける間、上限3回・間隔1秒で流す ==="
recreate_parse_logs
reset_defaults
docker exec -i "$NAME" "${PSQL_ARR[@]}" -c "BEGIN; SELECT count(*) FROM products; SELECT pg_sleep(30); COMMIT;" >"$OUT_DIR/A3.out" 2>&1 &
A_PID=$!
sleep 1
SQL_RETRY_MAX_ATTEMPTS=3
SQL_RETRY_SLEEP_SEC=1
s=$(date +%s%N)
run_sql "$DROP_SQL" >"$OUT_DIR/t3.log" 2>&1
T3_RC=$?
e=$(date +%s%N)
T3_MS=$(( (e - s) / 1000000 ))
dsql "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE query LIKE '%pg_sleep(30)%' AND pid <> pg_backend_pid()" >/dev/null
wait "$A_PID" 2>/dev/null
echo "--- run_sql log (T3) ---"; cat "$OUT_DIR/t3.log"
if [ "$T3_RC" -ne 0 ] && grep -q "retry limit reached" "$OUT_DIR/t3.log" && [ "$T3_MS" -lt 10000 ]; then
  pass "T3 rc=${T3_RC} limit reached elapsed=${T3_MS}ms"
else
  fail "T3 rc=${T3_RC} elapsed=${T3_MS}ms limit_line=$(grep -c 'retry limit reached' "$OUT_DIR/t3.log" || true)"
fi
# T3 追加判定: 持ち主の一覧が出て products の AccessShareLock があり、SQL の文面（pg_sleep）は出ていない
if grep -q 'lock holders (xact > 1s):' "$OUT_DIR/t3.log" && grep -q 'products:AccessShareLock' "$OUT_DIR/t3.log"; then
  pass "T3b lock holders listed with products:AccessShareLock"
else
  fail "T3b lock holders missing (header=$(grep -c 'lock holders (xact > 1s):' "$OUT_DIR/t3.log" || true) products_lock=$(grep -c 'products:AccessShareLock' "$OUT_DIR/t3.log" || true))"
fi
# T3d: 持ち主の行の7列目（cmd）が英大文字か - だけで、T3 の持ち主は BEGIN
T3_CMDS="$(grep 'products:AccessShareLock' "$OUT_DIR/t3.log" | sed -E 's/^>>> \[[0-9]+\/[0-9]+\] +//' | awk -F' [|] ' '{print $7}')"
T3_BAD="$(printf '%s\n' "$T3_CMDS" | grep -vE '^[A-Z]+$|^-$' || true)"
T3_NOTBEGIN="$(printf '%s\n' "$T3_CMDS" | grep -vx 'BEGIN' || true)"
if [ -n "$T3_CMDS" ] && [ -z "$T3_BAD" ] && [ -z "$T3_NOTBEGIN" ]; then
  pass "T3d cmd column is BEGIN (letters only)"
else
  fail "T3d cmd column cmds='$(printf '%s' "$T3_CMDS" | tr '\n' ',')'"
fi
if ! grep -q 'pg_sleep' "$OUT_DIR/t3.log"; then
  pass "T3c no SQL text (pg_sleep) in log"
else
  fail "T3c pg_sleep found in log"
fi

# ===== T4 =====
echo "=== T4: deadlock は1回目だけ出て2回目は成功する ==="
reset_defaults
SQL_RETRY_SLEEP_SEC=1
REPO_DIR="$OUT_DIR"
make_fail_sql "$OUT_DIR/t4.sql" seq_t4 1
run_sql "t4.sql" >"$OUT_DIR/t4.log" 2>&1
T4_RC=$?
REPO_DIR="$(pwd)"
echo "--- run_sql log (T4) ---"; cat "$OUT_DIR/t4.log"
T4_RETRY="$(count_retry "$OUT_DIR/t4.log")"
if [ "$T4_RC" -eq 0 ] && [ "$T4_RETRY" -eq 1 ]; then pass "T4 rc=0 retry=1"; else fail "T4 rc=${T4_RC} retry=${T4_RETRY}"; fi

# ===== T5 =====
echo "=== T5: ほかのエラーは即停止 ==="
reset_defaults
SQL_RETRY_SLEEP_SEC=1
REPO_DIR="$OUT_DIR"
printf 'SELECT 1/0;\n' > "$OUT_DIR/t5.sql"
run_sql "t5.sql" >"$OUT_DIR/t5.log" 2>&1
T5_RC=$?
REPO_DIR="$(pwd)"
echo "--- run_sql log (T5) ---"; cat "$OUT_DIR/t5.log"
T5_RETRY="$(count_retry "$OUT_DIR/t5.log")"
if [ "$T5_RC" -ne 0 ] && [ "$T5_RETRY" -eq 0 ]; then pass "T5 rc=${T5_RC} retry=0"; else fail "T5 rc=${T5_RC} retry=${T5_RETRY}"; fi

# ===== T6 =====
echo "=== T6: 全体の上限 SQL_RETRY_BUDGET=2 ==="
reset_defaults
SQL_RETRY_SLEEP_SEC=1
SQL_RETRY_BUDGET=2
REPO_DIR="$OUT_DIR"
make_fail_sql "$OUT_DIR/t6.sql" seq_t6 3
run_sql "t6.sql" >"$OUT_DIR/t6.log" 2>&1
T6_RC=$?
REPO_DIR="$(pwd)"
echo "--- run_sql log (T6) ---"; cat "$OUT_DIR/t6.log"
T6_RETRY="$(count_retry "$OUT_DIR/t6.log")"
if [ "$T6_RC" -ne 0 ] && [ "$T6_RETRY" -eq 2 ]; then pass "T6 rc=${T6_RC} retry=2 (budget stop)"; else fail "T6 rc=${T6_RC} retry=${T6_RETRY}"; fi

# ===== T8 =====
echo "=== T8: 1回目だけ deadlock のとき lock holders は1回だけ ==="
reset_defaults
SQL_RETRY_SLEEP_SEC=1
REPO_DIR="$OUT_DIR"
make_fail_sql "$OUT_DIR/t8.sql" seq_t8 1
run_sql "t8.sql" >"$OUT_DIR/t8.log" 2>&1
T8_RC=$?
REPO_DIR="$(pwd)"
echo "--- run_sql log (T8) ---"; cat "$OUT_DIR/t8.log"
T8_HOLDERS="$(grep -c 'lock holders (xact > 1s):' "$OUT_DIR/t8.log" || true)"
if [ "$T8_RC" -eq 0 ] && [ "$T8_HOLDERS" -eq 1 ]; then pass "T8 rc=0 lock_holders=1"; else fail "T8 rc=${T8_RC} lock_holders=${T8_HOLDERS}"; fi
reset_defaults

# ===== R1〜R4: 本物の run_py（入口経由・流し直し）。ADR-1037 の拡張 =====
# run_py は本物を上の EXTRACT から読み込む（写しは作らない）。docker は python を含む呼び出しだけ偽物にし、
# ほか（dsql・log_lock_holders）は本物へ渡す。R1〜R4 が終わったら関数を消し、T1〜T8 に影響させない。
echo "=== R: run_py（偽の python 呼び出し）==="
if printf '%s\n' "$EXTRACT" | grep -q '^run_py() {'; then pass "R0 run_py is inside the extracted range"; else fail "R0 run_py not in extracted range"; fi
BACKEND="sb-fake-backend"
DATABASE_URL="postgresql://fake/fake"
ADMIN_DATABASE_URL="postgresql://fake/fake"
FAKE_COUNT_FILE="$OUT_DIR/fake_count"
FAKE_MODE=""
docker() {
  case " $* " in
    *" python "*)
      local n
      n=$(( $(cat "$FAKE_COUNT_FILE" 2>/dev/null || echo 0) + 1 ))
      echo "$n" > "$FAKE_COUNT_FILE"
      case "$FAKE_MODE" in
        once_then_ok)
          if [ "$n" -eq 1 ]; then
            echo "fake-python: sqlalchemy.exc.DBAPIError: canceling statement due to lock timeout" >&2
            return 1
          fi
          echo "fake-python: running attempt $n" >&2
          return 0 ;;
        always_lock)
          echo "fake-python: canceling statement due to lock timeout" >&2
          return 1 ;;
        other_error)
          echo "fake-python: ZeroDivisionError: division by zero" >&2
          return 1 ;;
      esac
      return 99 ;;
    *) command docker "$@" ;;
  esac
}
count_calls() { cat "$FAKE_COUNT_FILE" 2>/dev/null || echo 0; }

# R1: 1回目だけロック待ちで失敗 → 流し直して成功。実行中の行が標準エラーに出ている
echo "=== R1: run_py の流し直し ==="
reset_defaults
SQL_RETRY_SLEEP_SEC=1
rm -f "$FAKE_COUNT_FILE"; FAKE_MODE=once_then_ok
run_py "scripts/migrate_fake.py" >"$OUT_DIR/r1.out" 2>"$OUT_DIR/r1.err"
R1_RC=$?
echo "--- run_py stdout (R1) ---"; cat "$OUT_DIR/r1.out"; echo "--- run_py stderr (R1) ---"; cat "$OUT_DIR/r1.err"
R1_RETRY="$(count_retry "$OUT_DIR/r1.err")"; R1_RETRY_OUT="$(count_retry "$OUT_DIR/r1.out")"
R1_LIVE="$(grep -c 'fake-python: running attempt 2' "$OUT_DIR/r1.err" || true)"
if [ "$R1_RC" -eq 0 ] && [ "$((R1_RETRY + R1_RETRY_OUT))" -eq 1 ] && [ "$R1_LIVE" -ge 1 ] && [ "$(count_calls)" -eq 2 ]; then
  pass "R1 rc=0 retry=1 live_line=${R1_LIVE} calls=2"
else
  fail "R1 rc=${R1_RC} retry=$((R1_RETRY + R1_RETRY_OUT)) live_line=${R1_LIVE} calls=$(count_calls)"
fi

# R2: 毎回ロック待ちで失敗 → 上限3回で止まる
echo "=== R2: run_py の上限 ==="
reset_defaults
SQL_RETRY_MAX_ATTEMPTS=3
SQL_RETRY_SLEEP_SEC=1
rm -f "$FAKE_COUNT_FILE"; FAKE_MODE=always_lock
s=$(date +%s%N)
run_py "scripts/migrate_fake.py" >"$OUT_DIR/r2.out" 2>"$OUT_DIR/r2.err"
R2_RC=$?
e=$(date +%s%N)
R2_MS=$(( (e - s) / 1000000 ))
echo "--- run_py stdout (R2) ---"; cat "$OUT_DIR/r2.out"
if [ "$R2_RC" -ne 0 ] && grep -q 'retry limit reached' "$OUT_DIR/r2.out" && [ "$R2_MS" -lt 10000 ] && [ "$(count_calls)" -eq 3 ]; then
  pass "R2 rc=${R2_RC} limit reached elapsed=${R2_MS}ms calls=3"
else
  fail "R2 rc=${R2_RC} elapsed=${R2_MS}ms calls=$(count_calls) limit_line=$(grep -c 'retry limit reached' "$OUT_DIR/r2.out" || true)"
fi

# R3: ほかのエラーは流し直さず即停止
echo "=== R3: ほかのエラーは即停止 ==="
reset_defaults
SQL_RETRY_SLEEP_SEC=1
rm -f "$FAKE_COUNT_FILE"; FAKE_MODE=other_error
run_py "scripts/migrate_fake.py" >"$OUT_DIR/r3.out" 2>"$OUT_DIR/r3.err"
R3_RC=$?
echo "--- run_py stdout (R3) ---"; cat "$OUT_DIR/r3.out"
R3_RETRY=$(( $(count_retry "$OUT_DIR/r3.out") + $(count_retry "$OUT_DIR/r3.err") ))
if [ "$R3_RC" -ne 0 ] && [ "$R3_RETRY" -eq 0 ] && [ "$(count_calls)" -eq 1 ]; then
  pass "R3 rc=${R3_RC} retry=0 calls=1"
else
  fail "R3 rc=${R3_RC} retry=${R3_RETRY} calls=$(count_calls)"
fi

# R4: 全体の上限を run_sql と共有する（run_sql で1回使った後、SQL_RETRY_BUDGET=2 だと run_py は1回しか流し直さない）
echo "=== R4: run_sql と run_py で全体の上限を共有 ==="
reset_defaults
SQL_RETRY_SLEEP_SEC=1
SQL_RETRY_BUDGET=2
REPO_DIR="$OUT_DIR"
make_fail_sql "$OUT_DIR/r4.sql" seq_r4 1
run_sql "r4.sql" >"$OUT_DIR/r4_sql.log" 2>&1
R4_SQL_RC=$?
REPO_DIR="$(pwd)"
rm -f "$FAKE_COUNT_FILE"; FAKE_MODE=always_lock
run_py "scripts/migrate_fake.py" >"$OUT_DIR/r4.out" 2>"$OUT_DIR/r4.err"
R4_RC=$?
echo "--- run_py stdout (R4) ---"; cat "$OUT_DIR/r4.out"
R4_RETRY="$(count_retry "$OUT_DIR/r4.out")"
if [ "$R4_SQL_RC" -eq 0 ] && [ "$R4_RC" -ne 0 ] && [ "$R4_RETRY" -eq 1 ] && grep -q 'retry limit reached' "$OUT_DIR/r4.out" && [ "$(count_calls)" -eq 2 ]; then
  pass "R4 sql_rc=0 py_rc=${R4_RC} py_retry=1 (shared budget stop) calls=2"
else
  fail "R4 sql_rc=${R4_SQL_RC} py_rc=${R4_RC} py_retry=${R4_RETRY} calls=$(count_calls)"
fi

# 偽の docker を消して T1〜T8 に影響させない
unset -f docker count_calls
reset_defaults

if [ "$RESULT" -eq 0 ]; then echo "RESULT: PASS"; else echo "RESULT: FAIL"; exit 1; fi
