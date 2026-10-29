#!/bin/bash
# 本番反映の取り残しの片付け（scripts/deploy-db-orphan-cleanup.sh）と、その周りの試験。
# 設計: docs/handoff/deploy-db-stall/design.md §16-6（C1〜C9）
#
#   C4 名前の正本（lib と migration_py_entry.py が同じ文字列）  docker 不要
#   C9 古いサーバーのコード（deploy.yml の台本を読む）          docker 不要（pyyaml 要）
#   C1 名前が付く / C2 控えの取り残しを止める / C3 移行の形の取り残しを止める
#   C5 部分一致で止めない / C6 何も無いとき / C7 残ったら止まる   docker 要
#   C8 本物の run_all_migrations.sh の TERM の trap（偽 docker） docker 不要（bash 5 要）
#
# 実行: bash scripts/tests/test-deploy-orphan-cleanup.sh
# docker が使えないとき: 既定では docker の要る試験を SKIP。REQUIRE_DOCKER=1 なら docker が無いこと自体を FAIL にする（CI）。
# 入れ物の compose は name: astro-webapp でコンテナ名を本番と同じ astro-webapp-postgres-1 にする
# （片付けのスクリプトはコンテナ名を固定で持つため）。同名のコンテナが既にあれば何もせず止まる。

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CLEANUP_SH="${ROOT}/scripts/deploy-db-orphan-cleanup.sh"
BACKUP_SH="${ROOT}/scripts/backup.sh"
LIB_SH="${ROOT}/scripts/lib/db-app-names.sh"

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
count_glob() { # count_glob <dir> <pattern>
  find "$1" -maxdepth 1 -name "$2" | wc -l | tr -d ' '
}

if command -v setsid >/dev/null 2>&1; then
  SESSION=(setsid)
else
  # setsid が無い環境（macOS）: python で同じ pid のまま新しいグループにする。argv[0] は bash のまま
  SESSION=(python3 -I -c 'import os,sys;os.setsid();os.execvp(sys.argv[1],sys.argv[1:])')
fi

# ---------------------------------------------------------------- C4
echo "=== C4: 名前の正本 ==="
LIB_MIG=$(bash -c "source '${LIB_SH}' && printf %s \"\${SA_APPNAME_MIGRATION}\"")
LIB_BD=$(bash -c "source '${LIB_SH}' && printf %s \"\${SA_APPNAME_BACKUP_DEPLOY}\"")
LIB_BC=$(bash -c "source '${LIB_SH}' && printf %s \"\${SA_APPNAME_BACKUP_CRON}\"")
PY_NAME=$(sed -n 's/^APP_NAME = "\([^"]*\)"$/\1/p' "${ROOT}/scripts/migration_py_entry.py")
ok_if "C4 lib の移行の名前が空でない（${LIB_MIG}）" test -n "${LIB_MIG}"
ok_if "C4 lib の移行の名前と migration_py_entry.py の APP_NAME が同じ（${LIB_MIG} / ${PY_NAME}）" test "${LIB_MIG}" = "${PY_NAME}"
ok_if "C4 控え（本番反映）の名前が salesanchor_backup_deploy" test "${LIB_BD}" = "salesanchor_backup_deploy"
ok_if "C4 控え（cron）の名前が salesanchor_backup_cron" test "${LIB_BC}" = "salesanchor_backup_cron"

# ---------------------------------------------------------------- C9
echo "=== C9: 古いサーバーのコード（deploy.yml の台本） ==="
EMPTY_DIR="${TMP}/c9-empty"
mkdir -p "${EMPTY_DIR}"
C9_OUT="${TMP}/c9.out"
C9_RC=0
python3 -I - "${ROOT}/.github/workflows/deploy.yml" "${EMPTY_DIR}" >"${C9_OUT}" 2>&1 <<'PYEOF' || C9_RC=$?
import subprocess
import sys

import yaml

deploy_yml, empty_dir = sys.argv[1], sys.argv[2]
EXPECTED_IF = (
    'if [ -f scripts/deploy-db-orphan-cleanup.sh ]; then bash scripts/deploy-db-orphan-cleanup.sh; '
    'else echo ">>> [cleanup] skipped: script not present (old checkout)"; fi'
)
CD = "cd /home/ubuntu/salesanchor"

with open(deploy_yml, encoding="utf-8") as f:
    doc = yaml.safe_load(f)

