#!/bin/bash
# Hourly LINE talk-history export (runs inside the Ubuntu proot, started by Termux job scheduler).
# wake + PIN unlock -> LINE export -> Termux EDIT -> wait for client.py send result -> lock.
# Results go to the existing outbox events table (stage='auto'); the PIN is never printed.
set -u
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
DIR=/root/line-auto-export
TH=/data/data/com.termux/files/home
PIN_FILE=$TH/line-import/state/unlock-pin
STATE=$TH/line-import/state
DB=$STATE/outbox.sqlite3
LOG=$DIR/auto-export.log
EDIT_X=872; EDIT_Y=1237   # Termux "EDIT" button; dialog is not exposed to uiautomator (verified by screenshot 2026-09-17)

exec 9>"$DIR/lock"
flock -n 9 || exit 0
exec >>"$LOG" 2>&1

ts() { date '+%F %T'; }
say() { echo "$(ts) $*"; }
T0=$(date +%s)

# Record in the shared outbox history and notify (notify only when $3 is set).
record() {
  python3 - "$1" "$2" "${3:-}" "$(( $(date +%s) - T0 ))" <<'PY'
import subprocess
import sys
sys.path.insert(0, '/data/data/com.termux/files/home/line-import/lib')
import client

result, reason, notify, elapsed = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])


def loud_notify(nid, title, content):
    # 連続2回目以降の失敗通知：--alert-once を付けないので、更新ごとに鳴り直す。
    # 鳴り方そのものは Android 8 以降は通知チャンネルが決めるため、ここでは指定しない
    # （実測 2026-10-06: チャンネル termux-notification は importance=3・音あり・
    #  振動は FLAG_MUTE_HAPTIC で無効。--vibrate / --priority は効かない）。
    try:
        r = subprocess.run(
            [client.TERMUX_NOTIFICATION, '--id', str(nid), '-t', title, '-c', content],
            timeout=10, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, check=False)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0


box = client.Outbox('/data/data/com.termux/files/home/line-import/state')

# 今回の記録より前の、直前の stage='auto' の結果（復旧通知の判定に使う）。
# 見送り（skipped＝スマホ使用中）は成功でも失敗でもないので除外する。
prev = box.db.execute(
    "SELECT result FROM events WHERE stage='auto' AND result<>'skipped' ORDER BY id DESC LIMIT 1").fetchone()
prev_result = prev[0] if prev else None

box.record('auto', result, reason=reason or None, elapsed=elapsed, detected_by='schedule')

if notify:
    # 今回を1回目として、stage='auto' の連続失敗回数を数える（見送りは除外）。
    n = 0
    for (r,) in box.db.execute("SELECT result FROM events WHERE stage='auto' AND result<>'skipped' ORDER BY id DESC"):
        if r == 'failed':
            n += 1
        else:
            break
    title = 'LINE自動書き出し：' + notify if n <= 1 else 'LINE自動書き出し：{}（連続{}回）'.format(notify, n)
    if n >= 2:
        box.notifier = loud_notify
    box._notify(4203, title, reason)
elif result == 'ok' and prev_result == 'failed':
    box._notify(4203, 'LINE自動書き出し：復旧しました', reason)

box.db.close()
PY
}
fail() {  # fail <step> <reason>
  say "FAIL $1: $2"
  record failed "$1: $2" "失敗"
  adb shell input keyevent KEYCODE_HOME >/dev/null 2>&1
  adb shell input keyevent KEYCODE_SLEEP >/dev/null 2>&1
  exit 1
}
# grep -q / grep -m1 は先に終了してパイプを閉じるため、tr が「Broken pipe」を
# 標準エラーに出す（動作に影響はないがログが汚れる）。tr の標準エラーは捨てる。
q() { timeout 20 adb shell "$@" 2>/dev/null | tr -d '\r' 2>/dev/null; }
locked() { q dumpsys window policy | grep -q 'showing=true'; }
awake() { q dumpsys power | grep -q 'mWakefulness=Awake'; }
focus() { q dumpsys window | grep -m1 mCurrentFocus | sed -E 's/.* ([^ ]+)\}.*/\1/'; }

say "start"
[ "$(stat -c %a "$PIN_FILE" 2>/dev/null)" = 600 ] || fail setup "暗証番号ファイルがない、または権限が600ではない"

