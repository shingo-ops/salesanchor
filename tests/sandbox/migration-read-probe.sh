#!/usr/bin/env bash
# 試験: scripts/run_all_migrations.sh の read_probe_start / read_probe_stop（移行中の読み取り計測）T1〜T9（ADR-1037 便1.2）。
# 計測の本体は「# >>> read-probe begin」〜「# <<< read-probe end」を本物から切り出して使う（写しは作らない）。
# 使い捨て postgres:16 のみ（jarvis / jarvis_db）。パスワードは試験専用の固定値（秘密ではない）。本番・secrets には触れない。
# リポジトリ直下で実行する。
set -uo pipefail

NAME=sb-probe-pg
SCRIPT=scripts/run_all_migrations.sh
PSQL_ARR=(psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1)
OUT_DIR="$(mktemp -d)"
ALL_LOG="$OUT_DIR/all.log"
: > "$ALL_LOG"
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

docker run -d --name "$NAME" -e POSTGRES_USER=jarvis -e POSTGRES_DB=jarvis_db -e POSTGRES_PASSWORD=sandbox postgres:16 >/dev/null
ready=0
for _ in $(seq 1 60); do
  if docker exec "$NAME" pg_isready -U jarvis -d jarvis_db >/dev/null 2>&1; then ready=1; break; fi
  sleep 1
done
[ "$ready" = 1 ] || { echo "postgres did not become ready within 60s"; exit 1; }
sleep 3
for _ in $(seq 1 30); do dsql 'select 1' >/dev/null 2>&1 && break; sleep 1; done
echo "bash=${BASH_VERSION} EPOCHREALTIME=${EPOCHREALTIME:-unset}"

# --- T6: 本物の切り出し ---
BEGIN_N="$(grep -c '^# >>> read-probe begin$' "$SCRIPT" || true)"
END_N="$(grep -c '^# <<< read-probe end$' "$SCRIPT" || true)"
awk '/^# >>> read-probe begin$/{p=1} p{print} /^# <<< read-probe end$/{exit}' "$SCRIPT" > "$OUT_DIR/probe.sh"
PROBE_LINES="$(wc -l < "$OUT_DIR/probe.sh" | tr -d ' ')"
echo "T6 extracted lines (read-probe block) from ${SCRIPT}: ${PROBE_LINES} begin_marks=${BEGIN_N} end_marks=${END_N}"
if [ "$PROBE_LINES" -gt 2 ] && [ "$BEGIN_N" = 1 ] && [ "$END_N" = 1 ]; then
  pass "T6 read-probe block ${PROBE_LINES} lines"
else
  fail "T6 read-probe block lines=${PROBE_LINES} begin=${BEGIN_N} end=${END_N}"
  exit 1
fi
# run_sql の切り出し（tests/sandbox/migration-run-sql-retry.sh と同じ目印）
awk '/^SQL_LOCK_TIMEOUT=/{p=1} p{print} p&&/^run_sql\(\) \{/{r=1} r&&/^}/{exit}' "$SCRIPT" > "$OUT_DIR/runsql.sh"
RUNSQL_LINES="$(wc -l < "$OUT_DIR/runsql.sh" | tr -d ' ')"
# ai_ro の trap 部分の切り出し（tests/sandbox/ai-ro-restore-on-failure.sh と同じ目印）
awk '/^AI_RO_CREATE_SQL=/{p=1} p{print} p&&/^trap _ai_ro_create_on_exit EXIT/{exit}' "$SCRIPT" > "$OUT_DIR/airo.sh"
AIRO_LINES="$(wc -l < "$OUT_DIR/airo.sh" | tr -d ' ')"
echo "T6 extracted lines: run_sql=${RUNSQL_LINES} ai_ro=${AIRO_LINES}"
if [ "$RUNSQL_LINES" -le 2 ] || [ "$AIRO_LINES" -le 2 ]; then fail "T6 run_sql/ai_ro extract is empty"; exit 1; fi

# --- 準備 ---
dsql "CREATE TABLE public.sb_a (id int); CREATE TABLE public.sb_b (id int); CREATE TABLE public.sb_prod (id int);
      INSERT INTO public.sb_a VALUES (1); INSERT INTO public.sb_b VALUES (1); INSERT INTO public.sb_prod VALUES (1);
      DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='ai_reader') THEN CREATE ROLE ai_reader NOLOGIN; END IF; END \$\$;" >/dev/null
