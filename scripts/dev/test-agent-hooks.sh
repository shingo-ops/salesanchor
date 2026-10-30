#!/bin/bash
# test-agent-hooks.sh — PreToolUse フック3本の受入試験（設計承認チケット 段2）
#
# 使い方: bash scripts/dev/test-agent-hooks.sh <フックのあるディレクトリ> [--real-home]
#   フックディレクトリ: stage2-hooks/（試作）や ~/.claude/scripts（本物）
#   --real-home       : 本物の HOME と本物の agent-tokens.json を使う（本物の反映後の試験用）。
#                       省略時は偽の HOME（一時ディレクトリ）を使い、~/.claude には何も書かない。
#
# 試験の中身: 入力 JSON を一時ファイルに書き、`bash <フック> < <入力ファイル>` で渡して exit を比べるだけ。
# コマンドは実行されない（フックが判定するだけ）。1件でも不合格なら exit 1。
#
# 本店役: 試験用に一時ディレクトリへ作る git リポジトリ（main ブランチ・origin=shingo-ops/salesanchor）。
# 自分の worktree 役: 環境変数 WT_ROOT（既定はこのスクリプトのあるリポジトリの根）。
#   ~/worktrees/salesanchor/<名前>/ の下にあり、<名前>/.git がファイルであること。
set -u

HOOKDIR="${1:-}"
REAL_HOME_MODE="${2:-}"
if [ -z "$HOOKDIR" ] || [ ! -d "$HOOKDIR" ]; then
  echo "使い方: $0 <フックのあるディレクトリ> [--real-home]" >&2
  exit 2
fi
HOOKDIR="$(cd "$HOOKDIR" && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WT_ROOT="${WT_ROOT:-$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)}"

T="$(mktemp -d "${TMPDIR:-/tmp}/test-agent-hooks.XXXXXX")"
_selftest_window_end() {
  if [ "$REAL_HOME_MODE" = "--real-home" ]; then
    printf '{"end": "%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$HOME/.claude/logs/consent-selftest-windows.jsonl"
  fi
}
trap '_selftest_window_end; rm -rf "$T"' EXIT
# 本物の HOME で走らせるときは、試験の区間を記録する（consent-audit.py が区間内の consent_guard_blocked を本物の検知から除く）
if [ "$REAL_HOME_MODE" = "--real-home" ]; then
  mkdir -p "$HOME/.claude/logs"
  printf '{"start": "%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$HOME/.claude/logs/consent-selftest-windows.jsonl"
fi

# ── 試験の舞台を作る ─────────────────────────────────────────────
FAKE_HOME="$T/home"
if [ "$REAL_HOME_MODE" != "--real-home" ]; then
  mkdir -p "$FAKE_HOME/.claude/logs" "$FAKE_HOME/.claude/permits"
  # notify.sh は $HOME/.claude/VOICEVOX_MUTED があれば何もしない。偽 HOME にもミュートの印を必ず置く（音を鳴らさない）
  : > "$FAKE_HOME/.claude/VOICEVOX_MUTED"
  printf '%s' '{"danger_ops":["rm -rf","DROP TABLE","DELETE FROM","TRUNCATE"],"speaker_warning":"3"}' > "$FAKE_HOME/.claude/agent-tokens.json"
fi

HONTEN="$T/honten"
mkdir -p "$HONTEN"
git -C "$HONTEN" init -q -b main
git -C "$HONTEN" remote add origin https://github.com/shingo-ops/salesanchor.git
git -C "$HONTEN" -c user.name=t -c user.email=t@example.com commit -q --allow-empty -m init

SAN=""
[ -f "$HOOKDIR/danger_sanitize.py" ] && SAN="$HOOKDIR/danger_sanitize.py"

PASS=0
FAIL=0
RESULTS=()

# run_hook <フック名> <cwd> <入力ファイル> → exit コードを表示
run_hook() {
  local hook="$1" cwd="$2" inf="$3"
  if [ "$REAL_HOME_MODE" = "--real-home" ]; then
    ( cd "$cwd" && env ${SAN:+DANGER_SANITIZER="$SAN"} ${EXTRA_ENV:+"$EXTRA_ENV"} bash "$HOOKDIR/$hook" < "$inf" >/dev/null 2>&1 )
  else
    ( cd "$cwd" && env HOME="$FAKE_HOME" ${SAN:+DANGER_SANITIZER="$SAN"} ${EXTRA_ENV:+"$EXTRA_ENV"} bash "$HOOKDIR/$hook" < "$inf" >/dev/null 2>&1 )
  fi
  echo $?
}

# run_hook_err <フック名> <cwd> <入力ファイル> → フックの stderr を表示（文言の試験用）
run_hook_err() {
  local hook="$1" cwd="$2" inf="$3"
  if [ "$REAL_HOME_MODE" = "--real-home" ]; then
    ( cd "$cwd" && env ${SAN:+DANGER_SANITIZER="$SAN"} bash "$HOOKDIR/$hook" < "$inf" 2>&1 >/dev/null )
  else
    ( cd "$cwd" && env HOME="$FAKE_HOME" ${SAN:+DANGER_SANITIZER="$SAN"} bash "$HOOKDIR/$hook" < "$inf" 2>&1 >/dev/null )
  fi
}

