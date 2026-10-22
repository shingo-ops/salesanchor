#!/bin/bash
[ "$CLAUDE_CODE_REMOTE" = "true" ] || exit 0
# 新規（クラウドでだけ動く入口）。段階1 便1 / docs/handoff/cloud-parity/card-1.md
# 標準入力の hook JSON を一度だけ読み、イベントごとに見張りへ振り分ける。
# 止めるときは exit 2、理由は日本語で標準エラーへ。JSON の読み取りは python3（jq に頼らない）。
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT="$(cat)"
EVENT="$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try:
    print(json.load(sys.stdin).get("hook_event_name",""))
except Exception:
    print("")' 2>/dev/null)"

case "$EVENT" in
  PreToolUse)
    printf '%s' "$INPUT" | python3 "$DIR/guard_pre_tool.py"
    exit $?
    ;;
  Stop)
    printf '%s' "$INPUT" | python3 "$DIR/guard_stop.py"
    exit $?
    ;;
  SessionStart)
    python3 "$DIR/session_start.py" "$DIR/rules.md"
    exit 0
    ;;
esac
exit 0
