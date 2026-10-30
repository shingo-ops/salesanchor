#!/bin/bash
# Gemini を prompt_ab で解かせ、渡した文字列を残す（design.md §5-1, §5-5）。PO が ! で実行する台本。AI は実行しない。
# 使い方: bash vps_run_gemini.sh <test-id> <runs-file(Mac)> run|dry <origin/main の40桁sha>
#   第4引数 = Mac で git ls-remote origin refs/heads/main した sha（本番の HEAD と照らす）。
#   環境変数 RD = 読み取り専用鍵で SQL を流す rd.sh のパス（使った額の合計を読む。無ければ止まる）。
#   例: bash vps_run_gemini.sh llmcmp-g1 /path/to/runs.txt dry <sha>  # まず dry（Gemini を呼ばない。指示書の sha256 の行を確かめる）
#       bash vps_run_gemini.sh llmcmp-g1 /path/to/runs.txt run <sha>  # 本番の試験（約 300 回、上限 5.00 USD）
#   途中で止まったら、未完了の job だけの runs ファイルで test-id を llmcmp-g2 にして続きを流す（別名なので上書きされない）。
# 別の箱: docker compose run --rm --no-deps（本番 worker とは別コンテナ）。-e PYTHONPATH=/app が必須（backend/Dockerfile:4 は PYTHONPATH 無し）。
# 健康診断の上書き（no-health.yml）を必ず付ける: 付けないと約2.5分で unhealthy になり本番の警報が鳴る（RUNBOOK_fdm.md:12-17）。
set -u
TID=${1:?test-id}
RUNS=${2:?runs file}
MODE=${3:?run か dry}
case "$MODE" in run|dry) ;; *) echo "ABORT: 第3引数は run か dry（\"$MODE\" は不可）"; exit 1;; esac
ORIGIN_MAIN=${4:-}
TOTAL_USD=5.00   # llmcmp-* 全体の合計上限（test-id ごとではない）。使った分を引いた残りを --max-cost-usd に渡す
MIN_REMAIN=1.00
RD=${RD:-/Users/tanizawashingo/CC報告ファイル-keep/accuracy-gold-20261020/box-error189/T2/pcc/rd.sh}
HERE=$(cd "$(dirname "$0")" && pwd)
K="-i $HOME/.ssh/manual-only/id_ed25519 ubuntu@49.212.137.46"
BASE=/home/ubuntu/fhd-test/llmcmp
printf '%s\n' "$TID" | grep -Eq '^llmcmp-[a-z0-9-]+$' || { echo "ABORT: test-id は ^llmcmp-[a-z0-9-]+\$ のみ（SQL と ssh 命令に入るため）"; exit 1; }
[ -f "$RUNS" ] || { echo "ABORT: runs が無い"; exit 1; }
REMAIN=0
if [ "$MODE" != dry ]; then
  # 止め①: 本番の deploy が動いていない（start_fdm.sh:35）
  gh run list -R shingo-ops/salesanchor --workflow deploy.yml --limit 3 --json status -q '.[].status' | grep -qE 'in_progress|queued' && { echo "ABORT: deploy running"; exit 1; }
  # 止め②: 本番の HEAD が origin/main と同じ（start_fdm.sh:53-56）
  [ "${#ORIGIN_MAIN}" = "40" ] || { echo "ABORT: 第4引数に origin/main の sha（40桁）を渡す"; exit 1; }
  HEAD_SHA=$(ssh $K "git -C /home/ubuntu/salesanchor rev-parse HEAD" | tr -d ' \r')
  case "$HEAD_SHA" in [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]*) ;; *) echo "ABORT: host HEAD not a sha"; exit 1;; esac
  [ "$HEAD_SHA" = "$ORIGIN_MAIN" ] || { echo "ABORT: 本番の HEAD が origin/main と違う"; exit 1; }
  # 止め③: 使った額（llmcmp-* 全体）を読み取り専用鍵で読み、残りを上限にする（start_fdm.sh:69-77）
  [ -f "$RD" ] || { echo "ABORT: 読み取り専用の rd.sh が無い（RD=$RD）"; exit 1; }
  QD=$(mktemp -d) || exit 1
  echo "SELECT COALESCE(sum(cost_usd),0) AS usd, count(*) FILTER (WHERE source_ref = 'prompt_ab:${TID}') AS this_run_rows, count(*) FILTER (WHERE cost_usd IS NULL) AS null_cost FROM ai_ro.public__llm_usage_events WHERE source_ref LIKE 'prompt_ab:llmcmp-%';" > "$QD/q.sql"
  bash "$RD" "$QD/q.sql" 2>&1 | grep -v '^AUDIT\|^time=\|Container\|Pseudo' > "$QD/spent.raw"
  SPENT=$(awk -F'\t' 'NR==2{print $1}' "$QD/spent.raw"); THIS=$(awk -F'\t' 'NR==2{print $2}' "$QD/spent.raw"); NULLC=$(awk -F'\t' 'NR==2{print $3}' "$QD/spent.raw")
  case "$SPENT" in ''|*[!0-9.]*) echo "ABORT: 使った額を読めない"; exit 1;; esac
  [ "$THIS" = "0" ] && [ "$NULLC" = "0" ] || { echo "ABORT: 今回の test-id の台帳行がもうある／費用が空の行がある"; exit 1; }
  REMAIN=$(awk -v t="$TOTAL_USD" -v s="$SPENT" 'BEGIN{printf "%.4f", t-s}')
  awk -v r="$REMAIN" -v m="$MIN_REMAIN" 'BEGIN{exit !(r>=m)}' || { echo "ABORT: 残りの予算が ${MIN_REMAIN} USD 未満 ($REMAIN)"; exit 1; }
  echo "使った額=${SPENT} USD  残り=${REMAIN} USD（合計 ${TOTAL_USD}）"
