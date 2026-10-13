#!/bin/bash
# PO 用: 許可の自律保守の例外の文（設計書 §5-2）を settings.json の autoMode.allow の末尾に1件追記する。
# - 文は実行のたびに設計書 §5-2 から読む（直書きしない）
# - settings.json を settings.json.bak-<日時> に写してから追記する
# - 同じ文が既にあれば何もしない
# - 追記後に claude auto-mode critique を実行し、出力を保存する（失敗しても登録は戻さない）
# 第1引数で settings.json のパスを差し替えられる（試験用）。SM_SKIP_CRITIQUE=1 で critique を飛ばす。
set -euo pipefail

SETTINGS="${1:-/Users/tanizawashingo/.claude/settings.json}"
HERE="$(cd "$(dirname "$0")" && pwd)"
DESIGN="${HERE}/self-maintenance-design.md"
STAMP="$(date +%Y%m%d%H%M%S)"

if [ ! -f "${SETTINGS}" ]; then
  echo "ERROR: ${SETTINGS} が見つかりません。" >&2
  exit 1
fi

BACKUP="${SETTINGS}.bak-${STAMP}"
cp -p "${SETTINGS}" "${BACKUP}"
echo "backup: ${BACKUP}"

python3 "${HERE}/po_register_self_maintenance.py" "${SETTINGS}" "${BACKUP}" "${DESIGN}"

if [ "${SM_SKIP_CRITIQUE:-}" = "1" ]; then
  echo "critique: skipped (SM_SKIP_CRITIQUE=1)"
  exit 0
fi

LOGDIR="/Users/tanizawashingo/.claude/logs"
mkdir -p "${LOGDIR}"
OUT="${LOGDIR}/automode-critique-${STAMP}.txt"
if claude auto-mode critique > "${OUT}" 2>&1; then
  echo "critique: saved ${OUT}"
else
  echo "critique: FAILED (登録は戻していません)。出力: ${OUT}"
fi
echo "--- critique 先頭40行 ---"
head -40 "${OUT}"
