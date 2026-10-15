#!/bin/bash
# test-mac-jobs-watch.sh — scripts/mac-jobs-watch.sh の試験（design §4 K1 の ①〜㉔）
#
# すべて mktemp -d で作った一時ディレクトリの中だけで動く。偽の launchctl / curl を使い、
# MJW_ 環境変数（状態・ログ・ロック・通知先・時刻）も一時領域へ向ける。HOME も一時領域に向ける。
# 本物の ~/Library、~/.config、launchctl、curl、Discord には一切触れない。
#
# 実行方法: bash scripts/tests/test-mac-jobs-watch.sh
# 終了コード: 0=FAIL が 0 件 / 1=FAIL あり

# shellcheck disable=SC2015  # ok/ng は常に 0 を返すので A && B || C で問題ない
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="${SCRIPT_DIR}/../mac-jobs-watch.sh"
PASS=0
FAIL=0

ok() { echo "PASS: $1"; PASS=$(( PASS + 1 )); }
ng() { echo "FAIL: $1"; FAIL=$(( FAIL + 1 )); }
eq() { # eq <説明> <実際> <期待>
  if [ "$2" = "$3" ]; then ok "$1"; else ng "$1 (実際=[$2] 期待=[$3])"; fi
}

T_RAW="$(mktemp -d "${TMPDIR:-/tmp}/mac-jobs-watch-test.XXXXXX")" || { echo "mktemp 失敗"; exit 1; }
T="$(cd -P "${T_RAW}" && pwd -P)"
SLEEP_PID=""
cleanup() {
  if [ -n "${SLEEP_PID}" ]; then kill "${SLEEP_PID}" 2>/dev/null || true; fi
  case "${T}" in
    */mac-jobs-watch-test.*) rm -rf -- "${T}" ;;
  esac
}
trap cleanup EXIT

BIN="${T}/bin"
D="${T}/d"
mkdir -p "${BIN}"

# ── 偽コマンド ───────────────────────────────────────────────────────────────
cat > "${BIN}/launchctl" <<'EOS'
#!/bin/bash
echo "$*" >> "${FAKE}/launchctl.calls"
[ "${1:-}" = print ] || exit 0
label="${2##*/}"
if grep -Fxq -- "${label}" "${FAKE}/absent" 2>/dev/null; then exit 113; fi
exit 0
EOS
cat > "${BIN}/curl" <<'EOS'
#!/bin/bash
n="$(cat "${FAKE}/curl.n" 2>/dev/null || echo 0)"
n=$(( n + 1 ))
echo "${n}" > "${FAKE}/curl.n"
printf '%s\n' "$@" > "${FAKE}/curl.args.${n}"
cat > "${FAKE}/curl.stdin.${n}"
exit "$(cat "${FAKE}/curl.rc" 2>/dev/null || echo 0)"
EOS
chmod +x "${BIN}/launchctl" "${BIN}/curl"

FAKE_URL='https://discord.com/api/webhooks/TESTID/TESTTOKEN-not-real'

# 基準の時刻: 2026-10-15 12:00:00（ローカル）。直近 04:00 はその 8 時間前
T04="$(date -j -f '%Y-%m-%d %H:%M:%S' '2026-10-15 04:00:00' +%s)"
NOW=0
BOOT=0

iso() { date -j -r "$1" '+%Y-%m-%dT%H:%M:%S%z'; }
djfmt() { date -j -r "$1" '+%Y-%m-%d %H:%M:%S'; }
settime() { touch -t "$(date -j -r "$2" '+%Y%m%d%H%M.%S')" "$1"; }

colima_line() { # colima_line <epoch> <result> <reason>
  printf '%s result=%s reason=%s elapsed=- detail=試験\n' "$(iso "$1")" "$2" "$3" >> "${D}/colima.log"
}
dj_start() { printf '===== disk-janitor 開始 %s mode=execute =====\n' "$(djfmt "$1")" >> "${D}/dj.log"; }
dj_end() { printf '===== disk-janitor 終了 %s mode=execute 合計 0 件 =====\n' "$(djfmt "$1")" >> "${D}/dj.log"; }
mk_state() { # mk_state <prev_run> <boot_sec> <colima_seen> <d_run> <dj_err_seen>
  mkdir -p "${D}/state"
  printf 'prev_run=%s\nboot_sec=%s\ncolima_seen=%s\ncolima_d_run=%s\ndj_err_seen=%s\n' \
    "$1" "$2" "$3" "$4" "$5" > "${D}/state/state"
  : > "${D}/state/problems"
}

