#!/bin/bash
# 3種の答え（Gemini の JSONL・Claude 2種の JSONL）を、1回の起動でまとめて採点用の形（14列 TSV）にする（design.md §5-3, §5-5）。
# 読み取りのみ（fhd_snapshot.py は READ ONLY 取引で最後に rollback）。PO が ! で実行する台本。AI は実行しない。
# 使い方: bash vps_convert.sh run   <出力フォルダ(Mac)> <origin/main の40桁sha> <jsonl...>
#         bash vps_convert.sh fetch <出力フォルダ(Mac)>
#   第3引数 = Mac で git ls-remote origin refs/heads/main した sha（本番の HEAD と照らす）。
#   JSONL の名前（拡張子を除く）が tag になる（^[a-z0-9-]+$ のみ）。Gemini は repeat 1〜3 が1本に入っている。
#   run は VPS 側で裏で動く。終わったら fetch で取り寄せる（まだなら「まだ」と出て終わる）。
# 別の箱: docker compose run --rm --no-deps（本番 worker とは別コンテナ。本番反映で worker が作り直されても rc=137 で殺されない）。
#   -e PYTHONPATH=/app が必須: ファイルとして実行すると sys.path[0] はそのファイルの場所（/fhd/llmcmp）で /app は入らない
#   （stdin 渡しの旧方式は cwd=/app が入っていた）。app パッケージは /app/app（backend/Dockerfile:4 WORKDIR /app, :24 COPY . .、PYTHONPATH 無し）。
# 健康診断の上書き（no-health.yml）を必ず付ける: 付けないと約2.5分で unhealthy になり本番の警報が鳴る（RUNBOOK_fdm.md:12-17）。
set -u
CMD=${1:?run か fetch}; shift
OUT=${1:?出力フォルダ}; shift
HERE=$(cd "$(dirname "$0")" && pwd)
K="-i $HOME/.ssh/manual-only/id_ed25519 ubuntu@49.212.137.46"
BASE=/home/ubuntu/fhd-test/llmcmp/convert
case "$CMD" in
run)
  ORIGIN_MAIN=${1:?origin/main の40桁sha}; shift
  [ $# -ge 1 ] || { echo "ABORT: jsonl が無い"; exit 1; }
  # 止め(d): jsonl の名前（拡張子を除く）は ^[a-z0-9-]+$ のみ（ssh 命令と台本に入るため）
  for f in "$@"; do
    n=$(basename "$f"); n=${n%.jsonl}
    [[ "$n" =~ ^[a-z0-9-]+$ ]] || { echo "ABORT: jsonl の名前は ^[a-z0-9-]+\$ のみ（\"$n\" は不可）"; exit 1; }
    [ -f "$f" ] || { echo "ABORT: $f が無い"; exit 1; }
  done
  # 止め(a): 本番の deploy が動いていない（start_fdm.sh:35）
  gh run list -R shingo-ops/salesanchor --workflow deploy.yml --limit 3 --json status -q '.[].status' | grep -qE 'in_progress|queued' && { echo "ABORT: deploy running"; exit 1; }
  # 止め(b): 本番の HEAD が origin/main と同じ（start_fdm.sh:53-56）
  [ "${#ORIGIN_MAIN}" = "40" ] || { echo "ABORT: 第3引数に origin/main の sha（40桁）を渡す"; exit 1; }
  HEAD_SHA=$(ssh $K "git -C /home/ubuntu/salesanchor rev-parse HEAD" | tr -d ' \r')
  case "$HEAD_SHA" in [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]*) ;; *) echo "ABORT: host HEAD not a sha"; exit 1;; esac
  [ "$HEAD_SHA" = "$ORIGIN_MAIN" ] || { echo "ABORT: 本番の HEAD が origin/main と違う"; exit 1; }
  # 止め(c): Mac 側の出力がもうあれば上書きしない
  mkdir -p "$OUT"
  [ ! -e "$OUT/snap_all.tsv" ] || { echo "ABORT: $OUT/snap_all.tsv がもうある（上書きしない）"; exit 1; }
  # VPS 側: 置き場を作り、既存の出力があれば上書きせず止まる
  ssh $K "mkdir -p $BASE && chmod 777 $BASE" || exit 1
  ssh $K "[ ! -e $BASE/snap_all.tsv ] && [ ! -e $BASE/convert.out ]" || { echo "ABORT: VPS の $BASE に snap_all.tsv か convert.out がもうある（上書きしない）"; exit 1; }
  NAMES=""
  for f in "$@"; do
    b=$(basename "$f")
    ssh $K "cat > $BASE/$b" < "$f" || { echo "ABORT: $b を置けない"; exit 1; }
    NAMES="$NAMES $b"
  done
  ssh $K "cat > $BASE/fhd_snapshot.py" < "$HERE/fhd_snapshot.py" || exit 1
  ssh $K "cat > $BASE/remote_convert.sh" <<'REMOTE' || exit 1
