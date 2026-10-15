#!/bin/bash
# colima-idle-stop.sh — 使い終わった Colima（profile default）の自動停止
# 設計: docs/handoff/colima-idle-stop/design.md
#
# 15 分ごとに見回り、DB 接続なし・CPU ほぼ 0・操作中プロセスなしが CIS_IDLE_SECONDS 続いたら
# `colima stop -p default` を 1 回だけ実行する。判定に失敗したときは止めない（使用中と同じ扱い）。
#
# 使い方:
#   bash scripts/colima-idle-stop.sh             # 通常（LaunchAgent はこちら）
#   bash scripts/colima-idle-stop.sh --dry-run   # 判定と状態ファイル更新まで。stop だけ実行しない
#
# 設定（CIS_ 環境変数で上書き可。試験用）は cis_config に 1 か所でまとめてある。

set -u

# ── 設定（1か所）─────────────────────────────────────────────────────────────
cis_config() {
  local home_dir="${HOME:-/Users/tanizawashingo}"
  : "${CIS_PROFILE:=default}"
  : "${CIS_IDLE_SECONDS:=1800}"
  : "${CIS_CPU_BUSY:=1.0}"
  : "${CIS_STATE_DIR:=${home_dir}/Library/Application Support/colima-idle-stop}"
  : "${CIS_LOG:=${home_dir}/Library/Logs/colima-idle-stop.log}"
  : "${CIS_LOCK_DIR:=/tmp/colima-idle-stop.lock.d}"
  : "${CIS_LIMA_HOME:=${home_dir}/.colima/_lima}"
  : "${CIS_LIMA_INSTANCE:=colima}"
  : "${CIS_LOG_MAX_BYTES:=1048576}"
}

DRY_RUN=0
LOCK_OWNED=0
NOW=0

cis_log() { # cis_log <result> <reason> <elapsed> <detail>
  local f="${CIS_LOG}" sz
  mkdir -p "$(dirname "${f}")" 2>/dev/null || true
  if [ -f "${f}" ]; then
    sz="$(wc -c < "${f}" 2>/dev/null | tr -d ' ')"
    if [ "${sz:-0}" -gt "${CIS_LOG_MAX_BYTES}" ]; then mv -f -- "${f}" "${f}.1" 2>/dev/null || true; fi
  fi
  printf '%s result=%s reason=%s elapsed=%s detail=%s\n' \
    "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$1" "$2" "$3" "$4" >> "${f}" 2>/dev/null || true
}

cis_cleanup() {
  if [ "${LOCK_OWNED}" -eq 1 ]; then rm -rf -- "${CIS_LOCK_DIR}"; fi
}

# 排他。取れたら 0、生きた持ち主がいる/取れない場合は 1
cis_lock() {
  local pid
  if mkdir "${CIS_LOCK_DIR}" 2>/dev/null; then
    echo "$$" > "${CIS_LOCK_DIR}/pid"
    LOCK_OWNED=1
    return 0
  fi
  pid="$(cat "${CIS_LOCK_DIR}/pid" 2>/dev/null || true)"
  if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
    cis_log skip - - "別の見回りが実行中 (pid=${pid})"
    return 1
  fi
  cis_log skip - - "stale lock removed (pid=${pid:-unknown})"
  rm -rf -- "${CIS_LOCK_DIR}"
  if mkdir "${CIS_LOCK_DIR}" 2>/dev/null; then
    echo "$$" > "${CIS_LOCK_DIR}/pid"
    LOCK_OWNED=1
    return 0
  fi
  cis_log skip - - "ロックを取り直せなかった"
  return 1
}

cis_state_file() { printf '%s/idle-since' "${CIS_STATE_DIR}"; }
cis_state_clear() { rm -f -- "$(cis_state_file)"; }

# 判定失敗（reason=d）。使用中と同じ扱いで状態ファイルを消して終わる
cis_fail_d() { # cis_fail_d <detail>
  cis_state_clear
  cis_log busy d - "判定失敗: $1"
  exit 0
}

cis_busy() { # cis_busy <reason> <detail>
  cis_state_clear
  cis_log busy "$1" - "$2"
  exit 0
}

