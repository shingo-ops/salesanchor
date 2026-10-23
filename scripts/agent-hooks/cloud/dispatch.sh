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
    print("__INVALID__")' 2>/dev/null)"

case "$EVENT" in
  __INVALID__)
    echo "BLOCKED(cloud): 見張りの入力(JSON)を読めなかったため止めます。" >&2
    exit 2
    ;;
  PreToolUse)
    printf '%s' "$INPUT" | python3 "$DIR/guard_pre_tool.py"
    RC=$?
    if [ "$RC" -ne 0 ] && [ "$RC" -ne 2 ]; then
      echo "BLOCKED(cloud): 見張りの内部エラーのため止めます（終了コード ${RC}）。" >&2
      exit 2
    fi
    exit $RC
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
