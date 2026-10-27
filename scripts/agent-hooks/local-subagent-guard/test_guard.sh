#!/bin/bash
# test_guard.sh — local-subagent-guard (ADR-1046) の受入試験。docs/handoff/local-subagent-guard/design.md §8 の K1〜K8 と cases.md の全例。
#
# 使い方: bash scripts/agent-hooks/local-subagent-guard/test_guard.sh
# 本物の ~/.claude には触れない。HOME は mktemp -d。最後に「合格 N / 不合格 M」を出し、不合格が 1 つでもあれば exit 1。
set -u

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SELF_DIR/../../.." && pwd)"
GUARD="$SELF_DIR/guard.py"
CASES="$REPO/docs/handoff/local-subagent-guard/cases.md"
[ -f "$GUARD" ] || { echo "見つかりません: $GUARD" >&2; exit 2; }
[ -f "$CASES" ] || { echo "見つかりません: $CASES" >&2; exit 2; }

T="$(mktemp -d "${TMPDIR:-/tmp}/local-subagent-guard-test.XXXXXX")"
trap 'rm -rf "$T"' EXIT
export HOME="$T/home"; mkdir -p "$HOME"
export PYTHONDONTWRITEBYTECODE=1
LOG="$HOME/.claude/logs/local-subagent-guard.log"

PASS=0; FAIL=0
ok() { PASS=$((PASS+1)); echo "合格: $1"; }
ng() { FAIL=$((FAIL+1)); echo "不合格: $1 ($2)"; }

# mkjson <agent|main|emptyid> <tool> <command|-> : 入力 JSON を作る
mkjson() {
  python3 -B -c '
import json, sys
who, tool, cmd = sys.argv[1:4]
d = {"tool_name": tool, "tool_input": {} if cmd == "-" else {"command": cmd}}
if who == "agent": d.update(agent_id="t1", agent_type="general-purpose")
elif who == "emptyid": d.update(agent_id="", agent_type="general-purpose")
print(json.dumps(d))' "$@"
}

run() { # <script> <json> -> RC, ERR
  ERR="$(printf '%s' "$2" | python3 -I "$1" 2>&1 >/dev/null)"; RC=$?
}

expect() { # <name> <want rc> <json> [guard]
  run "${4:-$GUARD}" "$3"
  if [ "$RC" = "$2" ]; then ok "$1"; else ng "$1" "rc=$RC want=$2 $ERR"; fi
}

# K1: 担当の道具 6 種
for t in Write Edit MultiEdit NotebookEdit EnterWorktree ExitWorktree; do
  j="$(python3 -B -c 'import json,sys;print(json.dumps({"agent_id":"t1","agent_type":"general-purpose","tool_name":sys.argv[1],"tool_input":{"file_path":"/tmp/x"}}))' "$t")"
  run "$GUARD" "$j"
  if [ "$RC" = 2 ] && echo "$ERR" | grep -q 'ADR-1046' && echo "$ERR" | grep -q '規則 tool'; then ok "K1 $t"; else ng "K1 $t" "rc=$RC $ERR"; fi
done

# K2: 本体（agent_id なし・空文字）は止まらない
j="$(python3 -B -c 'import json;print(json.dumps({"tool_name":"Write","tool_input":{"file_path":"/tmp/x"}}))')"
expect "K2 本体 Write" 0 "$j"
j="$(python3 -B -c 'import json;print(json.dumps({"agent_id":"","tool_name":"Write","tool_input":{"file_path":"/tmp/x"}}))')"
expect "K2 空 agent_id Write" 0 "$j"
for c in 'git commit -m x' 'git push' 'claude -p x' 'bash scripts/dev/executor-preflight.sh'; do
  expect "K2 本体 Bash: $c" 0 "$(mkjson main Bash "$c")"
  expect "K2 空 agent_id Bash: $c" 0 "$(mkjson emptyid Bash "$c")"
done

# K3・K4: cases.md の全例（Bash・Monitor の両方）
python3 -B - "$CASES" "$T" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
out = sys.argv[2]
for name, fname in (("止める例", "block.txt"), ("通す例", "pass.txt")):
    m = re.search(r"^## " + name + r"\s*\n+```\n(.*?)\n```", text, re.S | re.M)
    lines = [l.replace("\\n", "\n") for l in m.group(1).split("\n") if l != ""]
    with open(out + "/" + fname, "w", encoding="utf-8") as f:
        f.write("\0".join(lines))
