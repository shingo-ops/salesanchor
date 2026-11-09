#!/bin/bash
# build-on-github 便0: dockerd の値を書く係（scripts/ops/dockerd_state.py）と見張り 2 本・台本の入口を GitHub の試験場で確かめる。
# 実行: gh workflow run sandbox-test.yml --ref (ブランチ名) -f test=dockerd-state
# secrets・本番には触れない。
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
OUT="$(mktemp -d)"
PROM=prom/prometheus:v3.11.3

echo "== 1. 係の試験"
python3 --version
python3 scripts/tests/test_dockerd_state.py

echo "== 2. 見張りの検査"
python3 monitoring/scripts/check_alert_rules.py
docker run --rm -v "$PWD/monitoring/prometheus:/p:ro" --entrypoint promtool "$PROM" check rules /p/alert_rules.yml
docker run --rm -v "$PWD/monitoring/prometheus:/p:ro" --entrypoint promtool "$PROM" test rules /p/tests/alert_rules_test.yml

echo "== 3. 本物の dockerd で書く"
ls -l /run/docker.pid
pid="$(cat /run/docker.pid)"
grep -E '^(Name|VmRSS|VmSwap|Threads):' "/proc/$pid/status"
TF="$OUT/textfile"
mkdir -p "$TF"
time DOCKERD_STATE_TEXTFILE_DIR="$TF" python3 scripts/ops/dockerd_state.py
cat "$TF/dockerd_state.prom"
val() { grep -E "^$1 " "$TF/dockerd_state.prom" | awk '{print $2}'; }
rss="$(val salesanchor_dockerd_rss_bytes)"
thr="$(val salesanchor_dockerd_threads)"
start="$(val salesanchor_dockerd_start_time_seconds)"
[ "$rss" -gt 0 ] || { echo "NG: rss"; exit 1; }
[ "$thr" -gt 0 ] || { echo "NG: threads"; exit 1; }
[ "$start" = "$(stat -c %Y /run/docker.pid)" ] || { echo "NG: start time"; exit 1; }
for m in salesanchor_dockerd_rss_bytes salesanchor_dockerd_vmswap_bytes salesanchor_dockerd_threads salesanchor_dockerd_start_time_seconds salesanchor_dockerd_state_last_run_timestamp_seconds; do
  [ "$(grep -c "^$m " "$TF/dockerd_state.prom")" = 1 ] || { echo "NG: line $m"; exit 1; }
done
[ "$(stat -c %a "$TF/dockerd_state.prom")" = 644 ] || { echo "NG: mode"; exit 1; }
docker run --rm -i --entrypoint promtool "$PROM" check metrics < "$TF/dockerd_state.prom"

echo "== 4. 失敗の試験（pid ファイルが無い・dockerd でない → rc=1・ファイルは変わらない・一時ファイルが残らない）"
before="$(sha256sum "$TF/dockerd_state.prom")"
set +e
DOCKERD_STATE_PID_FILE=/nonexistent.pid DOCKERD_STATE_TEXTFILE_DIR="$TF" python3 scripts/ops/dockerd_state.py
rc1=$?
echo "$$" > "$OUT/not-dockerd.pid"
DOCKERD_STATE_PID_FILE="$OUT/not-dockerd.pid" DOCKERD_STATE_TEXTFILE_DIR="$TF" python3 scripts/ops/dockerd_state.py
rc2=$?
set -e
echo "rc1=$rc1 rc2=$rc2"
[ "$rc1" -eq 1 ] && [ "$rc2" -eq 1 ] || { echo "NG: rc"; exit 1; }
[ "$(sha256sum "$TF/dockerd_state.prom")" = "$before" ] || { echo "NG: file changed"; exit 1; }
ls -a "$TF"
if ls -A "$TF" | grep -q '^\.dockerd_state\.'; then echo "NG: temp left"; exit 1; fi

echo "== 5. 台本の入口（外の操作の前に止まること。gh・ssh は呼ばれない）"
bash -n scripts/ops/dockerd-restart-window.sh
set +e
bash scripts/ops/dockerd-restart-window.sh bogus; r1=$?
DOCKERD_WINDOW_NOW_HHMM=0900 bash scripts/ops/dockerd-restart-window.sh restart; r2=$?
DOCKERD_WINDOW_NOW_HHMM=1545 bash scripts/ops/dockerd-restart-window.sh live-restore; r3=$?
DOCKERD_WINDOW_NOW_HHMM=1359 bash scripts/ops/dockerd-restart-window.sh restart; r4=$?
DOCKERD_WINDOW_NOW_HHMM=ab12 bash scripts/ops/dockerd-restart-window.sh restart; r5=$?
set -e
echo "r1=$r1 r2=$r2 r3=$r3 r4=$r4 r5=$r5"
[ "$r1" -eq 2 ] && [ "$r2" -eq 3 ] && [ "$r3" -eq 3 ] && [ "$r4" -eq 3 ] && [ "$r5" -eq 3 ] || { echo "NG: entry"; exit 1; }
if command -v shellcheck >/dev/null; then shellcheck -S warning scripts/ops/dockerd-restart-window.sh tests/sandbox/dockerd-state.sh; else echo "shellcheck なし（スキップ）"; fi
echo "ALL OK"
