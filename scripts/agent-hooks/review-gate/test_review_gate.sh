#!/bin/bash
# test_review_gate.sh — review-gate (ADR-1029) の受入試験。docs/handoff/review-gate-hook/design.md §8 を 1 行 1 試験にしたもの。
#
# 使い方: bash scripts/agent-hooks/review-gate/test_review_gate.sh [gate.py と record.py のあるディレクトリ]
#   引数省略時は環境変数 REVIEW_GATE_SCRIPTS、それも無ければこのファイルと同じディレクトリ。
#   install.sh は写した先 (~/.claude/scripts/review-gate) を引数に渡して流す。
#
# 本物の ~/.claude/review-gate には触れない。REVIEW_GATE_DIR は mktemp の一時ディレクトリ、
# REVIEW_GATE_GH は偽 gh。最後に PASS n / FAIL m を出し、FAIL>0 なら exit 1。
set -u

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${1:-${REVIEW_GATE_SCRIPTS:-$SELF_DIR}}"
GATE="$SRC/gate.py"
RECORD="$SRC/record.py"
for f in "$GATE" "$RECORD"; do
  [ -f "$f" ] || { echo "見つかりません: $f" >&2; exit 2; }
done

T="$(mktemp -d "${TMPDIR:-/tmp}/review-gate-test.XXXXXX")"
trap 'rm -rf "$T"' EXIT
export REVIEW_GATE_DIR="$T/gate"
export REVIEW_GATE_GH="$T/fakegh"
export FAKE_HEAD_FILE="$T/head"
export PYTHONDONTWRITEBYTECODE=1
GD="$REVIEW_GATE_DIR"
WORK="$T/work"; mkdir -p "$WORK"
GITWT="$T/gitwt"; mkdir -p "$GITWT"
git -C "$GITWT" init -q 2>/dev/null
echo 1 > "$GITWT/.pr-number"

SHA1=1111111111111111111111111111111111111111
SHA2=2222222222222222222222222222222222222222
echo "$SHA1" > "$FAKE_HEAD_FILE"

cat > "$REVIEW_GATE_GH" <<'EOF'
#!/bin/bash
# 偽 gh: pr view だけ答える。head は $FAKE_HEAD_FILE。$FAKE_GH_FAIL があれば失敗する。
[ -n "${FAKE_GH_FAIL:-}" ] && exit 1
if [ "$1" = "pr" ] && [ "$2" = "view" ]; then
  printf '{"headRefOid":"%s","url":"https://github.com/o/r/pull/%s"}\n' "$(cat "$FAKE_HEAD_FILE")" "$3"
  exit 0
fi
exit 1
EOF
chmod +x "$REVIEW_GATE_GH"

PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "PASS: $1"; }
ng()  { FAIL=$((FAIL+1)); echo "FAIL: $1 ($2)"; }

# JSON を作る
bash_json() { python3 -B -c 'import json,sys;print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]},"cwd":sys.argv[2]}))' "$1" "$2"; }
tool_json() { python3 -B -c 'import json,sys;print(json.dumps({"tool_name":sys.argv[1],"tool_input":json.loads(sys.argv[2]),"cwd":sys.argv[3]}))' "$1" "$2" "$3"; }

run_gate() { # JSON -> $RC / $T/err
  printf '%s' "$1" | python3 -B "$GATE" 2> "$T/err" > /dev/null
  RC=$?
}
clear_records() { rm -rf "$GD/records"; mkdir -p "$GD/records"; }
mk_rec() { # N SHA
  mkdir -p "$GD/records"
  printf '{"pr":%s,"repo":"o/r","head":"%s","verdict":"APPROVE"}' "$1" "$2" > "$GD/records/o__r-$1-$2.json"
}

# expect NAME EXPECTED_RC COMMAND [CWD] [STDERR_PATTERN]
expect() {
  local name="$1" want="$2" cmd="$3" cwd="${4:-$WORK}" pat="${5:-}"
  run_gate "$(bash_json "$cmd" "$cwd")"
  if [ "$RC" != "$want" ]; then ng "$name" "exit $RC, 期待 $want: $(head -c 200 "$T/err")"; return; fi
  if [ -n "$pat" ] && ! grep -q -- "$pat" "$T/err"; then ng "$name" "stderr に '$pat' が無い"; return; fi
  ok "$name"
}
expect_tool() { # NAME WANT TOOL INPUT_JSON
  run_gate "$(tool_json "$3" "$4" "$WORK")"
  [ "$RC" = "$2" ] && ok "$1" || ng "$1" "exit $RC, 期待 $2"
}