# 各試験の前に作り直す。既定は「全部正常・前回は 30 分前・起動は 5 日前」
setup() { # setup [now]
  NOW="${1:-$(( T04 + 28800 ))}"
  BOOT=$(( NOW - 432000 ))
  rm -rf "${D}"
  mkdir -p "${D}/state" "${D}/fake" "${D}/home"
  : > "${D}/fake/absent"
  export FAKE="${D}/fake"
  printf '%s\n' "${FAKE_URL}" > "${D}/webhook"
  export HOME="${D}/home"
  export MJW_LABELS="jp.salesanchor.colima-idle-stop jp.salesanchor.disk-janitor"
  export MJW_SELF_LABEL="jp.salesanchor.mac-jobs-watch"
  export MJW_COLIMA_LOG="${D}/colima.log"
  export MJW_DJ_LOG="${D}/dj.log"
  export MJW_DJ_ERR="${D}/dj.err"
  export MJW_DJ_LOCK="${D}/nolock"
  export MJW_WEBHOOK_FILE="${D}/webhook"
  export MJW_STATE_DIR="${D}/state"
  export MJW_LOG="${D}/mjw.log"
  export MJW_LOCK_DIR="${D}/lock"
  export MJW_LAUNCHCTL="${BIN}/launchctl"
  export MJW_CURL="${BIN}/curl"
  export MJW_NOW="${NOW}"
  export MJW_BOOT_SEC="${BOOT}"
  colima_line $(( NOW - 60 )) idle -
  dj_start $(( NOW - 28800 )); dj_end $(( NOW - 28700 ))
  mk_state $(( NOW - 1800 )) "${BOOT}" $(( NOW - 60 )) 0 0
}

run_mjw() { bash "${TARGET}" "$@"; }
set_now() { NOW="$1"; export MJW_NOW="$1"; }
ncalls() { cat "${D}/fake/curl.n" 2>/dev/null || echo 0; }
logc() { grep -c -F -- "$1" "${D}/mjw.log" 2>/dev/null || true; }
stv() { sed -n "s/^$1=//p" "${D}/state/state" | tail -1; }
has_prob() { grep -q -F -- "$1" "${D}/state/problems" 2>/dev/null; }
sentmsg() { cat "${D}/fake/curl.args.$1" 2>/dev/null; }

# ── ① 全部正常で送らない ─────────────────────────────────────────────────────
setup
run_mjw; rc=$?
eq "①-1 全部正常: 終了 0" "${rc}" "0"
eq "①-2 全部正常: 送らない" "$(ncalls)" "0"
eq "①-3 全部正常: ログ result=ok send=-" "$(logc 'result=ok send=-')" "1"
eq "①-4 prev_run が進む" "$(stv prev_run)" "${NOW}"

# ── ②〜⑤ 読み込まれていない → 続く → 24h → 直る ──────────────────────────────
setup
echo "jp.salesanchor.colima-idle-stop" > "${D}/fake/absent"
run_mjw; rc=$?
eq "②-1 未読み込み: 終了 0" "${rc}" "0"
eq "②-2 未読み込み: alert 1 通" "$(ncalls)" "1"
eq "②-3 ログ result=alert send=ok" "$(logc 'result=alert send=ok')" "1"
has_prob "unloaded:jp.salesanchor.colima-idle-stop" && ok "②-4 problems に入る" || ng "②-4 problems に入る"
sentmsg 1 | grep -q 'jp.salesanchor.colima-idle-stop が Mac に読み込まれていません' && ok "②-5 固定文が入る" || ng "②-5 固定文が入る"
sentmsg 1 | grep -q '🖥️ Mac の見張り: ⚠️ 異常' && ok "②-6 見出し" || ng "②-6 見出し"
set_now $(( NOW + 1800 ))
run_mjw
eq "③ 次の回も同じ: 送らない" "$(ncalls)" "1"
set_now $(( NOW + 86400 - 1800 ))
run_mjw
eq "④-1 24 時間後: repeat 1 通" "$(ncalls)" "2"
eq "④-2 ログ result=repeat send=ok" "$(logc 'result=repeat send=ok')" "1"
sentmsg 2 | grep -q 'まだ続いています' && ok "④-3 見出し" || ng "④-3 見出し"
: > "${D}/fake/absent"
set_now $(( NOW + 5000 ))
run_mjw
eq "⑤-1 直る: recover 1 通" "$(ncalls)" "3"
eq "⑤-2 ログ result=recover send=ok" "$(logc 'result=recover send=ok')" "1"
has_prob "unloaded:" && ng "⑤-3 problems から消える" || ok "⑤-3 problems から消える"
sentmsg 3 | grep -q '直りました' && ok "⑤-4 復旧文" || ng "⑤-4 復旧文"

