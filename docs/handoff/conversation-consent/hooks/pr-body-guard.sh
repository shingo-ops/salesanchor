#!/usr/bin/env bash
# pr-body-guard.sh
# Claude Code PreToolUse hook: gh pr create / gh pr edit --body 実行前にPR本文を検証する。
# exit 0: 許可 / exit 2: ブロック
set -euo pipefail

# stdin から JSON を読み込む
INPUT="$(cat)"

# 停止理由の記録（設計承認チケット 段1: 記録のみ。止める・通すの判定には影響しない）
# 使い方: _hook_blocked_log "<フック名>" "<止める理由>"  → agent-events.jsonl に hook_blocked を1行追記
_hook_blocked_log() {
  printf '%s' "${INPUT:-}" | HB_HOOK="$1" HB_REASON="$2" python3 -c '
import sys, os, re, json, datetime
try:
    pats = [
        re.compile(r"(?i)(token|secret|password|passwd|api_key|apikey)[A-Za-z_]*\s*[=:]\s*\S+"),
        re.compile(r"Bearer\s+\S+"),
        re.compile(r"https://discord(app)?\.com/api/webhooks/\S+"),
    ]
    def mask(s):
        for p in pats:
            s = p.sub("***", s)
        return s
    cmd = ""
    try:
        d = json.loads(sys.stdin.read())
        ti = d.get("tool_input", {}) if isinstance(d, dict) else {}
        cmd = ti.get("command") or ti.get("file_path") or ""
    except Exception:
        cmd = ""
    rec = {
        "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": "hook_blocked",
        "hook": os.environ.get("HB_HOOK", ""),
        "reason": mask(os.environ.get("HB_REASON", "").split("\n")[0]),
        "cmd_head": mask(str(cmd))[:120],
    }
    with open(os.path.expanduser("~/.claude/logs/agent-events.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
except Exception:
    pass
' >/dev/null 2>&1 || true
}

# tool_name を取得（Bash 以外はスキップ）
TOOL_NAME="$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || true)"
if [[ "$TOOL_NAME" != "Bash" ]]; then
  exit 0
fi

# コマンドを抽出
COMMAND="$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null || true)"

# gh pr create --body(-file) または gh pr edit --body(-file) を含まなければスキップ
# gh pr comment --body には反応しない（create/edit のみ対象）
#
# 設計承認チケット 段2: ファイルに書く heredoc の本文（cat > f <<'E' ... E）は判定の対象外にする。
# 判定用の文字列 SCAN_COMMAND は heredoc 本文だけを取り除いたもの。取り除けないときは元のコマンドを使う。
# 本文の抽出と検証（下の extract-pr-body.py）は、これまでどおり元の COMMAND に対して行う。
SANITIZER="${DANGER_SANITIZER:-/Users/tanizawashingo/.claude/scripts/danger_sanitize.py}"
SCAN_COMMAND="$(printf '%s' "$INPUT" | python3 "$SANITIZER" heredoc 2>/dev/null)" || SCAN_COMMAND="$COMMAND"
if [[ -z "$SCAN_COMMAND" ]]; then
  SCAN_COMMAND="$COMMAND"
fi
IS_PR_CREATE=false
IS_PR_EDIT_BODY=false
if echo "$SCAN_COMMAND" | grep -qE 'gh[[:space:]]+pr[[:space:]]+create' && echo "$SCAN_COMMAND" | grep -qE '\-\-body(\-file)?([[:space:]=]|$)'; then
  IS_PR_CREATE=true
elif echo "$SCAN_COMMAND" | grep -qE 'gh[[:space:]]+pr[[:space:]]+edit' && echo "$SCAN_COMMAND" | grep -qE '\-\-body(\-file)?([[:space:]=]|$)'; then
  IS_PR_EDIT_BODY=true
fi
if [[ "$IS_PR_CREATE" == "false" ]] && [[ "$IS_PR_EDIT_BODY" == "false" ]]; then
  exit 0
fi

# PR_BODY_VALIDATE_SKIP=1 ならスキップ（環境変数またはコマンド文字列内の設定を確認）
if [[ "${PR_BODY_VALIDATE_SKIP:-}" == "1" ]]; then
  exit 0
fi
if echo "$SCAN_COMMAND" | grep -qE '(^|[[:space:];&&])PR_BODY_VALIDATE_SKIP=1([[:space:];&&]|$)'; then
  exit 0
fi

# cwd を取得（worktree のルート）
CWD="$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('cwd',''))" 2>/dev/null || true)"

# コマンド中の 'cd <path>' を抽出して実効 CWD を補正する
# 例: "cd /Users/.../worktrees/salesanchor/release-foo && gh pr create ..."
CMD_CD="$(echo "$COMMAND" | python3 -c "
import sys, re
cmd = sys.stdin.read()
m = re.search(r'cd\s+([\S]+)', cmd)
if m:
    print(m.group(1).strip())
" 2>/dev/null || true)"
if [[ -n "$CMD_CD" ]] && [[ -d "$CMD_CD" ]]; then
  CWD="$CMD_CD"
fi

# 本文（--body-file の相対パス）は gh が命令を流した場所で読むので、worktree へ切り替える前の場所で読む
BODY_CWD="$CWD"

# 命令文に cd が無いときだけ、--head／PR 番号のブランチから、そのブランチの worktree を検証の場所にする。
# ちょうど 1 つ見つかったときだけ変える。それ以外は何もしない（失敗してもフック全体は落とさない）。
if [[ -z "$CMD_CD" ]] && [[ -n "$CWD" ]] && [[ -d "$CWD" ]]; then
  HEAD_BRANCH="$(printf '%s' "$COMMAND" | python3 -c "
import sys, shlex, subprocess
try:
    w = shlex.split(sys.stdin.read())
except Exception:
    sys.exit(0)
repo = ''
rest = []
i = 0
while i < len(w):
    a = w[i]
    if a in ('-R', '--repo') and i + 1 < len(w):
        repo = w[i + 1]; i += 2; continue
    if a.startswith('--repo='):
        repo = a[7:]; i += 1; continue
    rest.append(a); i += 1
seq = None
for j in range(len(rest) - 2):
    if rest[j] == 'gh' and rest[j + 1] == 'pr' and rest[j + 2] in ('create', 'edit'):
        seq = j; break
if seq is None:
    sys.exit(0)
sub = rest[seq + 2]
args = rest[seq + 3:]
if sub == 'create':
    for k, a in enumerate(args):
        if a in ('--head', '-H') and k + 1 < len(args):
            print(args[k + 1]); break
        if a.startswith('--head='):
            print(a[7:]); break
else:
    target = next((a for a in args if not a.startswith('-')), '')
    if target:
        cmd = ['gh', 'pr', 'view', target]
        if repo:
            cmd += ['-R', repo]
        cmd += ['--json', 'headRefName', '-q', '.headRefName']
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                print(r.stdout.strip())
        except Exception:
            pass
" 2>/dev/null || true)"
  if [[ -n "$HEAD_BRANCH" ]]; then
    HEAD_WT="$(git -C "$CWD" worktree list --porcelain 2>/dev/null | python3 -c "
import sys
b = 'refs/heads/' + sys.argv[1]
hits = []
for blk in sys.stdin.read().split('\n\n'):
    path = ''; br = ''
    for ln in blk.splitlines():
        if ln.startswith('worktree '):
            path = ln[9:]
        elif ln.startswith('branch '):
            br = ln[7:]
    if path and br == b:
        hits.append(path)
if len(hits) == 1:
    print(hits[0])
" "$HEAD_BRANCH" 2>/dev/null || true)"
    if [[ -n "$HEAD_WT" ]] && [[ -d "$HEAD_WT" ]]; then
      CWD="$HEAD_WT"
      echo "pr-body-guard: 作業場所を ${HEAD_BRANCH} の worktree ${HEAD_WT} にしました" >&2
    fi
  fi
fi

# 送り先が salesanchor 以外なら検査しない（PO 承認 2026-10-15）。送り先が決まらないときは検査を続ける。
TARGET_REPO="$(echo "$COMMAND" | python3 -c "
import sys, re
m = re.search(r'(?:^|\s)(?:-R|--repo)(?:\s+|=)(\S+)', sys.stdin.read())
print(m.group(1) if m else '')
" 2>/dev/null || true)"
if [[ -z "$TARGET_REPO" ]] && [[ -n "$CWD" ]] && [[ -d "$CWD" ]]; then
  TARGET_REPO="$(git -C "$CWD" remote get-url origin 2>/dev/null || true)"
fi
if [[ -n "$TARGET_REPO" ]] && ! echo "$TARGET_REPO" | grep -qi 'salesanchor'; then
  echo "pr-body-guard: salesanchor 以外のリポジトリ(${TARGET_REPO})のため検査しません" >&2
  exit 0
fi

# validate-pr-body.sh のパスを解決
# 優先順: 1) cwd から探す 2) ~/salesanchor から探す
VALIDATE_SCRIPT=""
if [[ -n "$CWD" ]] && [[ -f "${CWD}/scripts/dev/validate-pr-body.sh" ]]; then
  VALIDATE_SCRIPT="${CWD}/scripts/dev/validate-pr-body.sh"
elif [[ -f "${HOME}/salesanchor/scripts/dev/validate-pr-body.sh" ]]; then
  VALIDATE_SCRIPT="${HOME}/salesanchor/scripts/dev/validate-pr-body.sh"
else
  # worktrees 配下を探す
  FOUND="$(find "${HOME}/worktrees" -name "validate-pr-body.sh" -path "*/scripts/dev/*" 2>/dev/null | head -1 || true)"
  if [[ -n "$FOUND" ]]; then
    VALIDATE_SCRIPT="$FOUND"
  fi
fi

if [[ -z "$VALIDATE_SCRIPT" ]]; then
  echo "⚠️  validate-pr-body.sh が見つかりません。PR本文検証をスキップします" >&2
  exit 0
fi

# --body の値を抽出する
# パターン1: --body "..." or --body '...'
# パターン2: --body "$(cat <<'EOF'\n...\nEOF\n)"
EXTRACT_SCRIPT="${0%/*}/extract-pr-body.py"
if [[ ! -f "$EXTRACT_SCRIPT" ]]; then
  echo "⚠️  extract-pr-body.py が見つかりません。PR本文検証をスキップします" >&2
  exit 0
fi

# CWD（cd 補正済み）を extract-pr-body.py に渡し、--body-file の相対パス解決や
# gh pr create/edit セグメントの切り分けに使わせる
# set -e 下でExit code を確実に拾うため、代入文の外で明示的に無効化/再有効化する
set +e
PR_BODY="$(echo "$COMMAND" | python3 "$EXTRACT_SCRIPT" "$BODY_CWD")"
EXTRACT_RC=$?
set -e

# exit 3: --body-file が指定されたが読み込めなかった（未存在・読み取り不可）。
# 本文を検証できない以上、安全側に倒してブロックする（fail-closed）。
if [[ "$EXTRACT_RC" -eq 3 ]]; then
  _hook_blocked_log "pr-body-guard" "BLOCKED [pr-body-guard]: --body-file を読み込めないため PR本文を検証できません。"
  echo "🚫 BLOCKED [pr-body-guard]: --body-file を読み込めないため PR本文を検証できません。" >&2
  echo "   本文ファイルを Write で先に作り、別のコマンドで gh を実行してください。" >&2
  exit 2
fi

if [[ -z "$PR_BODY" ]]; then
  echo "⚠️  PR本文を抽出できませんでした。検証をスキップします" >&2
  exit 0
fi

# validate-pr-body.sh に PR本文を渡して検証
# CWD（コマンド中の cd から補正済み）へ移動することで git rev-parse が worktree を返す
if [[ -n "$CWD" ]] && [[ -d "$CWD" ]]; then
  cd "$CWD"
fi
if echo "$PR_BODY" | bash "$VALIDATE_SCRIPT"; then
  exit 0
else
  _hook_blocked_log "pr-body-guard" "BLOCKED [pr-body-guard]: validate-pr-body.sh が不合格 (PR本文の検証失敗)"
  exit 2
fi