printf 'BEGIN;\nLOCK TABLE public.sb_prod IN ACCESS EXCLUSIVE MODE;\nCOMMIT;\n' > "$OUT_DIR/t7.sql"

# 親の bash を作る。$1=ファイル名 $2=POSTGRES 名 $3=読み込む追加の切り出し（空可） $4=計測の後の本文
make_parent() {
  cat > "$OUT_DIR/$1" <<EOF
set -e
POSTGRES="$2"
PSQL="psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1"
REPO_DIR="$(pwd)"
STEP=0
TOTAL=1
eval "\$(cat $OUT_DIR/probe.sh)"
$3
read_probe_start
echo "\$READ_PROBE_PID" > "$OUT_DIR/$1.pid"
$4
EOF
}

# まとめの行から項目の値を取る。$1=ログ $2=項目名
field() { grep -ao "read probe: n=[0-9]* slow=[0-9]* error=[0-9]* invalid=[0-9]* max=[0-9]*ms" "$1" | tail -n 1 | grep -o "$2=[0-9]*" | head -n 1 | cut -d= -f2; }
final_line_count() { grep -ac '^>>> \[final\] read probe: n=[0-9]* slow=[0-9]* error=[0-9]* invalid=[0-9]* max=[0-9]*ms$' "$1" || true; }

# --- T1: 普段 ---
echo "=== T1: 鍵の取り合いが無いまま6秒回す ==="
make_parent p1.sh "$NAME" "" "sleep 6; read_probe_stop"
env READ_PROBE_TABLES="sb_a sb_b" READ_PROBE_INTERVAL_SEC=1 bash "$OUT_DIR/p1.sh" >"$OUT_DIR/t1.log" 2>&1; T1_RC=$?
cat "$OUT_DIR/t1.log"; cat "$OUT_DIR/t1.log" >> "$ALL_LOG"
T1_N="$(field "$OUT_DIR/t1.log" n)"; T1_SLOW="$(field "$OUT_DIR/t1.log" slow)"; T1_ERR="$(field "$OUT_DIR/t1.log" error)"
T1_INV="$(field "$OUT_DIR/t1.log" invalid)"; T1_MAX="$(field "$OUT_DIR/t1.log" max)"
echo "T1 (record) rc=${T1_RC} n=${T1_N:-none} slow=${T1_SLOW:-none} error=${T1_ERR:-none} invalid=${T1_INV:-none} normal_max_ms=${T1_MAX:-none}"
if [ "$T1_RC" = 0 ] && [ "${T1_N:-0}" -ge 2 ] && [ "${T1_SLOW:-1}" = 0 ] && [ "${T1_ERR:-1}" = 0 ] && [ "${T1_INV:-1}" = 0 ]; then
  pass "T1 n=${T1_N} slow=0 error=0 invalid=0 max=${T1_MAX}ms"
else
  fail "T1 rc=${T1_RC} n=${T1_N:-none} slow=${T1_SLOW:-none} error=${T1_ERR:-none} invalid=${T1_INV:-none}"
fi

# --- T2: 既に取られた鍵 ---
echo "=== T2: 別の接続が sb_a の ACCESS EXCLUSIVE を6秒持つ ==="
docker exec -i "$NAME" "${PSQL_ARR[@]}" -c "BEGIN; LOCK TABLE public.sb_a IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(6); COMMIT;" >"$OUT_DIR/t2-holder.log" 2>&1 &
H2_PID=$!
sleep 1
make_parent p2.sh "$NAME" "" "sleep 7; read_probe_stop"
env READ_PROBE_TABLES="sb_a sb_b" READ_PROBE_INTERVAL_SEC=1 READ_PROBE_STMT_TIMEOUT=3s bash "$OUT_DIR/p2.sh" >"$OUT_DIR/t2.log" 2>&1; T2_RC=$?
wait "$H2_PID" || true
cat "$OUT_DIR/t2.log"; cat "$OUT_DIR/t2.log" >> "$ALL_LOG"
T2_SLOW="$(field "$OUT_DIR/t2.log" slow)"; T2_ERR="$(field "$OUT_DIR/t2.log" error)"; T2_MAX="$(field "$OUT_DIR/t2.log" max)"
T2_SLOWLINES="$(grep -ac 'read probe slow:' "$OUT_DIR/t2.log" || true)"
T2_BADFMT="$(grep -a 'read probe slow:' "$OUT_DIR/t2.log" | grep -avcE '^>>> \[final\] read probe slow: [0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z [0-9]+ms$' || true)"
echo "T2 rc=${T2_RC} slow=${T2_SLOW:-none} error=${T2_ERR:-none} max=${T2_MAX:-none} slow_lines=${T2_SLOWLINES} bad_format_lines=${T2_BADFMT}"
if [ "$T2_RC" = 0 ] && [ "${T2_SLOW:-0}" -ge 1 ] && [ "${T2_ERR:-0}" -ge 1 ] && [ "$(final_line_count "$OUT_DIR/t2.log")" = 1 ] && [ "$T2_SLOWLINES" -ge 1 ]; then
  pass "T2 slow=${T2_SLOW} error=${T2_ERR} max=${T2_MAX}ms"
