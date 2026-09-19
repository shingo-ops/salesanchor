#!/bin/bash
# ジョブ4203の位相を :00/:15/:30/:45 に揃え直す。
# termux-job-scheduler は時刻を指定できず、登録した瞬間を起点に周期が始まる。
# よって「次のちょうどの時刻まで待ってから登録し直す」ことで位相を揃える。
# auto-export.sh から切り離して起動される（ジョブの実行時間制限を受けないため）。
set -u
export PATH=/data/data/com.termux/files/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
DIR=/root/line-auto-export
LOG=$DIR/reanchor.log
JOB_ID=4203
PERIOD_MS=900000
SCRIPT=/data/data/com.termux/files/home/bin/line-auto-export

ts() { date '+%F %T'; }
now=$(date +%s)
next=$(( (now / 900 + 1) * 900 ))   # 次の15分境界（:00/:15/:30/:45）
wait=$(( next - now ))
echo "$(ts) 位相リセット開始: $wait 秒待って $(date -d @$next '+%H:%M:%S') に登録し直す" >> "$LOG"

# ウェイクロックは使わない（合意事項）。端末が深く眠ると待ちが伸びるが、数分の誤差は許容する。
sleep "$wait"

termux-job-scheduler --job-id "$JOB_ID" --period-ms "$PERIOD_MS" --script "$SCRIPT" \
  --persisted true --network none --battery-not-low false >> "$LOG" 2>&1
rc=$?
echo "$(ts) 登録し直し 終了コード=$rc（狙い $(date -d @$next '+%H:%M:%S') / 実際 $(date '+%H:%M:%S')）" >> "$LOG"
