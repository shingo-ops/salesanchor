#!/bin/bash
# 状態の語を足す前後の試し（6 回）を本番の写しの上で順に流す（design.md §2, §8）。
# 読み取りのみ（replay_words.py は READ ONLY 設定・1 投稿ごとに rollback）。PO が ! で実行する台本。AI は実行しない。
# 使い方: bash vps_replay.sh run   <出力フォルダ(Mac)> <origin/main の40桁sha> <posts.txt>
#         bash vps_replay.sh fetch <出力フォルダ(Mac)>
#   第3引数 = Mac で git ls-remote origin refs/heads/main した sha（本番の HEAD と照らす）。
#   6 回: base1(なし) base2(なし) A(シュリあり) B(シュリンク有り・シュリンク有) C(有〆・有り〆) ALL(5つ全部)。足す先は CN0003。
#   run は VPS 側で裏で動く。終わったら fetch で取り寄せる（まだなら「まだ」と出て終わる）。
# 別の箱: docker compose run --rm --no-deps（本番 worker とは別コンテナ）。-e PYTHONPATH=/app が必須（vps_convert.sh と同じ理由）。
# 健康診断の上書き（no-health.yml）を必ず付ける: 付けないと約2.5分で unhealthy になり本番の警報が鳴る。
set -u
CMD=${1:?run か fetch}; shift
OUT=${1:?出力フォルダ}; shift
HERE=$(cd "$(dirname "$0")" && pwd)
K="-i $HOME/.ssh/manual-only/id_ed25519 ubuntu@49.212.137.46"
BASE=/home/ubuntu/fhd-test/condwords
case "$CMD" in
run)
  ORIGIN_MAIN=${1:?origin/main の40桁sha}; shift
  POSTS=${1:?posts.txt}; shift
  [ -f "$POSTS" ] || { echo "ABORT: $POSTS が無い"; exit 1; }
  # 止め(a): 本番の deploy が動いていない
  gh run list -R shingo-ops/salesanchor --workflow deploy.yml --limit 3 --json status -q '.[].status' | grep -qE 'in_progress|queued' && { echo "ABORT: deploy running"; exit 1; }
  # 止め(b): 本番の HEAD が origin/main と同じ
  [ "${#ORIGIN_MAIN}" = "40" ] || { echo "ABORT: 第3引数に origin/main の sha（40桁）を渡す"; exit 1; }
  HEAD_SHA=$(ssh $K "git -C /home/ubuntu/salesanchor rev-parse HEAD" | tr -d ' \r')
  case "$HEAD_SHA" in [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]*) ;; *) echo "ABORT: host HEAD not a sha"; exit 1;; esac
  [ "$HEAD_SHA" = "$ORIGIN_MAIN" ] || { echo "ABORT: 本番の HEAD が origin/main と違う"; exit 1; }
  # 止め(c): Mac 側の出力がもうあれば上書きしない
  mkdir -p "$OUT"
  [ ! -e "$OUT/run.out" ] || { echo "ABORT: $OUT/run.out がもうある（上書きしない）"; exit 1; }
  # VPS 側: 置き場を作り、既存の出力があれば上書きせず止まる
  ssh $K "mkdir -p $BASE && chmod 777 $BASE" || exit 1
  ssh $K "[ ! -e $BASE/run.out ] && [ -z \"\$(ls $BASE/*.jsonl 2>/dev/null)\" ]" || { echo "ABORT: VPS の $BASE に run.out か jsonl がもうある（上書きしない）"; exit 1; }
  ssh $K "cat > $BASE/posts.txt" < "$POSTS" || { echo "ABORT: posts.txt を置けない"; exit 1; }
  ssh $K "cat > $BASE/replay_words.py" < "$HERE/replay_words.py" || exit 1
  ssh $K "cat > $BASE/remote_replay.sh" <<'REMOTE' || exit 1
#!/bin/bash
# VPS のホストで動く。6 回を順に流す。
set -u
BASE=/home/ubuntu/fhd-test/condwords
COMPOSE_DIR=/home/ubuntu/salesanchor
SVC=celery-worker
NAME=condwords-replay
cd "$COMPOSE_DIR" || { echo "ABORT: cd $COMPOSE_DIR"; exit 1; }
# 健康診断の上書き（常に成功）。本番の compose の一式に1本足す
printf 'services:\n  %s:\n    healthcheck:\n      test: ["CMD", "true"]\n' "$SVC" > "$BASE/no-health.yml"
CF=$(grep '^COMPOSE_FILE=' .env 2>/dev/null | tail -n 1 | cut -d= -f2- | tr -d "\"'")
if [ -z "$CF" ]; then CF=docker-compose.yml; [ -f docker-compose.override.yml ] && CF="$CF:docker-compose.override.yml"; fi
export COMPOSE_FILE="$CF:$BASE/no-health.yml"
# 起動前の止め①: 組み合わせた一式の healthcheck が ["CMD","true"] と完全一致でなければ ABORT
HCT=$(docker compose config --format json | python3 -I -B -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["services"]["celery-worker"]["healthcheck"]["test"]))') \
  || { echo "ABORT: compose config を読めない"; exit 1; }
