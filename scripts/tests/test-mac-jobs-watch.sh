#!/bin/bash
# test-mac-jobs-watch.sh — scripts/mac-jobs-watch.sh の試験（design §4 K1 の ①〜㉙ ＋ disk-low D㉕〜D㉝）
# （phone-missing の P㉞〜P㊸ は末尾。design-phone.md §4）
# （週次点検の NG・未実行 weekly-ng / weekly-missing の W1〜W17 はその後。design-weekly-ng.md §4）
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
if [ "${1:-}" = kickstart ]; then exit "$(cat "${FAKE}/launchctl.kick.rc" 2>/dev/null || echo 0)"; fi
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
cat > "${BIN}/df" <<'EOS'
#!/bin/bash
# 偽 df: 1 行目ヘッダ、2 行目の 4 列目に DF_KB（空なら数字でない出力）
echo "Filesystem 1024-blocks Used Available Capacity Mounted on"
echo "/dev/fake 1000000000 1000 ${DF_KB:-} 1% /System/Volumes/Data"
EOS
cat > "${BIN}/adb" <<'EOS'
#!/bin/bash
# 偽 adb: 呼ばれた引数を adb.calls に書き、adb.out の中身を出す
echo "$*" >> "${FAKE}/adb.calls"
# connect が届いたら、adb.after があれば一覧をそれに入れ替える（つなぎ直しの偽物）
if [ "${1:-}" = connect ] && [ -f "${FAKE}/adb.after" ]; then cp "${FAKE}/adb.after" "${FAKE}/adb.out"; fi
cat "${FAKE}/adb.out" 2>/dev/null
exit 0
EOS
cat > "${BIN}/dns-sd" <<'EOS'
#!/bin/bash
# 偽 dns-sd: -B は dnssd.B、-L <名前> は dnssd.L、-G は dnssd.G の中身を出す（無ければ何も出さない）。
# dnssd.hang があれば出したあと止まらない（本物の dns-sd と同じ）
echo "$*" >> "${FAKE}/dnssd.calls"
case "${1:-}" in
  -B) cat "${FAKE}/dnssd.B" 2>/dev/null ;;
  -L) cat "${FAKE}/dnssd.L" 2>/dev/null ;;
  -G) cat "${FAKE}/dnssd.G" 2>/dev/null ;;
esac
if [ -f "${FAKE}/dnssd.hang" ]; then exec sleep 100; fi
exit 0
EOS
chmod +x "${BIN}/launchctl" "${BIN}/curl" "${BIN}/df" "${BIN}/adb" "${BIN}/dns-sd"
PHONE_SH="${SCRIPT_DIR}/../dev/phone-serial.sh"

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
  export MJW_DF="${BIN}/df"
  export MJW_PHONE_CMD=""
  export PHONE_ADB="${BIN}/adb"
  export PHONE_DNSSD="${BIN}/dns-sd"
  unset PHONE_MODEL PHONE_RECONNECT PHONE_NAME
  export DF_KB=52428800
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

