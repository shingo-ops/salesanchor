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
trap 'rm -rf "$T"' EXIT

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
    ( cd "$cwd" && env ${SAN:+DANGER_SANITIZER="$SAN"} bash "$HOOKDIR/$hook" < "$inf" >/dev/null 2>&1 )
  else
    ( cd "$cwd" && env HOME="$FAKE_HOME" ${SAN:+DANGER_SANITIZER="$SAN"} bash "$HOOKDIR/$hook" < "$inf" >/dev/null 2>&1 )
  fi
  echo $?
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
t T2-11d agent-danger-hook.sh   W 2 'rm -rf docs/handoff/stage2-test-nonexistent'
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

echo "フックディレクトリ: $HOOKDIR"
echo "worktree 役: $WT_ROOT"
echo "モード: $([ "$REAL_HOME_MODE" = "--real-home" ] && echo 本物のHOME || echo 偽のHOME)"
printf '%-9s %-22s %-6s %-5s %-6s %s\n' ID フック 場所 期待 実際 判定
for r in "${RESULTS[@]}"; do echo "$r"; done
echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