cis_main() {
  local arg
  for arg in "$@"; do
    case "${arg}" in
      --dry-run) DRY_RUN=1 ;;
      *) echo "unknown option: ${arg}" >&2; exit 2 ;;
    esac
  done
  cis_config
  trap cis_cleanup EXIT
  mkdir -p "${CIS_STATE_DIR}" 2>/dev/null || true

  cis_lock || exit 0

  # 1. 状態
  local st_out st_rc
  st_out="$(colima status -p "${CIS_PROFILE}" 2>&1)"; st_rc=$?
  if [ "${st_rc}" -ne 0 ]; then
    if printf '%s' "${st_out}" | grep -q 'is not running'; then
      cis_state_clear
      cis_log stopped - - "colima は停止中"
      exit 0
    fi
    cis_fail_d "colima status exit=${st_rc}"
  fi

  # 2. c. 操作中プロセス（自分が docker を呼ぶ前に調べる）
  local pat rc
  for pat in \
    '(^|/)docker(-compose)? (compose|run|exec|build|cp|pull|push|start|attach|logs|up)' \
    '(^|/)colima (start|ssh|restart)' \
    '(^|/)psql( |$)'; do
    pgrep -f "${pat}" >/dev/null 2>&1; rc=$?
    if [ "${rc}" -eq 0 ]; then
      cis_busy c "操作中プロセスあり (pattern=${pat})"
    elif [ "${rc}" -ge 2 ]; then
      cis_fail_d "pgrep exit=${rc}"
    fi
  done

  # 3. a. CPU
  local ps_out stats_out names=() images=() name image
  ps_out="$(docker ps --filter status=running --format '{{.Names}}\t{{.Image}}' 2>/dev/null)"; rc=$?
  [ "${rc}" -eq 0 ] || cis_fail_d "docker ps exit=${rc}"
  while IFS=$'\t' read -r name image; do
    [ -n "${name}" ] || continue
    names+=("${name}"); images+=("${image}")
  done <<< "${ps_out}"

  if [ "${#names[@]}" -gt 0 ]; then
    stats_out="$(docker stats --no-stream --format '{{.Name}}\t{{.CPUPerc}}' 2>/dev/null)"; rc=$?
    [ "${rc}" -eq 0 ] || cis_fail_d "docker stats exit=${rc}"
    local cpu
    while IFS=$'\t' read -r name cpu; do
      [ -n "${name}" ] || continue
      cpu="${cpu%\%}"
      printf '%s' "${cpu}" | grep -Eq '^[0-9]+(\.[0-9]+)?$' || cis_fail_d "CPU 値が数値でない (${name})"
      if awk -v c="${cpu}" -v t="${CIS_CPU_BUSY}" 'BEGIN{exit !(c+0 >= t+0)}'; then
        cis_busy a "CPU ${cpu}% (${name})"
      fi
    done <<< "${stats_out}"

    # 4. b. DB 接続
    local i cnt
    for i in "${!names[@]}"; do
      if printf '%s' "${images[$i]}" | grep -Eq '^postgres(:|@|$)'; then
        cnt="$(docker exec "${names[$i]}" sh -c 'psql -U "$POSTGRES_USER" -d postgres -Atc "select count(*) from pg_stat_activity where backend_type = '"'"'client backend'"'"' and pid <> pg_backend_pid()"' 2>/dev/null)"; rc=$?
        [ "${rc}" -eq 0 ] || cis_fail_d "docker exec psql exit=${rc} (${names[$i]})"
        printf '%s' "${cnt}" | grep -Eq '^[0-9]+$' || cis_fail_d "接続数が整数でない (${names[$i]})"
        if [ "${cnt}" -ge 1 ]; then
          cis_busy b "DB 接続 ${cnt} 件 (${names[$i]})"
        fi
      fi
    done
  fi

  # 5. 未使用。VM の同一性（ha.pid）を確かめる
  local hapid_file hapid
  hapid_file="${CIS_LIMA_HOME}/${CIS_LIMA_INSTANCE}/ha.pid"
  hapid="$(tr -d ' \n\r' < "${hapid_file}" 2>/dev/null || true)"
  printf '%s' "${hapid}" | grep -Eq '^[0-9]+$' || cis_fail_d "ha.pid を読めない (${hapid_file})"

  NOW="$(date +%s)"
  local sf rec_ts rec_pid extra elapsed
  sf="$(cis_state_file)"
  rec_ts=""; rec_pid=""; extra=""
  if [ -f "${sf}" ]; then read -r rec_ts rec_pid extra < "${sf}" 2>/dev/null || true; fi
  if ! printf '%s' "${rec_ts}" | grep -Eq '^[0-9]+$' \
     || ! printf '%s' "${rec_pid}" | grep -Eq '^[0-9]+$' \
     || [ -n "${extra}" ] || [ "${rec_pid}" != "${hapid}" ]; then
    printf '%s %s\n' "${NOW}" "${hapid}" > "${sf}"
    cis_log idle - 0 "未使用を初めて記録 (ha.pid=${hapid})"
    exit 0
  fi

  elapsed=$(( NOW - rec_ts ))
  if [ "${elapsed}" -lt "${CIS_IDLE_SECONDS}" ]; then
    cis_log idle - "${elapsed}" "未使用 ${elapsed} 秒 (基準 ${CIS_IDLE_SECONDS} 秒)"
    exit 0
  fi

  if [ "${DRY_RUN}" -eq 1 ]; then
    cis_log would-stop - "${elapsed}" "dry-run のため colima stop を実行しない"
    exit 0
  fi

  local t0 t1 stop_rc after_rc
  t0="$(date +%s)"
  colima stop -p "${CIS_PROFILE}" >/dev/null 2>&1; stop_rc=$?
  t1="$(date +%s)"
  colima status -p "${CIS_PROFILE}" >/dev/null 2>&1; after_rc=$?
  cis_state_clear
  if [ "${stop_rc}" -eq 0 ]; then
    cis_log stop-ok - "${elapsed}" "colima stop exit=0 所要=$(( t1 - t0 ))秒 stop後status_exit=${after_rc}"
    exit 0
  fi
  cis_log stop-fail - "${elapsed}" "colima stop exit=${stop_rc} 所要=$(( t1 - t0 ))秒 stop後status_exit=${after_rc}"
  exit 1
}

# source 時は何も実行しない
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  cis_main "$@"
fi
