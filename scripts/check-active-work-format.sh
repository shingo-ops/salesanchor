#!/bin/bash
set -e

# --dfile <path>: active-work.d/ 単票の検証モード（便1追加・既定動作は不変）
if [ "${1:-}" = "--dfile" ]; then
  DF="${2:-}"
  [ -f "${DF}" ] || { echo "❌ ファイルなし: ${DF}"; exit 1; }
  grep -q '^branch: ' "${DF}" || { echo "❌ branch: 行がありません: ${DF}"; exit 1; }
  BAD=$(awk -F'|' '/^\|/ {
    l=$0; sep=1;
    for(i=2;i<=NF-1;i++){x=$i; gsub(/[ -]/,"",x); if(length(x)>0){sep=0;break}}
    if(sep==1) next;
    h=$2; gsub(/^ +| +$/,"",h); if(h=="ブランチ名") next;
    if(NF-2!=7) print NR": "l}' "${DF}")
  if [ -n "${BAD}" ]; then echo "❌ 7列違反:"; echo "${BAD}"; exit 1; fi
  echo "✅ 単票フォーマット正常: ${DF}"
  exit 0
fi
