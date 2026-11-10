#!/bin/bash
# 移行の前の点検（scripts/deploy-db-precheck.sh）と、deploy.yml の新しい段の試験。
# 設計: docs/handoff/deploy-db-stall/design.md §18-4（P1〜P8、P4a〜P4c）
#
#   P4a〜P4c 3回続けての数え・上限・FAKE の行（DB_PRECHECK_FAKE_COUNTS）  docker 不要
#   P6 DB につながらない（偽 docker）                                    docker 不要
#   P7 deploy.yml の新しい段の形                                        docker 不要（pyyaml 要）
#   P8 deploy.yml に DB_PRECHECK_FAKE_COUNTS が無い                      docker 不要
#   P1 何も無い / P2 開いたままの取引で止まる / P3 待つ間に閉じる / P5 active は数えない   docker 要
#
# 実行: bash scripts/tests/test-deploy-db-precheck.sh
# docker が使えないとき: 既定では docker の要る試験を SKIP。REQUIRE_DOCKER=1 なら docker が無いこと自体を FAIL にする（CI）。
# 入れ物の compose は name: astro-webapp でコンテナ名を本番と同じ astro-webapp-postgres-1 にする
# （点検のスクリプトはコンテナ名を固定で持つため）。同名のコンテナが既にあれば何もせず止まる。

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PRECHECK="${ROOT}/scripts/deploy-db-precheck.sh"
DEPLOY_YML="${ROOT}/.github/workflows/deploy.yml"

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
last_sample_elapsed() { # last_sample_elapsed <ファイル>: 台本が書いた最後の sample 行の elapsed
  grep 'sample ' "$1" | tail -1 | sed -n 's/.*elapsed=\([0-9]*\)$/\1/p'
}

# ---------------------------------------------------------------- P4a
echo "=== P4a: 3回続けて0本で通る（0,1,0,0,0 → 5回目の数えの後に clean） ==="
O="${TMP}/p4a.out"
RC=0
DB_PRECHECK_FAKE_COUNTS="0,1,0,0,0" DB_PRECHECK_POLL_SEC=0 timeout 30 bash "${PRECHECK}" >"${O}" 2>&1 || RC=$?
sed 's/^/  | /' "${O}"
ok_if "P4a exit 0（実際 ${RC}）" test "${RC}" -eq 0
ok_if "P4a sample の行が5行" test "$(count_lines 'sample [0-9]+:' "${O}")" = "5"
ok_if "P4a clean の行が1行" test "$(count_lines '\] clean:' "${O}")" = "1"
ok_if "P4a clean は5回目の sample の後（1回目の0では通らない）" bash -c "awk '/sample 5:/{s=NR} /\\] clean:/{c=NR} END{exit !(s>0 && c>s)}' '${O}'"
ok_if "P4a 最後の行が precheck finished ... waited=" bash -c "tail -1 '${O}' | grep -qE 'precheck finished at [0-9T:Z-]+ waited=[0-9]+\$'"

# ---------------------------------------------------------------- P4b
echo "=== P4b: ずっと1本 → 上限（3秒）で止まる ==="
O="${TMP}/p4b.out"
RC=0
DB_PRECHECK_FAKE_COUNTS="1" DB_PRECHECK_POLL_SEC=1 DB_PRECHECK_LIMIT_SEC=3 timeout 30 bash "${PRECHECK}" >"${O}" 2>&1 || RC=$?
sed 's/^/  | /' "${O}"
ok_if "P4b 30秒の時間切れでなく exit 1（実際 ${RC}）" test "${RC}" -eq 1
ok_if "P4b 止めた理由の行（STOP ... did not clear）" grep -qE '\] STOP: open transactions did not clear within 3s' "${O}"
EL=$(last_sample_elapsed "${O}")
ok_if "P4b 最後の sample 行の elapsed が3以上（実際 ${EL:-なし}）" test "${EL:-0}" -ge 3
ok_if "P4b clean の行が無い" test "$(count_lines '\] clean:' "${O}")" = "0"
ok_if "P4b FAKE のときは握り手の記録と docker ps を飛ばす" test "$(count_lines 'holders|running one-off' "${O}")" = "0"
ok_if "P4b webhook が無いので webhook not set の行" grep -qF 'discord: webhook not set' "${O}"

# ---------------------------------------------------------------- P4c
echo "=== P4c: FAKE counts in use の行が1行 ==="
O="${TMP}/p4c.out"
RC=0
DB_PRECHECK_FAKE_COUNTS="0,1,0,0,0" DB_PRECHECK_POLL_SEC=0 timeout 30 bash "${PRECHECK}" >"${O}" 2>&1 || RC=$?
ok_if "P4c FAKE counts in use が1行" test "$(count_lines 'FAKE counts in use' "${O}")" = "1"
O="${TMP}/p4c2.out"
RC=0
mkdir -p "${TMP}/p6-bin"
printf '#!/bin/bash\nexit 1\n' >"${TMP}/p6-bin/docker"
chmod +x "${TMP}/p6-bin/docker"
env -u DB_PRECHECK_FAKE_COUNTS PATH="${TMP}/p6-bin:${PATH}" timeout 30 bash "${PRECHECK}" >"${O}" 2>&1 || RC=$?
ok_if "P4c 変数が無いとき FAKE の行は出ない" test "$(count_lines 'FAKE' "${O}")" = "0"

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