#!/bin/bash
# VPS のホストで動く。引数: jsonl のファイル名（BASE の中）
set -u
BASE=/home/ubuntu/fhd-test/llmcmp/convert
COMPOSE_DIR=/home/ubuntu/salesanchor
SVC=celery-worker
NAME=llmcmp-convert
cd "$COMPOSE_DIR" || { echo "ABORT: cd $COMPOSE_DIR"; exit 1; }
# 健康診断の上書き（常に成功）。本番の compose の一式に1本足す
printf 'services:\n  %s:\n    healthcheck:\n      test: ["CMD", "true"]\n' "$SVC" > "$BASE/no-health.yml"
CF=$(grep '^COMPOSE_FILE=' .env 2>/dev/null | tail -n 1 | cut -d= -f2- | tr -d "\"'")
if [ -z "$CF" ]; then CF=docker-compose.yml; [ -f docker-compose.override.yml ] && CF="$CF:docker-compose.override.yml"; fi
export COMPOSE_FILE="$CF:$BASE/no-health.yml"
echo "compose_files=$COMPOSE_FILE" > "$BASE/convert.composefiles"
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
# 起動前の止め④: 出力がもうあれば上書きせず止まる
for f in "$BASE/snap_all.tsv" "$BASE/convert.out"; do
  [ ! -e "$f" ] || { echo "ABORT: $f がもうある（上書きしない）"; exit 1; }
done
# 全 jsonl を1回の起動でまとめて渡す（同じ読み取り・同じマスタ。fhd_snapshot.py の convert は複数パスを取る）
ARGS=()
for b in "$@"; do ARGS+=("/fhd/llmcmp/$b"); done
# 起動後の止め: 120 秒以内に healthy にならなければ docker stop
(
  s=""
  for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
    s=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}NO_HEALTH{{end}}' "$NAME" 2>/dev/null)
    [ "$s" = healthy ] && break
    sleep 10
  done
  { echo "health=$s"; } > "$BASE/convert.health"
  if [ "$s" != healthy ]; then echo "HEALTH_ABORT" >> "$BASE/convert.health"; docker stop -t 10 "$NAME" >> "$BASE/convert.health" 2>&1; fi
) &
docker compose run --rm --no-deps -T --name "$NAME" -v "$BASE:/fhd/llmcmp" -e PYTHONPATH=/app -w /app "$SVC" \
  python /fhd/llmcmp/fhd_snapshot.py convert "${ARGS[@]}" > "$BASE/snap_all.tsv" 2> "$BASE/convert_stderr.txt"
echo "exit=$?" >> "$BASE/convert.out"
echo "LLMCMP_CONVERT_DONE" >> "$BASE/convert.out"
REMOTE
  # VPS 側で裏で動かす。終わりの確認: bash vps_convert.sh fetch <出力フォルダ>
  ssh $K "nohup bash $BASE/remote_convert.sh$NAMES > $BASE/convert.remote.log 2>&1 < /dev/null &"
  echo "起動した。終わったら: bash $0 fetch $OUT  （まだなら「まだ」と出る）"
  echo "起動前の止め（healthcheck・他の稼働・既存ファイル）で止まった理由は $BASE/convert.remote.log に残る: ssh $K \"cat $BASE/convert.remote.log\""
  echo "止めたいとき: ssh $K \"docker stop llmcmp-convert\""
  ;;
fetch)
  ssh $K "grep -q LLMCMP_CONVERT_DONE $BASE/convert.out" 2>/dev/null || { echo "まだ（$BASE/convert.out に LLMCMP_CONVERT_DONE が無い）"; exit 0; }
  mkdir -p "$OUT"
  for f in snap_all.tsv convert_stderr.txt convert.out; do
    ssh $K "cat $BASE/$f" > "$OUT/$f" || { echo "ABORT: $f を取り寄せられない"; exit 1; }
  done
  cat "$OUT/convert.out"
  grep -c '^SKIP' "$OUT/convert_stderr.txt"; grep -E '^CONVERT|^TX|ABORT' "$OUT/convert_stderr.txt"
  wc -l "$OUT/snap_all.tsv"
  # VPS の jsonl だけ消す（snap_all.tsv などは残す。BASE ごとは消さない）
  ssh $K "rm -f $BASE/*.jsonl"
  ;;
*) echo "ABORT: 第1引数は run か fetch（\"$CMD\" は不可）"; exit 1;;
esac
