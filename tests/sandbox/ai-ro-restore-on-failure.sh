#!/usr/bin/env bash
# 試験: scripts/run_all_migrations.sh の _ai_ro_create_on_exit（失敗しても ai_ro を作り直す）T1〜T8（ADR-1024 改訂）。
# 関数は本物を awk で切り出して使う（写しは作らない）。使い捨て postgres:16 のみ。
# パスワードは試験専用の固定値（秘密ではない）。本番・secrets には触れない。リポジトリ直下で実行する。
set -uo pipefail

NAME=sb-airo-pg
SCRIPT=scripts/run_all_migrations.sh
DROP_SQL=migrations/20261017_125900_drop_ai_ro_views.sql
PSQL_ARR=(psql -U postgres -d postgres -v ON_ERROR_STOP=1)
OUT_DIR="$(mktemp -d)"
RESULT=0

dsql() { docker exec -i "$NAME" "${PSQL_ARR[@]}" -Atc "$1"; }
now_ms() { echo $(( $(date +%s%N) / 1000000 )); }

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

# --- T6: 本物の切り出し ---
EXTRACT="$(awk '/^AI_RO_CREATE_SQL=/{p=1} p{print} p&&/^trap _ai_ro_create_on_exit EXIT/{exit}' "$SCRIPT")"
EX_LINES="$(printf '%s\n' "$EXTRACT" | wc -l | tr -d ' ')"
EX_FIRST="$(printf '%s\n' "$EXTRACT" | head -n 1)"
EX_LAST="$(printf '%s\n' "$EXTRACT" | tail -n 1)"
echo "T6 extracted lines from ${SCRIPT}: ${EX_LINES}"
echo "T6 first: ${EX_FIRST}"
echo "T6 last:  ${EX_LAST}"
if [ "$EX_LAST" != "trap _ai_ro_create_on_exit EXIT" ]; then
  fail "T6 extract end is not the trap line"
  exit 1
fi
pass "T6 extracted ${EX_LINES} lines, ends with trap line"
printf '%s\n' "$EXTRACT" > "$OUT_DIR/extract.sh"

# --- 準備: 試験用の表。api_token は拒否リスト（_token）に当たる名前 ---
grep -n "deny constant" migrations/20261017_130100_create_ai_ro_views.sql
dsql "CREATE TABLE public.sb_items (id int, name text, api_token text);
      INSERT INTO public.sb_items VALUES (1,'a','secret-a'),(2,'b','secret-b');" >/dev/null

ensure_role() { dsql "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='ai_reader') THEN CREATE ROLE ai_reader NOLOGIN; END IF; END \$\$;" >/dev/null; }
drop_role() { dsql "DROP ROLE IF EXISTS ai_reader;" >/dev/null; }
# 本番で :119 がビューを外すのと同じ状態から始める
reset_state() {
  docker exec -i "$NAME" "${PSQL_ARR[@]}" < "$DROP_SQL" >/dev/null
}
count_views() { dsql "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='ai_ro' AND c.relkind='v';"; }

# 子の bash を作る。$1=ファイル名 $2=末尾（exit 3 / true）$3=POSTGRES 名
make_child() {
  cat > "$OUT_DIR/$1" <<EOF
set -e
POSTGRES="$3"
PSQL="psql -U postgres -d postgres -v ON_ERROR_STOP=1"
REPO_DIR="$(pwd)"
eval "\$(cat $OUT_DIR/extract.sh)"
$2
EOF
}

# --- T1 ---
echo "=== T1: ai_reader あり・失敗(exit 3) でも作り直す ==="
ensure_role; reset_state
make_child c1.sh "exit 3" "$NAME"
bash "$OUT_DIR/c1.sh" >"$OUT_DIR/t1.log" 2>&1; T1_RC=$?
cat "$OUT_DIR/t1.log"
T1_N="$(grep -ao 'ai_ro views created: [0-9]*' "$OUT_DIR/t1.log" | grep -o '[0-9]*$' | head -n 1)"
T1_CNT="$(count_views)"
T1_COLS="$(dsql "SELECT count(*) FROM information_schema.columns WHERE table_schema='ai_ro' AND table_name='public__sb_items' AND column_name='api_token';")"
T1_HAS="$(dsql "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='ai_ro' AND c.relname='public__sb_items';")"
echo "T1 rc=${T1_RC} created_N=${T1_N:-none} view_count=${T1_CNT} has_sb_items=${T1_HAS} api_token_cols=${T1_COLS}"
if [ "$T1_RC" = 3 ] && grep -aq 'recreating ai_ro views anyway' "$OUT_DIR/t1.log" \
   && [ -n "$T1_N" ] && [ "$T1_N" = "$T1_CNT" ] && [ "$T1_HAS" = 1 ] && [ "$T1_COLS" = 0 ]; then
  pass "T1 rc=3, recreated N=${T1_N}, api_token hidden"
else
  fail "T1 rc=${T1_RC} N=${T1_N:-none} count=${T1_CNT}"
fi

# --- T2 ---
echo "=== T2: ai_reader あり・成功(true) ==="
ensure_role; reset_state
make_child c2.sh "true" "$NAME"
bash "$OUT_DIR/c2.sh" >"$OUT_DIR/t2.log" 2>&1; T2_RC=$?
cat "$OUT_DIR/t2.log"
T2_HAS="$(dsql "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='ai_ro' AND c.relname='public__sb_items';")"
if [ "$T2_RC" = 0 ] && [ "$T2_HAS" = 1 ]; then pass "T2 rc=0 view exists"; else fail "T2 rc=${T2_RC} has=${T2_HAS}"; fi

