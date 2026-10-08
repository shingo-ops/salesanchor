#!/bin/bash
# 15-minute LINE talk-history export job (runs inside the Ubuntu proot, started by Termux job scheduler).
# MODE=app（既定）: スマホ上の自作アプリ（jp.salesanchor.lineexport）へブロードキャストで合図を送り、
#   アプリ側の実行結果を outbox の events から読む。ADB不要（ADBのワイヤレスデバッグは鍵失効で
#   再発停止するため、2026-10-08 にこちらへ切り替えた。詳細: docs/handoff/line-auto-export-runtime/
#   design-app-trigger.md）。
# MODE=adb（切り戻し用・LINE_AUTO_EXPORT_MODE=adb で起動）: 従来方式。
#   wake + PIN unlock -> LINE export -> Termux EDIT -> wait for client.py send result -> lock。
# Results go to the existing outbox events table (stage='auto'); the PIN is never printed.
set -u
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
MODE=${LINE_AUTO_EXPORT_MODE:-app}
DIR=/root/line-auto-export
TH=/data/data/com.termux/files/home
PIN_FILE=$TH/line-import/state/unlock-pin   # MODE=adb のみ使用。appモードはPINをアプリ側が持つ。
STATE=$TH/line-import/state
DB=$STATE/outbox.sqlite3
LOG=$DIR/auto-export.log
EDIT_X=872; EDIT_Y=1237   # Termux "EDIT" button; dialog is not exposed to uiautomator (verified by screenshot 2026-09-17). MODE=adb only.

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
  if [ "$MODE" = adb ]; then
    adb shell input keyevent KEYCODE_HOME >/dev/null 2>&1
    adb shell input keyevent KEYCODE_SLEEP >/dev/null 2>&1
  fi
  exit 1
}
# grep -q / grep -m1 は先に終了してパイプを閉じるため、tr が「Broken pipe」を
# 標準エラーに出す（動作に影響はないがログが汚れる）。tr の標準エラーは捨てる。MODE=adb only.
q() { timeout 20 adb shell "$@" 2>/dev/null | tr -d '\r' 2>/dev/null; }
locked() { q dumpsys window policy | grep -q 'showing=true'; }
awake() { q dumpsys power | grep -q 'mWakefulness=Awake'; }
focus() { q dumpsys window | grep -m1 mCurrentFocus | sed -E 's/.* ([^ ]+)\}.*/\1/'; }

# アプリへ「全部やれ」の合図をブロードキャストで送る（MODE=app専用、ADB不要）。
# --user 0 と -n（宛先名指し）は両方必須。2026-10-08 実測で、-n の無い暗黙ブロードキャストは
# 一度も届かなかった（09:23・09:28の2回とも無反応）。--user 0 を省くと別ユーザー扱いになり届かない。
# テスト時は LINE_AUTO_EXPORT_BROADCAST_CMD で差し替え可能（例: echo に置き換えて、実機を使わずに
# ポーリング以降の処理だけを検証する。design-app-trigger.md には無い追加）。
#
# 標準出力（"Broadcasting: Intent ..." 等、成功時も毎回出る）は捨てて say() の行に混ざらないようにする
# （2026-10-08 実機ログで確認: 成功時でもこの出力が auto-export.log に流れ込んで読みにくかった）。
# 標準エラーは残す（撃てなかった原因を残すため）。終了コードが0以外、または標準エラーに出力があれば、
# 合図そのものを撃てなかった（または例外が出た）とみなして fail する。
broadcast_run_all() {
  bc_err_file=$(mktemp)
  if [ -n "${LINE_AUTO_EXPORT_BROADCAST_CMD:-}" ]; then
    eval "$LINE_AUTO_EXPORT_BROADCAST_CMD" >/dev/null 2>"$bc_err_file"
  else
    CLASSPATH=/data/data/com.termux/files/usr/libexec/termux-am/am.apk \
    /system/bin/app_process -Xnoimage-dex2oat / com.termux.termuxam.Am \
      broadcast --user 0 -n jp.salesanchor.lineexport/.RunReceiver \
      -a jp.salesanchor.lineexport.RUN_ALL >/dev/null 2>"$bc_err_file"
  fi
  bc_rc=$?
  bc_err=$(cat "$bc_err_file" 2>/dev/null)
  rm -f "$bc_err_file"
  if [ "$bc_rc" -ne 0 ] || [ -n "$bc_err" ]; then
    fail app "アプリへの合図を送れない（rc=$bc_rc${bc_err:+: $bc_err}）"
  fi
}

say "start"
if [ "$MODE" = adb ]; then
  [ "$(stat -c %a "$PIN_FILE" 2>/dev/null)" = 600 ] || fail setup "暗証番号ファイルがない、または権限が600ではない"
