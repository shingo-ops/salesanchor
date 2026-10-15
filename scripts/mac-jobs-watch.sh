#!/bin/bash
# mac-jobs-watch.sh — Mac の自動お手入れ（Docker 自動停止・毎日の自動片付け）の見張り
# 設計: docs/handoff/mac-jobs-watch/design.md
#
# 30 分ごとに 2 つの常駐の「読み込み」と「ログ」を見て、止まった・失敗したら Discord で知らせる。
# 通知先は ADR-1009 の番人と同じファイル（読むだけ）。URL は画面・ログ・引数に出さない。
#
# 使い方:
#   bash scripts/mac-jobs-watch.sh                # 通常（LaunchAgent はこちら）
#   bash scripts/mac-jobs-watch.sh --dry-run      # 判定してログに 1 行書く。送らず、状態も変えない
#   bash scripts/mac-jobs-watch.sh --test-notify  # 送信の試験を 1 通だけ送る（状態は変えない）
#
# 終了コード: 0=正常 / 2=通知先が読めない・引数が不正 / 3=送信失敗
# 設定（MJW_ 環境変数で上書き可。試験用）は mjw_config に 1 か所でまとめてある。
# bash 3.2（macOS 標準）で動く作りにしてある（連想配列を使わない）。

set -u

# ── 設定（1か所）─────────────────────────────────────────────────────────────
mjw_config() {
  local home_dir="${HOME:-/Users/tanizawashingo}"
  : "${MJW_LABELS:=jp.salesanchor.colima-idle-stop jp.salesanchor.disk-janitor}"
  : "${MJW_SELF_LABEL:=jp.salesanchor.mac-jobs-watch}"
  : "${MJW_COLIMA_LOG:=${home_dir}/Library/Logs/colima-idle-stop.log}"
  : "${MJW_DJ_LOG:=${home_dir}/Library/Logs/disk-janitor.log}"
  : "${MJW_DJ_ERR:=${home_dir}/Library/Logs/disk-janitor.err}"
  : "${MJW_DJ_LOCK:=/tmp/disk-janitor.lock.d}"
  : "${MJW_WEBHOOK_FILE:=${home_dir}/.config/sa-ops-intake/watchdog-webhook}"
  : "${MJW_STATE_DIR:=${home_dir}/Library/Application Support/mac-jobs-watch}"
  : "${MJW_LOG:=${home_dir}/Library/Logs/mac-jobs-watch.log}"
  : "${MJW_LOCK_DIR:=/tmp/mac-jobs-watch.lock.d}"
  : "${MJW_LOG_MAX_BYTES:=1048576}"
  : "${MJW_AWAKE_GAP:=1920}"
  : "${MJW_BOOT_GRACE:=600}"
  : "${MJW_COLIMA_STALE:=5400}"
  : "${MJW_DJ_STALE:=93600}"
  : "${MJW_DJ_UNFINISHED:=7200}"
  : "${MJW_DJ_HOUR:=4}"
  : "${MJW_DJ_GRACE:=3600}"
  : "${MJW_REPEAT_SECONDS:=86400}"
  : "${MJW_LAUNCHCTL:=launchctl}"
  : "${MJW_CURL:=curl}"
  : "${MJW_DISK_PATH:=/System/Volumes/Data}"
  : "${MJW_DISK_LOW_GIB:=20}"
  : "${MJW_DISK_OK_GIB:=25}"
  : "${MJW_DF:=df}"
}

DRY_RUN=0
TEST_NOTIFY=0
LOCK_OWNED=0
NOW=0
BOOT_SEC=0
AWAKE=0
JUST_BOOTED=0
FIRST=0
URL=""
SEND_FAIL=0

