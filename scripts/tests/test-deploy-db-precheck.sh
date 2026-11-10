#!/bin/bash
# 移行の前の点検（scripts/deploy-db-precheck.sh）の試験（本物の DB が要る P1〜P3・P5 と、偽 docker の P6）。
# 設計: docs/handoff/deploy-db-stall/design.md §18-4（第4.1版）
#
#   P6 DB につながらない（偽 docker）                                    docker 不要
#   P1 何も無い / P2 開いたままの取引で止まる / P3 待つ間に閉じる / P5 active は数えない   docker 要
#
# P4a〜P4e・P7〜P9（DB が要らない）は必須の pytest に移した:
#   backend/tests/ops/test_deploy_precheck_wiring.py（同じ試験を2か所に置かない）
#
# 実行: bash scripts/tests/test-deploy-db-precheck.sh
# docker が使えないとき: 既定では docker の要る試験を SKIP。REQUIRE_DOCKER=1 なら docker が無いこと自体を FAIL にする（CI）。
# 入れ物の compose は name: astro-webapp でコンテナ名を本番と同じ astro-webapp-postgres-1 にする
# （点検のスクリプトはコンテナ名を固定で持つため）。同名のコンテナが既にあれば何もせず止まる。

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PRECHECK="${ROOT}/scripts/deploy-db-precheck.sh"

TMP=$(mktemp -d)
FAIL=0
COMPOSE_UP=0
COMPOSE_FILE="${TMP}/compose/docker-compose.yml"
BG_PIDS=()

cleanup() {
  local p
  for p in "${BG_PIDS[@]:-}"; do
    [ -n "${p}" ] || continue
    pkill -KILL -P "${p}" 2>/dev/null || true
    kill -KILL "${p}" 2>/dev/null || true
  done
  jobs -p | xargs kill 2>/dev/null || true
  if [ "${COMPOSE_UP}" -eq 1 ]; then
    docker compose -f "${COMPOSE_FILE}" down -v >/dev/null 2>&1 || true
  fi
  rm -rf "${TMP}"
}
trap cleanup EXIT

