#!/usr/bin/env bash
# master-register-rules-guard.py の試験（design.md §6 T1〜T6）。
# 使い方: bash scripts/agent-hooks/test_master_register_rules_guard.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
export MRR_RULES_FILE="${MRR_RULES_FILE:-$ROOT/docs/specs/product-master/registration-rules.md}"
G="$HERE/master-register-rules-guard.py"
ACK="$(python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest()[:8])' "$MRR_RULES_FILE")"
FAIL=0
run() { python3 -c 'import json,sys;print(json.dumps(json.loads(sys.argv[1])))' "$1" | python3 "$G"; }
check() { # name, ok(0/1)
  if [ "$2" = 0 ]; then echo "PASS $1"; else echo "FAIL $1"; FAIL=1; fi
}
mk() { python3 - "$@" <<'PY'
import json,sys
ev,tool,key,val=sys.argv[1:5]
extra=sys.argv[5] if len(sys.argv)>5 else ""
if ev=="UserPromptSubmit":
    print(json.dumps({"hook_event_name":ev,"prompt":val}))
else:
    ti={key:val}
    if extra: ti["file_path"]=extra
    print(json.dumps({"hook_event_name":ev,"tool_name":tool,"tool_input":ti}))
PY
}
RULES_HEAD="$(head -c 60 "$MRR_RULES_FILE" | head -n1)"

# T1
O="$(mk PreToolUse Write content 'create_product(x)' /tmp/a.py | python3 "$G")"
echo "$O" | grep -q '"permissionDecision": "deny"' && echo "$O" | grep -q "$ACK" && echo "$O" | grep -q "$RULES_HEAD"; check "T1 deny+全文" $?
# T2
O="$(mk PreToolUse Write content "# rules-ack: $ACK
create_product(x)" /tmp/a.py | python3 "$G")"
[ -z "$O" ]; check "T2 正しい印はallow(出力なし)" $?
# T3
O="$(mk PreToolUse Write content 'create_product(x)' /repo/backend/app/a.py | python3 "$G")"
[ -z "$O" ]; check "T3 /backend/ は素通り" $?
# T4
O="$(mk UserPromptSubmit x x 'この商品をマスタに登録して' | python3 "$G")"
echo "$O" | grep -q '"additionalContext"' && echo "$O" | grep -q "$RULES_HEAD"; check "T4 additionalContextに全文" $?
# T5
O="$(mk PreToolUse Write content "# rules-ack: 00000000
create_product(x)" /tmp/a.py | python3 "$G")"
echo "$O" | grep -q '"permissionDecision": "deny"'; check "T5 古い印はdeny" $?
# T6
O="$(mk PreToolUse Bash command 'grep -rn create_product backend' | python3 "$G")"
[ -z "$O" ]; check "T6 grepは素通り" $?
# T7
O="$(mk PreToolUse Bash command "cat > /tmp/x.py <<'EOF'
create_product(x)
EOF" | python3 "$G")"
echo "$O" | grep -q '"permissionDecision": "deny"'; check "T7 cat heredoc書き込みはdeny" $?
# T8 (許容する副作用: リダイレクト付きgrepもdeny)
O="$(mk PreToolUse Bash command 'grep -rn create_product backend > /tmp/out.txt' | python3 "$G")"
echo "$O" | grep -q '"permissionDecision": "deny"'; check "T8 grep+リダイレクトもdeny(許容する副作用)" $?
exit $FAIL