# 状態（前回の値）と今回の値
ST_PREV_RUN=""
ST_BOOT=0
ST_SEEN=0
ST_DRUN=0
ST_ERR=0
C_SEEN=0   # 確定した既読位置
C_DRUN=0
C_ERR=0
N_SEEN=0   # 今回の判定で得た候補
N_DRUN=0
N_ERR=0
NEW_BOOT=0
PROB=""    # 1 行 1 件「名前<TAB>最後に知らせた時刻」
DETECTED=""
NEW_LIST=""
REP_LIST=""
REC_LIST=""
EV_LIST=""

# ログ読み取り結果
CL_N=0
CL_LAST=0
CL_T=()
CL_RES=()
CL_RSN=()
DJ_START_T=""
DJ_START_LN=0
DJ_END_LN=0
LAST04=0

STATE_F=""
PROB_F=""

# ── 共通 ────────────────────────────────────────────────────────────────────
mjw_num() { case "${1:-}" in ''|*[!0-9]*) echo 0 ;; *) echo "$1" ;; esac; }

mjw_csv() { # 改行区切りの一覧 → カンマ区切り（空なら -）
  local out
  out="$(printf '%s\n' "$1" | grep -v '^$' | paste -sd, - 2>/dev/null)"
  if [ -n "${out}" ]; then printf '%s' "${out}"; else printf '%s' '-'; fi
}

mjw_log() { # mjw_log <result> <send> <problems> <events> <awake>
  local f="${MJW_LOG}" sz
  mkdir -p "$(dirname "${f}")" 2>/dev/null || true
  if [ -f "${f}" ]; then
    sz="$(wc -c < "${f}" 2>/dev/null | tr -d ' ')"
    if [ "${sz:-0}" -gt "${MJW_LOG_MAX_BYTES}" ]; then mv -f -- "${f}" "${f}.1" 2>/dev/null || true; fi
  fi
  printf '%s result=%s send=%s problems=%s events=%s awake=%s\n' \
    "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$1" "$2" "$3" "$4" "$5" >> "${f}" 2>/dev/null || true
}

mjw_cleanup() {
  if [ "${LOCK_OWNED}" -eq 1 ]; then rm -rf -- "${MJW_LOCK_DIR}"; fi
}

# 排他。取れたら 0、生きた持ち主がいる/取れない場合は 1
mjw_lock() {
  local pid
  if mkdir "${MJW_LOCK_DIR}" 2>/dev/null; then
    echo "$$" > "${MJW_LOCK_DIR}/pid"
    LOCK_OWNED=1
    return 0
  fi
  pid="$(cat "${MJW_LOCK_DIR}/pid" 2>/dev/null || true)"
  if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
    return 1
  fi
  rm -rf -- "${MJW_LOCK_DIR}"
  if mkdir "${MJW_LOCK_DIR}" 2>/dev/null; then
    echo "$$" > "${MJW_LOCK_DIR}/pid"
    LOCK_OWNED=1
    return 0
  fi
  return 1
}