# t <ID> <フック名> <W|HONTEN> <期待exit> <コマンド文字列>
t() {
  local id="$1" hook="$2" where="$3" expect="$4" command="$5" cwd actual inf verdict
  # ONLY=<ID> のときはその1件だけ回す（音が鳴らないことの単発確認用）
  if [ -n "${ONLY:-}" ] && [ "$ONLY" != "$id" ]; then return; fi
  # 通知で音が鳴らないよう、ミュートの印が無ければ回さない（偽 HOME・本物とも）
  local mute_home="$FAKE_HOME"; [ "$REAL_HOME_MODE" = "--real-home" ] && mute_home="$HOME"
  if [ ! -f "$mute_home/.claude/VOICEVOX_MUTED" ]; then echo "中止: $mute_home/.claude/VOICEVOX_MUTED が無い" >&2; exit 2; fi
  if [ ! -f "$HOOKDIR/$hook" ]; then
    RESULTS+=("$(printf '%-9s %-22s %-6s %-5s %-6s %s' "$id" "$hook" "$where" "$expect" "-" "SKIP(フック無し)")")
    return
  fi
  if [ "$where" = "HONTEN" ]; then cwd="$HONTEN"; else cwd="$WT_ROOT"; fi
  inf="$T/in-$id.json"
  python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]},"cwd":sys.argv[2]}))' "$command" "$cwd" > "$inf"
  actual="$(run_hook "$hook" "$cwd" "$inf")"
  if [ "$actual" = "$expect" ]; then verdict="PASS"; PASS=$((PASS + 1)); else verdict="FAIL"; FAIL=$((FAIL + 1)); fi
  RESULTS+=("$(printf '%-9s %-22s %-6s %-5s %-6s %s' "$id" "$hook" "$where" "$expect" "$actual" "$verdict")")
}

