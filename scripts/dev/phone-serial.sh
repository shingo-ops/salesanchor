#!/bin/bash
# phone-serial.sh — 実機スマホ（既定 SC-51G）の今のつなぎ先の名前を 1 行出す
# 設計: docs/handoff/mac-jobs-watch/design-phone.md §3-1
#
# 使い方: adb -s "$(bash scripts/dev/phone-serial.sh)" shell ...
# 見るだけ。つながりを切る・入れ直す命令は使わない（adb devices -l だけ）。
# adb の待ち受け役が動いていなければ、adb devices が待ち受け役を起動する（adb の標準の動き）。
# 終了コード: 0=見つかった / 1=見えない / 2=adb が無い
#
# 設定: PHONE_MODEL（既定 SC_51G。adb devices -l の model: の値）、PHONE_ADB（既定 adb。試験用）
set -u
model="${PHONE_MODEL:-SC_51G}"
adb_cmd="${PHONE_ADB:-adb}"
command -v "${adb_cmd}" >/dev/null 2>&1 || exit 2
list="$("${adb_cmd}" devices -l 2>/dev/null | awk -v m="model:${model}" '$2=="device"{for(i=3;i<=NF;i++) if($i==m){print $1; break}}')"
[ -n "${list}" ] || exit 1
# 名前で探すつながり（番号が変わっても追従する）を先に選ぶ
pick="$(printf '%s\n' "${list}" | grep -m1 -F '._adb-tls-connect._tcp' || true)"
[ -n "${pick}" ] || pick="$(printf '%s\n' "${list}" | head -n 1)"
printf '%s\n' "${pick}"