# ---------------------------------------------------------------- R1 記録なしは止まる
clear_records
expect "R1 gh pr merge 1 --merge (記録なし)" 2 'gh pr merge 1 --merge' "$WORK" 'Opus の審査役'
expect "R1 check-pr-merge-ready.py 1 release/x" 2 'python3 scripts/dev/check-pr-merge-ready.py 1 release/x'
expect "R1 gh api PUT pulls/1/merge" 2 'gh api -X PUT repos/o/r/pulls/1/merge'
expect "R1 curl PUT api.github.com pulls/1/merge" 2 'curl -X PUT https://api.github.com/repos/o/r/pulls/1/merge'
expect "R1 --disable-auto の後ろに merge" 2 'gh pr merge 1 --disable-auto; gh pr merge 1 --merge'
mk_rec 1 "$SHA1"
expect "R1 && の 2 つ目 (PR2) は記録なし" 2 'gh pr merge 1 --merge && gh pr merge 2 --merge'
clear_records
expect "R1 番号なし gh pr merge --merge" 2 'gh pr merge --merge'
expect "R1 改行の後ろの gh pr merge" 2 $'ls\ngh pr merge 1 --merge'
expect "R1 (gh pr merge 1 --merge)" 2 '(gh pr merge 1 --merge)'
expect "R1 if true; then gh pr merge ...; fi" 2 'if true; then gh pr merge 1 --merge; fi'
expect "R1 /opt/homebrew/bin/gh pr merge" 2 '/opt/homebrew/bin/gh pr merge 1 --merge'
expect "R1 env A=1 gh pr merge" 2 'env A=1 gh pr merge 1 --merge'
expect "R1 bash -c \"gh pr merge ...\"" 2 'bash -c "gh pr merge 1 --merge"'
expect "R1 echo \$(gh pr merge ...)" 2 'echo $(gh pr merge 1 --merge)'
expect "R1 echo \`gh pr merge ...\`" 2 'echo `gh pr merge 1 --merge`'
expect "R1 timeout 120 gh pr merge" 2 'timeout 120 gh pr merge 1 --merge'
expect "R1 xargs gh pr merge" 2 'echo 1 | xargs gh pr merge'
expect "R1 sudo gh pr merge" 2 'sudo gh pr merge 1 --merge'
expect "R1 caffeinate -i gh pr merge" 2 'caffeinate -i gh pr merge 1 --merge'
expect "R1 timeout 60 bash scripts/gh-pr-merge-safe.sh" 2 'timeout 60 bash scripts/gh-pr-merge-safe.sh --merge' "$GITWT"
expect "R1 bash <<'EOF' で gh pr merge を渡す" 2 $'bash <<\'EOF\'\ngh pr merge 1 --merge\nEOF'
expect "R1 echo \"gh pr merge ...\" | bash" 2 'echo "gh pr merge 1 --merge" | bash'

# ---------------------------------------------------------------- R2 記録ありは通る
mk_rec 1 "$SHA1"
expect "R2 gh pr merge 1 --merge (記録あり)" 0 'gh pr merge 1 --merge'
clear_records
expect "R2 .pr-number=1 で cd <dir> && gh-pr-merge-safe.sh (記録なし)" 2 "cd $GITWT && bash scripts/gh-pr-merge-safe.sh --merge"
mk_rec 1 "$SHA1"
expect "R2 .pr-number=1 で cd <dir> && gh-pr-merge-safe.sh (記録あり)" 0 "cd $GITWT && bash scripts/gh-pr-merge-safe.sh --merge"
# gh が失敗したら止まる (fail closed)
FAKE_GH_FAIL=1 expect "R2 gh pr view 失敗は止まる" 2 'gh pr merge 1 --merge'

# ---------------------------------------------------------------- R3 HEAD が変わると止まる
echo "$SHA2" > "$FAKE_HEAD_FILE"
expect "R3 記録後に HEAD が変わる" 2 'gh pr merge 1 --merge'
echo "$SHA1" > "$FAKE_HEAD_FILE"
expect "R3 --auto で --match-head-commit なし" 2 'gh pr merge 1 --auto --merge'
expect "R3 --auto で --match-head-commit が記録と同じ" 0 "gh pr merge 1 --auto --merge --match-head-commit $SHA1"
expect "R3 --auto で --match-head-commit が違う" 2 "gh pr merge 1 --auto --merge --match-head-commit $SHA2"