# ── ⑥ stop-fail の出来事 ─────────────────────────────────────────────────────
setup
colima_line $(( NOW - 30 )) stop-fail -
run_mjw
eq "⑥-1 新しい stop-fail: alert 1 通" "$(ncalls)" "1"
sentmsg 1 | grep -q '停止に失敗しました' && ok "⑥-2 固定文" || ng "⑥-2 固定文"
eq "⑥-3 既読位置が進む" "$(stv colima_seen)" "$(( NOW - 30 ))"
set_now $(( NOW + 900 ))
colima_line $(( NOW - 30 )) idle -
run_mjw
eq "⑥-4 次の回（新しい行が idle）: 何も送らない" "$(ncalls)" "1"
eq "⑥-5 recover も出ない" "$(logc 'result=recover')" "0"
has_prob "colima-stopfail" && ng "⑥-6 出来事は problems に入らない" || ok "⑥-6 出来事は problems に入らない"

# ── ⑦ reason=d 2 回続き ──────────────────────────────────────────────────────
setup
colima_line $(( NOW - 30 )) busy d
colima_line $(( NOW - 20 )) busy d
run_mjw
eq "⑦-1 d が 2 行続き: alert 1 通" "$(ncalls)" "1"
sentmsg 1 | grep -q '2 回続けて判定に失敗しました' && ok "⑦-2 固定文" || ng "⑦-2 固定文"
setup
colima_line $(( NOW - 30 )) busy d
run_mjw
eq "⑦-3 d が 1 行: 送らない" "$(ncalls)" "0"
eq "⑦-4 colima_d_run=1 を持ち越す" "$(stv colima_d_run)" "1"
setup
colima_line $(( NOW - 30 )) busy d
colima_line $(( NOW - 25 )) busy a
colima_line $(( NOW - 20 )) busy d
run_mjw
eq "⑦-5 d・a・d: 送らない" "$(ncalls)" "0"
setup
colima_line $(( NOW - 30 )) busy d
colima_line $(( NOW - 25 )) skip -
colima_line $(( NOW - 20 )) busy d
run_mjw
eq "⑦-6 d・skip・d: skip は数えず alert" "$(ncalls)" "1"

# ── ⑧ 起きていない回は stale を判定せず持ち越す ────────────────────────────────
setup
rm -f "${D}/colima.log" "${D}/dj.log"
colima_line $(( NOW - 20000 )) idle -
dj_start $(( NOW - 120000 )); dj_end $(( NOW - 119900 ))
mk_state $(( NOW - 5000 )) "${BOOT}" $(( NOW - 20000 )) 0 0
printf 'colima-stale\t%s\ndj-stale\t%s\n' "$(( NOW - 100 ))" "$(( NOW - 100 ))" > "${D}/state/problems"
run_mjw
eq "⑧-1 眠り明け: 送らない（recover も出ない）" "$(ncalls)" "0"
has_prob "colima-stale" && ok "⑧-2 前回の問題を持ち越す" || ng "⑧-2 前回の問題を持ち越す"
has_prob "dj-stale" && ok "⑧-3 dj-stale も前回を持ち越す（復旧にしない）" || ng "⑧-3 dj-stale も前回を持ち越す（復旧にしない）"
eq "⑧-4 ログ awake=0" "$(logc 'awake=0')" "1"

# ── ⑨ colima-stale ───────────────────────────────────────────────────────────
setup
rm -f "${D}/colima.log"
colima_line $(( NOW - 5401 )) idle -
mk_state $(( NOW - 1800 )) "${BOOT}" $(( NOW - 5401 )) 0 0
run_mjw
eq "⑨-1 最後の行が 5401 秒前: alert" "$(ncalls)" "1"
has_prob "colima-stale" && ok "⑨-2 problems に入る" || ng "⑨-2 problems に入る"
setup
rm -f "${D}/colima.log"
colima_line $(( NOW - 5400 )) idle -
mk_state $(( NOW - 1800 )) "${BOOT}" $(( NOW - 5400 )) 0 0
run_mjw
eq "⑨-3 5400 秒前ちょうど: 送らない" "$(ncalls)" "0"

# ── ⑩ dj-stale ───────────────────────────────────────────────────────────────
setup
rm -f "${D}/dj.log"
dj_start $(( NOW - 93601 )); dj_end $(( NOW - 93500 ))
run_mjw
eq "⑩-1 最後の開始が 26 時間超: alert" "$(ncalls)" "1"
has_prob "dj-stale" && ok "⑩-2 problems に入る" || ng "⑩-2 problems に入る"
setup
rm -f "${D}/dj.log"
dj_start $(( NOW - 93601 )); dj_end $(( NOW - 93500 ))
export MJW_BOOT_SEC=$(( NOW - 10800 ))
mk_state $(( NOW - 1800 )) "$(( NOW - 10800 ))" $(( NOW - 60 )) 0 0
run_mjw
eq "⑩-3 起動が直近 04:00 より後: 出ない" "$(ncalls)" "0"
setup $(( T04 + 1800 ))
rm -f "${D}/dj.log"
dj_start $(( NOW - 93601 )); dj_end $(( NOW - 93500 ))
run_mjw
eq "⑩-4 直近 04:00 から 3600 秒以内: 出ない" "$(ncalls)" "0"
set_now $(( T04 + 3600 ))
colima_line $(( NOW - 60 )) idle -
run_mjw
eq "⑩-5 直近 04:00 から 3600 秒ちょうど: 出る" "$(ncalls)" "1"