PY
CASE_OUT="$(python3 -B - "$GUARD" "$T" <<'PY'
import json, subprocess, sys
guard, t = sys.argv[1:3]
res = {"block": [0, 0], "pass": [0, 0]}
for kind, want in (("block", 2), ("pass", 0)):
    cases = open(f"{t}/{kind}.txt", encoding="utf-8").read().split("\0")
    for tool in ("Bash", "Monitor"):
        for c in cases:
            j = json.dumps({"agent_id": "t1", "agent_type": "general-purpose", "tool_name": tool, "tool_input": {"command": c}})
            p = subprocess.run(["python3", "-I", guard], input=j, capture_output=True, text=True)
            if p.returncode == want:
                res[kind][0] += 1
            else:
                res[kind][1] += 1
                print(f"CASE-NG {kind} {tool} rc={p.returncode}: {c!r}")
    print(f"CASE-COUNT {kind} {len(cases)}")
print("CASE-SUM", json.dumps(res))
PY
)"
echo "$CASE_OUT" | grep -E '^CASE-(NG|COUNT)' | head -60
NB="$(echo "$CASE_OUT" | sed -n 's/^CASE-COUNT block //p')"
NP="$(echo "$CASE_OUT" | sed -n 's/^CASE-COUNT pass //p')"
SUM="$(echo "$CASE_OUT" | sed -n 's/^CASE-SUM //p')"
read -r BOK BNG POK PNG <<<"$(python3 -B -c 'import json,sys;d=json.loads(sys.argv[1]);print(d["block"][0],d["block"][1],d["pass"][0],d["pass"][1])' "$SUM")"
PASS=$((PASS+BOK+POK)); FAIL=$((FAIL+BNG+PNG))
echo "K3 止める例 $NB 件 × 2 道具: 合格 $BOK / 不合格 $BNG"
echo "K4 通す例 $NP 件 × 2 道具: 合格 $POK / 不合格 $PNG"
[ "$NB" = 263 ] && [ "$NP" = 218 ] && ok "cases.md の件数（止める 263・通す 218）" || ng "cases.md の件数" "止める=$NB 通す=$NP"

# K3 追加: command が文字列でない → 止まる / K4 追加: Monitor で command が無い → 通る
for tool in Bash Monitor; do
  j="$(python3 -B -c 'import json,sys;print(json.dumps({"agent_id":"t1","tool_name":sys.argv[1],"tool_input":{"command":["git","push"]}}))' "$tool")"
  run "$GUARD" "$j"
  if [ "$RC" = 2 ] && echo "$ERR" | grep -q 'command-not-string'; then ok "K3 command が文字列でない $tool"; else ng "K3 command が文字列でない $tool" "rc=$RC $ERR"; fi
done
expect "K4 Monitor で command が無い" 0 "$(mkjson agent Monitor -)"

# K5: JSON でない入力は通す
expect "K5 JSON でない" 0 'not json {'
expect "K5 JSON だが辞書でない" 0 '[1,2]'
expect "K5 空入力" 0 ''

# K6 ①: python3 -I で ../cloud 置きでも同じディレクトリ置きでも import できる
expect "K6① リポジトリの置き方（../cloud）で止まる" 2 "$(mkjson agent Bash 'git push')"
mkdir -p "$T/installed"
cp "$GUARD" "$REPO/scripts/agent-hooks/cloud/guard_pre_tool.py" "$T/installed/"
expect "K6① 導入後の置き方（同じディレクトリ）で止まる" 2 "$(mkjson agent Bash 'git push')" "$T/installed/guard.py"
expect "K6① 導入後の置き方で読むだけは通る" 0 "$(mkjson agent Bash 'git status')" "$T/installed/guard.py"
# K6 ②: guard.py だけの置き方 → 担当は止まり（import-failed）、本体は通る
mkdir -p "$T/alone"; cp "$GUARD" "$T/alone/"
run "$T/alone/guard.py" "$(mkjson agent Bash 'git status')"
if [ "$RC" = 2 ] && echo "$ERR" | grep -q 'import-failed'; then ok "K6② import 失敗で担当 Bash は止まる"; else ng "K6② 担当" "rc=$RC $ERR"; fi
expect "K6② import 失敗でも本体 Bash は通る" 0 "$(mkjson main Bash 'git status')" "$T/alone/guard.py"