# ── 空き容量（disk-low）。design-disk-low.md §11-3 の D㉕〜D㉝ ──
nkick() { grep -c -F -- "kickstart gui/$(id -u)/jp.salesanchor.disk-janitor" "${D}/fake/launchctl.calls" 2>/dev/null || true; }
at() { set_now $(( $1 )); colima_line $(( NOW - 60 )) idle -; }
G() { export DF_KB=$(( $1 * 1048576 )); }
setup; G 19; T0="${NOW}"
run_mjw
eq "D㉕-1 kickstart 1 回" "$(nkick)" "1"
eq "D㉕-2 送信 0" "$(ncalls)" "0"
eq "D㉕-3 ログ disk-kick send=ok" "$(logc 'result=disk-kick send=ok')" "1"
eq "D㉕-4 状態 disk_kick=NOW" "$(stv disk_kick)" "${T0}"
at $(( T0 + 600 )); run_mjw
eq "D㉖-1 10 分後: kickstart 増えない" "$(nkick)" "1"
eq "D㉖-2 送信 0" "$(ncalls)" "0"
at $(( T0 + 1800 )); run_mjw
eq "D㉗-1 30 分後: 送信 1" "$(ncalls)" "1"
sentmsg 1 | grep -q '空き容量が少ないままです（いま 19 GiB' && ok "D㉗-2 本文" || ng "D㉗-2 本文"
has_prob "disk-low" && ok "D㉗-3 problems=disk-low" || ng "D㉗-3 problems=disk-low"
eq "D㉗-4 kickstart 増えない" "$(nkick)" "1"
# D㉘ 知らせ済みで 22GiB → 26GiB
setup; G 22; printf 'disk-low\t%s\n' "$(( NOW - 3600 ))" > "${D}/state/problems"
run_mjw
eq "D㉘-1 22GiB: 送らない" "$(ncalls)" "0"
has_prob "disk-low" && ok "D㉘-2 problems に残る" || ng "D㉘-2 problems に残る"
G 26; at $(( NOW + 1800 )); run_mjw
eq "D㉘-3 26GiB: 直りました 1 通" "$(ncalls)" "1"
sentmsg 1 | grep -q '直りました' && ok "D㉘-4 復旧文" || ng "D㉘-4 復旧文"
has_prob "disk-low" && ng "D㉘-5 problems から消える" || ok "D㉘-5 problems から消える"
eq "D㉘-6 kickstart 0" "$(nkick)" "0"
# D㉙ 知らせ済みで df が読めない
setup; G 19; printf 'disk-low\t%s\n' "$(( NOW - 3600 ))" > "${D}/state/problems"
export DF_KB=""; run_mjw
eq "D㉙-1 df 不明: 送らない" "$(ncalls)" "0"
has_prob "disk-low" && ok "D㉙-2 problems に残る" || ng "D㉙-2 problems に残る"
# D㉚ 19GiB → 30 分後 40GiB
setup; G 19; T0="${NOW}"; run_mjw
G 40; at $(( T0 + 1800 )); run_mjw
eq "D㉚-1 送信 0" "$(ncalls)" "0"
eq "D㉚-2 problems 空" "$(grep -c . "${D}/state/problems" 2>/dev/null || true)" "0"
eq "D㉚-3 kickstart 1" "$(nkick)" "1"
# D㉛ kickstart 失敗
setup; G 19; T0="${NOW}"; echo 1 > "${D}/fake/launchctl.kick.rc"; run_mjw
eq "D㉛-1 ログ disk-kick send=fail" "$(logc 'result=disk-kick send=fail')" "1"
eq "D㉛-2 状態 disk_kick=NOW（失敗でも記録）" "$(stv disk_kick)" "${T0}"
at $(( T0 + 1800 )); run_mjw
eq "D㉛-3 30 分後: 送信 1" "$(ncalls)" "1"
# D㉜ dry-run
setup; G 19
before_state="$(cksum "${D}/state/state" "${D}/state/problems")"
run_mjw --dry-run
eq "D㉜-1 kickstart 0" "$(nkick)" "0"
eq "D㉜-2 状態不変" "$(cksum "${D}/state/state" "${D}/state/problems")" "${before_state}"
grep -q 'result=dry-run.*events=.*disk-kick' "${D}/mjw.log" && ok "D㉜-3 events に disk-kick" || ng "D㉜-3 events に disk-kick"
eq "D㉜-4 送信 0" "$(ncalls)" "0"
# D㉝ 24h 未満で再び 19GiB → すぐ送信
setup; G 19; T0="${NOW}"; run_mjw
G 40; at $(( T0 + 1800 )); run_mjw
G 19; at $(( T0 + 7200 )); run_mjw
eq "D㉝-1 kickstart 増えない" "$(nkick)" "1"
eq "D㉝-2 すぐ送信 1" "$(ncalls)" "1"
export DF_KB=52428800

