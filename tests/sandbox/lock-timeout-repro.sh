#!/usr/bin/env bash
# 再現試験: 稼働中の読み取りが products を掴んでいる間に parse_logs を落とす migration を流すと、
# (1) migration が待つ (2) 後から来た読み取り(C)も待たされる (3) lock_timeout=1s だと migration が1秒で諦め C は待たない、を測る。
# 使い捨て postgres:16 のみ。パスワードは試験専用の固定値（秘密ではない）。本番・secrets には触れない。
set -uo pipefail

NAME=sb-lock-pg
DROP_SQL=migrations/20261002_170000_drop_discord_inventory_tables.sql
CREATE_SQL=migrations/20260604_120000_create_parse_logs.sql
VIEW_SQL=migrations/20260604_130000_create_supplier_parse_stats_view.sql
PSQL=(psql -U postgres -d postgres -v ON_ERROR_STOP=1)
T0=$(date +%s%N)

now_ms() { echo $(( ($(date +%s%N) - T0) / 1000000 )); }
log() { echo "[t=$(now_ms)ms] $*"; }
dsql() { docker exec -i "$NAME" "${PSQL[@]}" -Atc "$1"; }

cleanup() {
  echo "--- docker logs (tail 80) ---"
  docker logs "$NAME" 2>&1 | tail -80 || true
  docker rm -f "$NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run -d --name "$NAME" -e POSTGRES_PASSWORD=sandbox postgres:16 >/dev/null
ready=0
for _ in $(seq 1 60); do
  if docker exec "$NAME" pg_isready -U postgres >/dev/null 2>&1; then ready=1; break; fi
  sleep 1
done
[ "$ready" = 1 ] || { echo "postgres did not become ready within 60s"; exit 1; }
# initdb 直後の一時起動が終わるのを待つ（pg_isready が一瞬通ることがある）
sleep 3
for _ in $(seq 1 30); do dsql 'select 1' >/dev/null 2>&1 && break; sleep 1; done

dsql 'select version()'

setup_base() {
  dsql "CREATE TABLE IF NOT EXISTS public.products (id serial PRIMARY KEY, is_active bool);
        CREATE TABLE IF NOT EXISTS public.suppliers (id serial PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS public.ingestion_jobs (id serial PRIMARY KEY);" >/dev/null
  dsql "INSERT INTO public.products (is_active) SELECT true FROM generate_series(1,5);
        INSERT INTO public.suppliers DEFAULT VALUES; INSERT INTO public.suppliers DEFAULT VALUES;
        INSERT INTO public.ingestion_jobs DEFAULT VALUES;" >/dev/null
}

recreate_parse_logs() {
  # 本物の migration をそのまま流す（parse_logs と FK 3本）。ビューも作る（本番は毎回これを流してから消す）
  docker exec -i "$NAME" "${PSQL[@]}" < "$CREATE_SQL" >/dev/null
  docker exec -i "$NAME" "${PSQL[@]}" < "$VIEW_SQL" >/dev/null
  echo "parse_logs FK 本数: $(dsql "SELECT count(*) FROM pg_constraint WHERE conrelid='public.parse_logs'::regclass AND contype='f'")"
}

time_c() {
  # C: 在庫表の読み取りの代役。docker exec 往復込みの実測。
  local s e rc
  s=$(date +%s%N)
  docker exec -i "$NAME" "${PSQL[@]}" -Atc 'SELECT count(*) FROM products' >/dev/null
  rc=$?
  e=$(date +%s%N)
  echo "C_elapsed_ms=$(( (e - s) / 1000000 )) rc=${rc}"
}

dump_waiters() {
  echo "pg_locks granted=false:"
  dsql "SELECT l.pid, l.relation::regclass AS rel, l.mode, l.granted, left(a.query,70) AS query
        FROM pg_locks l JOIN pg_stat_activity a ON a.pid=l.pid
        WHERE NOT l.granted ORDER BY l.pid, l.relation::regclass::text;"
  echo "pg_locks A(granted) on products:"
  dsql "SELECT l.pid, l.relation::regclass AS rel, l.mode, l.granted
        FROM pg_locks l WHERE l.relation='public.products'::regclass ORDER BY l.granted DESC, l.pid;"
}

# 1回の試験。$1=名前, $2=B に付ける PGOPTIONS（空なら無し）
run_scenario() {
  local label="$1" pgopt="$2" a_pid b_start b_end b_rc c_out
  echo
  echo "=========== ${label} (PGOPTIONS='${pgopt}') ==========="
  log "A start: BEGIN; SELECT count(*) FROM products; pg_sleep(12); COMMIT"
  docker exec -i "$NAME" "${PSQL[@]}" -c "BEGIN; SELECT count(*) FROM products; SELECT pg_sleep(12); COMMIT;" >/tmp/A.out 2>&1 &
  a_pid=$!
  sleep 1
  b_start=$(now_ms)
  log "B start (migration ${DROP_SQL})"
  (
    if [ -n "$pgopt" ]; then
      docker exec -e PGOPTIONS="$pgopt" -i "$NAME" "${PSQL[@]}" < "$DROP_SQL" >/tmp/B.out 2>&1
    else
      docker exec -i "$NAME" "${PSQL[@]}" < "$DROP_SQL" >/tmp/B.out 2>&1
    fi
    echo $? >/tmp/B.rc
    now_ms >/tmp/B.end
  ) &
  local b_sub=$!
  sleep 0.5
  log "pg_locks sample (B waiting?)"
  dump_waiters
  sleep 1.5
  log "C start"
  c_out=$(time_c)
  log "C result: ${c_out}"
  wait "$b_sub"
  b_rc=$(cat /tmp/B.rc); b_end=$(cat /tmp/B.end)
  log "B end rc=${b_rc} B_start_ms=${b_start} B_end_ms=${b_end} B_elapsed_ms=$(( b_end - b_start ))"
  echo "--- B output ---"; cat /tmp/B.out
  wait "$a_pid"; log "A end rc=$?"
}

setup_base
recreate_parse_logs
echo "--- 基準: 何も待たない時の C ---"
time_c
time_c

run_scenario "試験1 今の形(lock_timeoutなし)" ""
echo "parse_logs 残存: $(dsql "SELECT to_regclass('public.parse_logs')")"

recreate_parse_logs
run_scenario "試験2 lock_timeout=1s" "-c lock_timeout=1s"
echo "parse_logs 残存: $(dsql "SELECT to_regclass('public.parse_logs')")"

echo
echo "=========== 試験3 失敗したBの再実行（Aが終わった後・失敗から5秒以上後） ==========="
sleep 5
log "B retry start (lock_timeout なし・A は終了済み)"
s=$(date +%s%N)
docker exec -i "$NAME" "${PSQL[@]}" < "$DROP_SQL"
rc=$?
e=$(date +%s%N)
log "B retry end rc=${rc} elapsed_ms=$(( (e - s) / 1000000 ))"
echo "parse_logs 残存: $(dsql "SELECT to_regclass('public.parse_logs')")"
echo "lock-timeout-repro: DONE"