# ---------------------------------------------------------------- R4 record.py
SESS="$T/sess"; mkdir -p "$SESS/subagents"
printf '{"agentType":"reviewer","model":"opus"}' > "$SESS/subagents/agent-xxx.meta.json"
printf '{"agentType":"reviewer","model":"sonnet"}' > "$SESS/subagents/agent-son.meta.json"
printf '{"agentType":"reviewer","model":"opus"}' > "$SESS/subagents/agent-mix.meta.json"
printf '{"type":"assistant","message":{"model":"claude-opus-5-5"}}\n' > "$SESS/subagents/agent-xxx.jsonl"
printf '{"type":"assistant","message":{"model":"claude-opus-5-5"}}\n{"type":"assistant","message":{"model":"claude-sonnet-5-5"}}\n' > "$SESS/subagents/agent-mix.jsonl"
MAIN_T="$T/sess.jsonl"; : > "$MAIN_T"
OWN_T="$SESS/subagents/agent-xxx.jsonl"

rec_json() { # MESSAGE AGENT_TYPE AGENT_ID TRANSCRIPT
  python3 -B -c 'import json,sys;print(json.dumps({"tool_name":"SubagentHandback","agent_type":sys.argv[2],"agent_id":sys.argv[3],"transcript_path":sys.argv[4],"cwd":sys.argv[5],"tool_input":{"message":sys.argv[1]}}))' "$1" "$2" "$3" "$4" "$WORK"
}
nrec() { ls "$GD/records" 2>/dev/null | wc -l | tr -d ' '; }
run_record() { printf '%s' "$1" | python3 -B "$RECORD" > /dev/null 2>&1; RC=$?; }
expect_rec() { # NAME WANT_COUNT MESSAGE AGENT_TYPE AGENT_ID TRANSCRIPT
  clear_records
  run_record "$(rec_json "$3" "$4" "$5" "$6")"
  local n; n="$(nrec)"
  if [ "$RC" = 0 ] && [ "$n" = "$2" ]; then ok "$1"; else ng "$1" "rc=$RC 記録 $n 件, 期待 $2"; fi
}
M_OK=$'審査しました。\nVERDICT: APPROVE on '"$SHA1"$' PR #1'
expect_rec "R4 APPROVE・opus・sha 一致 -> 記録 1 件" 1 "$M_OK" reviewer xxx "$MAIN_T"
[ -f "$GD/records/o__r-1-$SHA1.json" ] && ok "R4 記録ファイル名 o__r-1-<sha>.json" || ng "R4 記録ファイル名" "無い"
perm="$(stat -f %Lp "$GD/records/o__r-1-$SHA1.json" 2>/dev/null || stat -c %a "$GD/records/o__r-1-$SHA1.json")"
[ "$perm" = "600" ] && ok "R4 記録ファイルの権限 600" || ng "R4 記録ファイルの権限" "$perm"
expect_rec "R4 transcript が自分の形 + id=xxx" 1 "$M_OK" reviewer xxx "$OWN_T"
expect_rec "R4 transcript が本流の形 + id=agent-xxx" 1 "$M_OK" reviewer agent-xxx "$MAIN_T"
expect_rec "R4 transcript が自分の形 + id=agent-xxx" 1 "$M_OK" reviewer agent-xxx "$OWN_T"
expect_rec "R4 REQUEST_CHANGES は記録しない" 0 $'x\nVERDICT: REQUEST_CHANGES on '"$SHA1"$' PR #1' reviewer xxx "$MAIN_T"
run_gate "$(bash_json 'gh pr merge 1 --merge' "$WORK")"; [ "$RC" = 2 ] && ok "R4 REQUEST_CHANGES の後も gate は止まる" || ng "R4 REQUEST_CHANGES の後の gate" "exit $RC"
expect_rec "R4 REJECT は記録しない" 0 $'x\nVERDICT: REJECT on '"$SHA1"$' PR #1' reviewer xxx "$MAIN_T"
run_gate "$(bash_json 'gh pr merge 1 --merge' "$WORK")"; [ "$RC" = 2 ] && ok "R4 REJECT の後も gate は止まる" || ng "R4 REJECT の後の gate" "exit $RC"
expect_rec "R4 meta の model が sonnet は記録しない" 0 "$M_OK" reviewer son "$MAIN_T"
expect_rec "R4 meta.json が無いと記録しない" 0 "$M_OK" reviewer nometa "$MAIN_T"
expect_rec "R4 assistant に opus 以外が混じると記録しない" 0 "$M_OK" reviewer mix "$MAIN_T"
expect_rec "R4 VERDICT の sha が HEAD と違う" 0 $'x\nVERDICT: APPROVE on '"$SHA2"$' PR #1' reviewer xxx "$MAIN_T"
expect_rec "R4 agent_type が reviewer 以外" 0 "$M_OK" general-purpose xxx "$MAIN_T"
expect_rec "R4 VERDICT 行が無い" 0 "審査しました。問題ありません。" reviewer xxx "$MAIN_T"
expect_rec "R4 VERDICT が複数あるときは最後の 1 件 (APPROVE が最後)" 1 $'VERDICT: REJECT on '"$SHA1"$' PR #1\nVERDICT: APPROVE on '"$SHA1"$' PR #1' reviewer xxx "$MAIN_T"
# 記録 -> gate が通る (record.py と gate.py をつなぐ)
clear_records
run_record "$(rec_json "$M_OK" reviewer xxx "$MAIN_T")"
expect "R4 record.py の記録で gate が通る" 0 'gh pr merge 1 --merge'

