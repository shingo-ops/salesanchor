#!/bin/bash
# test-colima-idle-stop.sh — scripts/colima-idle-stop.sh の試験（T1〜T13）
#
# すべて mktemp -d で作った一時ディレクトリの中だけで動く。偽の colima / docker / pgrep を
# PATH の先頭に置き、CIS_ 環境変数（状態・ログ・ロック・ha.pid）も一時領域へ向ける。
# 実機の Colima・Docker・状態ファイルには触れない。
#
# 実行方法: bash scripts/tests/test-colima-idle-stop.sh
# 終了コード: 0=FAIL が 0 件 / 1=FAIL あり

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="${SCRIPT_DIR}/../colima-idle-stop.sh"
PASS=0
FAIL=0

ok() { echo "PASS: $1"; PASS=$(( PASS + 1 )); }
ng() { echo "FAIL: $1"; FAIL=$(( FAIL + 1 )); }
check() { # check <説明> <コマンド...>
  local desc="$1"; shift
  if "$@"; then ok "${desc}"; else ng "${desc}"; fi
}

T_RAW="$(mktemp -d "${TMPDIR:-/tmp}/colima-idle-stop-test.XXXXXX")" || { echo "mktemp 失敗"; exit 1; }
T="$(cd -P "${T_RAW}" && pwd -P)"
cleanup() {
  case "${T}" in
    */colima-idle-stop-test.*) rm -rf -- "${T}" ;;
  esac
}
trap cleanup EXIT

BIN="${T}/bin"
mkdir -p "${BIN}"

# ── 偽コマンド（挙動は ${FAKE} 配下のファイルで決める）─────────────────────
cat > "${BIN}/colima" <<'EOS'
#!/bin/bash
echo "colima $*" >> "${FAKE}/colima.calls"
case "${1:-}" in
  status) cat "${FAKE}/status.out" 2>/dev/null; exit "$(cat "${FAKE}/status.rc" 2>/dev/null || echo 0)" ;;
  stop)   exit "$(cat "${FAKE}/stop.rc" 2>/dev/null || echo 0)" ;;
esac
exit 0
EOS
cat > "${BIN}/docker" <<'EOS'
#!/bin/bash
echo "docker $*" >> "${FAKE}/docker.calls"
case "${1:-}" in
  ps)    cat "${FAKE}/ps.out" 2>/dev/null; exit "$(cat "${FAKE}/ps.rc" 2>/dev/null || echo 0)" ;;
  stats) cat "${FAKE}/stats.out" 2>/dev/null; exit "$(cat "${FAKE}/stats.rc" 2>/dev/null || echo 0)" ;;
  exec)  cat "${FAKE}/exec.out" 2>/dev/null; exit "$(cat "${FAKE}/exec.rc" 2>/dev/null || echo 0)" ;;
esac
exit 0
EOS
cat > "${BIN}/pgrep" <<'EOS'
#!/bin/bash
rc="$(cat "${FAKE}/pgrep.rc" 2>/dev/null || echo 1)"
[ "${rc}" -eq 0 ] && echo 99999
exit "${rc}"
EOS
chmod +x "${BIN}/colima" "${BIN}/docker" "${BIN}/pgrep"

TAB=$'\t'
HAPID=4242

# 各試験の前に作り直す。既定は「起動中・コンテナ postgres 1 つ・CPU 0%・接続 0 件」
setup() {
  FAKE="${T}/fake"; rm -rf "${FAKE}" "${T}/state" "${T}/lock.d" "${T}/lima" "${T}/test.log"
  mkdir -p "${FAKE}" "${T}/state" "${T}/lima/colima"
  export FAKE
  echo 0 > "${FAKE}/status.rc"
  echo 1 > "${FAKE}/pgrep.rc"
  printf 'salesanchor-postgres-1%spostgres:16\n' "${TAB}" > "${FAKE}/ps.out"
  printf 'salesanchor-postgres-1%s0.00%%\n' "${TAB}" > "${FAKE}/stats.out"
  echo 0 > "${FAKE}/exec.out"
  echo "${HAPID}" > "${T}/lima/colima/ha.pid"
}

run_cis() { # run_cis [args...]: 偽コマンド・一時領域の設定で本体を実行
  PATH="${BIN}:${PATH}" \
  CIS_STATE_DIR="${T}/state" CIS_LOG="${T}/test.log" CIS_LOCK_DIR="${T}/lock.d" \
  CIS_LIMA_HOME="${T}/lima" CIS_LIMA_INSTANCE=colima \
  bash "${TARGET}" "$@" > "${T}/run.out" 2>&1
  RC=$?
}

STATE="${T}/state/idle-since"
log_has() { grep -Eq -- "$1" "${T}/test.log"; }
no_stop_call() { ! grep -q '^colima stop' "${FAKE}/colima.calls" 2>/dev/null; }
no_state() { [ ! -e "${STATE}" ]; }
now() { date +%s; }

# T1 停止中
setup
echo 1 > "${FAKE}/status.rc"; echo "FATA[0000] colima is not running" > "${FAKE}/status.out"
touch "${STATE}"
run_cis
check "T1 停止中: result=stopped" log_has 'result=stopped'
check "T1 停止中: stop を呼ばない" no_stop_call
check "T1 停止中: 状態ファイルなし" no_state
check "T1 停止中: exit 0" test "${RC}" -eq 0

