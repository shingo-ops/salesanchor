#!/bin/bash
# build-on-github 便0（design.md §10-1・§24-4）: docker の土台（dockerd）を計画して入れ直す台本。
# PO が Mac の「ターミナル」で流す。prod1 には ssh prod1 で入る。
#   bash scripts/ops/dockerd-restart-window.sh live-restore … live-restore を入れる（箱は止まらない・管理者パスワードを 1 回聞かれる）
#   bash scripts/ops/dockerd-restart-window.sh restart      … dockerd を入れ直す（live-restore が有効なときだけ）
# どちらも: 日本時間 14:00〜15:44 だけ受け付ける／入れ替え（deploy.yml）が動いていれば止まる／
#           入れ替えを止め、終わりに必ず戻す（途中で止まっても戻す）／前後の値を出す／記録を Mac に残す。
# 戻し方: live-restore は prod1 で sudo rm /etc/docker/daemon.json → sudo systemctl reload docker。
set -euo pipefail

MODE="${1:-}"
REPO=shingo-ops/salesanchor
HOST=prod1
HEALTH_URL=https://api.salesanchor.jp/api/health
LOG_DIR="${DOCKERD_WINDOW_LOG_DIR:-$HOME/CC報告ファイル-keep/dockerd-restart-window}"

case "$MODE" in
  live-restore|restart) ;;
  *) echo "使い方: bash $0 live-restore|restart"; exit 2 ;;
esac

# 時間帯の確かめ（試験のときだけ DOCKERD_WINDOW_NOW_HHMM で時刻を与えられる）
now_hhmm="${DOCKERD_WINDOW_NOW_HHMM:-$(TZ=Asia/Tokyo date +%H%M)}"
case "$now_hhmm" in
  [0-9][0-9][0-9][0-9]) ;;
  *) echo "止めました: 時刻を読めません（$now_hhmm）"; exit 3 ;;
esac
now_num=$((10#$now_hhmm))
if [ "$now_num" -lt 1400 ] || [ "$now_num" -ge 1545 ]; then
  echo "止めました: 日本時間 14:00〜15:44 にだけ始められます（今 ${now_hhmm:0:2}:${now_hhmm:2:2}）"
  exit 3
fi

mkdir -p "$LOG_DIR"
STAMP="$(TZ=Asia/Tokyo date +%Y%m%d-%H%M%S)"
LOG="$LOG_DIR/$MODE-$STAMP.txt"
exec > >(tee -a "$LOG") 2>&1

DISABLED=0
HEALTH_PID=""
restore() {
  rc=$?
  set +e
  if [ -n "$HEALTH_PID" ]; then kill "$HEALTH_PID" 2>/dev/null; fi
  if [ "$DISABLED" = 1 ]; then
    gh workflow enable deploy.yml -R "$REPO"
    state="$(gh api "repos/$REPO/actions/workflows/deploy.yml" --jq .state)"
    echo "入れ替え（deploy.yml）の状態: $state"
    if [ "$state" != active ]; then
      echo "!! 入れ替えが戻っていません。Opus に知らせてください"
      rc=9
    fi
  fi
  echo "記録: $LOG"
  exit "$rc"
}
trap restore EXIT
trap 'exit 130' INT TERM HUP

HEALTH_LOG="$LOG_DIR/health-$STAMP.txt"
start_health() {
  (
    while :; do
      code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$HEALTH_URL" || true)"
      echo "$(date +%s) $code"
      sleep 2
    done
  ) > "$HEALTH_LOG" &
  HEALTH_PID=$!
  sleep 10
}
stop_health() {
  sleep 20
  kill "$HEALTH_PID" 2>/dev/null || true
  HEALTH_PID=""
  awk '$2!="200"{if(s==""){s=$1}; e=$1; n++} $2=="200"{if(s!=""){d=e-s+2; if(d>m){m=d}; s=""}} END{if(s!=""){d=e-s+2; if(d>m){m=d}}; printf "健康確認: %d 回のうち 200 以外 %d 回・最長の途切れ 約 %d 秒（記録 %s）\n", NR, n, m, FILENAME}' "$HEALTH_LOG"
}

busy_runs() {
  gh run list -R "$REPO" --workflow deploy.yml --limit 20 --json status \
    --jq '[.[] | select(.status != "completed")] | length'
}

snapshot() {
  echo "== $1 $(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S') JST"
  ssh "$HOST" 'pid=$(cat /run/docker.pid); grep -E "^(VmRSS|VmSwap|Threads):" "/proc/$pid/status"; echo "LiveRestore=$(docker info --format "{{.LiveRestoreEnabled}}")"; echo "running=$(docker ps -q | wc -l | tr -d " ")"; free -m'
}

echo "== 台本 $MODE を始めます"
busy="$(busy_runs)"
if [ "$busy" != 0 ]; then
  echo "止めました: 入れ替えが $busy 件動いています。終わってから流し直してください"
  exit 4
fi
gh workflow disable deploy.yml -R "$REPO"
DISABLED=1
busy="$(busy_runs)"
if [ "$busy" != 0 ]; then
  echo "止めました: 止める間に入れ替えが $busy 件始まりました"
  exit 4
fi
echo "入れ替えを止めました（終わりに戻します）"

snapshot "前"

if [ "$MODE" = live-restore ]; then
  before_running="$(ssh "$HOST" 'docker ps -q | wc -l' | tr -d ' ')"
  start_health
  ssh -t "$HOST" 'set -e
if test -e /etc/docker/daemon.json; then echo "止めました: /etc/docker/daemon.json が既にあります（中身を変えないため）"; exit 5; fi
tmp=$(mktemp)
printf "%s\n" "{\"live-restore\": true}" > "$tmp"
sudo dockerd --validate --config-file "$tmp"
sudo install -m 644 -o root -g root "$tmp" /etc/docker/daemon.json
rm -f "$tmp"
sudo systemctl reload docker
v=false
for i in $(seq 1 15); do
  v=$(docker info --format "{{.LiveRestoreEnabled}}")
  if test "$v" = true; then break; fi
  sleep 2
done
echo "LiveRestore=$v"
test "$v" = true'
  stop_health
  after_running="$(ssh "$HOST" 'docker ps -q | wc -l' | tr -d ' ')"
  echo "動いている箱: 前 $before_running → 後 $after_running"
else
  lr="$(ssh "$HOST" 'docker info --format "{{.LiveRestoreEnabled}}"')"
  if [ "$lr" != true ]; then
    echo "止めました: live-restore が有効ではありません。先に live-restore を流してください"
    exit 6
  fi
  if ! ssh "$HOST" 'sudo -n -l /usr/bin/systemctl restart docker >/dev/null'; then
    echo "止めました: 再起動の許可（/etc/sudoers.d/90-sa-docker-restart）がありません"
    exit 7
  fi
  before_running="$(ssh "$HOST" 'docker ps -q | wc -l' | tr -d ' ')"
  start_health
  ssh "$HOST" 'sudo -n /usr/bin/systemctl restart docker && sudo -n /usr/bin/systemctl is-active docker'
  after_running=""
  for _ in $(seq 1 30); do
    after_running="$(ssh "$HOST" 'docker ps -q | wc -l' | tr -d ' ' || true)"
    if [ "$after_running" = "$before_running" ]; then break; fi
    sleep 2
  done
  stop_health
  echo "動いている箱: 前 $before_running → 後 $after_running"
fi

snapshot "後"
echo "== 台本 $MODE を終えました"