# 送信。URL は標準入力の curl 設定だけで渡す（引数・ログ・画面に出さない）
mjw_send() { # mjw_send <text>
  local s payload
  s="${1//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  payload="{\"content\":\"${s}\"}"
  printf 'url = "%s"\n' "${URL}" | "${MJW_CURL}" -sS -o /dev/null --fail --max-time 20 -X POST \
    -H 'Content-Type: application/json' -d "${payload}" --config - 2>/dev/null
}

mjw_read_webhook() { # 読めて空でなければ 0
  [ -r "${MJW_WEBHOOK_FILE}" ] || return 1
  URL="$(tr -d '[:space:]' < "${MJW_WEBHOOK_FILE}" 2>/dev/null)"
  [ -n "${URL}" ]
}

# ── 一覧・問題の操作 ──────────────────────────────────────────────────────────
list_has() { printf '%s\n' "$1" | grep -Fxq -- "$2"; } # list_has <一覧> <名前>
list_add() { # list_add <変数名> <名前>
  local cur="${!1}"
  if [ -n "${cur}" ]; then printf -v "$1" '%s\n%s' "${cur}" "$2"; else printf -v "$1" '%s' "$2"; fi
}

prob_names() { printf '%s\n' "${PROB}" | cut -f1 | grep -v '^$'; }
prob_time() { printf '%s\n' "${PROB}" | awk -F'\t' -v n="$1" '$1==n{print $2; exit}'; }
prob_del() { PROB="$(printf '%s\n' "${PROB}" | awk -F'\t' -v n="$1" '$1!=n && $1!=""')"; }
prob_set() { # prob_set <名前> <時刻>
  prob_del "$1"
  if [ -n "${PROB}" ]; then PROB="${PROB}"$'\n'"$1"$'\t'"$2"; else PROB="$1"$'\t'"$2"; fi
}

# 判定する回か
mjw_judged() {
  case "$1" in
    unloaded:*) [ "${JUST_BOOTED}" -eq 0 ] ;;
    colima-stale) [ "${AWAKE}" -eq 1 ] ;;
    # dj-stale は、起きていた回・起動が直近 04:00 より前・04:00+猶予以降、の 3 つが揃う回だけ判定する
    dj-stale) [ "${AWAKE}" -eq 1 ] && [ "${BOOT_SEC}" -lt "${LAST04}" ] && [ "${NOW}" -ge $(( LAST04 + MJW_DJ_GRACE )) ] ;;
    disk-low) [ -n "${DISK_GIB}" ] ;;
    *) return 0 ;;
  esac
}

# ── 送る文 ────────────────────────────────────────────────────────────────────
mjw_text() { # 名前 → 固定文
  case "$1" in
    unloaded:*) printf '%s が Mac に読み込まれていません' "${1#unloaded:}" ;;
    colima-stale) printf 'Docker の自動停止が 90 分以上動いていません' ;;
    dj-stale) printf '毎日の自動片付けが 26 時間以上動いていません' ;;
    dj-unfinished) printf '毎日の自動片付けが、始まったまま 2 時間以上終わっていません' ;;
    dj-lock-stale) printf '毎日の自動片付けの使用中の印（/tmp/disk-janitor.lock.d）が 2 時間以上残っています。自動片付けと Docker の自動停止が動けません' ;;
    colima-stopfail) printf 'Docker の自動停止が、停止に失敗しました' ;;
    colima-judge-fail) printf 'Docker の自動停止が、2 回続けて判定に失敗しました' ;;
    disk-low) printf '空き容量が少なくなっています（いま %s GiB。%s GiB を切ると知らせます）' "${DISK_GIB:-?}" "${MJW_DISK_LOW_GIB}" ;;
    dj-err) printf '毎日の自動片付けが、道具の更新に失敗して実行しませんでした' ;;
    *) printf '%s' "$1" ;;
  esac
}

mjw_notice() { # mjw_notice <見出し> <一覧> [末尾に付ける文]
  local out n
  out="🖥️ Mac の見張り: $1"
  while IFS= read -r n; do
    [ -n "${n}" ] || continue
    out="${out}"$'\n'"- $(mjw_text "${n}")${3:-}"
  done <<< "$2"
  out="${out}"$'\n'"ログ: ~/Library/Logs/mac-jobs-watch.log"
  printf '%s' "${out}"
}

mjw_boot_text() {
  local out l state
  out="🖥️ Mac の見張り: 起動後の点検（起動 $(date -r "${BOOT_SEC}" '+%Y-%m-%d %H:%M' 2>/dev/null)）"
  for l in ${MJW_LABELS} ${MJW_SELF_LABEL}; do
    if "${MJW_LAUNCHCTL}" print "gui/$(id -u)/${l}" >/dev/null 2>&1; then state="読み込み済み"; else state="読み込まれていません"; fi
    out="${out}"$'\n'"- ${l}: ${state}"
  done
  out="${out}"$'\n'"ログ: ~/Library/Logs/mac-jobs-watch.log"
  printf '%s' "${out}"
}