check() { # check <説明> <0 なら PASS>
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
count_lines() { # count_lines <正規表現> <ファイル>
  grep -c -E "$1" "$2" 2>/dev/null || true
}

# P6 用の偽 docker（失敗する）
mkdir -p "${TMP}/p6-bin"
printf '#!/bin/bash\nexit 1\n' >"${TMP}/p6-bin/docker"
chmod +x "${TMP}/p6-bin/docker"

# ---------------------------------------------------------------- P6
echo "=== P6: DB につながらない → 止まる（偽 docker） ==="
O="${TMP}/p6a.out"
RC=0
env -u DB_PRECHECK_FAKE_COUNTS PATH="${TMP}/p6-bin:${PATH}" timeout 30 bash "${PRECHECK}" >"${O}" 2>&1 || RC=$?
sed 's/^/  | /' "${O}"
ok_if "P6 docker が失敗 → exit 1（実際 ${RC}）" test "${RC}" -eq 1
ok_if "P6 数えられなかったと書く" grep -qF 'could not count open transactions' "${O}"
ok_if "P6 clean とは書かない" test "$(count_lines '\] clean:' "${O}")" = "0"

mkdir -p "${TMP}/p6-hang"
printf '#!/bin/bash\nsleep 60\n' >"${TMP}/p6-hang/docker"
chmod +x "${TMP}/p6-hang/docker"
O="${TMP}/p6b.out"
RC=0
T0=$(date +%s)
env -u DB_PRECHECK_FAKE_COUNTS PATH="${TMP}/p6-hang:${PATH}" timeout 40 bash "${PRECHECK}" >"${O}" 2>&1 || RC=$?
T1=$(date +%s)
ok_if "P6 docker が固まっても10秒ほどで exit 1（実際 rc=${RC}、$((T1 - T0))秒）" test "${RC}" -eq 1 -a $((T1 - T0)) -lt 20
ok_if "P6 固まったときも数えられなかったと書く" grep -qF 'could not count open transactions' "${O}"

# ---------------------------------------------------------------- docker が要る試験
if ! docker info >/dev/null 2>&1; then
  if [ "${REQUIRE_DOCKER:-0}" = "1" ]; then
    check "docker が使える（REQUIRE_DOCKER=1）" 1
  else
    echo "SKIP: P1〜P3・P5（docker が使えない。CI で確かめる）"
  fi
  if [ "${FAIL}" -ne 0 ]; then echo "FAILED"; exit 1; fi
  echo "ALL PASSED (docker の要る試験は SKIP)"
  exit 0
fi

if docker inspect astro-webapp-postgres-1 >/dev/null 2>&1; then
  echo "ABORT: astro-webapp-postgres-1 が既にある（本物の環境かもしれない）。試験用の入れ物と名前がぶつかるので止める"
  exit 1
fi

mkdir -p "${TMP}/compose"
cat >"${COMPOSE_FILE}" <<'EOF'
name: astro-webapp
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
if docker inspect astro-webapp-postgres-1 >/dev/null 2>&1; then
  check "docker inspect astro-webapp-postgres-1 が動く（入れ物の名前が本番と同じ）" 0
else
  check "docker inspect astro-webapp-postgres-1 が動く（入れ物の名前が本番と同じ）" 1
  docker ps -a
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
holder_start() { # holder_start <application_name>: 取引を開いて表を握ったまま何もしない接続（idle in transaction）
  ( echo "BEGIN; LOCK TABLE lock_target IN ACCESS EXCLUSIVE MODE;"; sleep 300 ) \
    | docker exec -i -e PGAPPNAME="$1" astro-webapp-postgres-1 psql -U jarvis -d jarvis_db -At >/dev/null 2>&1 &
  BG_PIDS+=("$!")
  wait_for_sql "$1 が idle in transaction になった" "SELECT count(*) FROM pg_stat_activity WHERE application_name='$1' AND state='idle in transaction'"
}
holder_stop() { # holder_stop <application_name>
  psql_c "SELECT count(pg_terminate_backend(pid)) FROM pg_stat_activity WHERE application_name='$1'" >/dev/null 2>&1 || true
}

# ---------------------------------------------------------------- P1
echo "=== P1: 何も無い → 3回続けて0本で通る ==="
O="${TMP}/p1.out"
RC=0
env -u DB_PRECHECK_FAKE_COUNTS DB_PRECHECK_POLL_SEC=1 timeout 60 bash "${PRECHECK}" >"${O}" 2>&1 || RC=$?
sed 's/^/  | /' "${O}"
ok_if "P1 exit 0（実際 ${RC}）" test "${RC}" -eq 0
ok_if "P1 clean の行" grep -qE '\] clean:' "${O}"
ok_if "P1 sample の行が3行" test "$(count_lines 'sample [0-9]+:' "${O}")" = "3"

# ---------------------------------------------------------------- P2
echo "=== P2: 6秒以上 idle in transaction の接続がある → 上限で止まる ==="
holder_start p2holder
sleep 6
O="${TMP}/p2.out"
RC=0
env -u DB_PRECHECK_FAKE_COUNTS DB_PRECHECK_POLL_SEC=1 DB_PRECHECK_LIMIT_SEC=8 timeout 60 bash "${PRECHECK}" >"${O}" 2>&1 || RC=$?
sed 's/^/  | /' "${O}"
ok_if "P2 exit 1（実際 ${RC}）" test "${RC}" -eq 1
ok_if "P2 STOP の行" grep -qE '\] STOP: open transactions did not clear' "${O}"
ok_if "P2 握り手の application_name（p2holder）が出る" grep -qF 'p2holder' "${O}"
ok_if "P2 握った表の名前（lock_target）が出る" grep -qF 'lock_target' "${O}"
ok_if "P2 SQL の中身（LOCK TABLE / BEGIN）は出ない" test "$(count_lines 'LOCK TABLE|BEGIN' "${O}")" = "0"
ok_if "P2 一時コンテナの一覧の見出しが出る" grep -qF 'running one-off containers' "${O}"
ok_if "P2 点検は握りを切らない（接続が残っている）" test "$(psql_c "SELECT count(*) FROM pg_stat_activity WHERE application_name='p2holder'")" = "1"
holder_stop p2holder
sleep 1

# ---------------------------------------------------------------- P3
echo "=== P3: 待っている間に握り手が取引を閉じる → 通る ==="
holder_start p3holder
sleep 6
O="${TMP}/p3.out"
env -u DB_PRECHECK_FAKE_COUNTS DB_PRECHECK_POLL_SEC=1 DB_PRECHECK_LIMIT_SEC=40 timeout 60 bash "${PRECHECK}" >"${O}" 2>&1 &
P3=$!
BG_PIDS+=("${P3}")
for _ in $(seq 1 40); do grep -qE 'count=1' "${O}" && break; sleep 0.5; done
ok_if "P3 握っている間は count=1 と数える" grep -qE 'count=1' "${O}"
holder_stop p3holder
RC=0
wait "${P3}" || RC=$?
sed 's/^/  | /' "${O}"
ok_if "P3 握り手が閉じた後に exit 0（実際 ${RC}）" test "${RC}" -eq 0
ok_if "P3 clean の行" grep -qE '\] clean:' "${O}"

# ---------------------------------------------------------------- P5
echo "=== P5: active の長い文だけ → 通る（数えない） ==="
docker exec -e PGAPPNAME=p5active astro-webapp-postgres-1 psql -U jarvis -d jarvis_db -At -c "SELECT pg_sleep(60)" >/dev/null 2>&1 &
BG_PIDS+=("$!")
wait_for_sql "P5 p5active が active になった" "SELECT count(*) FROM pg_stat_activity WHERE application_name='p5active' AND state='active'"
sleep 6
O="${TMP}/p5.out"
RC=0
env -u DB_PRECHECK_FAKE_COUNTS DB_PRECHECK_POLL_SEC=1 DB_PRECHECK_LIMIT_SEC=20 timeout 60 bash "${PRECHECK}" >"${O}" 2>&1 || RC=$?
sed 's/^/  | /' "${O}"
ok_if "P5 exit 0（実際 ${RC}）" test "${RC}" -eq 0
ok_if "P5 数えた本数がすべて 0" test "$(count_lines 'count=[1-9]' "${O}")" = "0"
# 後半（第4.1版）: 長い active の文の秒数を 2 秒にすると、記録の行だけが出る（通る・止まるは変わらない）
O="${TMP}/p5b.out"
RC=0
env -u DB_PRECHECK_FAKE_COUNTS DB_PRECHECK_LONG_ACTIVE_SEC=2 DB_PRECHECK_POLL_SEC=1 DB_PRECHECK_LIMIT_SEC=20 timeout 60 bash "${PRECHECK}" >"${O}" 2>&1 || RC=$?
sed 's/^/  | /' "${O}"
ok_if "P5 後半 exit 0（実際 ${RC}）" test "${RC}" -eq 0
ok_if "P5 後半 info: long active statements=1 の行が出る" grep -qF 'info: long active statements=1' "${O}"
ok_if "P5 後半 数えた本数はやはり 0" test "$(count_lines 'count=[1-9]' "${O}")" = "0"
holder_stop p5active

if [ "${FAIL}" -ne 0 ]; then
  echo "FAILED"
  exit 1
fi
echo "ALL PASSED"
