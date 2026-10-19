#!/bin/bash
# PO 用: 権限の足し引きの道具（perm-change.py）を Opus が通せるようにする例外の文 PDL-1 を 外す（ADR-1034 §4-6）。
# - 第1引数: この変更を載せた便1の PR 番号（例: 4560 または PR#4560）。必須（台帳の po_ref になる）。
# - 第2引数: settings.json のパス（省略時は ~/.claude/settings.json。試験用に差し替え可）
# - settings.json を .bak-<日時> に写してから変更し、読み直して確かめる。
# - 変更したときだけ、台帳に record を書く（SKIP_RECORD=1 で飛ばす）。
set -euo pipefail

PR="${1:-}"
SETTINGS="${2:-$HOME/.claude/settings.json}"
HERE="$(cd "$(dirname "$0")" && pwd)"
DESIGN="${HERE}/design.md"
AUDIT="${HERE}/../../../scripts/dev/consent-audit.py"
STAMP="$(date +%Y%m%d%H%M%S)"

PR="${PR#PR#}"
if ! [[ "${PR}" =~ ^[0-9]+$ ]]; then
  echo "ERROR: 第1引数に便1の PR 番号を渡してください（例: 4560）。" >&2
  exit 1
fi
if [ ! -f "${SETTINGS}" ]; then
  echo "ERROR: ${SETTINGS} が見つかりません。" >&2
  exit 1
fi

BACKUP="${SETTINGS}.bak-${STAMP}"
cp -p "${SETTINGS}" "${BACKUP}"
echo "backup: ${BACKUP}"

OUT="$(python3 -I -B "${HERE}/po_delegation_edit.py" unregister "${SETTINGS}" "${DESIGN}" "${AUDIT}")" || {
  echo "${OUT:-}"
  echo "ERROR: 変更に失敗。控えから戻します。" >&2
  cp -p "${BACKUP}" "${SETTINGS}"
  exit 1
}
echo "${OUT}"

if [ "${SKIP_RECORD:-}" = "1" ]; then
  echo "record: skipped (SKIP_RECORD=1)"
  exit 0
fi
if ! echo "${OUT}" | grep -q '^CHANGED=yes$'; then
  echo "record: 変更が無かったので台帳には書きません"
  exit 0
fi
HASH="$(echo "${OUT}" | sed -n 's/^HASH=//p')"
cd "$HOME/.salesanchor-tools" && python3 -I -B scripts/dev/perm-change.py record --target user-automode-allow --op remove --item-hash "${HASH}" --po-ref "PR#${PR}" --actor po-script