else
  fail "T2 rc=${T2_RC} slow=${T2_SLOW:-none} error=${T2_ERR:-none} slow_lines=${T2_SLOWLINES}"
fi
# slow 行の書式
if [ "$T2_SLOWLINES" -ge 1 ] && [ "$T2_BADFMT" = 0 ]; then pass "slow line format (${T2_SLOWLINES} lines)"; else fail "slow line format lines=${T2_SLOWLINES} bad=${T2_BADFMT}"; fi

# --- T7: 本番で起きる形（読み取りの長い持ち主 → 移行の ACCESS EXCLUSIVE 待ち → 計測） ---
echo "=== T7: sb_prod を読むトランザクション6秒 + 本物の run_sql(1s, 間隔0) が後ろで待つ ==="
docker exec -i "$NAME" "${PSQL_ARR[@]}" -c "BEGIN; SELECT count(*) FROM public.sb_prod; SELECT pg_sleep(6); COMMIT;" >"$OUT_DIR/t7-holder.log" 2>&1 &
H7_PID=$!
sleep 1
rm -f "$OUT_DIR/t7.stop" "$OUT_DIR/t7.seen"
(
  seen=0
  while [ ! -f "$OUT_DIR/t7.stop" ]; do
    c="$(dsql "SELECT count(*) FROM pg_stat_activity WHERE application_name='sa_read_probe' AND wait_event_type='Lock'" 2>/dev/null)"
    [[ "$c" =~ ^[0-9]+$ ]] && [ "$c" -gt "$seen" ] && seen="$c"
    echo "$seen" > "$OUT_DIR/t7.seen"
    sleep 0.2
  done
) &
S7_PID=$!
make_parent p7.sh "$NAME" "REPO_DIR=\"$OUT_DIR\"
eval \"\$(cat $OUT_DIR/runsql.sh)\"" 'if run_sql t7.sql; then echo "RUN_SQL_RESULT=ok"; else echo "RUN_SQL_RESULT=fail"; fi; read_probe_stop'
env READ_PROBE_TABLES="sb_prod" READ_PROBE_INTERVAL_SEC=1 SQL_LOCK_TIMEOUT=1s SQL_RETRY_SLEEP_SEC=0 bash "$OUT_DIR/p7.sh" >"$OUT_DIR/t7.log" 2>&1; T7_RC=$?
touch "$OUT_DIR/t7.stop"
wait "$S7_PID" || true
wait "$H7_PID" || true
cat "$OUT_DIR/t7.log"
# 公開ログの検査用: run_sql の「持ち主の一覧」（既存の機能。表名と鍵の種類が出る）は除く
grep -av -E 'AccessShareLock|AccessExclusiveLock|RowExclusiveLock|RowShareLock' "$OUT_DIR/t7.log" >> "$ALL_LOG"
T7_MAX="$(field "$OUT_DIR/t7.log" max)"; T7_SLOW="$(field "$OUT_DIR/t7.log" slow)"; T7_SEEN="$(cat "$OUT_DIR/t7.seen" 2>/dev/null || echo 0)"
T7_RETRIES="$(grep -ac 'lock conflict; retry [0-9]' "$OUT_DIR/t7.log" || true)"
echo "T7 rc=${T7_RC} max=${T7_MAX:-none} slow=${T7_SLOW:-none} sa_read_probe_lock_wait_seen=${T7_SEEN} run_sql_retries=${T7_RETRIES}"
if [ "$T7_RC" = 0 ] && grep -aq 'RUN_SQL_RESULT=ok' "$OUT_DIR/t7.log" && [ "${T7_RETRIES}" -ge 1 ] \
   && [ "${T7_SEEN}" -ge 1 ] && [ "${T7_MAX:-0}" -ge 300 ] && [ "${T7_MAX:-99999}" -le 1500 ] && [ "${T7_SLOW:-1}" = 0 ]; then
  pass "T7 max=${T7_MAX}ms slow=0 lock_wait_seen=${T7_SEEN} retries=${T7_RETRIES} run_sql ok"
