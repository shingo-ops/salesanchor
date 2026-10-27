#!/bin/bash
# 元: ~/.claude/scripts/card-lint-hook.sh（クラウド用の写し）
# card-lint-hook.sh — UserPromptSubmit から card-lint.sh を呼ぶ
#
# 設置: ~/.claude/settings.json と ~/.codex/hooks.json の両方から呼ぶ。
#       スクリプト本体はこの1本を共有する（既存の4ガードと同じ構造）。
# 入力: 標準入力に JSON。プロンプト本文は .prompt（Claude Code / Codex とも同じ）
# exit 0 = 素通し / 2 = 差し戻し（stderr に理由）
#
# 設計: docs/handoff/design-partner-card-ops/card-lint-design.md
# 検査本体: <リポジトリ>/scripts/card-lint.sh
#
# 安全側の方針:
#   - カードでない入力（END OF CARD を含まない）は必ず素通しする
#   - 検査本体が見つからない・落ちた場合も素通しする（会話を止めない）
#   - クラウド版は warn モードなし。違反（rc=1）なら常に exit 2
set -u

INPUT="$(cat)"

PROMPT="$(printf '%s' "$INPUT" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    sys.stdout.write(d.get('prompt','') or '')
except Exception:
    pass
")"

# プロンプトが取れない場合は素通し（キー名の変更などで壊れても会話を止めない）
if [ -z "${PROMPT}" ]; then
  exit 0
fi

# カードでなければ素通し
case "${PROMPT}" in
  *"END OF CARD"*) ;;
  *) exit 0 ;;
esac

# 検査本体はリポジトリの scripts/card-lint.sh（この写しの 2 つ上の階層）
LINT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/card-lint.sh"
[ -f "$LINT" ] || exit 0

TMP="$(mktemp "${TMPDIR:-/tmp}/cardlint.XXXXXX")"
printf '%s' "${PROMPT}" > "${TMP}"
OUT="$(bash "${LINT}" "${TMP}" 2>&1)"
RC=$?
rm -f "${TMP}"

# 違反なし、または検査自体が落ちた場合は素通し
if [ "${RC}" -ne 1 ]; then
  exit 0
fi

echo "card-lint がカードの不備を検出しました。修正してから貼り直してください。" >&2
echo "${OUT}" >&2
exit 2