# ── 状態 ─────────────────────────────────────────────────────────────────────
mjw_st_get() { sed -n "s/^$1=//p" "${STATE_F}" 2>/dev/null | tail -1; }

mjw_read_state() {
  if [ -f "${STATE_F}" ]; then
    FIRST=0
    ST_PREV_RUN="$(mjw_st_get prev_run)"
    ST_BOOT="$(mjw_num "$(mjw_st_get boot_sec)")"
    ST_SEEN="$(mjw_num "$(mjw_st_get colima_seen)")"
    ST_DRUN="$(mjw_num "$(mjw_st_get colima_d_run)")"
    ST_ERR="$(mjw_num "$(mjw_st_get dj_err_seen)")"
    PROB="$(grep -v '^$' "${PROB_F}" 2>/dev/null || true)"
  else
    FIRST=1
    ST_PREV_RUN=""
    ST_BOOT=0
    ST_SEEN=0
    ST_DRUN=0
    ST_ERR=0
    PROB=""
  fi
}

mjw_write_state() {
  mkdir -p "${MJW_STATE_DIR}" 2>/dev/null || true
  {
    printf 'prev_run=%s\n' "${NOW}"
    printf 'boot_sec=%s\n' "${NEW_BOOT}"
    printf 'colima_seen=%s\n' "${C_SEEN}"
    printf 'colima_d_run=%s\n' "${C_DRUN}"
    printf 'dj_err_seen=%s\n' "${C_ERR}"
  } > "${STATE_F}.tmp" 2>/dev/null && mv -f -- "${STATE_F}.tmp" "${STATE_F}"
  printf '%s\n' "${PROB}" | grep -v '^$' > "${PROB_F}.tmp" 2>/dev/null
  mv -f -- "${PROB_F}.tmp" "${PROB_F}" 2>/dev/null || true
}

# ── ログの読み取り ────────────────────────────────────────────────────────────
mjw_colima_parse() {
  CL_N=0
  CL_LAST=0
  CL_T=()
  CL_RES=()
  CL_RSN=()
  [ -r "${MJW_COLIMA_LOG}" ] || return 0
  local line ts t res rsn l2
  while IFS= read -r line; do
    ts="${line%% *}"
    t="$(date -j -f "%Y-%m-%dT%H:%M:%S%z" "${ts}" +%s 2>/dev/null)" || continue
    case "${t}" in ''|*[!0-9]*) continue ;; esac
    l2=" ${line}"
    res=""; rsn=""
    case "${l2}" in *" result="*) res="${l2#* result=}"; res="${res%% *}" ;; esac
    case "${l2}" in *" reason="*) rsn="${l2#* reason=}"; rsn="${rsn%% *}" ;; esac
    CL_T[CL_N]="${t}"
    CL_RES[CL_N]="${res}"
    CL_RSN[CL_N]="${rsn}"
    CL_N=$(( CL_N + 1 ))
    CL_LAST="${t}"
  done < <(tail -n 300 "${MJW_COLIMA_LOG}" 2>/dev/null)
}

mjw_dj_parse() {
  DJ_START_T=""
  DJ_START_LN=0
  DJ_END_LN=0
  [ -r "${MJW_DJ_LOG}" ] || return 0
  local sl el rest d e
  sl="$(grep -n '^===== disk-janitor 開始 ' "${MJW_DJ_LOG}" 2>/dev/null | tail -1)"
  if [ -n "${sl}" ]; then
    DJ_START_LN="${sl%%:*}"
    rest="${sl#*:}"
    read -r _ _ _ d e _ <<< "${rest}"
    DJ_START_T="$(date -j -f "%Y-%m-%d %H:%M:%S" "${d} ${e}" +%s 2>/dev/null)" || DJ_START_T=""
    case "${DJ_START_T}" in ''|*[!0-9]*) DJ_START_T=""; DJ_START_LN=0 ;; esac
  fi
  el="$(grep -n '^===== disk-janitor 終了 ' "${MJW_DJ_LOG}" 2>/dev/null | tail -1)"
  if [ -n "${el}" ]; then DJ_END_LN="${el%%:*}"; fi
}