# ── phone-missing。design-phone.md §4 の P㉞〜P㊸ ──
PH_AUTO='adb-X-Y._adb-tls-connect._tcp'
PH_NUM='192.168.0.2:40000'
adb_out() { printf '%s\n' "$@" > "${D}/fake/adb.out"; }
adb_line() { printf '%s device product:SC-51G model:%s device:SC-51G transport_id:1' "$1" "${2:-SC_51G}"; }
adb_hdr() { echo "List of devices attached"; }
nadbcalls() { grep -c . "${D}/fake/adb.calls" 2>/dev/null || true; }
# P㉞ 2 行 → 自動のつながりを選ぶ
setup
adb_out "$(adb_hdr)" "$(adb_line "${PH_NUM}")" "$(adb_line "${PH_AUTO}")"
out="$(bash "${PHONE_SH}")"; rc=$?
eq "P㉞-1 終了 0" "${rc}" "0"
eq "P㉞-2 自動のつながりだけ" "${out}" "${PH_AUTO}"
# P㉟ 番号の行 1 行
adb_out "$(adb_hdr)" "$(adb_line "${PH_NUM}")"
out="$(bash "${PHONE_SH}")"; rc=$?
eq "P㉟-1 終了 0" "${rc}" "0"
eq "P㉟-2 その行の名前" "${out}" "${PH_NUM}"
# P㊱ offline / unauthorized / 別機種
adb_out "$(adb_hdr)" "${PH_NUM} offline model:SC_51G" "${PH_AUTO} unauthorized model:SC_51G"
out="$(bash "${PHONE_SH}")"; rc=$?
eq "P㊱-1 offline/unauthorized: 終了 1" "${rc}" "1"
eq "P㊱-2 出力なし" "${out}" ""
adb_out "$(adb_hdr)" "$(adb_line "${PH_NUM}" SM_X999)"
out="$(bash "${PHONE_SH}")"; rc=$?
eq "P㊱-3 別機種: 終了 1" "${rc}" "1"
eq "P㊱-4 出力なし" "${out}" ""
# P㊲ adb が無い
out="$(PHONE_ADB="${D}/no-such-adb" bash "${PHONE_SH}")"; rc=$?
eq "P㊲-1 adb が無い: 終了 2" "${rc}" "2"
eq "P㊲-2 出力なし" "${out}" ""
# P㊳ 偽 adb の引数は devices -l だけ
setup
adb_out "$(adb_hdr)" "$(adb_line "${PH_AUTO}")"
bash "${PHONE_SH}" >/dev/null
eq "P㊳-1 呼び出しは 1 回" "$(nadbcalls)" "1"
eq "P㊳-2 引数は devices -l だけ" "$(cat "${D}/fake/adb.calls")" "devices -l"

