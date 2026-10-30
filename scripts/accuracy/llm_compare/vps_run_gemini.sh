#!/bin/bash
# Gemini を prompt_ab で解かせ、渡した文字列を残す（design.md §5-1, §5-5）。PO が ! で実行する台本。AI は実行しない。
# 使い方: bash vps_run_gemini.sh <test-id> <runs-file(Mac)> [dry]
#   例: bash vps_run_gemini.sh llmcmp-g1 /path/to/runs.txt dry      # まず dry（Gemini を呼ばない。指示書の sha256 の行を確かめる）
#       bash vps_run_gemini.sh llmcmp-g1 /path/to/runs.txt          # 本番の試験（約 300 回、上限 5.00 USD）
#   途中で止まったら、未完了の job だけの runs ファイルで test-id を llmcmp-g2 にして続きを流す（別名なので上書きされない）。
# 別の箱: docker compose run --rm --no-deps（本番 worker とは別コンテナ）。-e PYTHONPATH=/app が必須（backend/Dockerfile:4 は PYTHONPATH 無し）。
# 健康診断の上書き（no-health.yml）を必ず付ける: 付けないと約2.5分で unhealthy になり本番の警報が鳴る（RUNBOOK_fdm.md:12-17）。
set -u
TID=${1:?test-id}
RUNS=${2:?runs file}
MODE=${3:-run}
HERE=$(cd "$(dirname "$0")" && pwd)
K="-i $HOME/.ssh/manual-only/id_ed25519 ubuntu@49.212.137.46"
BASE=/home/ubuntu/fhd-test/llmcmp
case "$TID" in llmcmp-*) ;; *) echo "ABORT: test-id は llmcmp- で始める"; exit 1;; esac
[ -f "$RUNS" ] || { echo "ABORT: runs が無い"; exit 1; }
ssh $K "mkdir -p $BASE/out && chmod 777 $BASE $BASE/out" || exit 1
ssh $K "cat > $BASE/capture_prompt_ab.py" < "$HERE/capture_prompt_ab.py" || exit 1
ssh $K "cat > $BASE/runs.txt" < "$RUNS" || exit 1
ssh $K "cat > $BASE/remote_run.sh" <<'REMOTE' || exit 1
#!/bin/bash
# VPS のホストで動く。引数: 1=test-id 2=run|dry
set -u
TID=$1; MODE=$2
BASE=/home/ubuntu/fhd-test/llmcmp
COMPOSE_DIR=/home/ubuntu/salesanchor
SVC=celery-worker
NAME=llmcmp-${TID}
cd "$COMPOSE_DIR" || { echo "ABORT: cd $COMPOSE_DIR"; exit 1; }
if [ -n "$(docker ps -a --filter "name=^${NAME}\$" --format '{{.ID}}')" ]; then echo "ABORT: コンテナ ${NAME} がもうある"; exit 1; fi
# 健康診断の上書き（常に成功）。本番の compose の一式に1本足す
printf 'services:\n  %s:\n    healthcheck:\n      test: ["CMD", "true"]\n' "$SVC" > "$BASE/no-health.yml"
CF=$(grep '^COMPOSE_FILE=' .env 2>/dev/null | tail -n 1 | cut -d= -f2- | tr -d "\"'")
if [ -z "$CF" ]; then CF=docker-compose.yml; [ -f docker-compose.override.yml ] && CF="$CF:docker-compose.override.yml"; fi
export COMPOSE_FILE="$CF:$BASE/no-health.yml"
echo "compose_files=$COMPOSE_FILE" > "$BASE/$TID.composefiles"
# 起動前の止め①: 組み合わせた一式の healthcheck が ["CMD","true"] でなければ ABORT
docker compose config 2>/dev/null | awk '/^  celery-worker:/{f=1;next} f&&/^  [a-z]/{f=0} f' | grep -A2 'healthcheck:' | grep -q 'true' \
  || { echo "ABORT: healthcheck の上書きが効いていない"; exit 1; }
# 起動前の止め②: 別コンテナで true が実行できること
docker compose run --rm --no-deps -T "$SVC" sh -c 'test -x /bin/true || test -x /usr/bin/true' \
  || { echo "ABORT: 別コンテナに true が無い"; exit 1; }
ARGS=(--config v102 --runs-file /fhd/llmcmp/runs.txt --out-dir /fhd/llmcmp/out --test-id "$TID" --prompt-key raw_copy_v101_f_dm --thinking-level high --retry-transient 3 --repeat 3 --max-cost-usd 5.00)
if [ "$MODE" = dry ]; then
  docker compose run --rm --no-deps -T --name "${NAME}-dry" -v "$BASE:/fhd/llmcmp" -e PYTHONPATH=/app "$SVC" \
    python /fhd/llmcmp/capture_prompt_ab.py "${ARGS[@]}" --dry-run > "$BASE/$TID.dry.out" 2>&1
  echo "dry exit=$? (見る: $BASE/$TID.dry.out に prompt_key=raw_copy_v101_f_dm sha256=84afd2e4... の行)"; exit 0
fi
# 起動後の止め: 120 秒以内に healthy にならなければ docker stop
(
  s=""
  for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
    s=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}NO_HEALTH{{end}}' "$NAME" 2>/dev/null)
    [ "$s" = healthy ] && break
    sleep 10
  done
  { echo "health=$s"; } > "$BASE/$TID.health"
  if [ "$s" != healthy ]; then echo "HEALTH_ABORT" >> "$BASE/$TID.health"; docker stop -t 10 "$NAME" >> "$BASE/$TID.health" 2>&1; fi
) &
docker compose run --rm --no-deps -T --name "$NAME" -v "$BASE:/fhd/llmcmp" -e PYTHONPATH=/app "$SVC" \
  python /fhd/llmcmp/capture_prompt_ab.py "${ARGS[@]}" > "$BASE/$TID.out" 2>&1
echo "exit=$?" >> "$BASE/$TID.out"
echo "LLMCMP_DONE_${TID}" >> "$BASE/$TID.out"
REMOTE
if [ "$MODE" = dry ]; then
  ssh $K "bash $BASE/remote_run.sh $TID dry"
else
  # 長いので VPS 側で裏で動かす。終わりの確認: ssh ... "tail -3 $BASE/$TID.out" に LLMCMP_DONE_$TID が出る（約1時間）
  ssh $K "nohup bash $BASE/remote_run.sh $TID run > $BASE/$TID.remote.log 2>&1 < /dev/null &"
  echo "起動した。終わりの確認: ssh $K \"tail -3 $BASE/$TID.out\"  （LLMCMP_DONE_$TID が出たら終わり）"
  echo "止めたいとき: ssh $K \"docker stop llmcmp-$TID\""
fi
