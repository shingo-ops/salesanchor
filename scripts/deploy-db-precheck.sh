#!/bin/bash
# 本番反映の移行の前に、開いたままの DB 取引を数えて、待つか止めて知らせる点検
# （docs/handoff/deploy-db-stall/design.md §18-3 便2）。
#
# deploy.yml の「Check open DB transactions before deploy」の段が、サーバーの作業場所ではなく
# origin/main から読んで流す（作業場所は入れ替えの段までは1つ前の版のため）。
# このスクリプトは作業場所の他のファイルを読まない。
#
# 動き:
#   1 jarvis の PostgreSQL で「idle in transaction（aborted も含む）で取引の始まりから5秒より長い接続」を数える
#   2 5秒おきに数え、3回続けて 0 本なら clean と書いて通る（exit 0）。1本でもあれば続けての数えは 0 に戻る
#   3 待ちは $SECONDS（実際の経過秒）で測る。600秒たっても clean にならなければ止まる（exit 1）
#   4 止まるときは握り手（pid・ユーザー・application_name・状態・取引の秒数・握った表）と一時コンテナの名前を書き、
#     ROLLBACK_DISCORD_WEBHOOK があれば Discord に1通送る（なければ webhook not set と書く）。SQL の文面・接続元は書かない
#   5 数えられなかった（docker/psql の失敗・10秒の時間切れ）ときも止まる（exit 1）。黙って通らない
#   6 試しを止める・接続を切ることはしない
#   7 毎回の数えの最後に、長い active の文（state が active で now() - query_start が LONG_ACTIVE_SEC 秒より長い）の本数を
#     「info: long active statements=K」と書く。記録だけで、数には入れず、通る・止まるの判定は変えない。
#     数えられなければ止めずに unknown と書く。偽の数の回は書かない
#
# 試験のためだけの環境変数: DB_PRECHECK_FAKE_COUNTS（例 0,1,0,0,0）。あれば DB の代わりにその数を順に使い、
# 並びを使い切ったら最後の値を繰り返す。本番の deploy.yml はこの変数を渡さない（試験 P8）。

set -u

# ---- 待ちの数の正本（ここ1か所。試験は環境変数で短くする） ----
POLL_SEC="${DB_PRECHECK_POLL_SEC:-5}"        # 数える間隔（秒）
CLEAN_STREAK="${DB_PRECHECK_STREAK:-3}"      # 何回続けて 0 本なら通すか
WAIT_LIMIT_SEC="${DB_PRECHECK_LIMIT_SEC:-600}" # 待つ上限（秒。$SECONDS で測る）
XACT_SEC="${DB_PRECHECK_XACT_SEC:-5}"        # この秒数より長く開いた取引を数える
LONG_ACTIVE_SEC="${DB_PRECHECK_LONG_ACTIVE_SEC:-60}" # この秒数より長く active の文を記録だけする（数に入れない）
# ---------------------------------------------------------

# コンテナ名・接続先は本番の値を固定で書く（scripts/run_all_migrations.sh と同じ値。作業場所のファイルを読まない）
POSTGRES="astro-webapp-postgres-1"
PG_USER="jarvis"
PG_DB="jarvis_db"

FAKE="${DB_PRECHECK_FAKE_COUNTS:-}"
WEBHOOK="${ROLLBACK_DISCORD_WEBHOOK:-}"

SECONDS=0

finish() { # finish: 最後の1行（移行の段の始まりとの差が、点検の後の隙の長さ）
  echo ">>> [precheck] precheck finished at $(date -u +%Y-%m-%dT%H:%M:%SZ) waited=${SECONDS}"
}

# 取引が開いたままの接続の条件（数えるのと握り手の記録で同じ条件）
WHERE_SQL="state IN ('idle in transaction', 'idle in transaction (aborted)')
  AND now() - xact_start > interval '${XACT_SEC} seconds'
  AND pid <> pg_backend_pid()
  AND backend_type = 'client backend'
  AND datname = current_database()"

run_sql() { # run_sql <SQL>: 結果を標準出力へ。つながる前・docker exec で止まっても10秒で戻る
  timeout -k 2 10 docker exec -e PGCONNECT_TIMEOUT=5 \
    -e PGOPTIONS="-c statement_timeout=5s -c lock_timeout=1s" \
    "${POSTGRES}" \
    psql -X -U "${PG_USER}" -d "${PG_DB}" -v ON_ERROR_STOP=1 -At -F '|' -c "$1" 2>/dev/null
}

log_long_active() { # 長い active の文の本数を記録だけする（動き7）。失敗しても止めない。偽の数の回は飛ばす
  [ -n "${FAKE}" ] && return 0
  local out
  out=$(run_sql "SELECT count(*) FROM pg_stat_activity
    WHERE state = 'active'
      AND now() - query_start > interval '${LONG_ACTIVE_SEC} seconds'
      AND pid <> pg_backend_pid()
      AND backend_type = 'client backend'
      AND datname = current_database()") || out=""
  case "${out}" in
    '' | *[!0-9]*) out=unknown ;;
  esac
  echo ">>> [precheck] info: long active statements=${out}"
  return 0
}