# 見張り側。道具は本物の phone-serial.sh、adb は偽
ph_setup() { setup; export MJW_PHONE_CMD="${PHONE_SH}"; }
ph_gone() { adb_out "$(adb_hdr)"; }
ph_here() { adb_out "$(adb_hdr)" "$(adb_line "${PH_AUTO}")"; }
# P㊴ 見えない 1 回目
ph_setup; ph_gone; T0="${NOW}"
run_mjw
eq "P㊴-1 送らない" "$(ncalls)" "0"
eq "P㊴-2 state に phone_gone=NOW" "$(stv phone_gone)" "${T0}"
# P㊵ 3600 秒後も見えない（30 分ごとに起きて見ている）
at $(( T0 + 1800 )); run_mjw
eq "P㊵-0 1800 秒後: まだ送らない" "$(ncalls)" "0"
at $(( T0 + 3600 )); run_mjw
eq "P㊵-1 alert 1 通" "$(ncalls)" "1"
eq "P㊵-2 ログ alert problems=phone-missing" "$(logc 'result=alert send=ok problems=phone-missing')" "1"
sentmsg 1 | grep -q 'ワイヤレスデバッグ' && ok "P㊵-3 文にワイヤレスデバッグ" || ng "P㊵-3 文にワイヤレスデバッグ"
has_prob "phone-missing" && ok "P㊵-4 problems=phone-missing" || ng "P㊵-4 problems=phone-missing"
eq "P㊵-5 phone_gone は最初の時刻のまま" "$(stv phone_gone)" "${T0}"
# P㊶ 見える → 復旧
ph_here; at $(( T0 + 5400 )); run_mjw
eq "P㊶-1 recover 1 通（合計 2）" "$(ncalls)" "2"
sentmsg 2 | grep -q '直りました' && ok "P㊶-2 復旧文" || ng "P㊶-2 復旧文"
eq "P㊶-3 phone_gone=0" "$(stv phone_gone)" "0"
eq "P㊶-4 ログ recover" "$(logc 'result=recover send=ok')" "1"
# P㊷ 眠っていた回（前回から 1920 秒超）。知らせ済み・phone_gone あり
ph_asleep() {
  mk_state $(( NOW - 100000 )) "${BOOT}" $(( NOW - 60 )) 0 0
  printf 'phone_gone=%s\n' "$(( NOW - 7200 ))" >> "${D}/state/state"
  printf 'phone-missing\t%s\n' "$(( NOW - 3600 ))" > "${D}/state/problems"
}
ph_setup; ph_gone; T0="${NOW}"; ph_asleep; run_mjw
eq "P㊷-1 眠っていた回（見えない）: 送らない" "$(ncalls)" "0"
eq "P㊷-2 phone_gone は前回のまま" "$(stv phone_gone)" "$(( T0 - 7200 ))"
has_prob "phone-missing" && ok "P㊷-3 problems は前回のまま" || ng "P㊷-3 problems は前回のまま"
ph_here; ph_asleep; run_mjw
eq "P㊷-4 眠っていた回（見える）: 復旧も出ない" "$(ncalls)" "0"
eq "P㊷-5 phone_gone は前回のまま" "$(stv phone_gone)" "$(( T0 - 7200 ))"
has_prob "phone-missing" && ok "P㊷-6 problems は前回のまま" || ng "P㊷-6 problems は前回のまま"
# P㊸ adb が無い（phone-serial が 2）
ph_setup; T0="${NOW}"; export PHONE_ADB="${D}/no-such-adb"
mk_state $(( NOW - 1800 )) "${BOOT}" $(( NOW - 60 )) 0 0
printf 'phone_gone=%s\n' "$(( T0 - 7200 ))" >> "${D}/state/state"
printf 'phone-missing\t%s\n' "$(( T0 - 3600 ))" > "${D}/state/problems"
run_mjw
eq "P㊸-1 判定しない・送らない" "$(ncalls)" "0"
eq "P㊸-2 phone_gone は前回のまま" "$(stv phone_gone)" "$(( T0 - 7200 ))"
has_prob "phone-missing" && ok "P㊸-3 problems は前回のまま" || ng "P㊸-3 problems は前回のまま"
export PHONE_ADB="${BIN}/adb"
export MJW_PHONE_CMD=""

