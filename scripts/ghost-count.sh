#!/bin/bash
# ghost-count.sh — 台帳の幽霊（IN_PROGRESSだが実在しない/マージ済みブランチ）を数えるだけの見張り。
# 読み取り専用。何も変更しない。定期job・手動どちらでも叩ける。
# 設計: docs/specs/ledger-guard/README.md（幽霊見張り）
set -u
MAIN_REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
git -C "${MAIN_REPO_ROOT}" fetch --prune --quiet 2>/dev/null || true
git -C "${MAIN_REPO_ROOT}" ls-remote --heads origin | awk '{print $2}' | sed 's#refs/heads/##' | sort -u > /tmp/gc-rb.txt
git -C "${MAIN_REPO_ROOT}" show origin/main:.claude-pipeline/active-work.md \
  | grep "IN_PROGRESS" | awk -F'|' '{print $2}' | tr -d ' ' | grep -E '^[A-Za-z]' | grep -v '^IN_PROGRESS$' | sort -u > /tmp/gc-lip.txt
IP=$(wc -l < /tmp/gc-lip.txt | tr -d ' ')
GHOST=$(comm -23 /tmp/gc-lip.txt /tmp/gc-rb.txt | wc -l | tr -d ' ')
echo "[ghost-count] $(date '+%Y-%m-%d %H:%M') IN_PROGRESS=${IP} 幽霊(実在せず)=${GHOST}"
# 閾値超過で警告（既定20・GHOST_THRESHOLDで注入可）。exit値は変えない（見張りのみ）
TH="${GHOST_THRESHOLD:-20}"
if [ "${GHOST}" -gt "${TH}" ]; then
  echo "[ghost-count][WARN] 幽霊が ${GHOST} 件（閾値 ${TH} 超）— 台帳掃除便を検討してください"
fi