steps = []
for job in doc["jobs"].values():
    steps.extend(job.get("steps") or [])


def find(pred):
    hit = [s for s in steps if pred(s)]
    return hit[0] if len(hit) == 1 else None


targets = {
    "backup(id)": (find(lambda s: s.get("id") == "backup"), "10m"),
    "migrate(id)": (find(lambda s: s.get("id") == "migrate"), "10m"),
    "失敗のときの段": (find(lambda s: s.get("name") == "Clean up DB orphans after failure"), "5m"),
}

bad = 0
for label, (step, timeout) in targets.items():
    if step is None:
        print("FAIL: %s の段が1つだけ見つからない" % label)
        bad = 1
        continue
    script = step["with"]["script"]
    lines = [ln.strip() for ln in script.splitlines()]
    try:
        i_set = lines.index("set -e")
        i_cd = lines.index(CD)
        if_lines = [n for n, ln in enumerate(lines) if ln.startswith("if [ -f scripts/deploy-db-orphan-cleanup.sh ]")]
        i_if = if_lines[0]
    except (ValueError, IndexError):
        print("FAIL: %s に set -e・cd・片付けの if 文のどれかが無い" % label)
        bad = 1
        continue
    if not (i_set < i_cd < i_if):
        print("FAIL: %s の set -e・cd・if 文の順が違う" % label)
        bad = 1
    if lines[i_if] != EXPECTED_IF:
        print("FAIL: %s の if 文が設計の文と一字一句同じでない: %s" % (label, lines[i_if]))
        bad = 1
    if str(step["with"].get("command_timeout")) != timeout:
        print("FAIL: %s の command_timeout が %s でない" % (label, timeout))
        bad = 1
    # 片付けのファイルが無いフォルダで set -e の下で流すと rc=0 と skipped の行
    r = subprocess.run(
        ["bash", "-c", "set -e; " + lines[i_if]],
        cwd=empty_dir, capture_output=True, text=True,
    )
    if r.returncode != 0 or "skipped: script not present (old checkout)" not in r.stdout:
        print("FAIL: %s の if 文をファイルの無い所で流した結果 rc=%s out=%r" % (label, r.returncode, r.stdout))
        bad = 1
    else:
        print("OK: %s set -e < cd < if 文、文面一致、ファイルが無いとき rc=0 と skipped" % label)

# 失敗のときの段の条件
fs = targets["失敗のときの段"][0]
if fs is not None:
    cond = str(fs.get("if", ""))
    for token in (
        "always()",
        "steps.backup.outcome == 'failure'",
        "steps.backup.outcome == 'cancelled'",
        "steps.migrate.outcome == 'failure'",
        "steps.migrate.outcome == 'cancelled'",
    ):
        if token not in cond:
            print("FAIL: 失敗のときの段の if に %s が無い" % token)
            bad = 1

sys.exit(bad)
PYEOF
sed 's/^/  | /' "${C9_OUT}"
check "C9 deploy.yml の3つの段の台本（set -e → cd → if 文・一字一句・古いサーバーで rc=0）" "${C9_RC}"

# ---------------------------------------------------------------- C8
echo "=== C8: 本物の run_all_migrations.sh の TERM の trap（偽 docker） ==="
if [ "${BASH_VERSINFO[0]}" -lt 5 ]; then
  echo "SKIP: C8（bash 5 が要る。read probe が EPOCHREALTIME を使う。CI の Ubuntu で確かめる）"
else
  D8="${TMP}/c8"
  FB8="${D8}/bin"
  mkdir -p "${FB8}"
  cat > "${FB8}/docker" <<'EOF'
#!/bin/bash
# 偽の docker。呼ばれるたびに START / END を1行ずつ記録に追記する。
# PGAPPNAME=salesanchor_migration と -i を両方持つ呼び出し（run_sql）の「2回目」だけ眠る
# （1回目は drop。読み取り監視の呼び出しは -i を持たないので数えない）
id=$$
args="$*"
echo "START ${id} ${args}" >> "${FAKE_LOG}"
case "${args}" in
  *"PGAPPNAME=salesanchor_migration"*" -i "*)
    n=$(cat "${FAKE_CNT}" 2>/dev/null || echo 0)
    n=$((n + 1))
    echo "${n}" > "${FAKE_CNT}"
    if [ "${n}" -eq 2 ]; then
      echo "${id}" > "${FAKE_HELD}"
      sleep 300 &
      echo $! > "${FAKE_SLEEPPID}"
      wait $!
    fi
    ;;
