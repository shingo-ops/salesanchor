#!/bin/bash
# lessons-view.sh — 教訓の束ね表示: design-partner.md §6本文＋lessons.d/ を連結表示
# 使い方: bash scripts/lessons-view.sh
# 設計: docs/specs/lessons-guard/design.md §1（KGI-L3の実体）
set -u
GIT_COMMON_DIR="$(git rev-parse --git-common-dir 2>/dev/null)"
if [[ "${GIT_COMMON_DIR}" = /* ]]; then MAIN_REPO_ROOT="$(dirname "${GIT_COMMON_DIR}")"; else MAIN_REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; fi
DP_FILE="${MAIN_REPO_ROOT}/docs/ai-agents/design-partner.md"
LESSONS_DIR="${MAIN_REPO_ROOT}/docs/ai-agents/lessons.d"
N_BODY=0; N_POST=0
echo "===== §6 本文（design-partner.md） ====="
if [ -f "${DP_FILE}" ]; then
  while IFS= read -r row; do echo "${row}"; N_BODY=$((N_BODY+1)); done < <(
    awk '/^## 6\. /{s=1} /^## 7\. /{s=0} s' "${DP_FILE}")
fi
echo ""
echo "===== 未清書ポスト（lessons.d/） ====="
for tag in 6-1 6-2 6-3 6-4 6-5; do
  for f in "${LESSONS_DIR}"/*.md; do
    [ -e "$f" ] || continue
    case "$f" in */archive/*) continue;; esac
    if grep -q "^分類: ${tag}" "$f"; then
      echo "--- $(basename "$f") ---"; cat "$f"; echo ""
      N_POST=$((N_POST+1))
    fi
  done
done
for f in "${LESSONS_DIR}"/*.md; do
  [ -e "$f" ] || continue
  case "$f" in */archive/*) continue;; esac
  if ! grep -q "^分類: 6-" "$f"; then
    echo "--- $(basename "$f")（分類タグなし） ---"; cat "$f"; echo ""
    N_POST=$((N_POST+1))
  fi
done
echo "（§6本文 ${N_BODY} 行 ＋ ポスト ${N_POST} 枚）"
if [ "${N_POST}" -gt 20 ]; then
  echo "⚠️ ポストが20枚を超えています。清書便（本体§6への逐語移植）を計画してください。"
fi