mjw_disk_parse() { # DISK_GIB に空き GiB（整数・切り捨て）。読めなければ空
  local kb
  DISK_GIB=""
  kb="$("${MJW_DF}" -k "${MJW_DISK_PATH}" 2>/dev/null | awk 'NR==2{print $4}')"
  case "${kb}" in ''|*[!0-9]*) return 0 ;; esac
  DISK_GIB=$(( kb / 1048576 ))
}

# ── 判定 ─────────────────────────────────────────────────────────────────────
mjw_detect_states() {
  DETECTED=""
  local l mt lim
  # unloaded:*
  if [ "${JUST_BOOTED}" -eq 0 ]; then
    for l in ${MJW_LABELS}; do
      if ! "${MJW_LAUNCHCTL}" print "gui/$(id -u)/${l}" >/dev/null 2>&1; then
        list_add DETECTED "unloaded:${l}"
      fi
    done
  fi
  mjw_colima_parse
  mjw_dj_parse
  # colima-stale
  if [ "${AWAKE}" -eq 1 ]; then
    if [ "${CL_LAST}" -eq 0 ] || [ $(( NOW - CL_LAST )) -gt "${MJW_COLIMA_STALE}" ]; then
      list_add DETECTED colima-stale
    fi
  fi
  # dj-stale
  LAST04="$(date -j -r "${NOW}" -v"${MJW_DJ_HOUR}"H -v0M -v0S +%s 2>/dev/null)"
  LAST04="$(mjw_num "${LAST04}")"
  if [ "${LAST04}" -gt "${NOW}" ]; then LAST04=$(( LAST04 - 86400 )); fi
  if mjw_judged dj-stale; then
    if [ -z "${DJ_START_T}" ] || [ $(( NOW - DJ_START_T )) -gt "${MJW_DJ_STALE}" ]; then
      list_add DETECTED dj-stale
    fi
  fi
  # dj-unfinished
  if [ -n "${DJ_START_T}" ] && [ "${DJ_END_LN}" -le "${DJ_START_LN}" ] \
     && [ $(( NOW - DJ_START_T )) -gt "${MJW_DJ_UNFINISHED}" ]; then
    list_add DETECTED dj-unfinished
  fi
  # dj-lock-stale
  if [ -d "${MJW_DJ_LOCK}" ]; then
    mt="$(mjw_num "$(stat -f %m "${MJW_DJ_LOCK}" 2>/dev/null)")"
    if [ $(( NOW - mt )) -gt "${MJW_DJ_UNFINISHED}" ]; then list_add DETECTED dj-lock-stale; fi
  fi
  # disk-low（知らせ済みなら 25GiB 以上に戻るまで続いている扱い）
  mjw_disk_parse
  if [ -n "${DISK_GIB}" ]; then
    if [ -n "$(prob_time disk-low)" ]; then lim="${MJW_DISK_OK_GIB}"; else lim="${MJW_DISK_LOW_GIB}"; fi
    if [ "${DISK_GIB}" -lt "${lim}" ]; then list_add DETECTED disk-low; fi
  fi
}