esac
echo "END ${id}" >> "${FAKE_LOG}"
exit 0
EOF
  chmod +x "${FB8}/docker"
  : > "${D8}/log"
  ( cd "${ROOT}" && exec env PATH="${FB8}:${PATH}" REPO_DIR="${ROOT}" FAKE_LOG="${D8}/log" FAKE_CNT="${D8}/cnt" \
      FAKE_HELD="${D8}/held" FAKE_SLEEPPID="${D8}/sleeppid" bash scripts/run_all_migrations.sh ) >"${D8}/out.txt" 2>&1 &
  P8=$!
  BG_PIDS+=("${P8}")
  for _ in $(seq 1 600); do [ -e "${D8}/held" ] && break; kill -0 "${P8}" 2>/dev/null || break; sleep 0.1; done
  ok_if "C8 013 の run_sql の呼び出しで眠った（記録で確認）" test -e "${D8}/held"
  if [ -e "${D8}/held" ]; then
    HELD=$(cat "${D8}/held")
    kill -TERM "${P8}" 2>/dev/null || true
    sleep 3
    kill "$(cat "${D8}/sleeppid")" 2>/dev/null || true
    # 止めた run_sql の終了の行が記録に書かれるのを待つ（終了の行より先に判定しない）
    for _ in $(seq 1 300); do grep -q "^END ${HELD}$" "${D8}/log" && break; sleep 0.1; done
    for _ in $(seq 1 300); do kill -0 "${P8}" 2>/dev/null || break; sleep 0.1; done
    R8=0
    wait "${P8}" || R8=$?
    L_END=$(grep -n "^END ${HELD}$" "${D8}/log" | head -1 | cut -d: -f1)
    L_RE=$(grep -n '^START .*VERBOSITY=terse' "${D8}/log" | head -1 | cut -d: -f1)
    ok_if "C8 rc=143（実際 ${R8}）" test "${R8}" -eq 143
    ok_if "C8 標準出力に [final] psql < ai_ro の作成 SQL の行" grep -qF '>>> [final] psql < migrations/20261017_130100_create_ai_ro_views.sql' "${D8}/out.txt"
    ok_if "C8 止めた run_sql の終了の行が記録にある" test -n "${L_END}"
    ok_if "C8 作り直しの最初の呼び出しの開始が記録にある" test -n "${L_RE}"
    ok_if "C8 作り直しの開始が止めた run_sql の終了より後（行 ${L_RE:-?} > ${L_END:-?}）" test "${L_RE:-0}" -gt "${L_END:-999999}"
    if [ "${FAIL}" -ne 0 ]; then sed 's/^/  | /' "${D8}/out.txt" | tail -30; fi
  fi
fi

# ---------------------------------------------------------------- docker が要る試験
if ! docker info >/dev/null 2>&1; then
  if [ "${REQUIRE_DOCKER:-0}" = "1" ]; then
    check "docker が使える（REQUIRE_DOCKER=1）" 1
  else
    echo "SKIP: C1〜C3・C5〜C7（docker が使えない。CI で確かめる）"
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
cat > "${COMPOSE_FILE}" <<'EOF'
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
# 片付けのスクリプトが固定で持つコンテナ名と、入れ物の名前が同じこと（違うと C2・C3 は赤、C5・C6 は何も確かめずに緑になる）
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
app_count() { # app_count <application_name>
  psql_c "SELECT count(*) FROM pg_stat_activity WHERE application_name='$1'" 2>/dev/null || echo x
}
grip_count() { # 握り（排他ロックを持って眠る接続）の本数
  psql_c "SELECT count(*) FROM pg_locks WHERE locktype='relation' AND relation='lock_target'::regclass AND mode='AccessExclusiveLock' AND granted AND pid <> pg_backend_pid()" 2>/dev/null || echo x
}
grip_start() { # B4b と同じ握り（排他ロックを持って pg_sleep(300)）
  psql_c "BEGIN; LOCK TABLE lock_target IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(300);" >/dev/null 2>&1 &
  BG_PIDS+=("$!")
  wait_for_sql "握りの排他ロックが取れた（pg_locks）" "SELECT count(*) FROM pg_locks WHERE locktype='relation' AND relation='lock_target'::regclass AND mode='AccessExclusiveLock' AND granted AND pid <> pg_backend_pid()"
}
release_all() { # pg_sleep を持つ接続を全部止める（待たずに戻る後始末）
  psql_c "SELECT count(pg_terminate_backend(pid)) FROM pg_stat_activity WHERE pid <> pg_backend_pid() AND query LIKE '%pg_sleep%'" >/dev/null 2>&1 || true
  local n
  for _ in $(seq 1 60); do
    n=$(psql_c "SELECT count(*) FROM pg_stat_activity WHERE pid <> pg_backend_pid() AND query LIKE '%pg_sleep%'" 2>/dev/null || echo 1)
    [ "${n}" = "0" ] && break
    sleep 0.5
  done
  check "握りを全部止めた" "$([ "${n}" = "0" ] && echo 0 || echo 1)"
}
backup_env() { # backup_env <dir>: backup.sh を入れ物に向ける環境変数
  mkdir -p "$1/tf" "$1/bk"
  echo "SALESANCHOR_BACKUP_DIR=$1/bk SALESANCHOR_BACKUP_COMPOSE_FILE=${COMPOSE_FILE} BACKUP_TEXTFILE_DIR=$1/tf"
}
proc_count() { # proc_count <完全一致の正規表現>
  pgrep -x -f "$1" 2>/dev/null | wc -l | tr -d ' '
}

