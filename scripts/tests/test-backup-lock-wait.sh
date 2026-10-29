#!/bin/bash
# scripts/backup.sh の pg_dump にロック待ちの上限が付いていること、
# 失敗・中断で書き途中のファイルが残らないことを試す。
# 設計: docs/handoff/deploy-db-stall/design.md §15-4（B1・B2・B4。B3 は既存の2本をワークフローが流す）
#
#   B2 backup.sh 全体を偽の docker で（docker 不要）
#   B1 実物の PostgreSQL 16 で pg_dump の上限が効くこと（docker 要）
#   B4 本物の backup.sh を本物の pg_dump で（docker 要。B4b は約2分かかる）
#
# 実行: bash scripts/tests/test-backup-lock-wait.sh
# docker が使えないとき: 既定では B1・B4 を SKIP して B2 だけ流す。
#   REQUIRE_DOCKER=1 なら docker が無いこと自体を FAIL にする（CI はこちら）。
# backup.sh は mapfile を使うので bash 4 以上で流す（BASH_BIN で指定できる）。

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# BACKUP_SH_OVERRIDE は赤の実演（壊した写しを試す）と bash 3.2 での手元確認用
BACKUP_SH="${BACKUP_SH_OVERRIDE:-$(cd "${SCRIPT_DIR}/.." && pwd)/backup.sh}"
BASH_BIN="${BASH_BIN:-bash}"

TMP=$(mktemp -d)
FAIL=0
COMPOSE_UP=0
COMPOSE_FILE="${TMP}/compose/docker-compose.yml"

cleanup() {
  jobs -p | xargs kill 2>/dev/null || true
  if [ "${COMPOSE_UP}" -eq 1 ]; then
    docker compose -f "${COMPOSE_FILE}" down -v >/dev/null 2>&1 || true
  fi
  rm -rf "${TMP}"
}
trap cleanup EXIT

check() {
  # check <説明> <0 なら PASS>
  if [ "$2" -eq 0 ]; then
    echo "PASS: $1"
  else
    echo "FAIL: $1"
    FAIL=1
  fi
}
ok_if() { # ok_if <説明> <コマンド...>
  local d="$1"
  shift
  if "$@"; then check "${d}" 0; else check "${d}" 1; fi
}
count_glob() { # count_glob <dir> <pattern>
  find "$1" -maxdepth 1 -name "$2" | wc -l | tr -d ' '
}

# ---------------------------------------------------------------- B2
FAKE_BIN="${TMP}/bin"
mkdir -p "${FAKE_BIN}"
cat > "${FAKE_BIN}/docker" <<'EOF'
#!/bin/bash
# 偽の docker。FAKE_DOCKER_MODE: ok（SQL を出して 0）/ fail（少し出して 1）/ hang（印を作って眠る）
printf '%s\n' "$*" >> "${FAKE_DOCKER_ARGS}"
case "${FAKE_DOCKER_MODE}" in
  ok) echo "SELECT 1; -- fake dump"; exit 0 ;;
  fail) echo "partial output"; exit 1 ;;
  hang) : > "${FAKE_DOCKER_MARK}"; sleep 60; exit 0 ;;
esac
exit 99
EOF
chmod +x "${FAKE_BIN}/docker"

# 古い控えを N 本置く（時刻を1時間ずつずらす）
seed_old() { # seed_old <dir> <n>
  mkdir -p "$1"
  python3 -I - "$1" "$2" <<'EOF'
import os, sys, time
d, n = sys.argv[1], int(sys.argv[2])
now = time.time()
for i in range(n):
    p = os.path.join(d, "salesanchor_db_20200101_%06d.sql.gz" % i)
    open(p, "w").write("old")
    t = now - (i + 1) * 3600 - 7200
    os.utime(p, (t, t))
EOF
}

