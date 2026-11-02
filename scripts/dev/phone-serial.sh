#!/bin/bash
# phone-serial.sh — 実機スマホ（既定 SC-51G）の今のつなぎ先の名前を 1 行出す
# 設計: docs/handoff/mac-jobs-watch/design-phone.md §3-1、つなぎ直し: 同じ場所の「つなぎ直しの設計書」§3
#
# 使い方: adb -s "$(bash scripts/dev/phone-serial.sh)" shell ...
# 切る命令は使わない。一覧に無く、Mac の仕組み（dns-sd）で見えるときだけ adb connect を 1 回呼ぶ（つなぎ直しの設計書）。
# adb の待ち受け役が動いていなければ、adb devices が待ち受け役を起動する（adb の標準の動き）。
# 終了コード: 0=見つかった / 1=見えない / 2=adb が無い
#
# 設定: PHONE_MODEL（既定 SC_51G。adb devices -l の model: の値）、PHONE_ADB（既定 adb。試験用）、
#       PHONE_RECONNECT（既定 1。0 でつなぎ直さない）、PHONE_NAME（既定 SC-51G。dns-sd の name=）、
#       PHONE_DNSSD（既定 dns-sd。試験用）
set -u
model="${PHONE_MODEL:-SC_51G}"
adb_cmd="${PHONE_ADB:-adb}"
name="${PHONE_NAME:-SC-51G}"
dnssd="${PHONE_DNSSD:-dns-sd}"
command -v "${adb_cmd}" >/dev/null 2>&1 || exit 2

find_list() {
  "${adb_cmd}" devices -l 2>/dev/null | awk -v m="model:${model}" '$2=="device"{for(i=3;i<=NF;i++) if($i==m){print $1; break}}'
}

# run_dnssd <出力ファイル> <秒数> <打ち切りの語（空なら秒数まで待つ）> <引数...>
# dns-sd は自分では終わらないので背景で起動し、秒数のあと止める（macOS に timeout 命令が無い）。
# 止めるのは自分が起動したものだけ。
run_dnssd() {
  local out="$1" secs="$2" pat="$3" pid i
  shift 3
  : > "${out}"
  "${dnssd}" "$@" > "${out}" 2>/dev/null &
  pid=$!
  for ((i = 0; i < secs * 4; i++)); do
    sleep 0.25
    if [ -n "${pat}" ] && grep -q -F -- "${pat}" "${out}" 2>/dev/null; then break; fi
  done
  kill "${pid}" 2>/dev/null || true
  wait "${pid}" 2>/dev/null || true
}

# 一覧に無いとき、dns-sd で見えるスマホへ adb connect を 1 回だけ呼ぶ（見つからなければ何もしない）
relink() {
  [ "${PHONE_RECONNECT:-1}" = 0 ] && return 0
  command -v "${dnssd}" >/dev/null 2>&1 || return 0
  local tmp inst hp host port ip start=${SECONDS}
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/phone-serial.XXXXXX")" || return 0
  run_dnssd "${tmp}/b" 3 "" -B _adb-tls-connect._tcp local.
  host=""
  port=""
  while IFS= read -r inst; do
    [ -n "${inst}" ] || continue
    [ $((SECONDS - start)) -le 6 ] || break
    run_dnssd "${tmp}/l" 3 "can be reached at" -L "${inst}" _adb-tls-connect._tcp local.
    if grep -q -F -- "name=${name}" "${tmp}/l"; then
      hp="$(sed -n 's/.*can be reached at \([^ ]*\):\([0-9][0-9]*\).*/\1 \2/p' "${tmp}/l" | head -n 1)"
      host="${hp%% *}"
      port="${hp##* }"
      host="${host%.}"
      if [ -n "${hp}" ] && [ -n "${host}" ] && [ -n "${port}" ]; then break; fi
      host=""
    fi
  done < <(awk '$2=="Add"{print $NF}' "${tmp}/b")
  if [ -n "${host}" ]; then
    run_dnssd "${tmp}/g" 3 "Add" -G v4 "${host}"
    ip="$(awk '$2=="Add"{for(i=3;i<=NF;i++) if($i ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/){print $i; exit}}' "${tmp}/g")"
    if [ -n "${ip}" ]; then "${adb_cmd}" connect "${ip}:${port}" >/dev/null 2>&1 || true; fi
  fi
  rm -f -- "${tmp}/b" "${tmp}/l" "${tmp}/g"
  rmdir -- "${tmp}" 2>/dev/null || true
  return 0
}

list="$(find_list)"
if [ -z "${list}" ]; then
  relink
  list="$(find_list)"
fi
[ -n "${list}" ] || exit 1
# 名前で探すつながり（番号が変わっても追従する）を先に選ぶ
pick="$(printf '%s\n' "${list}" | grep -m1 -F '._adb-tls-connect._tcp' || true)"
[ -n "${pick}" ] || pick="$(printf '%s\n' "${list}" | head -n 1)"
printf '%s\n' "${pick}"