# ---------------------------------------------------------------- C1
echo "=== C1: 名前が付く ==="
D="${TMP}/c1a"
# shellcheck disable=SC2046
BE=$(backup_env "${D}")
grip_start
# shellcheck disable=SC2086
( cd "${ROOT}" && exec env ${BE} "${SESSION[@]}" bash scripts/backup.sh deploy ) >"${D}/out.txt" 2>&1 &
C1A=$!
BG_PIDS+=("${C1A}")
wait_for_sql "C1 backup.sh deploy の pg_dump が salesanchor_backup_deploy の名前で接続している" "SELECT count(*) FROM pg_stat_activity WHERE application_name='salesanchor_backup_deploy'"
ok_if "C1 deploy の名前の接続が1本" test "$(app_count salesanchor_backup_deploy)" = "1"
release_all
C1A_RC=0
wait "${C1A}" || C1A_RC=$?
ok_if "C1 backup.sh deploy が握りを離した後に rc=0（実際 ${C1A_RC}）" test "${C1A_RC}" -eq 0

D="${TMP}/c1b"
BE=$(backup_env "${D}")
grip_start
# shellcheck disable=SC2086
( cd "${ROOT}" && exec env ${BE} "${SESSION[@]}" bash scripts/backup.sh ) >"${D}/out.txt" 2>&1 &
C1B=$!
BG_PIDS+=("${C1B}")
wait_for_sql "C1 引数なしの backup.sh の pg_dump が salesanchor_backup_cron の名前で接続している" "SELECT count(*) FROM pg_stat_activity WHERE application_name='salesanchor_backup_cron'"
ok_if "C1 引数なしでは deploy の名前の接続が0本" test "$(app_count salesanchor_backup_deploy)" = "0"
release_all
C1B_RC=0
wait "${C1B}" || C1B_RC=$?
ok_if "C1 引数なしの backup.sh が rc=0（実際 ${C1B_RC}）" test "${C1B_RC}" -eq 0

D="${TMP}/c1c"
BE=$(backup_env "${D}")
C1C_RC=0
# shellcheck disable=SC2086
( cd "${ROOT}" && env ${BE} bash scripts/backup.sh foo ) >"${D}/out.txt" 2>&1 || C1C_RC=$?
ok_if "C1 backup.sh foo は rc=2（実際 ${C1C_RC}）" test "${C1C_RC}" -eq 2
ok_if "C1 backup.sh foo は控えを作らない" test "$(count_glob "${D}/bk" 'salesanchor_db_*.sql.gz')" = "0"
ok_if "C1 backup.sh foo は backup.log に FAILED 行を書かない" test "$(grep -c 'Backup FAILED' "${D}/bk/backup.log" 2>/dev/null || true)" = "0"