# backup.sh を偽 docker で流す。結果は R_RC に入る
run_fake() { # run_fake <mode> <dir>
  local mode="$1" d="$2"
  mkdir -p "${d}/tf"
  : > "${d}/args"
  R_RC=0
  env PATH="${FAKE_BIN}:${PATH}" FAKE_DOCKER_MODE="${mode}" FAKE_DOCKER_ARGS="${d}/args" \
    FAKE_DOCKER_MARK="${d}/mark" SALESANCHOR_BACKUP_DIR="${d}/bk" \
    SALESANCHOR_BACKUP_COMPOSE_FILE="${d}/compose.yml" BACKUP_TEXTFILE_DIR="${d}/tf" \
    "${BASH_BIN}" "${BACKUP_SH}" >"${d}/out.txt" 2>&1 || R_RC=$?
}

echo "=== B2: backup.sh 全体を偽の docker で ==="

# 成功
D="${TMP}/b2ok"
seed_old "${D}/bk" 11
run_fake ok "${D}"
[ "${R_RC}" -eq 0 ] || sed 's/^/  | /' "${D}/out.txt"
ok_if "B2 成功: rc=0" test "${R_RC}" -eq 0
NEWF=$(find "${D}/bk" -maxdepth 1 -name 'salesanchor_db_2*.sql.gz' ! -name 'salesanchor_db_2020*' | head -1)
ok_if "B2 成功: 新しい控えが1本できた" test -n "${NEWF}"
ok_if "B2 成功: gunzip で元の文字列に戻る" test "$(gunzip -c "${NEWF}" 2>/dev/null)" = "SELECT 1; -- fake dump"
# shellcheck disable=SC2012  # 権限の文字列だけ取り出す（find の書式は macOS と GNU で違う）
ok_if "B2 成功: 新しい控えの権限が 600" test "$(ls -l "${NEWF}" | cut -c1-10)" = "-rw-------"
ok_if "B2 成功: 控えが新しいものを含めて10本" test "$(count_glob "${D}/bk" 'salesanchor_db_*.sql.gz')" = "10"
ok_if "B2 成功: backup.log に保持の行" grep -q 'Count-based retention' "${D}/bk/backup.log"
ok_if "B2 成功: backup.log に Completed の行" grep -q 'Backup completed' "${D}/bk/backup.log"
ok_if "B2 成功: backup_local.prom がある" test -f "${D}/tf/backup_local.prom"
ok_if "B2 成功: .partial が0本" test "$(count_glob "${D}/bk" '*.partial')" = "0"
ok_if "B2 成功: 偽 docker の引数に --lock-wait-timeout=120000" grep -q -- '--lock-wait-timeout=120000' "${D}/args"
ok_if "B2 成功: FAILED の行が無い" test "$(grep -c 'Backup FAILED' "${D}/bk/backup.log" || true)" = "0"

# 失敗
D="${TMP}/b2ng"
seed_old "${D}/bk" 11
run_fake fail "${D}"
ok_if "B2 失敗: rc≠0" test "${R_RC}" -ne 0
ok_if "B2 失敗: 控えは11本のまま（件数の保持へ進まない）" test "$(count_glob "${D}/bk" 'salesanchor_db_*.sql.gz')" = "11"
ok_if "B2 失敗: .partial が0本" test "$(count_glob "${D}/bk" '*.partial')" = "0"
ok_if "B2 失敗: backup.log に Backup FAILED rc=" grep -q 'Backup FAILED rc=' "${D}/bk/backup.log"
ok_if "B2 失敗: backup_local.prom ができていない" test ! -e "${D}/tf/backup_local.prom"

# 古い書き途中の片付け
D="${TMP}/b2old"
seed_old "${D}/bk" 1
OLDP="${D}/bk/salesanchor_db_20200101_000000.sql.gz.partial"
NEWP="${D}/bk/salesanchor_db_20200102_000000.sql.gz.partial"
: > "${OLDP}"
: > "${NEWP}"
python3 -I - "${OLDP}" <<'EOF'
import os, sys, time
t = time.time() - 2 * 86400
os.utime(sys.argv[1], (t, t))
EOF
run_fake ok "${D}"
ok_if "B2 片付け: rc=0" test "${R_RC}" -eq 0
ok_if "B2 片付け: 2日前の .partial が消えた" test ! -e "${OLDP}"
ok_if "B2 片付け: いま作った .partial は残る" test -e "${NEWP}"