# ── つなぎ直し。つなぎ直しの設計書 §4 の R1・R2・R3・R5・PHONE_RECONNECT=0 ──
RC_INST='adb-RFGL61DLQCW-IwMTz9'
rc_dnssd() { # rc_dnssd <name=の値>
  printf 'Timestamp     A/R    Flags  if Domain  Service Type  Instance Name\n12:00:00.000  Add        2   4 local.  _adb-tls-connect._tcp.  %s\n' "${RC_INST}" > "${D}/fake/dnssd.B"
  printf 'Lookup %s._adb-tls-connect._tcp.local.\n%s._adb-tls-connect._tcp.local. can be reached at Android.local.:33815 (interface 4)\n name=%s\n' "${RC_INST}" "${RC_INST}" "$1" > "${D}/fake/dnssd.L"
  printf 'Timestamp     A/R    Flags  if Hostname  Address  TTL\n12:00:00.000  Add        2   4 Android.local.  192.168.10.106  120\n' > "${D}/fake/dnssd.G"
}
rc_gone() { adb_out "$(adb_hdr)"; }
rc_back() { printf '%s\n' "$(adb_hdr)" "$(adb_line '192.168.10.106:33815')" > "${D}/fake/adb.after"; }
nconnect() { grep -c '^connect' "${D}/fake/adb.calls" 2>/dev/null || true; }
# R1 一覧に無い・dns-sd に SC-51G が見える → connect 1 回・IP:番号
setup; rc_gone; rc_dnssd SC-51G; rc_back
out="$(bash "${PHONE_SH}")"; rc=$?
eq "R1-1 終了 0" "${rc}" "0"
eq "R1-2 IP:番号を 1 行" "${out}" "192.168.10.106:33815"
eq "R1-3 connect は 1 回" "$(nconnect)" "1"
eq "R1-4 connect の引数" "$(grep '^connect' "${D}/fake/adb.calls")" "connect 192.168.10.106:33815"
# R1 一覧に既にあるときは dns-sd を呼ばない
setup; adb_out "$(adb_hdr)" "$(adb_line "${PH_AUTO}")"; rc_dnssd SC-51G
out="$(bash "${PHONE_SH}")"; rc=$?
eq "R1-5 見えているときは今まで通り" "${out}" "${PH_AUTO}"
eq "R1-6 dns-sd を呼ばない" "$(cat "${D}/fake/dnssd.calls" 2>/dev/null | grep -c . || true)" "0"
# R2 別の Android（name= が違う）には connect しない
setup; rc_gone; rc_dnssd Pixel; rc_back
out="$(bash "${PHONE_SH}")"; rc=$?
eq "R2-1 終了 1" "${rc}" "1"
eq "R2-2 出力なし" "${out}" ""
eq "R2-3 connect 0 回" "$(nconnect)" "0"
# R3 dns-sd にも見えない → 終了 1・connect しない
setup; rc_gone
out="$(bash "${PHONE_SH}")"; rc=$?
eq "R3-1 終了 1" "${rc}" "1"
eq "R3-2 出力なし" "${out}" ""
eq "R3-3 connect 0 回" "$(nconnect)" "0"
# R5 dns-sd が止まらなくても 15 秒以内に終わる
setup; rc_gone; rc_dnssd SC-51G; rc_back; : > "${D}/fake/dnssd.hang"
t0="$(date +%s)"
out="$(bash "${PHONE_SH}")"; rc=$?
t1="$(date +%s)"
[ $(( t1 - t0 )) -le 15 ] && ok "R5-1 15 秒以内に終了" || ng "R5-1 15 秒以内に終了 ($(( t1 - t0 )) 秒)"
eq "R5-2 つなぎ直せて終了 0" "${rc}" "0"
eq "R5-3 IP:番号" "${out}" "192.168.10.106:33815"
# PHONE_RECONNECT=0 → 今まで通り（dns-sd も connect も呼ばない）
setup; rc_gone; rc_dnssd SC-51G; rc_back
out="$(PHONE_RECONNECT=0 bash "${PHONE_SH}")"; rc=$?
eq "RC0-1 終了 1" "${rc}" "1"
eq "RC0-2 connect 0 回" "$(nconnect)" "0"
eq "RC0-3 dns-sd を呼ばない" "$(cat "${D}/fake/dnssd.calls" 2>/dev/null | grep -c . || true)" "0"

# ── 週次点検の NG と未実行（weekly-ng・weekly-missing。design-weekly-ng.md §4 の W1〜W17）──
# 置き場は ${D}/weekly。基準は 2026-11-09（月）19:00。置き場が無ければ判定しないので、既存の試験には影響しない
wk_ts() { date -j -f '%Y-%m-%d %H:%M:%S' "$1" +%s; }
wk_setup() { # wk_setup <日時> [weekly_seen]。置き場を作り、weekly_seen があれば状態に足す
  setup "$(wk_ts "$1")"
  export MJW_WEEKLY_DIR="${D}/weekly"
  mkdir -p "${MJW_WEEKLY_DIR}"
  if [ -n "${2:-}" ]; then printf 'weekly_seen=%s\n' "$2" >> "${D}/state/state"; fi
}
wk_file() { printf 'x\nRESULT=%s\n' "$2" > "${MJW_WEEKLY_DIR}/$1"; } # wk_file <名前> <RESULT= の後ろ>
WK_1109_19="2026-11-09 19:00:00"

