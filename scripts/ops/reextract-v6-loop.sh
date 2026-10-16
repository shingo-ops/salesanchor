#!/usr/bin/env bash
# v6 -> v102 やり直しの繰り返し（ホストで動かす。nohup で長く流すときに使う）。
# 設計: docs/handoff/reextract-v6-with-v102/design.md D6
#
# 使い方（ホストの compose のディレクトリ = .env がある所で実行する）:
#   nohup bash scripts/ops/reextract-v6-loop.sh >> /home/ubuntu/reextract-v6/loop.log 2>&1 &
#   追加の引数は道具の --execute にそのまま渡す（例: --limit 20）。
#
# 1回（N）ごとに: --execute の後で --repair を流す。
#   execute の終了コード 3 または 2 ならそこで止める（上限・確かめの失敗）。
#   0 または 4（失敗が残った）なら続けて repair。execute も repair も 0 なら抜ける。4 なら次の回へ。
#   最大回数に達して 4 が出ていたら 4 で終える。
#   137 等（コンテナが消された）は、次の回へ進む。
# コンテナ名は reextract-v6-YYYYMMDD-N。デプロイが消す名前（astro-webapp-celery-worker*）から外してある。
# 名前がぶつかったら、前の回のコンテナを docker rm してから進む。
set -u

WORKDIR="${WORKDIR:-/home/ubuntu/reextract-v6}"      # コンテナの /work に載せるホストのディレクトリ
SERVICE="${SERVICE:-celery-worker}"
DOCKER_BIN="${DOCKER_BIN:-docker}"
MAX_ROUNDS="${MAX_ROUNDS:-10}"
DATE_TAG="${DATE_TAG:-$(date +%Y%m%d)}"
TOOL="python -m app.tools.reextract_v6_with_v102"

log() { echo "$(date '+%F %T') $*"; }

remove_if_exists() {
  # 名前がぶつかるコンテナが残っていたら消す
  local name="$1"
  if [ -n "$("$DOCKER_BIN" ps -a --filter "name=^${name}\$" --format '{{.Names}}' 2>/dev/null)" ]; then
    log "前の回のコンテナを削除: ${name}"
    "$DOCKER_BIN" rm -f "${name}" >/dev/null 2>&1 || true
  fi
}

run_tool() {
  # run_tool <round> <道具の引数...>
  local round="$1"; shift
  local name="reextract-v6-${DATE_TAG}-${round}"
  remove_if_exists "$name"
  "$DOCKER_BIN" compose run --rm --no-deps -T --name "$name" -v "${WORKDIR}:/work" "$SERVICE" $TOOL --out-dir /work "$@"
}

mkdir -p "$WORKDIR" || { log "WORKDIR を作れません: $WORKDIR"; exit 2; }

# 書込の確かめ: コンテナの appuser の uid で /work に書けること（書けなければ chown/chmod が要る）
check_name="reextract-v6-${DATE_TAG}-0"
remove_if_exists "$check_name"
if ! "$DOCKER_BIN" compose run --rm --no-deps -T --name "$check_name" -v "${WORKDIR}:/work" --entrypoint sh "$SERVICE" \
     -c 'echo "uid=$(id -u)"; touch /work/.write_test && rm -f /work/.write_test'; then
  log "コンテナ(appuser)が ${WORKDIR} に書けません。uid を確認して、ホストのディレクトリの持ち主を合わせてください。"
  exit 2
fi

residual=0   # 1 = 失敗が残った回があった（終了コード 4）
for round in $(seq 1 "$MAX_ROUNDS"); do
  log "round ${round}: execute"
  run_tool "$round" --execute "$@"
  rc=$?
  log "round ${round}: execute rc=${rc}"
  if [ "$rc" -eq 3 ] || [ "$rc" -eq 2 ]; then
    exit "$rc"
  fi
  if [ "$rc" -ne 0 ] && [ "$rc" -ne 4 ]; then
    continue   # 137 等。次の回で、残りから続ける
  fi
  exec_rc="$rc"

  log "round ${round}: repair"
  run_tool "$round" --repair --ids-file /work/order.txt
  rc=$?
  log "round ${round}: repair rc=${rc}"
  if [ "$rc" -eq 3 ] || [ "$rc" -eq 2 ]; then
    exit "$rc"
  fi
  if [ "$rc" -eq 0 ] && [ "$exec_rc" -eq 0 ]; then
    log "完了"
    exit 0
  fi
  if [ "$rc" -eq 4 ] || [ "$exec_rc" -eq 4 ]; then
    residual=1   # 失敗が残った。次の回で、残りをもう一度やる
  fi
done

if [ "$residual" -eq 1 ]; then
  log "最大 ${MAX_ROUNDS} 回に達しましたが、失敗した件が残っています。控え(/work/records.jsonl)を確認してください。"
  exit 4
fi
log "最大 ${MAX_ROUNDS} 回に達しました。控え(/work/records.jsonl)を確認してください。"
exit 1