else
  fail "T7 rc=${T7_RC} max=${T7_MAX:-none} slow=${T7_SLOW:-none} seen=${T7_SEEN} retries=${T7_RETRIES}"
fi

# --- T3: 終了コードが変わらない ---
echo "=== T3: 計測の後に rc=3 で終わる（本物の trap から止める） ==="
make_parent p3.sh "$NAME" "eval \"\$(cat $OUT_DIR/airo.sh)\"" "sleep 2; exit 3"
env READ_PROBE_TABLES="sb_a sb_b" READ_PROBE_INTERVAL_SEC=1 bash "$OUT_DIR/p3.sh" >"$OUT_DIR/t3.log" 2>&1; T3_RC=$?
cat "$OUT_DIR/t3.log"; cat "$OUT_DIR/t3.log" >> "$ALL_LOG"
T3_PID="$(cat "$OUT_DIR/p3.sh.pid" 2>/dev/null)"
T3_ALIVE=yes
kill -0 "$T3_PID" 2>/dev/null || T3_ALIVE=no
echo "T3 rc=${T3_RC} final_lines=$(final_line_count "$OUT_DIR/t3.log") child_pid=${T3_PID} child_alive=${T3_ALIVE}"
if [ "$T3_RC" = 3 ] && [ "$(final_line_count "$OUT_DIR/t3.log")" = 1 ] && [ "$T3_ALIVE" = no ]; then
  pass "T3 rc=3 final line shown, child gone"
else
  fail "T3 rc=${T3_RC} final=$(final_line_count "$OUT_DIR/t3.log") alive=${T3_ALIVE}"
fi

# --- T8: 親が先に消える（kill -9。trap は走らない） ---
echo "=== T8: 親を kill -9 しても計測の子が自分で終わる ==="
make_parent p8.sh "$NAME" "" "sleep 20"
env READ_PROBE_TABLES="sb_a sb_b" READ_PROBE_INTERVAL_SEC=1 bash "$OUT_DIR/p8.sh" >"$OUT_DIR/t8.log" 2>&1 &
P8_PID=$!
sleep 3
T8_CHILD="$(cat "$OUT_DIR/p8.sh.pid" 2>/dev/null)"
T8_BEFORE=no
kill -0 "$T8_CHILD" 2>/dev/null && T8_BEFORE=yes
kill -9 "$P8_PID" 2>/dev/null || true
wait "$P8_PID" 2>/dev/null || true
T8_START="$(date +%s)"
T8_ALIVE=yes
for _ in $(seq 1 40); do
  kill -0 "$T8_CHILD" 2>/dev/null || { T8_ALIVE=no; break; }
  sleep 0.25
done
T8_SEC=$(( $(date +%s) - T8_START ))
cat "$OUT_DIR/t8.log"; cat "$OUT_DIR/t8.log" >> "$ALL_LOG"
echo "T8 child_alive_before_kill=${T8_BEFORE} child_alive_after=${T8_ALIVE} seconds_to_exit=${T8_SEC} (limit 2 intervals + 2s slack = 4s)"
if [ "$T8_BEFORE" = yes ] && [ "$T8_ALIVE" = no ] && [ "$T8_SEC" -le 4 ]; then
  pass "T8 child exited by itself in ${T8_SEC}s"
else
  fail "T8 before=${T8_BEFORE} alive=${T8_ALIVE} sec=${T8_SEC}"
fi
pkill -f "sleep 20" 2>/dev/null || true

