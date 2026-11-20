#!/bin/bash
# ADR-1012 段階3 便G: 応急処置係（scripts/ops/first_aid.py）と見張りを GitHub の試験場で確かめる。
# 実行: gh workflow run sandbox-test.yml --ref (ブランチ名) -f test=first-aid
# 保守 API は tests/sandbox/first_aid_stub.py の代わりを使う。secrets・本番には触れない。後始末は trap で行う。
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
OUT="$(mktemp -d)"
PROM=prom/prometheus:v3.11.3
CD="$OUT/compose"
STUB=http://127.0.0.1:18080
TOKEN=sandbox-only-token-not-secret
STUB_PID=""
dc() { docker compose --project-directory "$CD" "$@"; }
cleanup() {
  rc=$?
  if [ "$rc" -ne 0 ]; then
    dc ps -a 2>&1 | head -20 || true
    tail -20 "$OUT/fa.err" 2>/dev/null || true
  fi
  dc down -t 1 >/dev/null 2>&1 || true
  [ -n "$STUB_PID" ] && kill "$STUB_PID" >/dev/null 2>&1 || true
  exit "$rc"
}
trap cleanup EXIT

field() { python3 -c 'import json,sys; v=json.load(sys.stdin).get(sys.argv[1]); print("" if v is None else v)' "$1"; }
new_inc() { curl -fsS -X POST -H 'Content-Type: application/json' -d "{\"service\":\"$1\",\"started_offset\":${2:-0}}" "$STUB/admin/incident" | field id; }
inc_field() { curl -fsS "$STUB/admin/incident/$1" | field "$2"; }
admin() { curl -fsS -X POST -H 'Content-Type: application/json' -d "{\"on\":$2}" "$STUB/admin/$1" >/dev/null; }
cid() { dc ps -q "$1"; }
health() { docker inspect -f '{{.State.Health.Status}}' "$(cid "$1")"; }
started() { docker inspect -f '{{.State.StartedAt}}' "$(cid "$1")"; }
wait_health() {
  for _ in $(seq 1 30); do
    [ "$(health "$1")" = "$2" ] && return 0
    sleep 1
  done
  echo "NG: $1 is not $2"
  return 1
}
fa() { python3 scripts/ops/first_aid.py 2>>"$OUT/fa.err"; }
ng() { echo "NG: $1"; exit 1; }

echo "== 1. 応急処置係の試験と見張りの検査"
python3 --version
python3 scripts/tests/test_first_aid.py
python3 monitoring/scripts/check_alert_rules.py
docker run --rm -v "$PWD/monitoring/prometheus:/p:ro" --entrypoint promtool "$PROM" check rules /p/alert_rules.yml
docker run --rm -v "$PWD/monitoring/prometheus:/p:ro" --entrypoint promtool "$PROM" test rules /p/tests/alert_rules_test.yml

echo "== 2. 代わりの保守 API と 4 つのコンテナを立てる"
python3 tests/sandbox/first_aid_stub.py 18080 "$TOKEN" >"$OUT/stub.log" 2>&1 &
STUB_PID=$!
for _ in $(seq 1 20); do curl -fsS "$STUB/admin/health" >/dev/null 2>&1 && break; sleep 0.5; done
curl -fsS "$STUB/admin/health" >/dev/null || ng "stub not up"
mkdir -p "$CD/flag" "$OUT/textfile"
cp tests/sandbox/first-aid-compose.yml "$CD/docker-compose.yml"
printf "COMPOSE_PROJECT_NAME=binfg\nOPS_API_TOKEN='%s'\n" "$TOKEN" >"$CD/.env"
dc up -d --wait
export FIRST_AID_API_BASE="$STUB/api/v1" FIRST_AID_ENV_FILE="$CD/.env" FIRST_AID_COMPOSE_DIR="$CD"
export FIRST_AID_TEXTFILE_DIR="$OUT/textfile" FIRST_AID_FRESH_SECONDS=0 FIRST_AID_HEALTHY_WAIT_SECONDS=60
export FIRST_AID_POLL_SECONDS=2 FIRST_AID_LIMIT_PER_HOUR=100

echo "== 3. 20 回：不健康にする → 係が再起動 → 5 分以内に recovered（19 回以上で合格）"
SERVICES=(celery-worker celery-beat discord-gateway gemini-egress)
ok=0
for i in $(seq 0 19); do
  s=${SERVICES[$((i % 4))]}
  dc exec -T "$s" touch /tmp/bad
  wait_health "$s" unhealthy
  id=$(new_inc "$s")
  t0=$(date +%s)
  fa || ng "rc at round $i"
  secs=$(( $(date +%s) - t0 ))
  r=$(inc_field "$id" first_aid_result)
  echo "round=$i service=$s result=$r secs=$secs"
  if [ "$r" = recovered ] && [ "$secs" -le 300 ] && [ "$(health "$s")" = healthy ]; then ok=$((ok + 1)); fi
