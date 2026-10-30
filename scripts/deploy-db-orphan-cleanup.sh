#!/bin/bash
# 本番反映の控え・移行の取り残しを片付ける（docs/handoff/deploy-db-stall/design.md §16-4）。
#
# 呼ばれたときに残っている「本番反映の控え・移行」は、前の本番反映の取り残しか、手で流したものとみなす。
# 毎朝3時の控え（cron の名前）は対象にしない。
#
# 使い方（deploy.yml から。サーバーにファイルがあるときだけ呼ぶ）:
#   cd /home/ubuntu/salesanchor && bash scripts/deploy-db-orphan-cleanup.sh
#
# 動き:
#   1 サーバー側の run_all_migrations.sh / backup.sh deploy のプロセスに TERM を送る（引数が完全一致するものだけ）
#   2 DB 側: application_name が移行か本番反映の控えの接続を pg_terminate_backend で切る
#   3 2秒ごとに、名前の付いた接続が残っていれば切り直す。プロセス0本かつ接続0本で終わる
#   4 待つ上限 120 秒。残ったら rc=1（KILL は送らない）
#   見つからなければ何もせず rc=0
#
# 公開ログに出すので、SQL の文面・接続元アドレスは出さない（数だけ）。

set -u

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/lib/db-app-names.sh"

# コンテナ名は本番の値を固定で書く（外から変えられない。試験は入れ物の名前を本番にそろえる）
POSTGRES="astro-webapp-postgres-1"
WAIT_LIMIT_SEC=120
POLL_SEC=2

# 部分一致は使わない（ssh-action の段の bash は台本全体を引数に持つので、部分一致だと自分の段を止める）
PAT_MIGRATE='^bash scripts/run_all_migrations\.sh$'
PAT_BACKUP='^bash scripts/backup\.sh deploy$'

# 対象のプロセス番号を1行ずつ出す。読み取り監視の子も同じ引数を持つので数に入る
list_pids() {
  pgrep -x -f "${PAT_MIGRATE}" 2>/dev/null || true
  pgrep -x -f "${PAT_BACKUP}" 2>/dev/null || true
}

# DB に問い合わせて数を出す。失敗したら x を出す（片付いたと誤認しない）
db_count() { # db_count <SQL>
  local out
  out=$(docker exec -e PGOPTIONS="-c statement_timeout=5s -c lock_timeout=1s" "${POSTGRES}" \
    psql -X -U jarvis -d jarvis_db -v ON_ERROR_STOP=1 -At -c "$1" 2>/dev/null) || { echo x; return 0; }
  case "${out}" in
    '' | *[!0-9]*) echo x ;;
    *) echo "${out}" ;;
  esac
}

NAMES_SQL="application_name IN ('${SA_APPNAME_MIGRATION}', '${SA_APPNAME_BACKUP_DEPLOY}') AND pid <> pg_backend_pid()"

count_backends() {
  db_count "SELECT count(*) FROM pg_stat_activity WHERE ${NAMES_SQL}"
}
terminate_backends() { # 切れた本数を出す
  db_count "SELECT count(*) FROM (SELECT pg_terminate_backend(pid) AS r FROM pg_stat_activity WHERE ${NAMES_SQL}) t WHERE r"
}

PIDS=$(list_pids | sort -u)
SCRIPTS=0
if [ -n "${PIDS}" ]; then
  SCRIPTS=$(printf '%s\n' "${PIDS}" | wc -l | tr -d ' ')
fi

# 1 サーバー側のスクリプトに TERM（trap が前面の docker exec を待ってから後始末する）
for p in ${PIDS}; do
  kill -TERM "${p}" 2>/dev/null || true
done

BACKENDS=0
REMAINING=0
DEADLINE=$((SECONDS + WAIT_LIMIT_SEC))
while true; do
  # 2・3 名前の付いた接続を切る（プロセスが見つかったかどうかに関係なく、残っていれば何度でも）
  NB=$(count_backends)
  if [ "${NB}" != "0" ]; then
    T=$(terminate_backends)
    case "${T}" in x) ;; *) BACKENDS=$((BACKENDS + T)) ;; esac
  fi
  NP=$(list_pids | sort -u | wc -l | tr -d ' ')
  NB=$(count_backends)
  if [ "${NP}" = "0" ] && [ "${NB}" = "0" ]; then
    REMAINING=0
    break
  fi
  case "${NB}" in x) NBN=1 ;; *) NBN=${NB} ;; esac
  REMAINING=$((NP + NBN))
  if [ "${SECONDS}" -ge "${DEADLINE}" ]; then
    break
  fi
  sleep "${POLL_SEC}"
done

echo ">>> [cleanup] scripts=${SCRIPTS} backends=${BACKENDS} remaining=${REMAINING}"
if [ "${REMAINING}" -ne 0 ]; then
  echo ">>> [cleanup] FAILED: ${WAIT_LIMIT_SEC} 秒で消えませんでした（KILL は送りません。人が prod1 で確認してください）"
  exit 1
fi
exit 0