# ---------------------------------------------------------------- R5 model
expect_tool "R5 Agent reviewer model=sonnet" 2 Agent '{"subagent_type":"reviewer","model":"sonnet","prompt":"x"}'
expect_tool "R5 Agent reviewer model=opus" 0 Agent '{"subagent_type":"reviewer","model":"opus","prompt":"x"}'
expect_tool "R5 Agent reviewer model 未指定" 0 Agent '{"subagent_type":"reviewer","prompt":"x"}'
expect_tool "R5 Agent 他の型は sonnet でも通す" 0 Agent '{"subagent_type":"generator","model":"sonnet","prompt":"x"}'

# ---------------------------------------------------------------- R6 記録の置き場・台本
echo '{}' > "$T/x.json"
expect "R6 echo > ~/.claude/review-gate/records/a.json" 2 'echo x > ~/.claude/review-gate/records/a.json'
expect "R6 cd ~/.claude && echo > review-gate/records/a.json" 2 'cd ~/.claude && echo x > review-gate/records/a.json'
expect "R6 python3 ~/.claude/scripts/review-gate/record.py" 2 "python3 ~/.claude/scripts/review-gate/record.py < $T/x.json"
expect "R6 python3 scripts/agent-hooks/review-gate/record.py" 2 "python3 scripts/agent-hooks/review-gate/record.py < $T/x.json"
expect "R6 試験 && record.py (例外は区切りごと)" 2 "bash scripts/agent-hooks/review-gate/test_review_gate.sh && python3 ~/.claude/scripts/review-gate/record.py < $T/x.json"
expect "R6 REVIEW_GATE_DIR を書き換える" 2 'REVIEW_GATE_DIR=/tmp/x gh pr merge 1 --merge'
expect "R6 ヒアドキュメントの本文でも止める" 2 $'cat <<\'EOF\' > /tmp/y\nreview-gate/records\nEOF'
expect_tool "R6 Write file_path" 2 Write "{\"file_path\":\"$GD/records/a.json\",\"content\":\"x\"}"
expect_tool "R6 Edit file_path" 2 Edit "{\"file_path\":\"$GD/records/a.json\",\"old_string\":\"a\",\"new_string\":\"b\"}"
expect_tool "R6 MultiEdit file_path" 2 MultiEdit "{\"file_path\":\"$GD/log.jsonl\",\"edits\":[]}"
expect_tool "R6 NotebookEdit notebook_path" 2 NotebookEdit "{\"notebook_path\":\"$GD/records/n.ipynb\"}"
expect_tool "R6 置き場の外への Write は通す" 0 Write "{\"file_path\":\"$T/other.txt\",\"content\":\"x\"}"

# ---------------------------------------------------------------- 誤止めなし
clear_records
expect "誤止めなし ls" 0 'ls'
expect "誤止めなし grep -n x check-pr-merge-ready.py" 0 'grep -n x scripts/dev/check-pr-merge-ready.py'
expect "誤止めなし git diff -- gh-pr-merge-safe.sh" 0 'git diff -- scripts/gh-pr-merge-safe.sh'
expect "誤止めなし gh pr create --body \"gh pr merge 1\"" 0 'gh pr create --body "gh pr merge 1"'
expect "誤止めなし git commit -m \"gh-pr-merge-safe.sh\"" 0 'git commit -m "gh-pr-merge-safe.sh"'
expect "誤止めなし gh pr merge 1 --disable-auto" 0 'gh pr merge 1 --disable-auto'
expect "誤止めなし bash test_review_gate.sh" 0 'bash scripts/agent-hooks/review-gate/test_review_gate.sh'
expect "誤止めなし gh pr create --body-file - <<'EOF' (本文に don't merge yet)" 0 \
  $'gh pr create --base main --title t --body-file - <<\'EOF\'\n本文: don\'t merge yet\nEOF'
expect "誤止めなし git commit -m \"\$(cat <<'EOF'\" (本文に 1) とバッククォート 3 個と閉じない引用符)" 0 \
  $'git commit -m "$(cat <<\'EOF\'\nfeat: gh pr merge の話 1) ``` don\'t\n\nCo-Authored-By: x\nEOF\n)"'
expect "誤止めなし grep -rn \"gh pr merge\" docs" 0 'grep -rn "gh pr merge" docs'

echo "----------------------------------------"
echo "PASS $PASS / FAIL $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