D="${TMP}/c1d"
BE=$(backup_env "${D}")
C1D_RC=0
# cron と同じく cwd が $HOME・絶対パスで呼んでも lib を読める
# shellcheck disable=SC2086
( cd "${HOME}" && env ${BE} bash "${BACKUP_SH}" ) >"${D}/out.txt" 2>&1 || C1D_RC=$?
ok_if "C1 cwd=\$HOME・絶対パスで呼んでも rc=0（実際 ${C1D_RC}）" test "${C1D_RC}" -eq 0

# ---------------------------------------------------------------- C6
echo "=== C6: 何も無いとき ==="
C6_RC=0
( cd "${ROOT}" && bash scripts/deploy-db-orphan-cleanup.sh ) >"${TMP}/c6.out" 2>&1 || C6_RC=$?
cat "${TMP}/c6.out"
ok_if "C6 rc=0（実際 ${C6_RC}）" test "${C6_RC}" -eq 0
ok_if "C6 出力に scripts=0 backends=0 remaining=0" grep -qF 'scripts=0 backends=0 remaining=0' "${TMP}/c6.out"

# ---------------------------------------------------------------- C2
echo "=== C2: 取り残しを止める（控え） ==="
D="${TMP}/c2"
BE=$(backup_env "${D}")
grip_start
# shellcheck disable=SC2086
( cd "${ROOT}" && exec env ${BE} "${SESSION[@]}" bash scripts/backup.sh deploy ) >"${D}/out.txt" 2>&1 &
C2=$!
BG_PIDS+=("${C2}")
wait_for_sql "C2 取り残しの控えが待ちに入った（salesanchor_backup_deploy の接続）" "SELECT count(*) FROM pg_stat_activity WHERE application_name='salesanchor_backup_deploy'"
ok_if "C2 片付ける前: backup.sh deploy のプロセスが1本" test "$(proc_count '^bash scripts/backup\.sh deploy$')" = "1"
C2_T0=$(date +%s)
C2_RC=0
( cd "${ROOT}" && bash scripts/deploy-db-orphan-cleanup.sh ) >"${D}/cleanup.out" 2>&1 || C2_RC=$?
C2_T1=$(date +%s)
cat "${D}/cleanup.out"
ok_if "C2 片付けは rc=0（実際 ${C2_RC}）" test "${C2_RC}" -eq 0
ok_if "C2 片付けが120秒以内（$((C2_T1 - C2_T0))秒）" test $((C2_T1 - C2_T0)) -le 120
ok_if "C2 backup.sh の bash が消えた" test "$(proc_count '^bash scripts/backup\.sh deploy$')" = "0"
ok_if "C2 名前の付いた接続が0本" test "$(app_count salesanchor_backup_deploy)" = "0"
ok_if "C2 .partial が0本" test "$(count_glob "${D}/bk" '*.partial')" = "0"
ok_if "C2 backup.log に FAILED 行" grep -q 'Backup FAILED' "${D}/bk/backup.log"
ok_if "C2 握りの接続は残っている（関係ない接続を止めない）" test "$(grip_count)" = "1"
release_all

# ---------------------------------------------------------------- C3
echo "=== C3: 取り残しを止める（移行の形） ==="
D="${TMP}/c3"
mkdir -p "${D}/scripts"
cat > "${D}/scripts/run_all_migrations.sh" <<'EOF'
#!/bin/bash
# 偽の移行スクリプト。前面は子プロセス1つで、その子が名前の付いた接続の pg_sleep(300) を3回続けて作り直す
# （本物の Python の移行1本が中で接続を作り直す形）。TERM・EXIT の trap は本物と同じ形
trap 'echo done > "${C3_MARK}"' EXIT
trap 'exit 143' TERM
bash -c 'for i in 1 2 3; do docker exec -e PGAPPNAME=salesanchor_migration astro-webapp-postgres-1 psql -U jarvis -d jarvis_db -c "SELECT pg_sleep(300)" >/dev/null 2>&1; done'
EOF
( cd "${D}" && exec env C3_MARK="${D}/exit-mark" "${SESSION[@]}" bash scripts/run_all_migrations.sh ) >"${D}/out.txt" 2>&1 &
C3=$!
BG_PIDS+=("${C3}")
wait_for_sql "C3 偽の移行が salesanchor_migration の名前で接続した" "SELECT count(*) FROM pg_stat_activity WHERE application_name='salesanchor_migration'"
C3_T0=$(date +%s)
C3_RC=0
( cd "${ROOT}" && bash scripts/deploy-db-orphan-cleanup.sh ) >"${D}/cleanup.out" 2>&1 || C3_RC=$?
C3_T1=$(date +%s)
cat "${D}/cleanup.out"
ok_if "C3 片付けは rc=0（実際 ${C3_RC}）" test "${C3_RC}" -eq 0
ok_if "C3 片付けの後120秒以内に偽物が消えた（$((C3_T1 - C3_T0))秒）" test "$(proc_count '^bash scripts/run_all_migrations\.sh$')" = "0"
ok_if "C3 EXIT の印がある" test -e "${D}/exit-mark"
ok_if "C3 名前の付いた接続が0本" test "$(app_count salesanchor_migration)" = "0"
release_all

