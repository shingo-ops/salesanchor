#!/usr/bin/env bash
# K1〜K3 の基準値と事後値を同じ方法で取る（読み取りのみ）。設計: design-pool-reset.md §6
# 使い方: bash docs/handoff/s1-rls-stage5/k-baseline.sh > <出力ファイル>
# - K1: https://api.salesanchor.jp/api/health を 60 回（1 秒おき）。状態コードと秒数。
# - K2/K3: 4 コンテナの docker logs（コンテナ起動から今まで）を 6 種の文字列で数え、1 時間あたりに直す。
# 本番で書き込む操作は無い（docker logs / docker inspect / curl の GET だけ）。
set -u

KEY="${HOME}/.ssh/manual-only/id_ed25519"
HOST="ubuntu@49.212.137.46"

echo "taken_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "## K1 health"
tmp=$(mktemp)
i=0
while test "$i" -lt 60; do
  curl -s -o /dev/null -w '%{http_code} %{time_total}\n' https://api.salesanchor.jp/api/health | tee -a "$tmp"
  i=$((i + 1))
  sleep 1
done
# 200 の回数・中央値・p95（ms）。p95 は 60 件を小さい順に並べた 57 番目
awk '$1 == 200 {n++} END {print "k1_ok200=" n+0 " k1_total=" NR}' "$tmp"
awk '{print $2 * 1000}' "$tmp" | sort -n | awk '{v[NR]=$1} END {printf "k1_median_ms=%.1f k1_p95_ms=%.1f\n", (v[30]+v[31])/2, v[57]}'
rm -f "$tmp"

echo "## K2/K3 logs"
ssh -F /dev/null -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes "$HOST" 'bash -s' <<'REMOTE'
set -u
now=$(date -u +%s)
for c in astro-webapp-backend-1 astro-webapp-celery-worker-1 astro-webapp-discord-gateway-1 astro-webapp-celery-beat-1; do
  start=$(docker inspect -f '{{.State.StartedAt}}' "$c")
  start_s=$(date -u -d "$start" +%s)
  hours=$(awk -v a="$now" -v b="$start_s" 'BEGIN{printf "%.3f", (a-b)/3600}')
  log=$(docker logs "$c" 2>&1)
  lines=$(printf '%s\n' "$log" | wc -l)
  out="c=$c start=$start hours=$hours lines=$lines"
  for pat in \
    'relnotexist|does not exist' \
    'rls|row-level security' \
    'invalid_int|invalid input syntax for type integer' \
    's500|" 500 ' \
    'traceback|Traceback (most recent call last)' \
    'reset_exc|Exception during reset' \
    'close_exc|Exception closing connection'; do
    name=${pat%%|*}
    needle=${pat#*|}
    n=$(printf '%s\n' "$log" | grep -c -F -- "$needle")
    rate=$(awk -v n="$n" -v h="$hours" 'BEGIN{ if (h > 0) printf "%.3f", n/h; else print "na" }')
    out="$out $name=$n ${name}_per_h=$rate"
  done
  echo "$out"
done
REMOTE
echo "rc_ssh=$?"