# ── ⑪ dj-unfinished ──────────────────────────────────────────────────────────
setup
rm -f "${D}/dj.log"
dj_start $(( NOW - 7201 ))
run_mjw
eq "⑪-1 開始から終了なしで 7201 秒: alert" "$(ncalls)" "1"
has_prob "dj-unfinished" && ok "⑪-2 problems に入る" || ng "⑪-2 problems に入る"
setup
rm -f "${D}/dj.log"
dj_start $(( NOW - 7201 )); dj_end $(( NOW - 7000 ))
run_mjw
eq "⑪-3 終了行あり: 送らない" "$(ncalls)" "0"
setup
rm -f "${D}/dj.log"
dj_start $(( NOW - 7000 ))
run_mjw
eq "⑪-4 開始から 7000 秒: 送らない" "$(ncalls)" "0"

# ── ⑫ dj-lock-stale ─────────────────────────────────────────────────────────
setup
export MJW_DJ_LOCK="${D}/djlock"
mkdir -p "${MJW_DJ_LOCK}"; settime "${MJW_DJ_LOCK}" $(( NOW - 7201 ))
run_mjw
eq "⑫-1 古いロック: alert" "$(ncalls)" "1"
has_prob "dj-lock-stale" && ok "⑫-2 problems に入る" || ng "⑫-2 problems に入る"
setup
export MJW_DJ_LOCK="${D}/djlock"
mkdir -p "${MJW_DJ_LOCK}"; settime "${MJW_DJ_LOCK}" $(( NOW - 100 ))
run_mjw
eq "⑫-3 新しいロック: 送らない" "$(ncalls)" "0"

# ── ⑬ dj-err ─────────────────────────────────────────────────────────────────
setup
rm -f "${D}/state/state"
echo "error text" > "${D}/dj.err"; settime "${D}/dj.err" $(( NOW - 30 ))
run_mjw
eq "⑬-1 初回: dj-err を出さない" "$(sentmsg 1 | grep -c '道具の更新に失敗')" "0"
eq "⑬-1b 初回: 送るのは起動後の点検の 1 通だけ（2 通目に dj-err が出ない）" "$(ncalls)" "1"
eq "⑬-2 初回: 既読位置が err の更新時刻" "$(stv dj_err_seen)" "$(( NOW - 30 ))"
set_now $(( NOW + 900 ))
run_mjw
before="$(ncalls)"
echo "error text 2" > "${D}/dj.err"; settime "${D}/dj.err" $(( NOW - 10 ))
set_now $(( NOW + 900 ))
run_mjw
eq "⑬-3 更新で 1 回だけ" "$(ncalls)" "$(( before + 1 ))"
sentmsg "$(ncalls)" | grep -q '道具の更新に失敗' && ok "⑬-4 固定文" || ng "⑬-4 固定文"
set_now $(( NOW + 900 ))
colima_line $(( NOW - 60 )) idle -
run_mjw
eq "⑬-5 次の回: 送らない" "$(ncalls)" "$(( before + 1 ))"
before="$(ncalls)"
: > "${D}/dj.err"; settime "${D}/dj.err" $(( NOW + 30 ))
set_now $(( NOW + 900 ))
colima_line $(( NOW - 60 )) idle -
zero_m=$(( NOW - 900 + 30 ))
run_mjw
eq "⑬-6 大きさ 0 の更新: 出さない" "$(ncalls)" "${before}"
eq "⑬-6b 大きさ 0 の更新でも既読位置は進む" "$(stv dj_err_seen)" "${zero_m}"
eq "⑬-7 recover は出ない" "$(logc 'result=recover')" "0"