# ---------------------------------------------------------------- P7
echo "=== P7: deploy.yml の新しい段の形 ==="
P7_OUT="${TMP}/p7.out"
P7_RC=0
python3 -I - "${DEPLOY_YML}" >"${P7_OUT}" 2>&1 <<'PYEOF' || P7_RC=$?
import sys

import yaml

with open(sys.argv[1], encoding="utf-8") as f:
    doc = yaml.safe_load(f)

NAME = "Check open DB transactions before deploy"
bad = 0


def fail(msg):
    global bad
    print("FAIL: " + msg)
    bad = 1


jobs_with = [
    (jn, job["steps"])
    for jn, job in doc["jobs"].items()
    if any(s.get("name") == NAME for s in (job.get("steps") or []))
]
if len(jobs_with) != 1:
    print("FAIL: 新しい段が1つの job にちょうど1つ、ではない（%d 個の job にある）" % len(jobs_with))
    sys.exit(1)
steps = jobs_with[0][1]


def idx(pred):
    hit = [i for i, s in enumerate(steps) if pred(s)]
    return hit[0] if len(hit) == 1 else None


i_new = idx(lambda s: s.get("name") == NAME)
i_disk = idx(lambda s: s.get("name") == "Check free disk space")
i_backup = idx(lambda s: s.get("id") == "backup")
i_deploy = idx(lambda s: s.get("name") == "Deploy to VPS (code + env + docker compose)")
i_migrate = idx(lambda s: s.get("id") == "migrate")
for label, i in (("空き容量の段", i_disk), ("控えの段", i_backup), ("入れ替えの段", i_deploy), ("移行の段", i_migrate)):
    if i is None:
        fail("%s が1つだけ見つからない" % label)
if bad:
    sys.exit(1)

if not (i_disk < i_new < i_backup < i_deploy < i_migrate):
    fail("段の順が 空き容量 < 新しい段 < 控え < 入れ替え < 移行 でない（%s）" % [i_disk, i_new, i_backup, i_deploy, i_migrate])
new = steps[i_new]
if new.get("if") != steps[i_migrate].get("if"):
    fail("if が移行の段と同じでない: %r / %r" % (new.get("if"), steps[i_migrate].get("if")))
if "steps.gate.outputs.migrations == 'true'" not in str(new.get("if")):
    fail("if に steps.gate.outputs.migrations == 'true' が無い")
if "ssh-action" not in str(new.get("uses")):
    fail("uses が ssh-action でない")
script = new["with"]["script"]
for token in (
    "git show origin/main:scripts/deploy-db-precheck.sh",
    "skipped: script not in origin/main",
    "mktemp",
    "git fetch origin main",
    "git rev-parse --verify origin/main",
    "git cat-file -e origin/main:scripts/deploy-db-precheck.sh",
):
    if token not in script:
        fail("script に %r が無い" % token)
if "bash scripts/deploy-db-precheck.sh" in script:
    fail("作業場所の台本を流す形（bash scripts/deploy-db-precheck.sh）がある")
lines = [ln.strip() for ln in script.splitlines()]
if "set -e" not in lines or "cd /home/ubuntu/salesanchor" not in lines:
    fail("set -e か cd /home/ubuntu/salesanchor が無い")
elif lines.index("set -e") > lines.index("cd /home/ubuntu/salesanchor"):
    fail("set -e が cd より後")
if (new.get("env") or {}).get("ROLLBACK_DISCORD_WEBHOOK") != "${{ secrets.DISCORD_WEBHOOK_OWNER_PING }}":
    fail("env の ROLLBACK_DISCORD_WEBHOOK が DISCORD_WEBHOOK_OWNER_PING から渡されていない")
if "ROLLBACK_DISCORD_WEBHOOK" not in str(new["with"].get("envs", "")).replace(" ", "").split(","):
    fail("with.envs に ROLLBACK_DISCORD_WEBHOOK が無い")
if str(new["with"].get("command_timeout")) != "12m":
    fail("command_timeout が 12m でない")
if not bad:
    print("OK: 順（空き容量 < 新しい段 < 控え < 入れ替え < 移行）・if・origin/main から読む形・env/envs・12m")
sys.exit(bad)
PYEOF
sed 's/^/  | /' "${P7_OUT}"
check "P7 deploy.yml の新しい段の形" "${P7_RC}"

# ---------------------------------------------------------------- P8
echo "=== P8: deploy.yml のどこにも DB_PRECHECK_FAKE_COUNTS が無い ==="
ok_if "P8 DB_PRECHECK_FAKE_COUNTS が deploy.yml に無い" test "$(grep -c 'DB_PRECHECK_FAKE_COUNTS' "${DEPLOY_YML}")" = "0"

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
holder_stop p5active

if [ "${FAIL}" -ne 0 ]; then
  echo "FAILED"
  exit 1
fi
echo "ALL PASSED"
