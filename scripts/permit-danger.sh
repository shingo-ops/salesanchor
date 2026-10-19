#!/bin/bash
# 危険操作ワンタイム許可チケット発行スクリプト
# Usage: bash scripts/permit-danger.sh "<operation>"
# 例:    bash scripts/permit-danger.sh "gh pr merge"
#
# ~/.claude/permits/danger-permit-*.json を生成（30分有効・1回消費）

if [ -z "${1:-}" ]; then
  echo "Usage: bash scripts/permit-danger.sh \"<operation>\"" >&2
  echo "例:    bash scripts/permit-danger.sh \"gh pr merge\"" >&2
  exit 1
fi

OP="$1"
PERMITS_DIR="$HOME/.claude/permits"
mkdir -p "$PERMITS_DIR"

SAFE_OP=$(echo "$OP" | tr ' /' '__' | tr -cd '[:alnum:]_-')
TICKET_FILE="$PERMITS_DIR/danger-permit-${SAFE_OP}-$(date -u +%Y%m%dT%H%M%S).json"

python3 - "$OP" "$TICKET_FILE" <<'PYEOF'
import sys, json
from datetime import datetime, timezone, timedelta

op = sys.argv[1]
out = sys.argv[2]

now = datetime.now(timezone.utc)
expires = now + timedelta(minutes=30)

data = {
    "op": op,
    "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "created_by": "manual"
}

with open(out, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ 許可チケット発行: {op}")
print(f"   有効期限: {data['expires_at']} (30分)")
print(f"   ファイル: {out}")
PYEOF
TICKET_RC=$?
[ "$TICKET_RC" -eq 0 ] || exit "$TICKET_RC"

# 発行の記録（ADR-1034 §4-4）。追記に失敗しても券の発行は止めない。
# by: 環境変数 CLAUDECODE があれば "ai"（AI か PO の `!`）、無ければ "human"。
BY="human"
[ -n "${CLAUDECODE:-}" ] && BY="ai"
python3 - "$OP" "$BY" <<'PYEOF' || echo "⚠️ permit_issued の記録に失敗しました（券の発行は完了しています）" >&2
import sys, os, json, hashlib
from datetime import datetime, timezone

op, by = sys.argv[1], sys.argv[2]
log_dir = os.path.join(os.path.expanduser("~"), ".claude", "logs")
os.makedirs(log_dir, exist_ok=True)
row = {
    "type": "permit_issued",
    "op_sha8": hashlib.sha256(op.encode("utf-8")).hexdigest()[:8],
    "by": by,
    "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}
with open(os.path.join(log_dir, "agent-events.jsonl"), "a", encoding="utf-8") as f:
    f.write(json.dumps(row, ensure_ascii=False) + "\n")
PYEOF
exit 0