# ── ⑭ 起動後の点検 ───────────────────────────────────────────────────────────
setup
mk_state $(( NOW - 1800 )) "$(( BOOT - 1000 ))" $(( NOW - 60 )) 0 0
run_mjw
eq "⑭-1 起動時刻が変わる: boot-notice 1 通" "$(ncalls)" "1"
eq "⑭-2 ログ result=boot-notice send=ok" "$(logc 'result=boot-notice send=ok')" "1"
eq "⑭-3 boot_sec を更新" "$(stv boot_sec)" "${BOOT}"
eq "⑭-4 3 つとも読み込み済み" "$(sentmsg 1 | grep -o '読み込み済み' | wc -l | tr -d ' ')" "3"
sentmsg 1 | grep -q '起動後の点検' && ok "⑭-5 見出し" || ng "⑭-5 見出し"
set_now $(( NOW + 1800 ))
colima_line $(( NOW - 60 )) idle -
run_mjw
eq "⑭-6 同じ起動時刻: 送らない" "$(ncalls)" "1"
setup
export MJW_BOOT_SEC=$(( NOW - 100 ))
mk_state $(( NOW - 1800 )) "$(( BOOT - 1000 ))" $(( NOW - 60 )) 0 0
echo "jp.salesanchor.colima-idle-stop" > "${D}/fake/absent"
run_mjw
eq "⑭-7 起動直後: 点検も unloaded も送らない" "$(ncalls)" "0"
eq "⑭-8 起動直後: boot_sec を変えない" "$(stv boot_sec)" "$(( BOOT - 1000 ))"

# ── ⑮ 通知先が無い ───────────────────────────────────────────────────────────
setup
rm -f "${D}/webhook"
echo "jp.salesanchor.colima-idle-stop" > "${D}/fake/absent"
run_mjw; rc=$?
eq "⑮-1 通知先なし: 終了 2" "${rc}" "2"
eq "⑮-2 送らない" "$(ncalls)" "0"
eq "⑮-3 ログ result=no-webhook" "$(logc 'result=no-webhook')" "1"
eq "⑮-4 状態を変えない" "$(stv prev_run)" "$(( NOW - 1800 ))"
: > "${D}/webhook"
run_mjw; rc=$?
eq "⑮-5 通知先が空: 終了 2" "${rc}" "2"

# ── ⑯ 送信失敗 ───────────────────────────────────────────────────────────────
setup
echo 1 > "${D}/fake/curl.rc"
colima_line $(( NOW - 30 )) stop-fail -
echo "jp.salesanchor.colima-idle-stop" > "${D}/fake/absent"
run_mjw; rc=$?
eq "⑯-1 送信失敗: 終了 3" "${rc}" "3"
eq "⑯-2 ログ send=fail" "$(logc 'result=alert send=fail')" "1"
has_prob "unloaded:" && ng "⑯-3 problems を変えない" || ok "⑯-3 problems を変えない"
eq "⑯-4 既読位置を変えない" "$(stv colima_seen)" "$(( NOW - 60 ))"
eq "⑯-5 prev_run は進む" "$(stv prev_run)" "${NOW}"
echo 0 > "${D}/fake/curl.rc"
set_now $(( NOW + 900 ))
colima_line $(( NOW - 60 )) idle -
run_mjw; rc=$?
eq "⑯-6 次回また送る: 終了 0" "${rc}" "0"
eq "⑯-7 ログ result=alert send=ok" "$(logc 'result=alert send=ok')" "1"
sentmsg "$(ncalls)" | grep -q '停止に失敗しました' && ok "⑯-8 出来事も再送" || ng "⑯-8 出来事も再送"
sentmsg "$(ncalls)" | grep -q 'が Mac に読み込まれていません' && ok "⑯-9 異常も再送" || ng "⑯-9 異常も再送"

# ── ⑰ --dry-run ─────────────────────────────────────────────────────────────
setup
echo "jp.salesanchor.colima-idle-stop" > "${D}/fake/absent"
colima_line $(( NOW - 30 )) stop-fail -
before_state="$(cksum "${D}/state/state" "${D}/state/problems")"
run_mjw --dry-run; rc=$?
eq "⑰-1 dry-run: 終了 0" "${rc}" "0"
eq "⑰-2 送らない" "$(ncalls)" "0"
eq "⑰-3 状態を変えない" "$(cksum "${D}/state/state" "${D}/state/problems")" "${before_state}"
eq "⑰-4 ログ result=dry-run send=-" "$(logc 'result=dry-run send=-')" "1"
rm -f "${D}/webhook"
run_mjw --dry-run; rc=$?
eq "⑰-5 通知先が無くても 0" "${rc}" "0"

# ── ⑱ --test-notify ─────────────────────────────────────────────────────────
setup
echo "jp.salesanchor.colima-idle-stop" > "${D}/fake/absent"
before_state="$(cksum "${D}/state/state" "${D}/state/problems")"
run_mjw --test-notify; rc=$?
eq "⑱-1 test-notify: 終了 0" "${rc}" "0"
eq "⑱-2 1 通だけ" "$(ncalls)" "1"
sentmsg 1 | grep -q '送信の試験です' && ok "⑱-3 試験文" || ng "⑱-3 試験文"
eq "⑱-4 状態を変えない" "$(cksum "${D}/state/state" "${D}/state/problems")" "${before_state}"
eq "⑱-5 ログ result=test send=ok" "$(logc 'result=test send=ok')" "1"
echo 1 > "${D}/fake/curl.rc"
run_mjw --test-notify; rc=$?
eq "⑱-6 失敗: 終了 3" "${rc}" "3"