# 途中で止められた（Ctrl-C と同じ形: プロセスグループ全体に TERM）
D="${TMP}/b2kill"
seed_old "${D}/bk" 2
mkdir -p "${D}/tf"
: > "${D}/args"
if command -v setsid >/dev/null 2>&1; then
  SESSION=(setsid)
else
  # setsid が無い環境（macOS）: python で同じ pid のまま新しいグループにする
  SESSION=(python3 -I -c 'import os,sys;os.setsid();os.execvp(sys.argv[1],sys.argv[1:])')
fi
env PATH="${FAKE_BIN}:${PATH}" FAKE_DOCKER_MODE=hang FAKE_DOCKER_ARGS="${D}/args" \
  FAKE_DOCKER_MARK="${D}/mark" SALESANCHOR_BACKUP_DIR="${D}/bk" \
  SALESANCHOR_BACKUP_COMPOSE_FILE="${D}/compose.yml" BACKUP_TEXTFILE_DIR="${D}/tf" \
  "${SESSION[@]}" "${BASH_BIN}" "${BACKUP_SH}" >"${D}/out.txt" 2>&1 &
KPID=$!
PGID=""
for _ in $(seq 1 50); do
  PGID=$(ps -o pgid= -p "${KPID}" | tr -d ' ')
  [ "${PGID}" = "${KPID}" ] && break
  sleep 0.1
done
ok_if "B2 中断: backup.sh が自分のプロセスグループの先頭（pgid=${PGID}, pid=${KPID}）" test "${PGID}" = "${KPID}"
for _ in $(seq 1 100); do [ -e "${D}/mark" ] && break; sleep 0.1; done
ok_if "B2 中断: 偽 docker が始まった（印がある）" test -e "${D}/mark"
sleep 0.5
# 試験自身のグループを巻き込まないよう、先頭だと確かめられたときだけグループへ送る
if [ "${PGID}" = "${KPID}" ]; then kill -TERM -- "-${PGID}" 2>/dev/null || true; else kill -TERM "${KPID}" 2>/dev/null || true; fi
T0=$(date +%s)
for _ in $(seq 1 100); do kill -0 "${KPID}" 2>/dev/null || break; sleep 0.1; done
KRC=0
if kill -0 "${KPID}" 2>/dev/null; then
  if [ "${PGID}" = "${KPID}" ]; then kill -KILL -- "-${PGID}" 2>/dev/null || true; else kill -KILL "${KPID}" 2>/dev/null || true; fi
  KRC=999
fi
wait "${KPID}" 2>/dev/null
RC_W=$?
[ "${KRC}" -eq 999 ] || KRC=${RC_W}
T1=$(date +%s)
ok_if "B2 中断: 10秒以内に終わった（$((T1 - T0))秒）" test $((T1 - T0)) -lt 10
ok_if "B2 中断: rc=143（実際 ${KRC}）" test "${KRC}" -eq 143
ok_if "B2 中断: .partial が0本" test "$(count_glob "${D}/bk" '*.partial')" = "0"
ok_if "B2 中断: 偽 docker が残っていない" test "$(pgrep -f "${FAKE_BIN}/docker" | wc -l | tr -d ' ')" = "0"
ok_if "B2 中断: backup.log に Backup FAILED rc=143" grep -q 'Backup FAILED rc=143' "${D}/bk/backup.log"

# ---------------------------------------------------------------- docker が要る試験
if ! docker info >/dev/null 2>&1; then
  if [ "${REQUIRE_DOCKER:-0}" = "1" ]; then
    check "docker が使える（REQUIRE_DOCKER=1）" 1
  else
    echo "SKIP: B1・B4（docker が使えない。CI で確かめる）"
  fi
  if [ "${FAIL}" -ne 0 ]; then echo "FAILED"; exit 1; fi
  echo "ALL PASSED (B1・B4 は SKIP)"
  exit 0
fi