OWN="$WT_ROOT/docs/handoff/stage2-test-nonexistent"
# 別の worktree 役: 本物のホームの ~/worktrees/salesanchor/ にある、自分以外の worktree（.git がファイルのもの）
REAL_HOME_DIR="$(python3 -c 'import pwd,os; print(pwd.getpwuid(os.getuid()).pw_dir)')"
OTHER_WT=""
for d in "$REAL_HOME_DIR"/worktrees/salesanchor/*/; do
  if [ -f "${d}.git" ] && [ "${d%/}" != "$WT_ROOT" ]; then OTHER_WT="${d%/}"; break; fi
done

# ── 段2 受入試験 ─────────────────────────────────────────────────
# 通すべきもの（誤検知の修正）
t T2-1   worktree-only-guard.sh W 0 'cd "$X" && ls'
t T2-2   agent-danger-hook.sh   W 0 $'cat > /tmp/f.txt <<\'E\'\nrm -rf /x\nE\n'
t T2-2b  worktree-only-guard.sh W 0 $'cat > /tmp/f.txt <<\'E\'\nrm -rf /x\nE\n'
t T2-3   agent-danger-hook.sh   W 0 'git commit -m "fix: DELETE FROM を含む説明文"'
t T2-3b  worktree-only-guard.sh W 0 'git commit -m "fix: DELETE FROM を含む説明文"'
t T2-4   pr-body-guard.sh       W 0 $'cat > /tmp/f.sh <<\'E\'\ngh pr create --title t --body-file /nonexistent/x.md\nE\n'
t T2-5   agent-danger-hook.sh   W 0 "rm -rf $OWN"
t T2-5b  agent-danger-hook.sh   W 0 "rm -rf /private/tmp/claude-501/x"
t T2-7   agent-danger-hook.sh   W 0 'grep -rn "foo|psql" docs/'
t T2-8   agent-danger-hook.sh   W 0 'gh pr create --title "DROP TABLE の説明" --body "DELETE FROM x"'

# 止め続けるもの
t T2-4b  pr-body-guard.sh       W 2 'env X=1 gh pr create --body-file /nonexistent'
t T2-6a  worktree-only-guard.sh HONTEN 2 'git commit -m x'
t T2-6b  agent-danger-hook.sh   W 2 'rm -rf /tmp/x'
t T2-6c  agent-danger-hook.sh   W 2 'rm -rf ~'
t T2-6d  agent-danger-hook.sh   W 2 "rm -rf $WT_ROOT"
t T2-6e  agent-danger-hook.sh   W 2 'bash -c "rm -rf /x"'
t T2-6f  agent-danger-hook.sh   W 2 'git commit -m "$(rm -rf /x)"'
t T2-6g  agent-danger-hook.sh   W 2 $'ssh prod1 psql <<EOF\nINSERT INTO t VALUES (1);\nEOF\n'
t T2-6h  agent-danger-hook.sh   HONTEN 2 'git clean -fd'
t T2-6i  agent-danger-hook.sh   W 2 'ls /Users/tanizawashingo/.claude/permits'
t T2-9a  worktree-only-guard.sh W 2 'cd "$X" && git commit -m x'
t T2-9b  worktree-only-guard.sh W 2 'cd "$X" && git push origin release/x'
t T2-9c  agent-danger-hook.sh   W 2 "rm -rf $WT_ROOT/.git"
t T2-9d  agent-danger-hook.sh   W 2 "rm -rf $WT_ROOT/../x"
t T2-9e  agent-danger-hook.sh   W 2 'eval "rm -rf /x"'
t T2-9f  agent-danger-hook.sh   W 2 $'cat > /tmp/f.txt <<EOF\n$(rm -rf /x)\nEOF\n'
t T2-10a agent-danger-hook.sh   W 2 'git commit -m "x `rm -rf /x`"'
t T2-10b agent-danger-hook.sh   W 2 $'cat > /tmp/f.txt <<EOF\n${X} rm -rf /x\nEOF\n'
t T2-10c agent-danger-hook.sh   W 2 'gh pr create --title "${X} DROP TABLE" --body "y"'
# F1: cd を挟んだ相対パスの削除、F3: 別の worktree・cwd が worktree の外
t T2-11a agent-danger-hook.sh   W 2 '(cd /etc; rm -rf y)'
t T2-11b agent-danger-hook.sh   W 2 '{ cd /etc; rm -rf y; }'
t T2-11c agent-danger-hook.sh   W 2 'pushd /etc && rm -rf y'
# ADR-1033 §4-6(a): cd 等が無いコマンドの作業場所の下の相対パスは止めない（段2の 2 から 0 に意図して変更）
t T2-11d agent-danger-hook.sh   W 0 'rm -rf docs/handoff/stage2-test-nonexistent'
t T2-11e agent-danger-hook.sh   W 2 'rm -rf /private/tmp/claude-501/*'
t T2-11f agent-danger-hook.sh   HONTEN 2 "rm -rf $OWN"
t T2-11g agent-danger-hook.sh   HONTEN 0 'rm -rf /private/tmp/claude-501/x'
if [ -n "$OTHER_WT" ]; then
  t T2-11h agent-danger-hook.sh W 2 "rm -rf $OTHER_WT/x"
else
  RESULTS+=("T2-11h   (別の worktree が無いので SKIP)")
fi
# F2: heredoc 本文の除外をすり抜けるパイプ・プロセス置換・/dev 書き込み
t T2-12a agent-danger-hook.sh   W 2 $'tee /tmp/x <<\'E\' | bash\nrm -rf /x\nE\n'
t T2-12b agent-danger-hook.sh   W 2 $'cat > /dev/stdout <<\'E\' | bash\nrm -rf /x\nE\n'
t T2-12c agent-danger-hook.sh   W 2 $'cat > >(bash) <<\'E\'\nrm -rf /x\nE\n'
t T2-12d agent-danger-hook.sh   W 2 $'cat > /dev/stdout <<\'E\'\nrm -rf /x\nE\n'
t T2-12e agent-danger-hook.sh   W 2 $'tee /dev/fd/1 <<\'E\'\nrm -rf /x\nE\n'
t T2-9g  agent-danger-hook.sh   W 2 'cd /tmp && rm -rf x'
t T2-9h  agent-danger-hook.sh   W 2 'rm -rf /private/tmp/claude-501/../x'
t T2-9i  worktree-only-guard.sh W 2 'git push --force origin main'
t T2-9j  pr-body-guard.sh       W 2 'GH_TOKEN=x gh pr create --title t --body-file /nonexistent/x.md'

# ── 段1 記録の試験10件（stage1-record.md）。S1-1 だけは段2で意図的に 2→0 に変わる ──
t S1-1   worktree-only-guard.sh W 0 'cd $(pwd) && ls'
t S1-1b  worktree-only-guard.sh W 2 'cd $(pwd) && git commit -m x'
t S1-2   worktree-only-guard.sh W 0 'ls'
t S1-3   agent-danger-hook.sh   W 2 'rm -rf /tmp/stage1-test-nonexistent'
t S1-4   agent-danger-hook.sh   W 2 'ssh prod1 psql < /tmp/stage1-test.sql'
t S1-5   agent-danger-hook.sh   W 2 'ls /Users/tanizawashingo/.claude/permits'
t S1-6   agent-danger-hook.sh   HONTEN 2 'git clean -fd'
t S1-7   agent-danger-hook.sh   W 0 'ls'
t S1-8   pr-body-guard.sh       W 2 'gh pr create --title x --body-file /nonexistent/stage1-test-body.md'
t S1-9   pr-body-guard.sh       W 0 'ls'
t S1-10  gh-scope-guard.sh   W 0 'gh pr list'

# ── ADR-1033 会話での同意 受入試験 T1〜T9（design §2） ─────────────────────
# 非 Bash ツール用: tj <ID> <フック名> <W|HONTEN> <期待exit> <ツール名> <tool_input の JSON>
tj() {
  local id="$1" hook="$2" where="$3" expect="$4" tool="$5" tin="$6" cwd actual inf verdict
  if [ -n "${ONLY:-}" ] && [ "$ONLY" != "$id" ]; then return; fi
  if [ ! -f "$HOOKDIR/$hook" ]; then
    RESULTS+=("$(printf '%-9s %-22s %-6s %-5s %-6s %s' "$id" "$hook" "$where" "$expect" "-" "SKIP(フック無し)")")
    return
  fi
  if [ "$where" = "HONTEN" ]; then cwd="$HONTEN"; else cwd="$WT_ROOT"; fi
  inf="$T/in-$id.json"
  python3 -c 'import json,sys; print(json.dumps({"tool_name":sys.argv[1],"tool_input":json.loads(sys.argv[2]),"cwd":sys.argv[3]}))' "$tool" "$tin" "$cwd" > "$inf"
  actual="$(run_hook "$hook" "$cwd" "$inf")"
  if [ "$actual" = "$expect" ]; then verdict="PASS"; PASS=$((PASS + 1)); else verdict="FAIL"; FAIL=$((FAIL + 1)); fi
  RESULTS+=("$(printf '%-9s %-22s %-6s %-5s %-6s %s' "$id" "$hook" "$where" "$expect" "$actual" "$verdict")")
}

EVENTS_FILE="$FAKE_HOME/.claude/logs/agent-events.jsonl"
[ "$REAL_HOME_MODE" = "--real-home" ] && EVENTS_FILE="$HOME/.claude/logs/agent-events.jsonl"
count_guard() { grep -c '"consent_guard_blocked"' "$EVENTS_FILE" 2>/dev/null || true; }
# consent_guard_blocked の各行の kind を順に空白区切りで出す。cmd_sha（16桁）と cmd_len（整数）が無い行があれば "BAD" を出す（フックの行 = hook が agent-danger-hook のものだけ cmd_sha を要求）
guard_kinds() {
  python3 -c '
import sys, json
out = []
try:
    for line in open(sys.argv[1], encoding="utf-8"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("type") != "consent_guard_blocked":
            continue
        k = r.get("kind", "NONE")
        if r.get("hook") == "agent-danger-hook":
            sha = r.get("cmd_sha")
            if not (isinstance(sha, str) and len(sha) == 16 and isinstance(r.get("cmd_len"), int)):
                k = "BAD"
        out.append(k)
except Exception:
    pass
print(" ".join(out))
' "$EVENTS_FILE"
}
# check_new_kinds <ID> <増える前の guard_kinds> <期待する kind の並び>
check_new_kinds() {
  local id="$1" before="$2" expect="$3" after new
  [ -z "${ONLY:-}" ] || return 0
  after="$(guard_kinds)"
  new="${after#"$before"}"; new="${new# }"
  if [ "$new" = "$expect" ]; then PASS=$((PASS + 1)); RESULTS+=("$id kind の並び=[$new] PASS")
  else FAIL=$((FAIL + 1)); RESULTS+=("$id kind の並び=[$new] 期待=[$expect] FAIL"); fi
}

if [ -f "$HOOKDIR/agent-danger-hook.sh" ]; then
  # T1(配線): 判定部品が allow を返したときだけ、psql の経路と danger_ops の経路が通る。部品が無い・不可なら今までどおり止める
  printf '#!/bin/bash\necho allow\n' > "$T/stub-allow.sh"
  printf '#!/bin/bash\nexit 2\n' > "$T/stub-deny.sh"
  printf 'import sys\nprint("allow")\n' > "$T/stub-allow.py"
  printf 'import sys\nsys.exit(2)\n' > "$T/stub-deny.py"
  EXTRA_ENV="CONSENT_CHECK=$T/stub-allow.py"
  t T1-h1  agent-danger-hook.sh W 0 'ssh prod1 psql < /tmp/stage1-test.sql'
  t T1-h2  agent-danger-hook.sh W 0 'rm -rf /tmp/x'
  EXTRA_ENV="CONSENT_CHECK=$T/stub-deny.py"
  t T1-h3  agent-danger-hook.sh W 2 'ssh prod1 psql < /tmp/stage1-test.sql'
  t T1-h4  agent-danger-hook.sh W 2 'rm -rf /tmp/x'
  EXTRA_ENV="CONSENT_CHECK=$T/no-such-file.py"
  t T1-h5  agent-danger-hook.sh W 2 'rm -rf /tmp/x'
  # 本店の破壊系 git は同意の対象にしない（部品が allow でも止める）
  EXTRA_ENV="CONSENT_CHECK=$T/stub-allow.py"
  t T1-h6  agent-danger-hook.sh HONTEN 2 'git clean -fd'
  EXTRA_ENV=""

  # T7: 会話記録・同意の台帳・端末への入力注入（Bash）。止めると consent_guard_blocked が1行ずつ増える
  G0="$(count_guard)"
  K0S="$(guard_kinds)"
  t T7-b1  agent-danger-hook.sh W 2 'cat /Users/x/.claude/projects/-p/s.jsonl'
  t T7-b2  agent-danger-hook.sh W 2 'tail -n 3 ~/.claude/logs/consent-used.jsonl'
  t T7-b3  agent-danger-hook.sh W 2 'tmux send-keys -t ac-1 1 Enter'
  t T7-b4  agent-danger-hook.sh W 2 'tmux load-buffer /tmp/x && tmux paste-buffer -t ac-1'
  t T7-b5  agent-danger-hook.sh W 2 "osascript -e 'tell application \"System Events\" to keystroke \"1\"'"
  t T7-b6  agent-danger-hook.sh W 2 'curl -s http://127.0.0.1:3000/chat/queue -d x'
  t T7-b7  agent-danger-hook.sh W 2 'curl -s http://localhost:3000/chat/queue -d x'
  G1="$(count_guard)"
  if [ -z "${ONLY:-}" ]; then
    if [ "$((G1 - G0))" = "7" ]; then PASS=$((PASS + 1)); RESULTS+=("T7-log   consent_guard_blocked が7件増えた PASS")
    else FAIL=$((FAIL + 1)); RESULTS+=("T7-log   consent_guard_blocked の増加=$((G1 - G0)) 期待=7 FAIL"); fi
  fi
  # K14: 各行の kind（読み取り2・注入5）と cmd_sha・cmd_len
  check_new_kinds T7-kind "$K0S" "read read inject inject inject inject inject"
  # K14: 書き込みの形 1〜4 の各例は write、読み取りの例は read
  K1S="$(guard_kinds)"
  t T7-k1  agent-danger-hook.sh W 2 'echo x >> /Users/x/.claude/projects/-p/s.jsonl'
  t T7-k2  agent-danger-hook.sh W 2 'echo x | tee -a /Users/x/.claude/logs/consent-used.jsonl'
  t T7-k3  agent-danger-hook.sh W 2 'sed -i s/a/b/ /Users/x/.claude/projects/-p/s.jsonl'
  t T7-k4  agent-danger-hook.sh W 2 "python3 -c \"open('/Users/x/.claude/projects/-p/s.jsonl','a').write('x')\""
  t T7-k5  agent-danger-hook.sh W 2 'cd /Users/x/.claude/projects/-p && echo x > s.jsonl'
  t T7-k6  agent-danger-hook.sh W 2 'cp /Users/x/.claude/projects/-p/s.jsonl /tmp/z'
  t T7-k7  agent-danger-hook.sh W 2 'grep x /Users/x/.claude/projects/-p/s.jsonl'
  t T7-k8  agent-danger-hook.sh W 2 'cd /Users/x/.claude/projects/-p && cat s.jsonl 2>&1'
  t T7-k9  agent-danger-hook.sh W 2 'cat /Users/x/.claude/projects/-p/s.jsonl > /tmp/out.txt'
  check_new_kinds T7-kind2 "$K1S" "write write write write write write read read read"
  # 審査 LOW-2: Path(...).open('a') は write
  K2S="$(guard_kinds)"
  t T7-k10 agent-danger-hook.sh W 2 "python3 -c \"from pathlib import Path; Path('/Users/x/.claude/projects/-p/s.jsonl').open('a').write('x')\""
  check_new_kinds T7-kind3 "$K2S" "write"
  # 審査 HIGH-1: 64KB 程度の長いコマンド（記録のパスと open(a, のくり返し）が5秒以内に exit 2 で止まり、kind は write
  K3S="$(guard_kinds)"
  LONGCMD="$(python3 -c 'print("python3 -c \"" + "open(a, " * 5000 + " /Users/x/.claude/projects/-p/s.jsonl" * 1000 + "\"")')"
  LT0=$SECONDS
  t T7-long agent-danger-hook.sh W 2 "$LONGCMD"
  LT1=$SECONDS
  if [ -z "${ONLY:-}" ]; then
    if [ "$((LT1 - LT0))" -le 5 ]; then PASS=$((PASS + 1)); RESULTS+=("T7-long-time 長いコマンド(${#LONGCMD}字)の所要 $((LT1 - LT0)) 秒 <= 5 PASS")
    else FAIL=$((FAIL + 1)); RESULTS+=("T7-long-time 長いコマンドの所要 $((LT1 - LT0)) 秒 > 5 FAIL"); fi
  fi
  check_new_kinds T7-kind4 "$K3S" "write"
  # 再審査 MEDIUM: 4000字ちょうどの最悪の形（open( のくり返し + 閉じない引用符）が2秒以内に exit 2 で止まり、kind が write か read で記録される
  K4S="$(guard_kinds)"
  WORST1="$(python3 -c 'p = "python3 -c /Users/x/.claude/projects/-p/s.jsonl " + "open(" * 267 + ", \x27"; print(p + "w" * (4000 - len(p)), end="")')"
  WORST2="$(python3 -c 'p = "python3 -c /Users/x/.claude/projects/-p/s.jsonl " + ".open(" * 267 + "\x27"; print(p + "w" * (4000 - len(p)), end="")')"
  LT0=$SECONDS
  t T7-worst1 agent-danger-hook.sh W 2 "$WORST1"
  t T7-worst2 agent-danger-hook.sh W 2 "$WORST2"
  LT1=$SECONDS
  if [ -z "${ONLY:-}" ]; then
    if [ "$((LT1 - LT0))" -le 2 ]; then PASS=$((PASS + 1)); RESULTS+=("T7-worst-time 最悪の形2件(${#WORST1}・${#WORST2}字)の所要 $((LT1 - LT0)) 秒 <= 2 PASS")
    else FAIL=$((FAIL + 1)); RESULTS+=("T7-worst-time 最悪の形の所要 $((LT1 - LT0)) 秒 > 2 FAIL"); fi
    W_AFTER="$(guard_kinds)"; W_NEW="${W_AFTER#"$K4S"}"; W_NEW="${W_NEW# }"
    case "$W_NEW" in
      "write write"|"write read"|"read write"|"read read") PASS=$((PASS + 1)); RESULTS+=("T7-worst-kind kind=[$W_NEW] PASS") ;;
      *) FAIL=$((FAIL + 1)); RESULTS+=("T7-worst-kind kind=[$W_NEW] FAIL") ;;
    esac
  fi
  t T7-b8  agent-danger-hook.sh W 0 'tmux ls'
  t T7-b9  agent-danger-hook.sh W 0 'ls'

  # T8: rm -rf の根（design §4-6(a)）。止めない側
  t T8-a1  agent-danger-hook.sh W 0 'rm -rf /tmp/CC報告ファイル/x'
  t T8-a2  agent-danger-hook.sh W 0 'rm -rf /private/tmp/CC報告ファイル/x/y'
  t T8-a3  agent-danger-hook.sh W 0 'rm -rf /private/tmp/claude-501/x'
  t T8-a4  agent-danger-hook.sh W 0 "rm -rf $OWN"
  t T8-a5  agent-danger-hook.sh W 0 'rm -rf ./docs/handoff/stage2-test-nonexistent'
  t T8-a6  agent-danger-hook.sh HONTEN 0 'rm -rf /tmp/CC報告ファイル/x'
  # 止める側
  t T8-b1  agent-danger-hook.sh W 2 'rm -rf /tmp/CC報告ファイル'
  t T8-b2  agent-danger-hook.sh W 2 'rm -rf /private/tmp/claude-501'
  t T8-b3  agent-danger-hook.sh W 2 'rm -rf /tmp/CC報告ファイル/..'
  t T8-b4  agent-danger-hook.sh W 2 'rm -rf /tmp/CC報告ファイル/.git'
  t T8-b5  agent-danger-hook.sh W 2 'rm -rf /private/tmp/claude-501/$X'
  t T8-b6  agent-danger-hook.sh W 2 'rm -rf /private/tmp/claude-501/*'
  t T8-b7  agent-danger-hook.sh W 2 'rm -rf /tmp/CC報告ファイル/{..,x}'
  t T8-b8  agent-danger-hook.sh W 2 'cd ~ && rm -rf x'
  t T8-b9  agent-danger-hook.sh W 2 '(cd /; rm -rf x)'
  t T8-b10 agent-danger-hook.sh W 2 'rm -rf ~'
  t T8-b11 agent-danger-hook.sh W 2 'rm -rf /tmp/CC報告ファイル/x\y'
  t T8-b12 agent-danger-hook.sh W 2 'rm -rf /tmp/CC報告ファイル/!x'
  t T8-b13 agent-danger-hook.sh W 2 'rm -rf /tmp/CC報告ファイル/?'
  t T8-b14 agent-danger-hook.sh W 2 'rm -rf /tmp/CC報告ファイル/[a]'
  t T8-b15 agent-danger-hook.sh W 2 'bash -c "rm -rf x"'
  t T8-b16 agent-danger-hook.sh W 2 'eval "rm -rf x"'
  t T8-b17 agent-danger-hook.sh W 2 '/bin/ln -s ~ /tmp/CC報告ファイル/x && rm -rf /tmp/CC報告ファイル/x/y'
  t T8-b18 agent-danger-hook.sh W 2 'rm -rf /tmp/CC報告ファイル/x/'
  t T8-b19 agent-danger-hook.sh W 2 'rm -rf ../x'
  t T8-b20 agent-danger-hook.sh W 2 'rm -rf .git'
  t T8-b21 agent-danger-hook.sh W 2 'rm -rf docs/../..'
  t T8-b22 agent-danger-hook.sh HONTEN 2 'rm -rf docs/x'
  t T8-b23 agent-danger-hook.sh W 2 'pushd /etc && rm -rf y'
  t T8-b24 agent-danger-hook.sh W 2 'ln -s ~ docs/lnk && rm -rf docs/lnk/y'
fi

if [ -f "$HOOKDIR/worktree-only-guard.sh" ]; then
  # T7: Write・Edit・MultiEdit・NotebookEdit で会話記録・同意の台帳を触る（file_path と notebook_path の両方、小文字の realpath）
  G0="$(count_guard)"
  KWS="$(guard_kinds)"
  JSONL_P="$REAL_HOME_DIR/.claude/projects/-Users-x/s.jsonl"
  tj T7-w1 worktree-only-guard.sh W 2 Write     "{\"file_path\":\"$JSONL_P\"}"
  tj T7-w2 worktree-only-guard.sh W 2 Edit      "{\"file_path\":\"$JSONL_P\"}"
  tj T7-w3 worktree-only-guard.sh W 2 MultiEdit "{\"file_path\":\"$JSONL_P\"}"
  tj T7-w4 worktree-only-guard.sh W 2 NotebookEdit "{\"notebook_path\":\"$JSONL_P\"}"
  tj T7-w5 worktree-only-guard.sh W 2 Write     "{\"file_path\":\"$REAL_HOME_DIR/.claude/logs/consent-used.jsonl\"}"
  tj T7-w6 worktree-only-guard.sh W 2 Write     "{\"file_path\":\"$REAL_HOME_DIR/.CLAUDE/Projects/-Users-x/S.JSONL\"}"
  G1="$(count_guard)"
  if [ -z "${ONLY:-}" ]; then
    if [ "$((G1 - G0))" = "6" ]; then PASS=$((PASS + 1)); RESULTS+=("T7-wlog  consent_guard_blocked が6件増えた PASS")
    else FAIL=$((FAIL + 1)); RESULTS+=("T7-wlog  consent_guard_blocked の増加=$((G1 - G0)) 期待=6 FAIL"); fi
  fi
  check_new_kinds T7-wkind "$KWS" "write write write write write write"
  tj T7-w7 worktree-only-guard.sh W 0 Write    "{\"file_path\":\"$WT_ROOT/docs/handoff/conversation-consent/x.md\"}"
  tj T7-w8 worktree-only-guard.sh W 0 NotebookEdit "{\"notebook_path\":\"$WT_ROOT/x.ipynb\"}"
  tj T7-w9 worktree-only-guard.sh W 0 Edit      "{\"file_path\":\"$REAL_HOME_DIR/.claude/projects/-Users-x/notes.md\"}"
fi

# T9: 本文ファイルが読めずに止めたときの文が、Write で先に作る手順を示す
if [ -f "$HOOKDIR/pr-body-guard.sh" ] && { [ -z "${ONLY:-}" ] || [ "$ONLY" = "T9" ]; }; then
  inf="$T/in-T9.json"
  python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":"gh pr create --title t --body-file /nonexistent/x.md"},"cwd":sys.argv[1]}))' "$WT_ROOT" > "$inf"
  T9_OUT="$(run_hook_err pr-body-guard.sh "$WT_ROOT" "$inf")"
  if echo "$T9_OUT" | grep -q '本文ファイルを Write で先に作り、別のコマンドで gh を実行してください'; then
    PASS=$((PASS + 1)); RESULTS+=("T9       pr-body-guard の止める文が手順を示す PASS")
  else
    FAIL=$((FAIL + 1)); RESULTS+=("T9       pr-body-guard の止める文に手順が無い FAIL")
  fi
fi

# K1〜K3: --head のブランチの worktree を検証の場所にする（標準エラーの行だけで判定）
if [ -f "$HOOKDIR/pr-body-guard.sh" ] && { [ -z "${ONLY:-}" ] || [ "$ONLY" = "K1" ] || [ "$ONLY" = "K2" ] || [ "$ONLY" = "K3" ] || [ "$ONLY" = "K7" ] || [ "$ONLY" = "K8" ]; }; then
  KMAIN="$T/k-main"; KWT="$T/k-wt"; KBODY="$T/k-body.md"
  mkdir -p "$KMAIN"
  git -C "$KMAIN" init -q -b main
  git -C "$KMAIN" remote add origin https://github.com/shingo-ops/salesanchor.git
  git -C "$KMAIN" -c user.name=t -c user.email=t@example.com commit -q --allow-empty -m init
  git -C "$KMAIN" worktree add -q -b release/t-headwt "$KWT"
  mkdir -p "$KWT/docs/handoff/t"
  : > "$KWT/docs/handoff/t/recon.md"
  : > "$KWT/docs/handoff/t/design.md"
  printf 't\n' > "$KBODY"
  k_check() {
    local id="$1" want="$2" cmd="$3" out got inf="$T/in-$1.json"
    if [ -n "${ONLY:-}" ] && [ "$ONLY" != "$id" ]; then return; fi
    python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]},"cwd":sys.argv[2]}))' "$cmd" "$KMAIN" > "$inf"
    out="$(run_hook_err pr-body-guard.sh "$KMAIN" "$inf")"
    if echo "$out" | grep -q '作業場所を release/t-headwt の worktree'; then got=yes; else got=no; fi
    if [ "$got" = "$want" ]; then PASS=$((PASS + 1)); RESULTS+=("$id       pr-body-guard の作業場所の行=$got PASS")
    else FAIL=$((FAIL + 1)); RESULTS+=("$id       pr-body-guard の作業場所の行=$got 期待=$want FAIL"); fi
  }
  k_check K1 yes "gh pr create --head release/t-headwt --title t --body-file $KBODY"
  k_check K2 no  "gh pr create --head no-such-branch --title t --body-file $KBODY"
  k_check K3 no  "cd $KMAIN && gh pr create --head release/t-headwt --title t --body-file $KBODY"
  # K7: 本文は元の場所（本体）で読む。rel.md は worktree にだけ置くので、読み込めずに止まる
  if [ -z "${ONLY:-}" ] || [ "$ONLY" = "K7" ]; then
    printf 't\n' > "$KWT/rel.md"
    # 検証スクリプトが worktree に無いと本文を読む手前でフックが抜けるので、写しを置く
    mkdir -p "$KWT/scripts/dev"
    cp "$WT_ROOT/scripts/dev/validate-pr-body.sh" "$KWT/scripts/dev/validate-pr-body.sh"
    python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]},"cwd":sys.argv[2]}))' "gh pr create --head release/t-headwt --title t --body-file rel.md" "$KMAIN" > "$T/in-K7.json"
    K7_OUT="$(run_hook_err pr-body-guard.sh "$KMAIN" "$T/in-K7.json")"
    if echo "$K7_OUT" | grep -q -e '--body-file を読み込めない'; then
      PASS=$((PASS + 1)); RESULTS+=("K7       pr-body-guard は本文を元の場所で読む PASS")
    else
      FAIL=$((FAIL + 1)); RESULTS+=("K7       pr-body-guard が本文を worktree 側で読んだ FAIL")
    fi
  fi
  # K8: --head の枝が分かるときだけ validate-pr-body.sh に CBS_PR_HEAD_REF=<枝> を渡す（偽の validate が環境変数を書き出す）
  if [ -z "${ONLY:-}" ] || [ "$ONLY" = "K8" ]; then
    K8_OUT="$T/k8-env.txt"
    mkdir -p "$KWT/scripts/dev"
    printf '#!/usr/bin/env bash\nprintf "%%s" "${CBS_PR_HEAD_REF-UNSET}" > "%s"\ncat > /dev/null\n' "$K8_OUT" > "$KWT/scripts/dev/validate-pr-body.sh"
    k8_run() {
      rm -f "$K8_OUT"
      python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]},"cwd":sys.argv[2]}))' "$1" "$KMAIN" > "$T/in-K8.json"
      run_hook_err pr-body-guard.sh "$KMAIN" "$T/in-K8.json" > /dev/null || true
      cat "$K8_OUT" 2>/dev/null || echo "NOFILE"
    }
    k8_got="$(k8_run "gh pr create --head release/t-headwt --title t --body-file $KBODY")"
    if [ "$k8_got" = "release/t-headwt" ]; then
      PASS=$((PASS + 1)); RESULTS+=("K8       pr-body-guard は --head の枝を CBS_PR_HEAD_REF で渡す PASS")
    else
      FAIL=$((FAIL + 1)); RESULTS+=("K8       pr-body-guard が CBS_PR_HEAD_REF を渡さない（得た値=$k8_got） FAIL")
    fi
    k8_got2="$(k8_run "cd $KMAIN && gh pr create --head release/t-headwt --title t --body-file $KBODY")"
    if [ "$k8_got2" = "UNSET" ] || [ "$k8_got2" = "NOFILE" ]; then
      PASS=$((PASS + 1)); RESULTS+=("K8b      pr-body-guard は cd を含む形では CBS_PR_HEAD_REF を渡さない PASS")
    else
      FAIL=$((FAIL + 1)); RESULTS+=("K8b      cd を含む形で CBS_PR_HEAD_REF を渡した（得た値=$k8_got2） FAIL")
    fi
  fi
fi

# T0〜T6: 判定部品 consent_check.py と consent-audit.py の単体試験（偽の会話記録・偽のホームで行う。本物の ~/.claude には書かない）
if [ -f "$HOOKDIR/consent_check.py" ] && { [ -z "${ONLY:-}" ] || [ "$ONLY" = "T1-6" ]; }; then
  while IFS= read -r line; do
    case "$line" in
      PASS*) PASS=$((PASS + 1)); RESULTS+=("$line") ;;
      FAIL*) FAIL=$((FAIL + 1)); RESULTS+=("$line") ;;
      *) RESULTS+=("(出力) $line") ;;
    esac
  done < <(python3 -I "$WT_ROOT/scripts/dev/consent-unit-tests.py" "$HOOKDIR" "$T" "$WT_ROOT")
fi

echo "フックディレクトリ: $HOOKDIR"
echo "worktree 役: $WT_ROOT"
echo "モード: $([ "$REAL_HOME_MODE" = "--real-home" ] && echo 本物のHOME || echo 偽のHOME)"
printf '%-9s %-22s %-6s %-5s %-6s %s\n' ID フック 場所 期待 実際 判定
for r in "${RESULTS[@]}"; do echo "$r"; done
echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