FAKE_IDX=0
get_count() { # get_count: 結果を変数 COUNT に入れる（サブシェルを使わない: FAKE の位置を進めるため）。数えられなければ x
  local out
  if [ -n "${FAKE}" ]; then
    local arr
    IFS=',' read -r -a arr <<<"${FAKE}"
    local last=$((${#arr[@]} - 1))
    local i="${FAKE_IDX}"
    [ "${i}" -gt "${last}" ] && i="${last}"
    FAKE_IDX=$((FAKE_IDX + 1))
    COUNT="${arr[${i}]}"
    return 0
  fi
  out=$(run_sql "SELECT count(*) FROM pg_stat_activity WHERE ${WHERE_SQL}") || { COUNT=x; return 0; }
  case "${out}" in
    '' | *[!0-9]*) COUNT=x ;;
    *) COUNT="${out}" ;;
  esac
}

HOLDERS=""
record_holders() { # 握り手の記録。SQL の文面・接続元アドレスは取らない
  if [ -n "${FAKE}" ]; then
    return 0 # 試験の偽の数を使う回は、握り手の記録と docker ps を飛ばす
  fi
  HOLDERS=$(run_sql "SELECT a.pid, a.usename, a.application_name, a.state,
      floor(extract(epoch FROM now() - a.xact_start))::int AS xact_sec,
      coalesce((SELECT string_agg(DISTINCT c.relname, ',' ORDER BY c.relname)
                FROM pg_locks l JOIN pg_class c ON c.oid = l.relation
                WHERE l.pid = a.pid AND l.locktype = 'relation' AND l.granted
                  AND c.relkind IN ('r', 'p')
                  AND c.relnamespace NOT IN ('pg_catalog'::regnamespace, 'information_schema'::regnamespace)), '') AS tables
    FROM pg_stat_activity a
    WHERE a.state IN ('idle in transaction', 'idle in transaction (aborted)')
      AND now() - a.xact_start > interval '${XACT_SEC} seconds'
      AND a.pid <> pg_backend_pid()
      AND a.backend_type = 'client backend'
      AND a.datname = current_database()
    ORDER BY a.xact_start") || HOLDERS=""
  echo ">>> [precheck] holders (pid|user|application_name|state|xact_sec|tables):"
  if [ -n "${HOLDERS}" ]; then
    echo "${HOLDERS}" | sed 's/^/>>> [precheck]   /'
  else
    echo ">>> [precheck]   (could not read holders)"
  fi
  echo ">>> [precheck] running one-off containers (label com.docker.compose.oneoff=True):"
  timeout -k 2 10 docker ps --filter label=com.docker.compose.oneoff=True --format '>>> [precheck]   {{.Names}}' 2>/dev/null \
    || echo ">>> [precheck]   (could not list containers)"
}

notify_discord() { # notify_discord <本数> <名前の一覧>
  if [ -z "${WEBHOOK}" ]; then
    echo ">>> [precheck] discord: webhook not set (not sent)"
    return 0
  fi
  local names msg payload
  names=$(printf '%s' "$2" | tr -cd 'A-Za-z0-9_,.() -')
  msg="移行の前の点検で止めました。本番は前のままです。止めた理由: 開いたままの取引 $1 本（名前: ${names:-不明}）。試しが終わってから、この回をやり直してください。"
  payload=$(printf '{"content":"%s"}' "${msg}")
  if curl -s --max-time 10 -X POST "${WEBHOOK}" -H 'Content-Type: application/json' -d "${payload}" -o /dev/null -f; then
    echo ">>> [precheck] discord: sent"
  else
    echo ">>> [precheck] discord: send failed (exit 1 is unchanged)"
  fi
  return 0
}

echo ">>> [precheck] start: poll=${POLL_SEC}s streak=${CLEAN_STREAK} limit=${WAIT_LIMIT_SEC}s xact>${XACT_SEC}s"
if [ -n "${FAKE}" ]; then
  echo ">>> [precheck] FAKE counts in use (${FAKE})"
fi

N=0
STREAK=0
COUNT=0
while true; do
  N=$((N + 1))
  get_count
  if [ "${COUNT}" = "x" ]; then
    echo ">>> [precheck] could not count open transactions (docker/psql failed or timed out) - stopping"
    finish
    exit 1
  fi
  if [ "${COUNT}" -eq 0 ]; then
    STREAK=$((STREAK + 1))
  else
    STREAK=0
  fi
  echo ">>> [precheck] sample ${N}: count=${COUNT} streak=${STREAK} elapsed=${SECONDS}"
  log_long_active
  if [ "${STREAK}" -ge "${CLEAN_STREAK}" ]; then
    echo ">>> [precheck] clean: no open transactions for ${CLEAN_STREAK} samples in a row"
    finish
    exit 0
  fi
  if [ "${SECONDS}" -ge "${WAIT_LIMIT_SEC}" ]; then
    break
  fi
  sleep "${POLL_SEC}"
done

echo ">>> [precheck] STOP: open transactions did not clear within ${WAIT_LIMIT_SEC}s (last count=${COUNT})"
record_holders
NAMES=""
if [ -n "${HOLDERS}" ]; then
  NAMES=$(echo "${HOLDERS}" | cut -d'|' -f3 | sort -u | paste -sd, -)
fi
notify_discord "${COUNT}" "${NAMES}"
finish
exit 1