# T1b status 失敗だが is not running なし
setup
echo 1 > "${FAKE}/status.rc"; echo "something else broke" > "${FAKE}/status.out"
run_cis
check "T1b 判定失敗: reason=d" log_has 'reason=d'
check "T1b 判定失敗: stop を呼ばない" no_stop_call

# T2 DB 接続 1 件
setup
echo "$(( $(now) - 100 )) ${HAPID}" > "${STATE}"
echo 1 > "${FAKE}/exec.out"
run_cis
check "T2 DB 接続あり: reason=b" log_has 'reason=b'
check "T2 DB 接続あり: 状態ファイルが消える" no_state
check "T2 DB 接続あり: stop を呼ばない" no_stop_call

# T3 CPU 5%
setup
printf 'salesanchor-postgres-1%s5.00%%\n' "${TAB}" > "${FAKE}/stats.out"
run_cis
check "T3 CPU 5%: reason=a" log_has 'reason=a'
check "T3 CPU 5%: stop を呼ばない" no_stop_call

# T4 docker compose 実行中（pgrep が 1 件）。docker が一度も呼ばれない
setup
echo 0 > "${FAKE}/pgrep.rc"
run_cis
check "T4 操作中プロセス: reason=c" log_has 'reason=c'
check "T4 操作中プロセス: 偽 docker が一度も呼ばれない" test ! -e "${FAKE}/docker.calls"
check "T4 操作中プロセス: stop を呼ばない" no_stop_call

# T5 docker stats が失敗
setup
echo 1 > "${FAKE}/stats.rc"
run_cis
check "T5 stats 失敗: reason=d" log_has 'reason=d'
check "T5 stats 失敗: stop を呼ばない" no_stop_call

# T5b psql の出力が整数でない
setup
echo "oops" > "${FAKE}/exec.out"
run_cis
check "T5b 接続数が整数でない: reason=d" log_has 'reason=d'
check "T5b 接続数が整数でない: stop を呼ばない" no_stop_call

# T6 未使用 1 回目
setup
run_cis
check "T6 1回目: 状態ファイルが <epoch> <pid> 形式" grep -Eq "^[0-9]+ ${HAPID}\$" "${STATE}"
check "T6 1回目: stop を呼ばない" no_stop_call
check "T6 1回目: result=idle" log_has 'result=idle'

# T7 未使用で 1800 秒前・同じ PID
setup
echo "$(( $(now) - 1800 )) ${HAPID}" > "${STATE}"
run_cis
check "T7 stop を -p default 付きで 1 回呼ぶ" test "$(grep -c '^colima stop -p default$' "${FAKE}/colima.calls")" -eq 1
check "T7 状態ファイルが消える" no_state
check "T7 result=stop-ok" log_has 'result=stop-ok'

# T8 1790 秒前
setup
echo "$(( $(now) - 1790 )) ${HAPID}" > "${STATE}"
run_cis
check "T8 1790 秒: stop を呼ばない" no_stop_call
check "T8 1790 秒: 状態ファイルは残る" test -e "${STATE}"

# T9 --dry-run
setup
echo "$(( $(now) - 1800 )) ${HAPID}" > "${STATE}"
run_cis --dry-run
check "T9 dry-run: stop を呼ばない" no_stop_call
check "T9 dry-run: result=would-stop" log_has 'result=would-stop'

# T10 3600 秒前だが PID が違う
setup
OLD="$(( $(now) - 3600 ))"
echo "${OLD} 1111" > "${STATE}"
run_cis
check "T10 PID 違い: stop を呼ばない" no_stop_call
check "T10 PID 違い: 新しい PID に書き直す" grep -Eq "^[0-9]+ ${HAPID}\$" "${STATE}"
check "T10 PID 違い: 時刻が新しくなる" test "$(cut -d' ' -f1 "${STATE}")" -gt "${OLD}"

# T11 コンテナ 0 件
setup
: > "${FAKE}/ps.out"
run_cis
check "T11 コンテナ0件: 未使用として状態ファイルを作る" test -e "${STATE}"
check "T11 コンテナ0件: reason=d でない" bash -c "! grep -q 'reason=d' '${T}/test.log'"
check "T11 コンテナ0件: stats を呼ばない" bash -c "! grep -q '^docker stats' '${FAKE}/docker.calls'"

# T12 ロック
setup
mkdir -p "${T}/lock.d"; echo 2147483646 > "${T}/lock.d/pid"
run_cis
check "T12 死んだ PID のロック: stale を記録" log_has 'stale lock removed'
check "T12 死んだ PID のロック: 実行される" test -e "${STATE}"
setup
mkdir -p "${T}/lock.d"; echo $$ > "${T}/lock.d/pid"
run_cis
check "T12 生きた PID のロック: result=skip" log_has 'result=skip'
check "T12 生きた PID のロック: 実行されない" no_state
check "T12 生きた PID のロック: exit 0" test "${RC}" -eq 0
check "T12 生きた PID のロック: ロックを消さない" test -d "${T}/lock.d"

# T13 ha.pid が無い
setup
rm -f "${T}/lima/colima/ha.pid"
echo "$(( $(now) - 3600 )) ${HAPID}" > "${STATE}"
run_cis
check "T13 ha.pid なし: reason=d" log_has 'reason=d'
check "T13 ha.pid なし: stop を呼ばない" no_stop_call

echo "---"
echo "PASS=${PASS} FAIL=${FAIL}"
[ "${FAIL}" -eq 0 ]