# W1 NG が出たら 1 通
wk_setup "${WK_1109_19}" 20261102; wk_file 20261109.txt "NG K1>210"
run_mjw
eq "W1-1 送信 1" "$(ncalls)" "1"
sentmsg 1 | grep -q '入口の文書の週次点検（2026-11-09）が NG でした（K1>210）' && ok "W1-2 本文" || ng "W1-2 本文"
eq "W1-3 weekly_seen=20261109" "$(stv weekly_seen)" "20261109"
eq "W1-4 ログ alert" "$(logc 'result=alert send=ok')" "1"
eq "W1-5 ログ events=weekly-ng" "$(logc 'events=weekly-ng')" "1"
# W2 30 分後は送らない
NOW0="${NOW}"; at $(( NOW0 + 1800 )); run_mjw
eq "W2 30 分後: 送信 0（合計 1 のまま）" "$(ncalls)" "1"
# W3 OK は知らせない
wk_setup "${WK_1109_19}" 20261102; wk_file 20261109.txt "OK"
run_mjw
eq "W3-1 送信 0" "$(ncalls)" "0"
eq "W3-2 weekly_seen=20261109" "$(stv weekly_seen)" "20261109"
# W4 設置直後（weekly_seen が無い）は古い NG を知らせない
wk_setup "2026-11-05 12:00:00"; wk_file 20261102.txt "NG K1>200 K9>6.5k"
run_mjw
eq "W4-1 送信 0" "$(ncalls)" "0"
eq "W4-2 weekly_seen=20261102" "$(stv weekly_seen)" "20261102"
# W5 初回（状態ファイルが無い）
wk_setup "2026-11-05 12:00:00"; wk_file 20261102.txt "NG K1>200 K9>6.5k"
rm -f "${D}/state/state" "${D}/state/problems"
run_mjw
w5n=0; for i in $(seq 1 "$(ncalls)"); do sentmsg "${i}" | grep -q '週次点検' && w5n=$(( w5n + 1 )); done
eq "W5-1 どの本文にも週次点検が無い" "${w5n}" "0"
eq "W5-2 weekly_seen=20261102" "$(stv weekly_seen)" "20261102"
# W6 RESULT= 行が無い間は知らせず、足したら知らせる
wk_setup "2026-11-09 16:30:00" 20261102; wk_file 20261102.txt "OK"; printf 'x\n' > "${MJW_WEEKLY_DIR}/20261109.txt"
run_mjw
eq "W6-1 送信 0" "$(ncalls)" "0"
eq "W6-2 weekly_seen=20261102" "$(stv weekly_seen)" "20261102"
printf 'RESULT=NG K1>210\n' >> "${MJW_WEEKLY_DIR}/20261109.txt"; at $(( NOW + 1800 )); run_mjw
eq "W6-3 足した後: 送信 1" "$(ncalls)" "1"
# W7 送信失敗なら次の回に送り直す
wk_setup "${WK_1109_19}" 20261102; wk_file 20261109.txt "NG K1>210"
echo 1 > "${D}/fake/curl.rc"; run_mjw
eq "W7-1 失敗した回は weekly_seen を進めない" "$(stv weekly_seen)" "20261102"
echo 0 > "${D}/fake/curl.rc"; at $(( NOW + 1800 )); run_mjw
eq "W7-2 次の回で weekly_seen=20261109" "$(stv weekly_seen)" "20261109"
eq "W7-3 ログ alert send=ok" "$(logc 'result=alert send=ok')" "1"
# W8 締め切り（16:00＋2 時間）を過ぎても結果が無い
wk_setup "2026-11-09 18:30:00" 20261102; wk_file 20261102.txt "OK"
run_mjw
eq "W8-1 送信 1" "$(ncalls)" "1"
sentmsg 1 | grep -q '結果が、2 時間たっても出ていません（2026-11-09 の分）' && ok "W8-2 本文" || ng "W8-2 本文"
has_prob "weekly-missing" && ok "W8-3 problems=weekly-missing" || ng "W8-3 problems=weekly-missing"
W8_NOW="${NOW}"
# W10 その後 OK が出たら「直りました」
wk_file 20261109.txt "OK"; at $(( W8_NOW + 1800 )); run_mjw
eq "W10-1 合計 2 通" "$(ncalls)" "2"
sentmsg 2 | grep -q '直りました' && ok "W10-2 復旧文" || ng "W10-2 復旧文"
has_prob "weekly-missing" && ng "W10-3 problems から消える" || ok "W10-3 problems から消える"
eq "W10-4 weekly-ng は出ない" "$(logc 'events=weekly-ng')" "0"
# W11 その後 NG が出たら NG の知らせと「直りました」
wk_setup "2026-11-09 18:30:00" 20261102; wk_file 20261102.txt "OK"; run_mjw
n1="$(ncalls)"; wk_file 20261109.txt "NG K9>7.5k"; at $(( NOW + 1800 )); run_mjw
eq "W11-1 送信 2（NG と復旧）" "$(( $(ncalls) - n1 ))" "2"
# W9 締め切り前は出さない
wk_setup "2026-11-09 17:30:00" 20261102; wk_file 20261102.txt "OK"
run_mjw
eq "W9-1 送信 0" "$(ncalls)" "0"
has_prob "weekly-missing" && ng "W9-2 problems に無い" || ok "W9-2 problems に無い"
# W12 置き場が無ければ出さない
wk_setup "${WK_1109_19}" 20261102; rm -rf "${MJW_WEEKLY_DIR}"
run_mjw
eq "W12-1 送信 0" "$(ncalls)" "0"
has_prob "weekly-missing" && ng "W12-2 problems に無い" || ok "W12-2 problems に無い"
# W13 NG の文から @ < バッククォートを除く
wk_setup "${WK_1109_19}" 20261102; wk_file 20261109.txt 'NG K1>210 <@everyone> `x`'
run_mjw
sentmsg 1 | grep -q 'K1>210' && ok "W13-1 K1>210 は残る" || ng "W13-1 K1>210 は残る"
sentmsg 1 | grep -q '@' && ng "W13-2 @ が無い" || ok "W13-2 @ が無い"
sentmsg 1 | grep -q '<' && ng "W13-3 < が無い" || ok "W13-3 < が無い"
sentmsg 1 | grep -q '`' && ng "W13-4 バッククォートが無い" || ok "W13-4 バッククォートが無い"
# W14 dry-run は送らず状態も変えない
wk_setup "${WK_1109_19}" 20261102; wk_file 20261109.txt "NG K1>210"
before_state="$(cksum "${D}/state/state" "${D}/state/problems")"
run_mjw --dry-run
eq "W14-1 送信 0" "$(ncalls)" "0"
eq "W14-2 状態を変えない" "$(cksum "${D}/state/state" "${D}/state/problems")" "${before_state}"
eq "W14-3 ログ result=dry-run" "$(logc 'result=dry-run')" "1"
eq "W14-4 ログ events=weekly-ng" "$(logc 'events=weekly-ng')" "1"
# W15 25 時間後もまだ無ければ「まだ続いています」
wk_setup "2026-11-09 18:30:00" 20261102; wk_file 20261102.txt "OK"; run_mjw
n1="$(ncalls)"; at $(( NOW + 25 * 3600 )); run_mjw
eq "W15-1 送信 1" "$(( $(ncalls) - n1 ))" "1"
sentmsg "$(ncalls)" | grep -q 'まだ続いています' && ok "W15-2 まだ続いています" || ng "W15-2 まだ続いています"
# W16 日曜: 締め切りは 11/02 の分で、それはある
wk_setup "2026-11-08 12:00:00" 20261102; wk_file 20261102.txt "OK"
run_mjw
eq "W16 日曜: 送信 0" "$(ncalls)" "0"
# W17 試しのファイルは読まない
wk_setup "${WK_1109_19}" 20261102; wk_file 20261109-trial.txt "NG K1>210"
run_mjw
eq "W17-1 weekly-ng は出ない" "$(logc 'events=weekly-ng')" "0"
has_prob "weekly-missing" && ok "W17-2 weekly-missing は出る" || ng "W17-2 weekly-missing は出る"
unset MJW_WEEKLY_DIR

echo "----"
echo "PASS=${PASS} FAIL=${FAIL}"
[ "${FAIL}" -eq 0 ]