mkdir -p "${TMP}/compose"
cat > "${COMPOSE_FILE}" <<'EOF'
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: jarvis
      POSTGRES_DB: jarvis_db
      POSTGRES_HOST_AUTH_METHOD: trust
EOF
dc() { docker compose -f "${COMPOSE_FILE}" "$@"; }
psql_c() { dc exec -T postgres psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1 -At -c "$1"; }

COMPOSE_UP=1
dc up -d >"${TMP}/up.txt" 2>&1
READY=1
for _ in $(seq 1 60); do
  if dc exec -T postgres pg_isready -h 127.0.0.1 -U jarvis -d jarvis_db >/dev/null 2>&1; then READY=0; break; fi
  sleep 1
done
check "入れ物の PostgreSQL 16 が起動した" "${READY}"
if [ "${READY}" -ne 0 ]; then
  cat "${TMP}/up.txt"
  echo "FAILED"
  exit 1
fi
psql_c "CREATE TABLE lock_target (id int); INSERT INTO lock_target VALUES (1);" >/dev/null

wait_for_sql() { # wait_for_sql <説明> <件数を返す SQL>（結果が1以上になるまで最大30秒）
  local n
  for _ in $(seq 1 60); do
    n=$(psql_c "$2" 2>/dev/null || echo 0)
    if [ "${n:-0}" -ge 1 ] 2>/dev/null; then check "$1" 0; return 0; fi
    sleep 0.5
  done
  check "$1" 1
  return 1
}
release_all() {
  psql_c "SELECT count(pg_terminate_backend(pid)) FROM pg_stat_activity WHERE pid <> pg_backend_pid() AND query LIKE '%pg_sleep%'" >/dev/null 2>&1 || true
  local n
  for _ in $(seq 1 60); do
    n=$(psql_c "SELECT count(*) FROM pg_stat_activity WHERE pid <> pg_backend_pid() AND query LIKE '%pg_sleep%'" 2>/dev/null || echo 1)
    [ "${n}" = "0" ] && break
    sleep 0.5
  done
  check "握りを全部止めた" "$([ "${n}" = "0" ] && echo 0 || echo 1)"
  wait 2>/dev/null || true
}

PG_DUMP_CMD=(dc exec -T postgres pg_dump -U jarvis --lock-wait-timeout=2000 jarvis_db)
LOCK_MS=$(sed -n 's/^PG_DUMP_LOCK_WAIT_MS=\([0-9]*\)$/\1/p' "${BACKUP_SH}")
case "${LOCK_MS}" in ''|*[!0-9]*) check "B1 backup.sh の PG_DUMP_LOCK_WAIT_MS が数字だけ（'${LOCK_MS}'）" 1 ;; *) check "B1 backup.sh の PG_DUMP_LOCK_WAIT_MS が数字だけ（${LOCK_MS}）" 0 ;; esac

judge_dump() { # judge_dump <ラベル>
  local t0 t1 rc=0
  t0=$(date +%s)
  "${PG_DUMP_CMD[@]}" >"${TMP}/dump.out" 2>"${TMP}/dump.err" || rc=$?
  t1=$(date +%s)
  ok_if "$1: rc=1（実際 ${rc}）" test "${rc}" -eq 1
  ok_if "$1: 所要10秒未満（$((t1 - t0))秒）" test $((t1 - t0)) -lt 10
  ok_if "$1: 標準エラーに canceling statement due to statement timeout" grep -q 'canceling statement due to statement timeout' "${TMP}/dump.err"
  ok_if "$1: 標準エラーに LOCK TABLE" grep -q 'LOCK TABLE' "${TMP}/dump.err"
}

echo "=== B1a: 排他ロックを握られている形 ==="
psql_c "BEGIN; LOCK TABLE lock_target IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(60);" >/dev/null 2>&1 &
wait_for_sql "B1a 排他ロックが取れた（pg_locks）" "SELECT count(*) FROM pg_locks WHERE locktype='relation' AND relation='lock_target'::regclass AND mode='AccessExclusiveLock' AND granted AND pid <> pg_backend_pid()"
judge_dump "B1a"
release_all
RC=0
"${PG_DUMP_CMD[@]}" >/dev/null 2>&1 || RC=$?
ok_if "B1a 握りを止めた後は同じ命令が rc=0（実際 ${RC}）" test "${RC}" -eq 0