fi

if [ "$MODE" != adb ]; then
  # MODE=app: アプリへ合図を送って、送信結果が events に記録されるのを待つだけ。
  # 再ロックはスクリプトでは行わない（ADBが無いため不可。アプリ側がRUN_ALLの最後に施錠する。
  # design-app-trigger.md 「アプリ側: 実行後の再ロック」参照）。
  before=$(python3 -c "import sqlite3;print(sqlite3.connect('$DB').execute('select coalesce(max(id),0) from events').fetchone()[0])")

  broadcast_run_all
  say "signal sent"

  send_result=""
  send_reason=""
  for i in $(seq 1 60); do  # 3秒 x 60回 = 最大180秒
    out=$(python3 -c "
import sqlite3
r = sqlite3.connect('$DB').execute(
    \"select result, coalesce(reason,'') from events where id>? and stage='send' and result<>'started' order by id desc limit 1\",
    ($before,)).fetchone()
print('' if r is None else r[0] + '\t' + r[1])")
    if [ -n "$out" ]; then
      IFS=$'\t' read -r send_result send_reason <<< "$out"
      break
    fi
    sleep 3
  done

  if [ -z "$send_result" ]; then
    # スマホ使用中の見送りと、アプリ側の失敗を、スクリプトからは区別できない
    # （結果はアプリの通知にしか出ず、proot からは /sdcard が見えないため読めない）。
    # failed にすると見送りでも失敗通知が鳴り続けるため、skipped として記録する
    # （design-app-trigger.md 「なぜ結果が来なければ failed ではなく skipped なのか」参照）。
    say "skip: no app response within 180s"
    record skipped "アプリが実行しなかった（スマホ使用中か、アプリ側の失敗。アプリの通知を確認）"

    # client.py の詰まり通知（stall, id 4202）は queued/retry/auth_required のジョブが残っている
    # ときしか鳴らない。appモードでアプリが一切動かなくなると新しいジョブが作られず、何も鳴らない
    # まま静かに止まる（design-app-trigger.md 追補2026-10-08「修正2」。当初「詰まり通知が拾う」と
    # 書いたのは設計の誤りだった）。ここで最後の stage='auto' result='ok' からの経過を独自に見張る。
    # 3時間の根拠: 実測86件/日（平均17分に1件）。送信量の絞り込み導入後は「新規なし」も ok として
    # 記録されるため、正常に動いていれば3時間以内に必ず ok が入る。日中にスマホを3時間使い続けた
    # 場合だけ誤検知し得るので、通知文は断定しない。
    python3 - <<'PY_STALL'
import sys
from datetime import datetime
sys.path.insert(0, '/data/data/com.termux/files/home/line-import/lib')
import client

box = client.Outbox('/data/data/com.termux/files/home/line-import/state')
row = box.db.execute(
    "SELECT at FROM events WHERE stage='auto' AND result='ok' ORDER BY id DESC LIMIT 1").fetchone()
if row is not None:
    last_at = row[0]
    elapsed = box.clock() - last_at
    if elapsed >= 3 * 3600:
        h, m = divmod(int(elapsed) // 60, 60)
        last_hhmm = datetime.fromtimestamp(last_at, client.JST).strftime('%H:%M')
        content = (f'最後の成功 {last_hhmm} から{h}時間{m}分。'
                   'スマホを使い続けた場合もこの通知が出ます')
        # box.notifier は既定の client.termux_notify のまま使う（--alert-once 付き・静かな通知）。
        # 初回だけ鳴り、以後は無音で更新されるため、appモードがskippedを積むたびに鳴り続けない。
        box._notify(4204, 'LINE自動書き出し：3時間以上成功していません', content)
box.db.close()
PY_STALL
    exit 0
  fi

  case "$send_result" in
    accepted|pending_review|duplicate|skipped)
      # duplicate: 同じ内容を取り込み済みのため送信なし（tools/termux-line-import/client.py:196）。
      # skipped（stage='send'側の値）: 新規が無いため送信なし（release/line-import-incremental-send
      # で新設）。どちらも正常な無操作であり失敗ではない。failed にすると、送信量の絞り込みが入った
      # 後は「新規なし」が最多の結果になり、失敗通知が鳴り続けて2026-10-06の連続失敗通知改修が逆効果
      # になる（design-app-trigger.md 追補2026-10-08「修正1」）。ここを failed に戻さないこと。
      say "done: $send_result"
      record ok "送信結果: $send_result" ;;
    *)
      fail send "送信結果: $send_result（${send_reason:-理由不明}）" ;;
  esac
  exit 0
fi

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
