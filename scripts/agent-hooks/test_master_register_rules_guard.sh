#!/usr/bin/env bash
# master-register-rules-guard.py の試験（design.md §6 T1〜T6）。
# 使い方: bash scripts/agent-hooks/test_master_register_rules_guard.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
export MRR_RULES_FILE="${MRR_RULES_FILE:-$ROOT/docs/specs/product-master/registration-rules.md}"
export CLAUDE_PROJECT_DIR=/repo
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
echo "$O" | grep -q '"permissionDecision": "denyX"' && echo "$O" | grep -q "$ACK" && echo "$O" | grep -q "$RULES_HEAD"; check "T1 deny+全文" $?
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
O="$(mk PreToolUse Bash command 'grep -rn "create_product(" backend' | python3 "$G")"
[ -z "$O" ]; check "T6 grepは素通り" $?
# T7
O="$(mk PreToolUse Bash command "cat > /tmp/x.py <<'EOF'
create_product(x)
EOF" | python3 "$G")"
echo "$O" | grep -q '"permissionDecision": "deny"'; check "T7 cat heredoc書き込みはdeny" $?
# T8 (許容する副作用: リダイレクト付きgrepもdeny)
O="$(mk PreToolUse Bash command 'grep -rn "create_product(" backend > /tmp/out.txt' | python3 "$G")"
echo "$O" | grep -q '"permissionDecision": "deny"'; check "T8 grep+リダイレクトもdeny(許容する副作用)" $?
# T9〜T18: 差し込み条件（doc-agenda-nav 段1。docs/handoff/doc-agenda-nav/card-stage1.md §4-2）
# 出ないこと（無関係4本・境界1本・マスタを含まない1本・無関係1本）
for P in \
  '在庫表の商品名の列幅を直して。あとログイン登録画面のバグも見て' \
  'ユーザー登録フォームで商品一覧が出ない' \
  'マスタ画面の表示が遅い。GitHub に登録してあるワークフローも確認' \
  'Discord の webhook を登録して商品の通知を流す' \
  'マスタを整備して正答率を上げたい。登録はまだしない' \
  '商品を登録して' \
  'PR を作って'; do
  O="$(mk UserPromptSubmit x x "$P" | python3 "$G")"
  [ -z "$O" ]; check "T9-15 出ない: $P" $?
done
# 出ること（関係あり2本・別マスタ1本）
for P in \
  '商品マスタに新しいカードを登録して' \
  '共用マスタへ登録する候補一覧を出して' \
  '販売先を顧客マスタに登録して'; do
  O="$(mk UserPromptSubmit x x "$P" | python3 "$G")"
  echo "$O" | grep -q '"additionalContext"' && echo "$O" | grep -q "$RULES_HEAD"; check "T16-18 出る: $P" $?
done
# T19〜T21: 調査記録の置き場の免除（doc-agenda-nav 段1b。docs/handoff/doc-agenda-nav/card-stage1b.md §4-2）
O="$(mk PreToolUse Write content 'create_product(x) の説明を引用したメモ' "$HOME/CC報告ファイル-keep/x.md" | python3 "$G")"
[ -z "$O" ]; check "T19 記録置き場(keep)への Write は素通り" $?
O="$(mk PreToolUse Write content 'create_product(x) の説明を引用したメモ' /tmp/CC報告ファイル/x.md | python3 "$G")"
[ -z "$O" ]; check "T20 記録置き場(tmp)への Write は素通り" $?
O="$(mk PreToolUse Bash command 'python3 /tmp/CC報告ファイル/x.py create_product(x)' | python3 "$G")"
echo "$O" | grep -q '"permissionDecision": "deny"'; check "T21 Bash の登録コマンドは止まる" $?
# T22〜T28: 免除は決まった場所で始まるときだけ（doc-agenda-nav 段1c。docs/handoff/doc-agenda-nav/card-stage1c.md §4-4）
O="$(mk PreToolUse Write content 'create_product(x)' "$HOME/x/docs/a.py" | python3 "$G")"
echo "$O" | grep -q '"permissionDecision": "deny"'; check "T22 リポジトリの外の docs は止まる" $?
O="$(mk PreToolUse Write content 'create_product(x)' /tmp/CC報告ファイル/x.py | python3 "$G")"
echo "$O" | grep -q '"permissionDecision": "deny"'; check "T23 記録置き場の .py は止まる" $?
O="$(mk PreToolUse Write content 'create_product(x)' "$HOME/worktrees/salesanchor/release-a/docs/a.md" | python3 "$G")"
[ -z "$O" ]; check "T24 作業場所の docs は素通り" $?
O="$(mk PreToolUse Write content 'create_product(x)' /repo/backend/../../tmp/a.py | python3 "$G")"
echo "$O" | grep -q '"permissionDecision": "deny"'; check "T25 .. で外へ出るパスは止まる" $?
O="$(mk PreToolUse Write content 'create_product(x) の説明を引用したメモ' /private/tmp/CC報告ファイル/x.md | python3 "$G")"
[ -z "$O" ]; check "T26 記録置き場(/private/tmp)への .md は素通り" $?
O="$(mk PreToolUse Write content 'create_product(x)' backend/a.py | python3 "$G")"
echo "$O" | grep -q '"permissionDecision": "deny"'; check "T27 絶対パスでないものは止まる" $?
O="$(mk PreToolUse Write content 'create_product(x)' /repo/backend | python3 "$G")"
echo "$O" | grep -q '"permissionDecision": "deny"'; check "T28 段の名前そのもの(下に何も無い)は止まる" $?
exit $FAIL