# ── ⑲ 同じ回の異常 2 件が 1 通 ────────────────────────────────────────────────
setup
printf 'jp.salesanchor.colima-idle-stop\njp.salesanchor.disk-janitor\n' > "${D}/fake/absent"
run_mjw
eq "⑲-1 2 件が 1 通" "$(ncalls)" "1"
eq "⑲-2 2 件とも入る" "$(sentmsg 1 | grep -o 'が Mac に読み込まれていません' | wc -l | tr -d ' ')" "2"

# ── ⑳ ロック ─────────────────────────────────────────────────────────────────
setup
sleep 60 &
SLEEP_PID=$!
mkdir -p "${D}/lock"; echo "${SLEEP_PID}" > "${D}/lock/pid"
echo "jp.salesanchor.colima-idle-stop" > "${D}/fake/absent"
run_mjw; rc=$?
eq "⑳-1 別の生きた pid が持つ: 終了 0" "${rc}" "0"
eq "⑳-2 送らない" "$(ncalls)" "0"
eq "⑳-3 ログ result=skip" "$(logc 'result=skip')" "1"
kill "${SLEEP_PID}" 2>/dev/null || true
{ wait "${SLEEP_PID}"; } 2>/dev/null || true
SLEEP_PID=""
[ -d "${D}/lock" ] && ok "⑳-4 他人のロックを消さない" || ng "⑳-4 他人のロックを消さない"

# ── ㉑ URL の扱い・JSON・大きさ ────────────────────────────────────────────────
setup
export MJW_LABELS='a"b c\d'
printf 'a"b\nc\\d\n' > "${D}/fake/absent"
run_mjw
eq "㉑-1 1 通" "$(ncalls)" "1"
eq "㉑-2 引数に URL が無い" "$(grep -c -F 'TESTTOKEN' "${D}/fake/curl.args.1")" "0"
eq "㉑-3 引数に discord.com が無い" "$(grep -c -F 'discord.com' "${D}/fake/curl.args.1")" "0"
grep -q -F 'TESTTOKEN' "${D}/fake/curl.stdin.1" && ok "㉑-4 標準入力にだけある" || ng "㉑-4 標準入力にだけある"
eq "㉑-5 ログに URL が無い" "$(grep -c -F 'TESTTOKEN' "${D}/mjw.log")" "0"
payload="$(grep -F '{"content"' "${D}/fake/curl.args.1")"
case "${payload}" in *'a\"b'*) ok "㉑-6 \" が逃がされる" ;; *) ng "㉑-6 \" が逃がされる" ;; esac
case "${payload}" in *'c\\d'*) ok "㉑-7 \\ が逃がされる" ;; *) ng "㉑-7 \\ が逃がされる" ;; esac
case "${payload}" in *'\n'*) ok "㉑-8 改行が \\n になる" ;; *) ng "㉑-8 改行が \\n になる" ;; esac
if command -v python3 >/dev/null 2>&1; then
  python3 -I -c 'import json,sys; json.loads(sys.stdin.read())' <<< "${payload}" 2>/dev/null && ok "㉑-9 JSON として正しい" || ng "㉑-9 JSON として正しい"
fi
# 最大規模（異常 8 件）でも 1 通 1900 バイト未満
setup
export MJW_DJ_LOCK="${D}/djlock"
printf 'jp.salesanchor.colima-idle-stop\njp.salesanchor.disk-janitor\n' > "${D}/fake/absent"
rm -f "${D}/colima.log" "${D}/dj.log"
colima_line $(( NOW - 6000 )) stop-fail -
colima_line $(( NOW - 5990 )) busy d
colima_line $(( NOW - 5980 )) busy d
dj_start $(( NOW - 120000 ))
mkdir -p "${MJW_DJ_LOCK}"; settime "${MJW_DJ_LOCK}" $(( NOW - 9000 ))
echo "err" > "${D}/dj.err"; settime "${D}/dj.err" $(( NOW - 30 ))
mk_state $(( NOW - 1800 )) "${BOOT}" $(( NOW - 7000 )) 0 0
run_mjw
eq "㉑-10 最大規模でも 1 通" "$(ncalls)" "1"
size="$(grep -F '{"content"' "${D}/fake/curl.args.1" | wc -c | tr -d ' ')"
if [ "${size}" -lt 1900 ]; then ok "㉑-11 1 通 1900 バイト未満 (${size})"; else ng "㉑-11 1 通 1900 バイト未満 (${size})"; fi
eq "㉑-12 8 件以上入る" "$([ "$(grep -o '\\n- ' "${D}/fake/curl.args.1" | wc -l | tr -d ' ')" -ge 8 ] && echo yes || echo no)" "yes"

