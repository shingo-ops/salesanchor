#!/bin/bash
# ledger-view.sh — 台帳の束ね表示: 本体＋active-work.d/ を1枚の表に連結して表示
# 使い方: bash scripts/ledger-view.sh
# 設計: docs/specs/ledger-guard/design-phase2.md §2（KGI-G4の実体）
set -u
GIT_COMMON_DIR="$(git rev-parse --git-common-dir 2>/dev/null)"
if [[ "${GIT_COMMON_DIR}" = /* ]]; then MAIN_REPO_ROOT="$(dirname "${GIT_COMMON_DIR}")"; else MAIN_REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; fi
LEDGER_FILE="${ACTIVE_WORK_FILE:-${MAIN_REPO_ROOT}/.claude-pipeline/active-work.md}"
LEDGER_DIR="${ACTIVE_WORK_DIR:-${MAIN_REPO_ROOT}/.claude-pipeline/active-work.d}"
echo "| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |"
echo "|-----------|--------------|---------|------|-----|------|------|"
N_MAIN=0; N_D=0
if [ -f "${LEDGER_FILE}" ]; then
  while IFS= read -r row; do echo "${row}"; N_MAIN=$((N_MAIN+1)); done < <(
    awk '/^## 現在進行中の作業/{s=1;next} /^##/{s=0} s && /^\|/ {
      l=$0; sep=1; n=split(l,a,"|");
      for(i=2;i<n;i++){x=a[i]; gsub(/[ -]/,"",x); if(length(x)>0){sep=0;break}}
      if(sep==1) next;
      h=a[2]; gsub(/^ +| +$/,"",h); if(h=="ブランチ名") next;
      print l}' "${LEDGER_FILE}")
fi
if [ -d "${LEDGER_DIR}" ]; then
  for f in "${LEDGER_DIR}"/*.md; do
    [ -e "$f" ] || continue
    while IFS= read -r row; do echo "${row}"; N_D=$((N_D+1)); done < <(
      awk '/^\|/ {
        l=$0; sep=1; n=split(l,a,"|");
        for(i=2;i<n;i++){x=a[i]; gsub(/[ -]/,"",x); if(length(x)>0){sep=0;break}}
        if(sep==1) next;
        h=a[2]; gsub(/^ +| +$/,"",h); if(h=="ブランチ名") next;
        print l}' "$f")
  done
fi
echo ""
echo "（本体 ${N_MAIN} 行 ＋ 分割 ${N_D} 行）"