[ "$HCT" = '["CMD", "true"]' ] || [ "$HCT" = '["CMD","true"]' ] || { echo "ABORT: celery-worker の healthcheck.test が CMD true になっていない"; exit 1; }
# 起動前の止め②: 別コンテナで true が実行できること
docker compose run --rm --no-deps -T "$SVC" sh -c 'test -x /bin/true || test -x /usr/bin/true' \
  || { echo "ABORT: 別コンテナに true が無い"; exit 1; }
# 起動前の止め③: 他の prompt_ab／試験コンテナが動いていない
n=$(pgrep -fc '[a]pp.tools.prompt_ab|[c]apture_prompt_ab' ; docker ps -q --filter name=fhd- | wc -l; docker ps -q --filter name=llmcmp- | wc -l; docker ps -q --filter name=condwords- | wc -l) || true
n=$(printf '%s\n' "$n" | awk '{s+=$1} END{print s+0}')
case "$n" in ''|*[!0-9]*) echo "ABORT: 動いている数を読めない"; exit 1;; esac
[ "$n" = "0" ] || { echo "ABORT: 他の prompt_ab／試験が動いている ($n)"; exit 1; }
# 起動前の止め④: 出力がもうあれば上書きせず止まる
[ ! -e "$BASE/run.out" ] || { echo "ABORT: $BASE/run.out がもうある（上書きしない）"; exit 1; }

run_one() {  # run_one <tag> [--add ...]
  tag=$1; shift
  # 起動後の止め: 120 秒以内に healthy にならなければ docker stop
  (
    s=""
    for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
      s=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}NO_HEALTH{{end}}' "$NAME" 2>/dev/null)
      [ "$s" = healthy ] && break
      sleep 10
    done
    echo "health=$s" > "$BASE/$tag.health"
    if [ "$s" != healthy ]; then echo "HEALTH_ABORT" >> "$BASE/$tag.health"; docker stop -t 10 "$NAME" >> "$BASE/$tag.health" 2>&1; fi
  ) &
  docker compose run --rm --no-deps -T --name "$NAME" -v "$BASE:/fhd/condwords" -e PYTHONPATH=/app -w /app "$SVC" \
    python /fhd/condwords/replay_words.py --posts /fhd/condwords/posts.txt --out "/fhd/condwords/$tag.jsonl" "$@" \
    > "$BASE/$tag.stdout" 2> "$BASE/$tag.stderr"
  rc=$?
  echo "$tag exit=$rc" >> "$BASE/run.out"
  return $rc
}

run_one base1 || { echo "STOPPED at base1" >> "$BASE/run.out"; echo "CONDWORDS_DONE" >> "$BASE/run.out"; exit 1; }
run_one base2 || { echo "STOPPED at base2" >> "$BASE/run.out"; echo "CONDWORDS_DONE" >> "$BASE/run.out"; exit 1; }
run_one A --add "CN0003=シュリあり" || { echo "STOPPED at A" >> "$BASE/run.out"; echo "CONDWORDS_DONE" >> "$BASE/run.out"; exit 1; }
run_one B --add "CN0003=シュリンク有り,シュリンク有" || { echo "STOPPED at B" >> "$BASE/run.out"; echo "CONDWORDS_DONE" >> "$BASE/run.out"; exit 1; }
run_one C --add "CN0003=有〆,有り〆" || { echo "STOPPED at C" >> "$BASE/run.out"; echo "CONDWORDS_DONE" >> "$BASE/run.out"; exit 1; }
run_one ALL --add "CN0003=シュリあり,シュリンク有り,シュリンク有,有〆,有り〆" || { echo "STOPPED at ALL" >> "$BASE/run.out"; echo "CONDWORDS_DONE" >> "$BASE/run.out"; exit 1; }
echo "CONDWORDS_DONE" >> "$BASE/run.out"
REMOTE
  # VPS 側で裏で動かす。終わりの確認: bash vps_replay.sh fetch <出力フォルダ>
  ssh $K "nohup bash $BASE/remote_replay.sh > $BASE/remote.log 2>&1 < /dev/null &"
  echo "起動した。終わったら: bash $0 fetch $OUT  （まだなら「まだ」と出る）"
  echo "起動前の止め（healthcheck・他の稼働・既存ファイル）で止まった理由は $BASE/remote.log に残る: ssh $K \"cat $BASE/remote.log\""
  echo "止めたいとき: ssh $K \"docker stop condwords-replay\""
  ;;
fetch)
  ssh $K "grep -q CONDWORDS_DONE $BASE/run.out" 2>/dev/null || { echo "まだ（$BASE/run.out に CONDWORDS_DONE が無い）"; exit 0; }
  mkdir -p "$OUT"
  for t in base1 base2 A B C ALL; do
    for ext in jsonl stdout stderr; do
      ssh $K "cat $BASE/$t.$ext" > "$OUT/$t.$ext" 2>/dev/null || echo "（$t.$ext は無い）"
    done
  done
  ssh $K "cat $BASE/run.out" > "$OUT/run.out" || { echo "ABORT: run.out を取り寄せられない"; exit 1; }
  cat "$OUT/run.out"
  wc -l "$OUT"/*.jsonl
  # VPS の jsonl だけ消す（stdout・stderr などは残す。BASE ごとは消さない）
  ssh $K "rm -f $BASE/*.jsonl"
  ;;
*) echo "ABORT: 第1引数は run か fetch（\"$CMD\" は不可）"; exit 1;;
esac