mjw_detect_events() {
  EV_LIST=""
  local i run sf=0 jf=0 t res rsn m
  N_SEEN="${ST_SEEN}"
  N_DRUN="${ST_DRUN}"
  N_ERR="${ST_ERR}"
  if [ "${FIRST}" -eq 1 ]; then
    N_SEEN="${CL_LAST}"
    N_DRUN=0
    N_ERR=0
    if [ -e "${MJW_DJ_ERR}" ]; then N_ERR="$(mjw_num "$(stat -f %m "${MJW_DJ_ERR}" 2>/dev/null)")"; fi
    return 0
  fi
  run="${ST_DRUN}"
  i=0
  while [ "${i}" -lt "${CL_N}" ]; do
    t="${CL_T[i]}"; res="${CL_RES[i]}"; rsn="${CL_RSN[i]}"
    i=$(( i + 1 ))
    [ "${t}" -gt "${ST_SEEN}" ] || continue
    if [ "${res}" = "stop-fail" ]; then sf=1; fi
    if [ "${res}" != "skip" ]; then
      if [ "${rsn}" = "d" ]; then run=$(( run + 1 )); else run=0; fi
      if [ "${run}" -eq 2 ]; then jf=1; fi
    fi
  done
  if [ "${CL_LAST}" -gt "${ST_SEEN}" ]; then N_SEEN="${CL_LAST}"; fi
  N_DRUN="${run}"
  if [ "${sf}" -eq 1 ]; then list_add EV_LIST colima-stopfail; fi
  if [ "${jf}" -eq 1 ]; then list_add EV_LIST colima-judge-fail; fi
  if [ -e "${MJW_DJ_ERR}" ]; then
    m="$(mjw_num "$(stat -f %m "${MJW_DJ_ERR}" 2>/dev/null)")"
    if [ "${m}" -gt "${ST_ERR}" ]; then
      N_ERR="${m}"
      if [ -s "${MJW_DJ_ERR}" ]; then list_add EV_LIST dj-err; fi
    fi
  fi
}

# 前回の問題との突き合わせ → NEW_LIST / REP_LIST / REC_LIST
mjw_classify() {
  NEW_LIST=""; REP_LIST=""; REC_LIST=""
  local n t
  while IFS= read -r n; do
    [ -n "${n}" ] || continue
    t="$(prob_time "${n}")"
    if [ -z "${t}" ]; then
      list_add NEW_LIST "${n}"
    elif [ $(( NOW - $(mjw_num "${t}") )) -ge "${MJW_REPEAT_SECONDS}" ]; then
      list_add REP_LIST "${n}"
    fi
  done <<< "${DETECTED}"
  while IFS= read -r n; do
    [ -n "${n}" ] || continue
    if mjw_judged "${n}" && ! list_has "${DETECTED}" "${n}"; then list_add REC_LIST "${n}"; fi
  done <<< "$(prob_names)"
}

mjw_commit_events() { C_SEEN="${N_SEEN}"; C_DRUN="${N_DRUN}"; C_ERR="${N_ERR}"; }

# ── 本体 ─────────────────────────────────────────────────────────────────────
mjw_log_now() { # mjw_log_now <result> <send>
  mjw_log "$1" "$2" "$(mjw_csv "$(prob_names)")" "$(mjw_csv "${EV_LIST}")" "${AWAKE}"
}

