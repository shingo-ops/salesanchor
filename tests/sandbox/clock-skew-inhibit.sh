#!/bin/bash
# outage-recovery-watch 便1: ClockSkew の警報と、その間の抑止（inhibit_rules）を GitHub の試験場で確かめる。
# 実行: gh workflow run sandbox-test.yml --ref (ブランチ名) -f test=clock-skew-inhibit
# secrets・本番には触れない。Alertmanager は外部通信なし（--network none）で起動し、疑似の警報だけを入れる。
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
OUT="$(mktemp -d)"
AM=prom/alertmanager:v0.28.1
PROM=prom/prometheus:v3.11.3
cleanup() {
  rc=$?
  if [ "$rc" -ne 0 ]; then
    docker logs bin1-am 2>&1 | tail -50 || true
  fi
  docker rm -f bin1-am >/dev/null 2>&1 || true
  exit "$rc"
}
trap cleanup EXIT

echo "== 試験用の偽の secrets（本物の値は使わない）"
mkdir -p "$OUT/secrets"
printf '%s' 'http://127.0.0.1:9/dummy' > "$OUT/secrets/discord-webhook"
printf '%s' 'dummy' > "$OUT/secrets/ops-ingest-token"
chmod -R a+rX "$OUT/secrets"

echo "== 段 0. 検査"
python3 monitoring/scripts/check_alert_rules.py
docker run --rm -v "$PWD/monitoring/prometheus:/p:ro" --entrypoint promtool "$PROM" check rules /p/alert_rules.yml
docker run --rm -v "$PWD/monitoring/prometheus:/p:ro" --entrypoint promtool "$PROM" test rules /p/tests/alert_rules_test.yml
docker run --rm -v "$PWD/monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro" -v "$OUT/secrets:/etc/alertmanager/secrets:ro" --entrypoint amtool "$AM" check-config /etc/alertmanager/alertmanager.yml
echo "OK: stage0"

echo "== 段 1. 壊すと落ちる（写しの ClockSkew の閾値を 60 から 6000 にする。リポジトリのファイルは書き換えない）"
cp -r monitoring/prometheus "$OUT/prom-broken"
sed -i 's/timestamp(node_time_seconds{job="node-exporter"})) > 60$/timestamp(node_time_seconds{job="node-exporter"})) > 6000/' "$OUT/prom-broken/alert_rules.yml"
n=$(grep -c 'node-exporter"})) > 6000$' "$OUT/prom-broken/alert_rules.yml" || true)
[ "$n" = 1 ] || { echo "NG: sed matched $n lines"; exit 1; }
set +e
docker run --rm -v "$OUT/prom-broken:/p:ro" --entrypoint promtool "$PROM" test rules /p/tests/alert_rules_test.yml
brc=$?
set -e
echo "broken rc=$brc"
[ "$brc" -ne 0 ] || { echo "NG: broken rule passed"; exit 1; }
echo "OK: stage1"

echo "== 段 2. Alertmanager を外部通信なしで起動"
docker run -d --name bin1-am --network none \
  -v "$PWD/monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro" \
  -v "$OUT/secrets:/etc/alertmanager/secrets:ro" \
  "$AM" --config.file=/etc/alertmanager/alertmanager.yml --cluster.listen-address= >/dev/null
ready=0
for i in $(seq 1 12); do
  if docker exec bin1-am wget -q -O- http://127.0.0.1:9093/-/ready >/dev/null 2>&1; then ready=1; break; fi
  sleep 5
done
[ "$ready" = 1 ] || { echo "NG: alertmanager not ready"; exit 1; }
echo "OK: stage2"

# alertname・state・inhibitedBy の件数を 3 列で出す
show() {
  docker exec bin1-am wget -q -O- http://127.0.0.1:9093/api/v2/alerts | python3 -c '
import json, sys
for a in sorted(json.load(sys.stdin), key=lambda x: x["labels"]["alertname"]):
    print(a["labels"]["alertname"], a["status"]["state"], len(a["status"]["inhibitedBy"]))
'
}
add() {
  docker exec bin1-am amtool --alertmanager.url=http://127.0.0.1:9093 alert add "$@"
}
# 期待の 3 列（改行区切り）に合うまで最大 12 回・5 秒おきに読み直す
wait_for() {
  expected="$1"
  last=""
  for i in $(seq 1 12); do
    last="$(show)"
    if [ "$last" = "$expected" ]; then echo "$last"; return 0; fi
    sleep 5
  done
  echo "$last"
  return 1
}

echo "== 段 3. ClockSkew なし"
add alertname=CeleryHeartbeatStale job=backend severity=critical
add alertname=ContainerStateStale instance=app-vps job=node-exporter severity=critical
add alertname=ServiceDown job=backend severity=critical
wait_for "CeleryHeartbeatStale active 0
ContainerStateStale active 0
ServiceDown active 0" || { echo "NG: stage3"; exit 1; }
echo "OK: stage3"

echo "== 段 4. ClockSkew あり"
add alertname=ClockSkew instance=app-vps job=node-exporter severity=critical
wait_for "CeleryHeartbeatStale suppressed 1
ClockSkew active 0
ContainerStateStale suppressed 1
ServiceDown active 0" || { echo "NG: stage4"; exit 1; }
echo "OK: stage4"

echo "OK: clock-skew-inhibit"