echo "=== B1b: 待ち行列にいる形（10/29 と同じ） ==="
psql_c "BEGIN; SELECT 1 FROM lock_target LIMIT 1; SELECT pg_sleep(60);" >/dev/null 2>&1 &
wait_for_sql "B1b 接続 A が共有ロックを持った（pg_locks）" "SELECT count(*) FROM pg_locks WHERE locktype='relation' AND relation='lock_target'::regclass AND mode='AccessShareLock' AND granted AND pid <> pg_backend_pid()"
psql_c "BEGIN; LOCK TABLE lock_target IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(60);" >/dev/null 2>&1 &
if ! wait_for_sql "B1b 接続 B が待っている（pg_locks の granted=false）" "SELECT count(*) FROM pg_locks WHERE locktype='relation' AND relation='lock_target'::regclass AND mode='AccessExclusiveLock' AND NOT granted"; then
  echo "NEEDS_DECISION: B1b で pg_locks の granted=false が作れない"
  echo "FAILED"
  exit 1
fi
judge_dump "B1b"
release_all
RC=0
"${PG_DUMP_CMD[@]}" >/dev/null 2>&1 || RC=$?
ok_if "B1b 握りを止めた後は同じ命令が rc=0（実際 ${RC}）" test "${RC}" -eq 0

echo "=== B4: 本物の backup.sh を本物の pg_dump で ==="
run_real() { # run_real <dir>
  local d="$1"
  mkdir -p "${d}/tf"
  R_RC=0
  env SALESANCHOR_BACKUP_DIR="${d}/bk" SALESANCHOR_BACKUP_COMPOSE_FILE="${COMPOSE_FILE}" \
    BACKUP_TEXTFILE_DIR="${d}/tf" "${BASH_BIN}" "${BACKUP_SH}" >"${d}/out.txt" 2>&1 || R_RC=$?
}
D="${TMP}/b4a"
run_real "${D}"
ok_if "B4a 成功: rc=0（実際 ${R_RC}）" test "${R_RC}" -eq 0
F4=$(find "${D}/bk" -maxdepth 1 -name 'salesanchor_db_*.sql.gz' | head -1)
ok_if "B4a 成功: 控えに CREATE TABLE public.lock_target がある" sh -c "gunzip -c '${F4}' | grep -q 'CREATE TABLE public.lock_target'"

D="${TMP}/b4b"
mkdir -p "${D}/bk"
psql_c "BEGIN; LOCK TABLE lock_target IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(300);" >/dev/null 2>&1 &
wait_for_sql "B4b 排他ロックが取れた（pg_locks）" "SELECT count(*) FROM pg_locks WHERE locktype='relation' AND relation='lock_target'::regclass AND mode='AccessExclusiveLock' AND granted AND pid <> pg_backend_pid()"
T0=$(date +%s)
run_real "${D}"
T1=$(date +%s)
EL=$((T1 - T0))
echo "B4b 所要 ${EL} 秒"
ok_if "B4b 上限で止まる: rc≠0（実際 ${R_RC}）" test "${R_RC}" -ne 0
ok_if "B4b 所要が120秒以上180秒未満（${EL}秒）" test "${EL}" -ge 120 -a "${EL}" -lt 180
ok_if "B4b .partial が0本" test "$(count_glob "${D}/bk" '*.partial')" = "0"
ok_if "B4b 控えが増えない" test "$(count_glob "${D}/bk" 'salesanchor_db_*.sql.gz')" = "0"
ok_if "B4b backup.log に FAILED の行" grep -q 'Backup FAILED rc=' "${D}/bk/backup.log"
release_all

if [ "${FAIL}" -ne 0 ]; then
  echo "FAILED"
  exit 1
fi
echo "ALL PASSED"