# K7: 止めたとき log に 1 行・命令文は含まれない
rm -rf "$HOME/.claude/logs"
run "$GUARD" "$(mkjson agent Bash 'git push SECRETMARKER')"
if [ "$RC" = 2 ] && [ "$(wc -l < "$LOG")" = 1 ] && ! grep -q 'SECRETMARKER\|git push' "$LOG" \
   && awk -F'\t' 'NF==4 && $2=="general-purpose" && $3=="Bash" && $4=="git-push"' "$LOG" | grep -q .; then
  ok "K7 log に 1 行（命令文なし）"
else ng "K7" "rc=$RC log=$(cat "$LOG" 2>&1)"; fi
run "$GUARD" "$(mkjson main Bash 'git push')"
[ "$(wc -l < "$LOG")" = 1 ] && ok "K7 通したときは log を足さない" || ng "K7 通したとき" "$(cat "$LOG")"

# K8: install / rollback（一時の HOME。リポジトリの中から流す）
export CLAUDE_DIR="$HOME/.claude"
mkdir -p "$CLAUDE_DIR"
python3 -B -c '
import json, os
p = os.path.join(os.environ["CLAUDE_DIR"], "settings.json")
json.dump({"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 /other/hook.py"}]}]}}, open(p, "w"))'
SETTINGS="$CLAUDE_DIR/settings.json"
count() { python3 -B -c '
import json, sys
d = json.load(open(sys.argv[1]))
n = sum(1 for e in d["hooks"]["PreToolUse"] for h in e["hooks"] if "local-subagent-guard/guard.py" in h["command"])
o = sum(1 for e in d["hooks"]["PreToolUse"] for h in e["hooks"] if h["command"] == "python3 /other/hook.py")
print(n, o)' "$SETTINGS"; }
DEST="$CLAUDE_DIR/scripts/local-subagent-guard"
( cd "$REPO" && bash "$SELF_DIR/install.sh" >"$T/i1.out" 2>&1 ) && ( cd "$REPO" && bash "$SELF_DIR/install.sh" >"$T/i2.out" 2>&1 ); IRC=$?
[ "$IRC" = 0 ] && ok "K8 install 2 回とも成功" || ng "K8 install" "$(cat "$T/i1.out" "$T/i2.out" 2>/dev/null | tail -5)"
[ "$(count)" = "1 1" ] && ok "K8 install 2 回でも項目は 1 つ（他の項目は残る）" || ng "K8 項目数" "$(count)"
[ -f "$DEST/installed-from.txt" ] && [ -f "$DEST/guard.py" ] && [ -f "$DEST/guard_pre_tool.py" ] && ok "K8 installed-from.txt と写し" || ng "K8 写し" "$(ls "$DEST" 2>&1)"
grep -q "$(git -C "$REPO" rev-parse HEAD)" "$DEST/installed-from.txt" 2>/dev/null && ok "K8 installed-from.txt に commit" || ng "K8 commit 記録" "-"
ls "$SETTINGS".bak-local-subagent-guard-* >/dev/null 2>&1 && ok "K8 バックアップ" || ng "K8 バックアップ" "-"
expect "K8 導入先の guard.py が動く" 2 "$(mkjson agent Bash 'git push')" "$DEST/guard.py"
( cd "$REPO" && bash "$SELF_DIR/rollback.sh" >"$T/r.out" 2>&1 ); RRC=$?
[ "$RRC" = 0 ] && ok "K8 rollback 成功" || ng "K8 rollback" "$(tail -5 "$T/r.out")"
[ "$(count)" = "0 1" ] && ok "K8 rollback で項目だけ消え、他の項目は残る" || ng "K8 rollback 後の項目" "$(count)"
[ ! -e "$DEST" ] && ok "K8 rollback で写しが消える" || ng "K8 写し" "残っている"
[ -f "$LOG" ] && ok "K8 rollback で log は残る" || ng "K8 log" "消えた"

echo ""
echo "合格 $PASS / 不合格 $FAIL"
[ "$FAIL" = 0 ] || exit 1
