#!/bin/bash
# PO 用: 許可の自律保守の例外の文（設計書 §5-2）と完全一致する1件を autoMode.allow から外す。
# - settings.json を settings.json.bak-<日時> に写してから外す
# - SM- で始まる文は残す
# 第1引数で settings.json のパスを差し替えられる（試験用）。
set -euo pipefail

SETTINGS="${1:-/Users/tanizawashingo/.claude/settings.json}"
HERE="$(cd "$(dirname "$0")" && pwd)"
DESIGN="${HERE}/self-maintenance-design.md"

if [ ! -f "${SETTINGS}" ]; then
  echo "ERROR: ${SETTINGS} が見つかりません。" >&2
  exit 1
fi

BACKUP="${SETTINGS}.bak-$(date +%Y%m%d%H%M%S)"
cp -p "${SETTINGS}" "${BACKUP}"
echo "backup: ${BACKUP}"

python3 "${HERE}/po_unregister_self_maintenance.py" "${SETTINGS}" "${DESIGN}"