# ---------------------------------------------------------------- C5
echo "=== C5: 部分一致で止めない ==="
D="${TMP}/c5"
mkdir -p "${D}/empty"
BE=$(backup_env "${D}")
# ssh-action の段と同じ形: 台本全体を引数に持つ bash（中に run_all_migrations.sh の文字列がある。cwd に scripts は無いので中身は動かない）
( cd "${D}/empty" && exec bash -c "sleep 120; bash scripts/run_all_migrations.sh; true" ) >/dev/null 2>&1 &
C5A=$!
BG_PIDS+=("${C5A}")
grip_start
# cron の名前の控え（引数なしの backup.sh を握りで待たせる）
# shellcheck disable=SC2086
( cd "${ROOT}" && exec env ${BE} "${SESSION[@]}" bash scripts/backup.sh ) >"${D}/out.txt" 2>&1 &
C5B=$!
BG_PIDS+=("${C5B}")
wait_for_sql "C5 cron の名前の控えが待ちに入った" "SELECT count(*) FROM pg_stat_activity WHERE application_name='salesanchor_backup_cron'"
C5_RC=0
( cd "${ROOT}" && bash scripts/deploy-db-orphan-cleanup.sh ) >"${D}/cleanup.out" 2>&1 || C5_RC=$?
cat "${D}/cleanup.out"
ok_if "C5 片付けは rc=0（実際 ${C5_RC}）" test "${C5_RC}" -eq 0
ok_if "C5 台本全体を引数に持つ bash は残っている" kill -0 "${C5A}"
ok_if "C5 cron の名前の控えのプロセスは残っている" kill -0 "${C5B}"
ok_if "C5 cron の名前の接続は残っている" test "$(app_count salesanchor_backup_cron)" = "1"
release_all
kill -KILL "${C5A}" 2>/dev/null || true
pkill -KILL -P "${C5A}" 2>/dev/null || true
C5B_RC=0
wait "${C5B}" || C5B_RC=$?

# ---------------------------------------------------------------- C7
echo "=== C7: 残ったら止まる（TERM を無視する偽スクリプト。120〜135秒かかる） ==="
D="${TMP}/c7"
mkdir -p "${D}/scripts"
cat > "${D}/scripts/run_all_migrations.sh" <<'EOF'
#!/bin/bash
trap '' TERM
sleep 600
EOF
( cd "${D}" && exec "${SESSION[@]}" bash scripts/run_all_migrations.sh ) >/dev/null 2>&1 &
C7=$!
BG_PIDS+=("${C7}")
sleep 1
ok_if "C7 偽スクリプトが動いている" test "$(proc_count '^bash scripts/run_all_migrations\.sh$')" = "1"
C7_T0=$(date +%s)
C7_RC=0
( cd "${ROOT}" && bash scripts/deploy-db-orphan-cleanup.sh ) >"${D}/cleanup.out" 2>&1 || C7_RC=$?
C7_T1=$(date +%s)
C7_EL=$((C7_T1 - C7_T0))
cat "${D}/cleanup.out"
ok_if "C7 片付けは rc=1（実際 ${C7_RC}）" test "${C7_RC}" -eq 1
ok_if "C7 所要が120秒以上140秒未満（${C7_EL}秒）" test "${C7_EL}" -ge 120 -a "${C7_EL}" -lt 140
ok_if "C7 出力に remaining=1" grep -qF 'remaining=1' "${D}/cleanup.out"
pkill -KILL -P "${C7}" 2>/dev/null || true
kill -KILL "${C7}" 2>/dev/null || true

if [ "${FAIL}" -ne 0 ]; then
  echo "FAILED"
  exit 1
fi
echo "ALL PASSED"