fi
ssh $K "mkdir -p $BASE/out && chmod 777 $BASE $BASE/out" || exit 1
ssh $K "cat > $BASE/capture_prompt_ab.py" < "$HERE/capture_prompt_ab.py" || exit 1
ssh $K "cat > $BASE/runs.txt" < "$RUNS" || exit 1
ssh $K "cat > $BASE/remote_run.sh" <<'REMOTE' || exit 1
#!/bin/bash
# VPS のホストで動く。引数: 1=test-id 2=run|dry
set -u
TID=$1; MODE=$2; REMAIN=${3:-0}
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
# 起動前の止め①: 組み合わせた一式の healthcheck が ["CMD","true"] と完全一致でなければ ABORT（start_fdm.sh:90-92）
HCT=$(docker compose config --format json | python3 -I -B -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["services"]["celery-worker"]["healthcheck"]["test"]))') \
  || { echo "ABORT: compose config を読めない"; exit 1; }
[ "$HCT" = '["CMD", "true"]' ] || [ "$HCT" = '["CMD","true"]' ] || { echo "ABORT: celery-worker の healthcheck.test が CMD true になっていない"; exit 1; }
# 起動前の止め②: 別コンテナで true が実行できること
docker compose run --rm --no-deps -T "$SVC" sh -c 'test -x /bin/true || test -x /usr/bin/true' \
  || { echo "ABORT: 別コンテナに true が無い"; exit 1; }
# 起動前の止め③: 他の prompt_ab／試験コンテナが動いていない（start_fdm.sh:38-41）
n=$(pgrep -fc '[a]pp.tools.prompt_ab|[c]apture_prompt_ab' ; docker ps -q --filter name=fhd- | wc -l; docker ps -q --filter name=llmcmp- | wc -l) || true
n=$(printf '%s\n' "$n" | awk '{s+=$1} END{print s+0}')
case "$n" in ''|*[!0-9]*) echo "ABORT: 動いている数を読めない"; exit 1;; esac
[ "$n" = "0" ] || { echo "ABORT: 他の prompt_ab／試験が動いている ($n)"; exit 1; }
# 起動前の止め④: 同じ test-id の出力がもうあれば上書きせず止まる（start_fdm.sh:42-43）
if [ "$MODE" != dry ]; then
  for f in "$BASE/out/$TID.jsonl" "$BASE/out/$TID.index.tsv" "$BASE/$TID.out"; do
    [ ! -e "$f" ] || { echo "ABORT: $f がもうある（別の test-id にする）"; exit 1; }
  done
fi
# 起動前の止め⑤: 像に --retry-transient が入っている（start_fdm.sh:97-100）
docker compose run --rm --no-deps -T -e PYTHONPATH=/app "$SVC" python -m app.tools.prompt_ab --help | grep -q -- '--retry-transient' \
  || { echo "ABORT: --retry-transient not in container"; exit 1; }
# 起動前の止め⑥: dry で指示書の sha256 を自動照合（合わなければ流さない。start_fdm.sh:104-114）
DRYARGS=(--config v102 --runs-file /fhd/llmcmp/runs.txt --out-dir /fhd/llmcmp/dryout --test-id "${TID}-dry" --prompt-key raw_copy_v101_f_dm --thinking-level high --retry-transient 3 --repeat 3 --max-cost-usd 1.00 --dry-run)
DRY=$(docker compose run --rm --no-deps -T --name "${NAME}-dry" -v "$BASE:/fhd/llmcmp" -e PYTHONPATH=/app "$SVC" python /fhd/llmcmp/capture_prompt_ab.py "${DRYARGS[@]}" 2>&1; echo dry_rc=$?)
echo "$DRY" > "$BASE/$TID.dry.out"
echo "$DRY" | grep -q '^dry_rc=0$' || { echo "ABORT: dry の終了コードが 0 でない"; exit 1; }
echo "$DRY" | grep -q "prompt_key=raw_copy_v101_f_dm sha256=84afd2e4e0094b542d5f1dada1fef39290aa6d997135296e78601fc945ac8b0c" \
  || { echo "ABORT: dry に 'prompt_key=raw_copy_v101_f_dm sha256=84afd2e4…8b0c' の行が無い"; exit 1; }
echo "dry の sha 行: OK"
if [ "$MODE" = dry ]; then exit 0; fi
ARGS=(--config v102 --runs-file /fhd/llmcmp/runs.txt --out-dir /fhd/llmcmp/out --test-id "$TID" --prompt-key raw_copy_v101_f_dm --thinking-level high --retry-transient 3 --repeat 3 --max-cost-usd "$REMAIN")
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
  ssh $K "nohup bash $BASE/remote_run.sh $TID run $REMAIN > $BASE/$TID.remote.log 2>&1 < /dev/null &"
  echo "起動した。終わりの確認: ssh $K \"tail -3 $BASE/$TID.out\"  （LLMCMP_DONE_$TID が出たら終わり）"
  echo "起動前の止め（healthcheck・他の稼働・既存ファイル・dry の sha 照合）で止まった理由は $BASE/$TID.remote.log に残る: ssh $K \"cat $BASE/$TID.remote.log\""
  echo "止めたいとき: ssh $K \"docker stop llmcmp-$TID\""
fi