mjw_main() {
  local arg n txt any_sent=0
  for arg in "$@"; do
    case "${arg}" in
      --dry-run) DRY_RUN=1 ;;
      --test-notify) TEST_NOTIFY=1 ;;
      *) echo "unknown option: ${arg}" >&2; exit 2 ;;
    esac
  done
  mjw_config
  export LC_ALL=en_US.UTF-8
  NOW="$(mjw_num "${MJW_NOW:-$(date +%s)}")"
  if [ -n "${MJW_BOOT_SEC:-}" ]; then
    BOOT_SEC="$(mjw_num "${MJW_BOOT_SEC}")"
  else
    BOOT_SEC="$(mjw_num "$(sysctl -n kern.boottime 2>/dev/null | sed -n 's/.*sec = \([0-9]*\).*/\1/p')")"
  fi
  STATE_F="${MJW_STATE_DIR}/state"
  PROB_F="${MJW_STATE_DIR}/problems"

  if [ "${TEST_NOTIFY}" -eq 1 ]; then
    if ! mjw_read_webhook; then
      mjw_log no-webhook - - - -
      exit 2
    fi
    if mjw_send "🖥️ Mac の見張り: 送信の試験です"; then
      mjw_log test ok - - -
      exit 0
    fi
    mjw_log test fail - - -
    exit 3
  fi

  if [ "${DRY_RUN}" -eq 0 ]; then
    trap mjw_cleanup EXIT
    if ! mjw_lock; then
      mjw_log skip - - - -
      exit 0
    fi
    if ! mjw_read_webhook; then
      mjw_log no-webhook - - - -
      exit 2
    fi
  fi

  mjw_read_state
  if [ -n "${ST_PREV_RUN}" ] && [ $(( NOW - $(mjw_num "${ST_PREV_RUN}") )) -le "${MJW_AWAKE_GAP}" ]; then AWAKE=1; else AWAKE=0; fi
  if [ $(( NOW - BOOT_SEC )) -lt "${MJW_BOOT_GRACE}" ]; then JUST_BOOTED=1; else JUST_BOOTED=0; fi

  mjw_detect_states
  mjw_detect_events
  C_SEEN="${ST_SEEN}"; C_DRUN="${ST_DRUN}"; C_ERR="${ST_ERR}"
  if [ "${FIRST}" -eq 1 ]; then mjw_commit_events; fi
  NEW_BOOT="${ST_BOOT}"
  mjw_classify

  if [ "${DRY_RUN}" -eq 1 ]; then
    mjw_log dry-run - "$(mjw_csv "${DETECTED}")" "$(mjw_csv "${EV_LIST}")" "${AWAKE}"
    exit 0
  fi

  # 起動後の点検
  if [ "${JUST_BOOTED}" -eq 0 ] && [ "${BOOT_SEC}" != "${ST_BOOT}" ]; then
    txt="$(mjw_boot_text)"
    if mjw_send "${txt}"; then
      NEW_BOOT="${BOOT_SEC}"; any_sent=1; mjw_log_now boot-notice ok
    else
      SEND_FAIL=1; any_sent=1; mjw_log_now boot-notice fail
    fi
  fi

  # 出来事が無ければ既読位置は進めてよい
  if [ -z "${EV_LIST}" ]; then mjw_commit_events; fi

  # ① 異常（新しい状態型 ＋ 出来事型）
  if [ -n "${NEW_LIST}${EV_LIST}" ]; then
    txt="$(mjw_notice '⚠️ 異常' "$(printf '%s\n%s' "${NEW_LIST}" "${EV_LIST}")")"
    if mjw_send "${txt}"; then
      while IFS= read -r n; do [ -n "${n}" ] && prob_set "${n}" "${NOW}"; done <<< "${NEW_LIST}"
      mjw_commit_events
      any_sent=1; mjw_log_now alert ok
    else
      SEND_FAIL=1; any_sent=1; mjw_log_now alert fail
    fi
  fi

  # ② まだ続いています
  if [ -n "${REP_LIST}" ]; then
    txt="$(mjw_notice '⚠️ まだ続いています' "${REP_LIST}")"
    if mjw_send "${txt}"; then
      while IFS= read -r n; do [ -n "${n}" ] && prob_set "${n}" "${NOW}"; done <<< "${REP_LIST}"
      any_sent=1; mjw_log_now repeat ok
    else
      SEND_FAIL=1; any_sent=1; mjw_log_now repeat fail
    fi
  fi

  # ③ 復旧
  if [ -n "${REC_LIST}" ]; then
    txt="$(mjw_notice '✅ 復旧' "${REC_LIST}" ' → 直りました')"
    if mjw_send "${txt}"; then
      while IFS= read -r n; do [ -n "${n}" ] && prob_del "${n}"; done <<< "${REC_LIST}"
      any_sent=1; mjw_log_now recover ok
    else
      SEND_FAIL=1; any_sent=1; mjw_log_now recover fail
    fi
  fi

  if [ "${any_sent}" -eq 0 ]; then mjw_log_now ok -; fi
  mjw_write_state
  if [ "${SEND_FAIL}" -eq 1 ]; then exit 3; fi
  exit 0
}

# source された場合は main を走らせない（試験用）
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  mjw_main "$@"
fi
