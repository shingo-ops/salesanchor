#!/bin/bash
# ADR-1012 段階3 便E: 状態書き係（scripts/ops/container_state.py）と見張り 2 本を GitHub の試験場で確かめる。
# 実行: gh workflow run sandbox-test.yml --ref (ブランチ名) -f test=container-state
# secrets・本番には触れない。後始末は trap で行う。
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
OUT="$(mktemp -d)"
PROM=prom/prometheus:v3.11.3
cleanup() {
  rc=$?
  if [ "$rc" -ne 0 ]; then
    docker inspect -f '{{.Name}} {{.State.Running}} {{json .State.Health}}' bine-worker bine-beat bine-beat-old 2>&1 | head -c 3000 || true
  fi
  docker rm -f bine-worker bine-beat bine-beat-old >/dev/null 2>&1 || true
  exit "$rc"
}
trap cleanup EXIT

echo "== 1. 状態書き係の試験"
python3 --version
python3 scripts/tests/test_container_state.py

echo "== 2. 見張りの検査"
python3 monitoring/scripts/check_alert_rules.py
docker run --rm -v "$PWD/monitoring/prometheus:/p:ro" --entrypoint promtool "$PROM" check rules /p/alert_rules.yml
docker run --rm -v "$PWD/monitoring/prometheus:/p:ro" --entrypoint promtool "$PROM" test rules /p/tests/alert_rules_test.yml

echo "== 3. 本物の docker で状態を書く（健康・不健康・止まった古いもの・無いもの）"
docker run -d --name bine-worker --label com.docker.compose.service=celery-worker --health-cmd true --health-interval 2s alpine:3.24 sleep 600 >/dev/null
docker run -d --name bine-beat --label com.docker.compose.service=celery-beat --health-cmd false --health-interval 2s --health-retries 1 alpine:3.24 sleep 600 >/dev/null
docker run --name bine-beat-old --label com.docker.compose.service=celery-beat alpine:3.24 true
for i in $(seq 1 15); do
  w=$(docker inspect -f '{{.State.Health.Status}}' bine-worker)
  b=$(docker inspect -f '{{.State.Health.Status}}' bine-beat)
  if [ "$w" = healthy ] && [ "$b" = unhealthy ]; then break; fi
  sleep 2
done
docker inspect -f '{{.Name}} {{.State.Running}} {{.State.Health.Status}}' bine-worker bine-beat
docker inspect -f '{{.Name}} {{.State.Running}}' bine-beat-old
TF="$OUT/textfile"
mkdir -p "$TF"
time CONTAINER_STATE_TEXTFILE_DIR="$TF" python3 scripts/ops/container_state.py
cat "$TF/container_state.prom"
expect() { grep -qxF "$1" "$TF/container_state.prom" || { echo "NG: missing line: $1"; exit 1; }; }
expect 'salesanchor_container_unhealthy{service="celery-worker"} 0'
expect 'salesanchor_container_running{service="celery-worker"} 1'
expect 'salesanchor_container_unhealthy{service="celery-beat"} 1'
expect 'salesanchor_container_running{service="celery-beat"} 1'
for s in discord-gateway gemini-egress backend; do
  expect "salesanchor_container_unhealthy{service=\"$s\"} 0"
  expect "salesanchor_container_running{service=\"$s\"} 0"
done
[ "$(grep -c '^salesanchor_container_state_last_run_timestamp_seconds ' "$TF/container_state.prom")" = 1 ] || { echo "NG: timestamp line"; exit 1; }
[ "$(stat -c %a "$TF/container_state.prom")" = 644 ] || { echo "NG: mode"; exit 1; }
docker run --rm -i --entrypoint promtool "$PROM" check metrics < "$TF/container_state.prom"

echo "== 4. 失敗の試験（docker に繋がらない → rc=1・ファイルは変わらない・一時ファイルが残らない）"
before=$(sha256sum "$TF/container_state.prom")
set +e
DOCKER_HOST=unix:///nonexistent.sock CONTAINER_STATE_TEXTFILE_DIR="$TF" python3 scripts/ops/container_state.py
rc=$?
set -e
echo "rc=$rc"
[ "$rc" -eq 1 ] || { echo "NG: rc"; exit 1; }
[ "$(sha256sum "$TF/container_state.prom")" = "$before" ] || { echo "NG: file changed"; exit 1; }
ls -a "$TF"
if ls -A "$TF" | grep -q '^\.container_state\.'; then echo "NG: temp left"; exit 1; fi
echo "ALL OK"