done
echo "recovered=$ok/20"
[ "$ok" -ge 19 ] || ng "recovered $ok/20"

echo "== 4. 回数の上限：直近 1 時間に 5 回 → 再起動せず escalated"
before=$(started celery-worker)
id=$(new_inc celery-worker)
FIRST_AID_LIMIT_PER_HOUR=3 fa || ng "rc limit"
[ "$(inc_field "$id" first_aid_result)" = escalated ] || ng "limit result"
[ "$(started celery-worker)" = "$before" ] || ng "restarted over limit"
grep -qx 'salesanchor_first_aid_escalated_timestamp_seconds{service="celery-worker"} [0-9]*' "$OUT/textfile/first_aid_escalated.prom" || ng "escalated line celery-worker"

echo "== 5. 止める札：処置 0 件 → 札を外すと処置する"
admin halt true
dc exec -T celery-beat touch /tmp/bad
wait_health celery-beat unhealthy
before=$(started celery-beat)
id=$(new_inc celery-beat)
fa || ng "rc halt"
[ "$(started celery-beat)" = "$before" ] || ng "restarted while halted"
[ -z "$(inc_field "$id" first_aid_started_at)" ] || ng "annotated while halted"
grep -qx 'salesanchor_first_aid_halted 1' "$OUT/textfile/first_aid_run.prom" || ng "halted line"
admin halt false
fa || ng "rc after halt"
[ "$(inc_field "$id" first_aid_result)" = recovered ] || ng "not recovered after halt"
grep -qx 'salesanchor_first_aid_halted 0' "$OUT/textfile/first_aid_run.prom" || ng "halted 0 line"

echo "== 6. 保守 API が 500：rc=1・再起動しない・印を書かない"
admin fail true
dc exec -T discord-gateway touch /tmp/bad
wait_health discord-gateway unhealthy
before=$(started discord-gateway)
id=$(new_inc discord-gateway)
run_before=$(sha256sum "$OUT/textfile/first_aid_run.prom")
set +e
fa
rc=$?
set -e
echo "rc=$rc"
[ "$rc" -eq 1 ] || ng "rc on 500"
[ "$(started discord-gateway)" = "$before" ] || ng "restarted on 500"
[ "$(sha256sum "$OUT/textfile/first_aid_run.prom")" = "$run_before" ] || ng "run prom changed on 500"
admin fail false
fa || ng "rc after fail"
[ "$(inc_field "$id" first_aid_result)" = recovered ] || ng "not recovered after fail"

echo "== 7. 再起動しても直らない：not_recovered → escalated の行"
touch "$CD/flag/stuck-gemini-egress"
wait_health gemini-egress unhealthy
id=$(new_inc gemini-egress)
FIRST_AID_HEALTHY_WAIT_SECONDS=10 fa || ng "rc stuck"
[ "$(inc_field "$id" first_aid_result)" = not_recovered ] || ng "stuck result"
grep -qx 'salesanchor_first_aid_escalated_timestamp_seconds{service="gemini-egress"} [0-9]*' "$OUT/textfile/first_aid_escalated.prom" || ng "escalated line gemini-egress"
grep -qx 'salesanchor_first_aid_escalated_timestamp_seconds{service="celery-worker"} [0-9]*' "$OUT/textfile/first_aid_escalated.prom" || ng "escalated merge lost celery-worker"
rm -f "$CD/flag/stuck-gemini-egress"

echo "== 8. 途中で止まった処置：11 分前に始めて終わりが無い → escalated・5 分前のものはそのまま"
old=$(new_inc celery-beat 660)
young=$(new_inc celery-beat 300)
fa || ng "rc stale"
[ "$(inc_field "$old" first_aid_result)" = escalated ] || ng "stale not escalated"
[ -z "$(inc_field "$young" first_aid_done_at)" ] || ng "young touched"

echo "== 9. 書いたファイルの形・鍵が出ていないこと"
cat "$OUT/textfile/first_aid_run.prom" "$OUT/textfile/first_aid_escalated.prom"
for f in first_aid_run.prom first_aid_escalated.prom; do
  docker run --rm -i --entrypoint promtool "$PROM" check metrics <"$OUT/textfile/$f"
  [ "$(stat -c %a "$OUT/textfile/$f")" = 644 ] || ng "mode $f"
done
if ls -A "$OUT/textfile" | grep -q '^\.first_aid\.'; then ng "temp left"; fi
wc -l "$OUT/fa.err"
if grep -qF "$TOKEN" "$OUT/fa.err"; then ng "token in stderr"; fi
echo "ALL OK"