# ADB connection (wireless debugging). Reconnect to the last known endpoint if needed.
timeout 10 adb start-server >/dev/null 2>&1
if ! timeout 10 adb get-state 2>/dev/null | grep -q device; then
  last=$(cat "$DIR/endpoint" 2>/dev/null)
  [ -n "$last" ] && timeout 10 adb connect "$last" >/dev/null 2>&1
  if ! timeout 10 adb get-state 2>/dev/null | grep -q device; then
    # Wi-Fi が切れて復帰すると、ワイヤレスデバッグは新しいポートで起動し直す
    # （2026-09-23: 40359 -> 44861 に変わり約6時間停止した）。保存済みの接続先で
    # 駄目なときはポートを探し直す（実測 約97秒）。
    say "接続先を探索"
    err_file=$(mktemp)
    found=$(bash "$DIR/adb-discover.sh" 2>"$err_file")
    rc=$?
    discover_err=$(cat "$err_file" 2>/dev/null)
    rm -f "$err_file"
    [ -n "$discover_err" ] && say "探索エラー出力: $discover_err"
    [ -n "$found" ] && say "接続先を更新: $found"
    if ! timeout 10 adb get-state 2>/dev/null | grep -q device; then
      case "$rc" in
        2) fail adb "ワイヤレスデバッグがOFF、またはWi-Fi未接続（待ち受けが無い）。端末の 設定→開発者向けオプション→ワイヤレスデバッグ をONにしてください" ;;
        3) candidates=$(echo "$discover_err" | sed -n 's/^candidates: //p')
           fail adb "ペア設定が切れている疑い（候補はあるが接続できない）。ペア設定コードで再ペアリングが必要。候補ポート: ${candidates:-不明}" ;;
        *) fail adb "ADBに接続できない（原因不明。auto-export.log を確認）" ;;
      esac
    fi
  fi
fi
timeout 10 adb devices | awk '/\tdevice$/{print $1; exit}' > "$DIR/endpoint"

if awake && ! locked; then
  say "skip: phone in use"
  record skipped "スマホ使用中のため見送り"
  exit 0
fi

q input keyevent KEYCODE_WAKEUP >/dev/null
sleep 1
if locked; then
  q wm dismiss-keyguard >/dev/null
  sleep 1.5
  timeout 10 adb shell input text "$(cat "$PIN_FILE")"
  q input keyevent KEYCODE_ENTER >/dev/null
  sleep 2
fi
locked && fail unlock "ロックを解除できない"
say "unlocked"

timeout 10 adb push "$DIR/flow.sh" /data/local/tmp/flow.sh >/dev/null || fail setup "操作スクリプトを転送できない"
before=$(python3 -c "import sqlite3;print(sqlite3.connect('$DB').execute('select coalesce(max(id),0) from events').fetchone()[0])")
out=$(timeout 120 adb shell sh /data/local/tmp/flow.sh 1 keep | tr -d '\r')
echo "$out" | grep -E '^run|not found'
case "$(focus)" in *ChooserActivity*) ;; *)
  step=$(echo "$out" | sed -nE 's/.*FAIL at=([a-z_]+).*/\1/p' | head -1)
  fail export "LINEの書き出し画面まで進めない（${step:-不明}）";;
esac

b=$(q "uiautomator dump /data/local/tmp/sheet.xml >/dev/null; tr '>' '\n' < /data/local/tmp/sheet.xml | grep 'text=\"Termux\"' | head -1 | sed -E 's/.*bounds=\"\[([0-9]+),([0-9]+)\]\[([0-9]+),([0-9]+)\]\".*/\1 \2 \3 \4/'; rm -f /data/local/tmp/sheet.xml")
[ -z "$b" ] && fail share "共有先にTermuxが見つからない"
set -- $b
q input tap $(( ($1+$3)/2 )) $(( ($2+$4)/2 )) >/dev/null
for i in $(seq 1 10); do focus | grep -q TermuxFileReceiverActivity && break; sleep 0.5; done
focus | grep -q TermuxFileReceiverActivity || fail share "Termuxの保存画面が出ない"
sleep 1
q input tap $EDIT_X $EDIT_Y >/dev/null
say "EDIT tapped"

res=""
for i in $(seq 1 240); do
  res=$(python3 -c "
import sqlite3
r=sqlite3.connect('$DB').execute(\"select result from events where id>? and stage='send' and result<>'started' order by id desc limit 1\",($before,)).fetchone()
print('' if r is None else r[0])")
  [ -n "$res" ] && break
  sleep 1
done
q input keyevent KEYCODE_HOME >/dev/null
q input keyevent KEYCODE_SLEEP >/dev/null
[ -z "$res" ] && fail import "書き出し後4分たっても送信結果が記録されない"
say "done: $res"
record ok "送信結果: $res"
