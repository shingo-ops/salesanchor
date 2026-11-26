#!/usr/bin/env bash
# 05-daily-read.sh — 段取り 7（読むだけ。設計担当 Opus が毎日 1 回流す）
# 正の設計: server-agent-design.md §12-2 G6・§12-3 段取り 7・§12-4。
# この台本は読む命令だけ。書き込み・止める・起動し直すの命令は 1 つも入れない（書き出しの記号も使わない）。
# 基準の値は card-trial-install.md §0（2026-11-25 15:18Z に測った値）。

set -uo pipefail

BASE_AVAIL_MB=2579
MIN_AVAIL_MB=500
BASE_LOKI=13
BASE_GHA=160

echo "== 時刻 =="
date -u

echo "== メモリ（G6: 500MB 以上なら OK。担当が動く分は減るので基準との差では見ない）=="
free -m
avail="$(free -m | awk '/^Mem:/ {print $7}')"
echo "available: ${avail} MB（基準 ${BASE_AVAIL_MB} MB・差 $((avail - BASE_AVAIL_MB)) MB・下限 ${MIN_AVAIL_MB} MB）"
if [ "${avail}" -ge "${MIN_AVAIL_MB}" ]; then
  echo "判定: OK"
else
  echo "判定: NG（500MB を切った。すぐ止める条件。PO へ報告）"
fi

echo "== 監視のコンテナ: RestartCount と OOMKilled（基準との差 0 なら OK）=="
printf '%-48s %6s %6s %6s %s\n' "名前" "基準" "今" "差" "OOMKilled"
for id in $(docker ps -aq); do
  line="$(docker inspect -f '{{.Name}} {{.RestartCount}} {{.State.OOMKilled}}' "${id}")"
  name="$(echo "${line}" | awk '{print $1}')"
  name="${name#/}"
  now="$(echo "${line}" | awk '{print $2}')"
  oom="$(echo "${line}" | awk '{print $3}')"
  base=0
  case "${name}" in
    salesanchor-monitoring-loki-1) base="${BASE_LOKI}" ;;
    salesanchor-monitoring-gha-exporter-1) base="${BASE_GHA}" ;;
  esac
  diff=$((now - base))
  flag=""
  if [ "${diff}" -ne 0 ] || [ "${oom}" != "false" ]; then
    flag="  ← 要確認（差が 0 でない／OOMKilled が false でない）"
  fi
  printf '%-48s %6s %6s %6s %s%s\n' "${name}" "${base}" "${now}" "${diff}" "${oom}" "${flag}"
done

echo "== 担当 ops-agent =="
printf 'is-active: '
systemctl is-active ops-agent.service || true
printf 'NRestarts: '
systemctl show -p NRestarts --value ops-agent.service || true
printf 'tmux の部屋: '; if sudo -u ops-agent tmux -S /home/ops-agent/.tmux/ops-agent.sock has-session -t ops-agent 2>/dev/null; then echo ある; else echo "無い  ← 要確認"; fi

printf 'memory.peak（バイト。上限 MemoryMax=1500M=1572864000 バイト）: '
cat /sys/fs/cgroup/system.slice/ops-agent.service/memory.peak || echo "未取得（ファイルが無い。カーネルが対応していない可能性・未確認）"

echo "== 過去 24 時間の記録のうち、メモリの上限・OOM に当たる行の数（0 が合格）=="
oom_lines="$(journalctl -u ops-agent.service --since="-24h" --no-pager | grep -ciE 'memory\.high|memory\.max|memory high|memory max|out of memory|oom-kill|oom_kill|Failed with result .oom' || true)"
echo "行数: ${oom_lines}"