# --- T4: 表が無い ---
echo "=== T4: 計測の表の1つが無い ==="
make_parent p4.sh "$NAME" "" "sleep 4; read_probe_stop"
env READ_PROBE_TABLES="sb_a sb_missing" READ_PROBE_INTERVAL_SEC=1 bash "$OUT_DIR/p4.sh" >"$OUT_DIR/t4.log" 2>&1; T4_RC=$?
cat "$OUT_DIR/t4.log"; cat "$OUT_DIR/t4.log" >> "$ALL_LOG"
T4_ERR="$(field "$OUT_DIR/t4.log" error)"
echo "T4 rc=${T4_RC} error=${T4_ERR:-none} final_lines=$(final_line_count "$OUT_DIR/t4.log")"
if [ "$T4_RC" = 0 ] && [ "${T4_ERR:-0}" -ge 1 ] && [ "$(final_line_count "$OUT_DIR/t4.log")" = 1 ]; then pass "T4 error=${T4_ERR}"; else fail "T4 rc=${T4_RC} error=${T4_ERR:-none}"; fi

# --- T4b: つながらない ---
echo "=== T4b: 存在しない入れ物 ==="
make_parent p4b.sh "no-such-container-probe" "" "sleep 4; read_probe_stop"
env READ_PROBE_TABLES="sb_a sb_b" READ_PROBE_INTERVAL_SEC=1 bash "$OUT_DIR/p4b.sh" >"$OUT_DIR/t4b.log" 2>&1; T4B_RC=$?
cat "$OUT_DIR/t4b.log"; cat "$OUT_DIR/t4b.log" >> "$ALL_LOG"
T4B_ERR="$(field "$OUT_DIR/t4b.log" error)"
echo "T4b rc=${T4B_RC} error=${T4B_ERR:-none} final_lines=$(final_line_count "$OUT_DIR/t4b.log")"
if [ "$T4B_RC" = 0 ] && [ "${T4B_ERR:-0}" -ge 1 ] && [ "$(final_line_count "$OUT_DIR/t4b.log")" = 1 ]; then pass "T4b error=${T4B_ERR}"; else fail "T4b rc=${T4B_RC} error=${T4B_ERR:-none}"; fi

# --- T5: 公開ログに SQL の文面・表名が出ない ---
echo "=== T5: 公開ログ（T1〜T8 の出力をまとめたもの）に SQL と表名が無い ==="
T5_SELECT="$(grep -ac 'SELECT' "$ALL_LOG" || true)"
T5_NAMES="$(grep -acE 'sb_a|sb_b|sb_missing' "$ALL_LOG" || true)"
echo "T5 corpus_lines=$(wc -l < "$ALL_LOG" | tr -d ' ') select_lines=${T5_SELECT} table_name_lines=${T5_NAMES}"
if [ "$T5_SELECT" = 0 ] && [ "$T5_NAMES" = 0 ]; then
  pass "T5 select_lines=0 table_name_lines=0"
else
  fail "T5 select_lines=${T5_SELECT} table_name_lines=${T5_NAMES}"
  grep -anE 'SELECT|sb_a|sb_b|sb_missing' "$ALL_LOG" | head -20
fi

# --- T9: 既存の試験の切り出し範囲に影響が無い ---
echo "=== T9: 既存試験の切り出し範囲 ==="
RETRY_EXTRACT="$(awk '/^SQL_LOCK_TIMEOUT=/{p=1} p{print} p&&/^run_sql\(\) \{/{r=1} r&&/^}/{exit}' "$SCRIPT")"
RETRY_PROBE="$(printf '%s\n' "$RETRY_EXTRACT" | grep -c 'read_probe' || true)"
AIRO_PROBE_LINES="$(grep -n 'read_probe' "$OUT_DIR/airo.sh" || true)"
AIRO_PROBE_N="$(grep -c 'read_probe' "$OUT_DIR/airo.sh" || true)"
AIRO_PROBE_IF="$(grep -cE '^[[:space:]]*if declare -F read_probe_stop' "$OUT_DIR/airo.sh" || true)"
echo "T9 retry_extract_read_probe_lines=${RETRY_PROBE} airo_extract_read_probe_lines=${AIRO_PROBE_N} airo_if_declare_lines=${AIRO_PROBE_IF}"
echo "$AIRO_PROBE_LINES"
if [ "$RETRY_PROBE" = 0 ] && [ "$AIRO_PROBE_N" = 1 ] && [ "$AIRO_PROBE_IF" = 1 ]; then
  pass "T9 extract ranges ok"
else
  fail "T9 retry=${RETRY_PROBE} airo=${AIRO_PROBE_N} airo_if=${AIRO_PROBE_IF}"
fi

if [ "$RESULT" -eq 0 ]; then echo "RESULT: PASS"; else echo "RESULT: FAIL"; exit 1; fi