# --- T3 ---
echo "=== T3: ai_reader 無し・失敗(exit 3) ==="
reset_state; drop_role
make_child c3.sh "exit 3" "$NAME"
bash "$OUT_DIR/c3.sh" >"$OUT_DIR/t3.log" 2>&1; T3_RC=$?
cat "$OUT_DIR/t3.log"
T3_CNT="$(count_views)"
if [ "$T3_RC" = 3 ] && grep -aq 'ai_ro views の作成に失敗' "$OUT_DIR/t3.log" && [ "$T3_CNT" = 0 ]; then
  pass "T3 rc=3 warning shown views=${T3_CNT}"
else
  fail "T3 rc=${T3_RC} views=${T3_CNT}"
fi

# --- T4 ---
echo "=== T4: 成功(true)・作成だけ失敗（存在しないコンテナ） ==="
ensure_role; reset_state
make_child c4.sh "true" "no-such-container-airo"
bash "$OUT_DIR/c4.sh" >"$OUT_DIR/t4.log" 2>&1; T4_RC=$?
cat "$OUT_DIR/t4.log"
if [ "$T4_RC" = 0 ] && grep -aq 'ai_ro views の作成に失敗' "$OUT_DIR/t4.log"; then
  pass "T4 rc=0 warning shown"
else
  fail "T4 rc=${T4_RC}"
fi

# --- T5 ---
echo "=== T5: ほかの接続が ACCESS SHARE を持っていても作成は待たない ==="
ensure_role; reset_state
docker exec -i "$NAME" "${PSQL_ARR[@]}" -c "BEGIN; SELECT count(*) FROM public.sb_items; SELECT pg_sleep(8);" >"$OUT_DIR/t5-holder.log" 2>&1 &
HOLD_PID=$!
sleep 2
make_child c5.sh "true" "$NAME"
T5_START="$(now_ms)"
bash "$OUT_DIR/c5.sh" >"$OUT_DIR/t5.log" 2>&1 &
CREATE_PID=$!
sleep 0.1
R_START="$(now_ms)"
dsql "SELECT count(*) FROM public.sb_items;" >/dev/null
R_END="$(now_ms)"
wait "$CREATE_PID"; T5_RC=$?
T5_END="$(now_ms)"
wait "$HOLD_PID" || true
cat "$OUT_DIR/t5.log"
T5_CREATE_MS=$(( T5_END - T5_START ))
T5_READ_MS=$(( R_END - R_START ))
echo "T5 create_ms=${T5_CREATE_MS} read_ms=${T5_READ_MS} rc=${T5_RC}"
if [ "$T5_RC" = 0 ] && [ "$T5_CREATE_MS" -lt 3000 ] && [ "$T5_READ_MS" -lt 1000 ]; then
  pass "T5 create_ms=${T5_CREATE_MS} read_ms=${T5_READ_MS}"
else
  fail "T5 create_ms=${T5_CREATE_MS} read_ms=${T5_READ_MS} rc=${T5_RC}"
fi

# --- T7 ---
echo "=== T7: ACCESS EXCLUSIVE を持たれても上限(3s)で打ち切る ==="
ensure_role; reset_state
docker exec -i "$NAME" "${PSQL_ARR[@]}" -c "BEGIN; LOCK TABLE public.sb_items IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(20);" >"$OUT_DIR/t7-holder.log" 2>&1 &
HOLD_PID=$!
sleep 2
make_child c7.sh "exit 3" "$NAME"
T7_START="$(date +%s)"
AI_RO_CREATE_TIMEOUT=3s bash "$OUT_DIR/c7.sh" >"$OUT_DIR/t7.log" 2>&1; T7_RC=$?
T7_END="$(date +%s)"
echo "--- pg_locks (T7, 作成の後) ---"
dsql "SELECT l.pid, l.mode, l.granted, c.relname FROM pg_locks l LEFT JOIN pg_class c ON c.oid=l.relation WHERE c.relname='sb_items';" || true
dsql "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE query LIKE '%pg_sleep(20)%' AND pid <> pg_backend_pid();" >/dev/null || true
wait "$HOLD_PID" || true
cat "$OUT_DIR/t7.log"
T7_SEC=$(( T7_END - T7_START ))
T7_CNT="$(count_views)"
echo "T7 elapsed_sec=${T7_SEC} rc=${T7_RC} views=${T7_CNT}"
if [ "$T7_SEC" -le 10 ] && [ "$T7_RC" = 3 ] && grep -aq 'ai_ro views の作成に失敗' "$OUT_DIR/t7.log" && [ "$T7_CNT" = 0 ]; then
  pass "T7 elapsed_sec=${T7_SEC} rc=3 views=0"
else
  fail "T7 elapsed_sec=${T7_SEC} rc=${T7_RC} views=${T7_CNT}"
fi

# --- T8（記録だけ。合否に入れない） ---
echo "=== T8: 移行の途中で SIGTERM（記録だけ） ==="
ensure_role; reset_state
make_child c8.sh "sleep 30" "$NAME"
bash "$OUT_DIR/c8.sh" >"$OUT_DIR/t8.log" 2>&1 &
C8_PID=$!
sleep 3
kill -TERM "$C8_PID" 2>/dev/null || true
wait "$C8_PID"; T8_RC=$?
sleep 2
cat "$OUT_DIR/t8.log"
T8_A="no"; T8_B="no"
grep -aq 'recreating ai_ro views anyway' "$OUT_DIR/t8.log" && T8_A="yes"
grep -aq 'ai_ro views created:' "$OUT_DIR/t8.log" && T8_B="yes"
echo "T8 (record only) child_rc=${T8_RC} recreating_line=${T8_A} created_line=${T8_B} bash=${BASH_VERSION}"

if [ "$RESULT" = 0 ]; then echo "ALL PASS (T1-T7)"; else echo "SOME FAILED (T1-T7)"; fi
exit "$RESULT"