# ── ㉒ ラベルを外す ──────────────────────────────────────────────────────────
setup
printf 'unloaded:jp.salesanchor.removed\t%s\n' "$(( NOW - 100 ))" > "${D}/state/problems"
run_mjw
eq "㉒-1 外したラベルの unloaded は recover" "$(ncalls)" "1"
eq "㉒-2 ログ result=recover send=ok" "$(logc 'result=recover send=ok')" "1"
has_prob "unloaded:" && ng "㉒-3 problems から消える" || ok "㉒-3 problems から消える"

# ── ㉓ ログが無い ────────────────────────────────────────────────────────────
setup
rm -f "${D}/colima.log" "${D}/dj.log"
run_mjw
eq "㉓-1 ログ無し: 1 通" "$(ncalls)" "1"
has_prob "colima-stale" && ok "㉓-2 Docker 自動停止ログ無し → colima-stale" || ng "㉓-2 Docker 自動停止ログ無し → colima-stale"
has_prob "dj-stale" && ok "㉓-3 自動片付けログ無し → dj-stale" || ng "㉓-3 自動片付けログ無し → dj-stale"
setup
printf 'ごみ行\n\n' > "${D}/dj.log"
run_mjw
has_prob "dj-stale" && ok "㉓-4 開始行が無い → dj-stale" || ng "㉓-4 開始行が無い → dj-stale"

# ── ㉔ ログ回転 ──────────────────────────────────────────────────────────────
setup
rm -f "${D}/colima.log"
colima_line $(( NOW - 100 )) stop-fail -
mk_state $(( NOW - 1800 )) "${BOOT}" $(( NOW - 60 )) 1 0
run_mjw
eq "㉔-1 既読位置より新しい行が 0 行: 送らない" "$(ncalls)" "0"
eq "㉔-2 既読位置は戻らない" "$(stv colima_seen)" "$(( NOW - 60 ))"

# ── ㉕ dj-stale は「判定する回」だけで判定する（猶予内・起動後は前回を持ち越す）─────────
dj_stale_setup() { # dj_stale_setup [now]
  setup "$@"
  rm -f "${D}/dj.log"
  dj_start $(( NOW - 120000 )); dj_end $(( NOW - 119900 ))
  printf 'dj-stale\t%s\n' "$(( NOW - 100 ))" > "${D}/state/problems"
}
dj_stale_setup $(( T04 + 1800 ))
run_mjw
eq "㉕-1 猶予内（04:30）: 復旧も異常も送らない" "$(ncalls)" "0"
has_prob "dj-stale" && ok "㉕-2 猶予内: 前回を持ち越す" || ng "㉕-2 猶予内: 前回を持ち越す"
eq "㉕-3 猶予内: recover が無い" "$(logc 'result=recover')" "0"
dj_stale_setup $(( T04 + 3600 ))
run_mjw
eq "㉕-4 猶予の終わり（05:00）: 続いているだけなので送らない" "$(ncalls)" "0"
has_prob "dj-stale" && ok "㉕-5 05:00: 問題は残る" || ng "㉕-5 05:00: 問題は残る"
dj_stale_setup
export MJW_BOOT_SEC=$(( NOW - 10800 ))
mk_state $(( NOW - 1800 )) "$(( NOW - 10800 ))" $(( NOW - 60 )) 0 0
printf 'dj-stale\t%s\n' "$(( NOW - 100 ))" > "${D}/state/problems"
run_mjw
eq "㉕-6 04:00 より後に起動: 復旧を送らない" "$(ncalls)" "0"
has_prob "dj-stale" && ok "㉕-7 04:00 より後に起動: 前回を持ち越す" || ng "㉕-7 04:00 より後に起動: 前回を持ち越す"
setup
printf 'dj-stale\t%s\n' "$(( NOW - 100 ))" > "${D}/state/problems"
run_mjw
eq "㉕-8 判定する回で直っていれば recover" "$(logc 'result=recover send=ok')" "1"
has_prob "dj-stale" && ng "㉕-9 直ったら problems から消える" || ok "㉕-9 直ったら problems から消える"

# ── ㉖ 空振り防止（設計 ⑧⑬⑭⑯）──────────────────────────────────────────────
setup
rm -f "${D}/state/state" "${D}/colima.log"
colima_line $(( NOW - 100 )) stop-fail -
colima_line $(( NOW - 60 )) idle -
run_mjw
eq "㉖-1 初回: colima_seen はログ最後の行の時刻" "$(stv colima_seen)" "$(( NOW - 60 ))"
eq "㉖-2 初回: 古い stop-fail は知らせない（点検の 1 通のみ）" "$(ncalls)" "1"
set_now $(( NOW + 900 ))
colima_line $(( NOW - 60 )) idle -
run_mjw
eq "㉖-3 初回の次の回: 古い stop-fail を誤報しない" "$(ncalls)" "1"
setup
export MJW_BOOT_SEC=$(( NOW - 100 ))
mk_state $(( NOW - 1800 )) "$(( NOW - 100 ))" $(( NOW - 60 )) 0 0
printf 'unloaded:jp.salesanchor.colima-idle-stop\t%s\n' "$(( NOW - 100 ))" > "${D}/state/problems"
run_mjw
eq "㉖-4 起動直後: unloaded を復旧にしない" "$(ncalls)" "0"
has_prob "unloaded:jp.salesanchor.colima-idle-stop" && ok "㉖-5 起動直後: unloaded を持ち越す" || ng "㉖-5 起動直後: unloaded を持ち越す"
setup
mk_state $(( NOW - 1800 )) "$(( BOOT - 1000 ))" $(( NOW - 60 )) 0 0
echo 1 > "${D}/fake/curl.rc"
run_mjw; rc=$?
eq "㉖-6 点検の送信失敗: 終了 3" "${rc}" "3"
eq "㉖-7 点検の送信失敗: boot_sec は進まない" "$(stv boot_sec)" "$(( BOOT - 1000 ))"
setup
echo "jp.salesanchor.colima-idle-stop" > "${D}/fake/absent"
old_t=$(( NOW - 90000 ))
printf 'unloaded:jp.salesanchor.colima-idle-stop\t%s\n' "${old_t}" > "${D}/state/problems"
echo 1 > "${D}/fake/curl.rc"
run_mjw; rc=$?
eq "㉖-8 ②送信失敗: 終了 3" "${rc}" "3"
eq "㉖-9 ②送信失敗: 最後に知らせた時刻を変えない" "$(grep -c -F "${old_t}" "${D}/state/problems")" "1"
setup
printf 'unloaded:jp.salesanchor.removed\t%s\n' "$(( NOW - 100 ))" > "${D}/state/problems"
echo 1 > "${D}/fake/curl.rc"
run_mjw; rc=$?
eq "㉖-10 ③送信失敗: 終了 3" "${rc}" "3"
has_prob "unloaded:jp.salesanchor.removed" && ok "㉖-11 ③送信失敗: 問題を消さない" || ng "㉖-11 ③送信失敗: 問題を消さない"
setup
mk_state $(( NOW - 1800 )) "${BOOT}" $(( NOW - 60 )) 2 0
colima_line $(( NOW - 30 )) busy d
run_mjw
eq "㉖-12 d が 3 回目: 2 回目の知らせは出ない" "$(ncalls)" "0"
eq "㉖-13 d が 3 回目: colima_d_run=3 を持ち越す" "$(stv colima_d_run)" "3"

# ── ㉗ 自分のログ回転・「起きていた」の境界 ────────────────────────────────────
setup
export MJW_LOG_MAX_BYTES=100
head -c 300 /dev/zero | tr '\0' 'x' > "${D}/mjw.log"
run_mjw
unset MJW_LOG_MAX_BYTES
[ -f "${D}/mjw.log.1" ] && ok "㉗-1 大きいログは .1 に退避" || ng "㉗-1 大きいログは .1 に退避"
eq "㉗-2 退避後の新しいログに 1 行" "$(wc -l < "${D}/mjw.log" | tr -d ' ')" "1"
setup
mk_state $(( NOW - 1920 )) "${BOOT}" $(( NOW - 60 )) 0 0
run_mjw
eq "㉗-3 前回から 1920 秒ちょうど: 起きていた" "$(logc 'awake=1')" "1"
setup
mk_state $(( NOW - 1921 )) "${BOOT}" $(( NOW - 60 )) 0 0
run_mjw
eq "㉗-4 前回から 1921 秒: 起きていない" "$(logc 'awake=0')" "1"

# ── ㉘ --dry-run の problems 欄は今回の判定結果 ───────────────────────────────
setup
echo "jp.salesanchor.colima-idle-stop" > "${D}/fake/absent"
run_mjw --dry-run
eq "㉘-1 dry-run の problems に今回の判定結果が出る" "$(logc 'problems=unloaded:jp.salesanchor.colima-idle-stop')" "1"
setup
run_mjw --dry-run
eq "㉘-2 異常が無ければ problems=-" "$(logc 'problems=-')" "1"

# ── ㉙ curl に時間制限 ────────────────────────────────────────────────────────
setup
echo "jp.salesanchor.colima-idle-stop" > "${D}/fake/absent"
run_mjw
grep -qx -- '--max-time' "${D}/fake/curl.args.1" && grep -qx -- '20' "${D}/fake/curl.args.1" && ok "㉙-1 curl に --max-time 20" || ng "㉙-1 curl に --max-time 20"

echo "----"
echo "PASS=${PASS} FAIL=${FAIL}"
[ "${FAIL}" -eq 0 ]
