#!/bin/bash
# 危険操作ブロックフック（PreToolUse — 同期実行）
#
# exit 0: 操作を許可
# exit 1: 操作をブロック（Claude に実行させない）
#
# ※ settings.json で async: false（省略）かつ PreToolUse に登録されている場合のみブロックが有効

TOKENS="$HOME/.claude/agent-tokens.json"
EVENTS_LOG="$HOME/.claude/logs/agent-events.jsonl"
PERMITS_DIR="$HOME/.claude/permits"

# stdin から JSON を読む
INPUT=$(cat)

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

# 会話での同意（ADR-1033）: 許可券が無いとき、同意票＋PO の「1」で通せるかを consent_check.py に聞く。
# allow が返ったときだけ通す（それ以外は今までどおり止める）。判定の中身は consent_check.py にある。
CONSENT_CHECK="${CONSENT_CHECK:-$HOME/.claude/scripts/consent_check.py}"
_consent_allows() {
  [ "$(printf '%s' "$INPUT" | python3 "$CONSENT_CHECK" 2>/dev/null)" = "allow" ]
}

# 偽造を防ぐ見張りが止めたときの記録: consent_guard_blocked（どの条件か・cmd_head）を1行追記
_consent_guard_log() {
  printf '%s' "${INPUT:-}" | CG_COND="$1" python3 -c '
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
        "type": "consent_guard_blocked",
        "hook": "agent-danger-hook",
        "condition": os.environ.get("CG_COND", ""),
        "cmd_head": mask(str(cmd))[:120],
    }
    with open(os.path.expanduser("~/.claude/logs/agent-events.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
except Exception:
    pass
' >/dev/null 2>&1 || true
}

# コマンド文字列を抽出（Bash ツールの場合）
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    cmd = data.get('tool_input', {}).get('command', '')
    print(cmd)
except:
    print('')
" 2>/dev/null)

if [ -z "$COMMAND" ]; then
  exit 0
fi

# 設計承認チケット 段2（誤検知修正）: 危険語・psql 書き込みの照合前に、ただの文字を取り除く。
# 取り除くもの: ファイルに書く heredoc の本文 / git commit -m の文 / gh pr の --body と --title /
#   grep の検索語 / 作業場所と /private/tmp/claude-501/ の下だけを消す rm -r
# bash -c / eval の中身、$(...) を含む語は取り除かない。解析できないときは元のコマンドをそのまま照合する。
# permits 自己発行ブロックと破壊的 git の検出は、取り除く前の COMMAND を使う（緩めない）。
SANITIZER="${DANGER_SANITIZER:-/Users/tanizawashingo/.claude/scripts/danger_sanitize.py}"
SCAN_COMMAND=$(printf '%s' "$INPUT" | python3 "$SANITIZER" all 2>/dev/null) || SCAN_COMMAND="$COMMAND"
if [ -z "$SCAN_COMMAND" ]; then
  SCAN_COMMAND="$COMMAND"
fi

# ── SalesAnchor スコープ判定 ─────────────────────────────────────────────────
# このブロックは shingo-ops/salesanchor リポジトリ内でのみ発火させる
# 他プロジェクト（crm-app 等）への誤爆を防ぐ
REMOTE_URL=$(git -C "$PWD" remote get-url origin 2>/dev/null || true)
if [[ "$REMOTE_URL" == *"shingo-ops/salesanchor"* ]]; then
  SALESANCHOR_SCOPE=1
else
  SALESANCHOR_SCOPE=0
fi

# ── 本番DB直接書き込みブロック（SalesAnchorのみ・対策A） ──────────────────────
# ファイル流し込みは中身を問わず一律ブロック（中身の解析は抜け道を生むため）
# 許可: ssh ... psql -c "SELECT ..."
# ブロック: < file / -f file / | psql / -c "INSERT/UPDATE/..."
if [ "$SALESANCHOR_SCOPE" = "1" ]; then
  PSQL_WRITE_BLOCKED=$(python3 - "$SCAN_COMMAND" <<'PYEOF'
import sys, re

cmd = sys.argv[1]

patterns = [
    (r"ssh\b.*\bpsql\b.*<\s*\S",        "ssh+psql < file"),
    (r"ssh\b.*\bpsql\b.*-f\s+\S",       "ssh+psql -f file"),
    (r"\|\s*(?:ssh\b[^|]*\bpsql|docker\b[^|]*\bpsql|\bpsql)\b", "pipe to psql"),
    (r"docker\b.*\bexec\b.*-i\b.*\bpsql\b.*<\s*\S", "docker+psql < file"),
    (r"docker\b.*\bexec\b.*\bpsql\b.*-f\s+\S",      "docker+psql -f file"),
]

for pattern, label in patterns:
    if re.search(pattern, cmd, re.IGNORECASE | re.DOTALL):
        print("blocked:" + label)
        sys.exit(0)

# -c オプションの中身に書き込みキーワードがある場合もブロック
# ダブルクォートで囲まれたSQL文字列を対象（シングルクォートも考慮）
c_match = re.search(r'\bpsql\b[^|&;]*-c\s+"([^"]+)"', cmd, re.IGNORECASE)
if c_match:
    sql = c_match.group(1)
    write_kw = r"\b(INSERT\s+INTO|UPDATE\s+\w+|DELETE\s+FROM|CREATE\s+|ALTER\s+|DROP\s+|TRUNCATE\s+|GRANT\s+|REVOKE\s+)\b"
    if re.search(write_kw, sql, re.IGNORECASE):
        print("blocked:-c write SQL")
        sys.exit(0)

print("")
PYEOF
  )

  if [[ "$PSQL_WRITE_BLOCKED" == blocked:* ]]; then
    REASON="${PSQL_WRITE_BLOCKED#blocked:}"
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    SESSION_NAME=$(basename "$PWD")
    BRANCH=$(git -C "$PWD" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

    printf '{"type":"danger_detected","session":"%s","branch":"%s","op":"psql-write:%s","ts":"%s"}\n' \
      "$SESSION_NAME" "$BRANCH" "$REASON" "$TIMESTAMP" >> "$EVENTS_LOG"

    # permit チェック（対策B）
    # Shared one-use bridge; failure remains a denial.
    PERMIT_RESULT=$(printf '%s' "$INPUT" | python3 "$HOME/.codex/salesanchor/permit_bridge.py" consume-ticket)


    if [ "$PERMIT_RESULT" = "consumed" ]; then
      printf '{"type":"danger_permit_consumed","session":"%s","branch":"%s","op":"psql-write","ts":"%s"}\n' \
        "$SESSION_NAME" "$BRANCH" "$TIMESTAMP" >> "$EVENTS_LOG"
      echo "🔑 使い捨て許可チケットを消費しました: psql write ($REASON)" >&2
      exit 0
    fi

    # 許可券（受領書）が無いとき: 会話の同意票＋PO の「1」で通せるか（ADR-1033）。permit_bridge.py は変えない。
    if _consent_allows; then
      echo "🔑 会話での同意を使いました: psql write ($REASON)" >&2
      exit 0
    fi

    _hook_blocked_log "agent-danger-hook" "BLOCKED [psql-write-guard]: psql-write:$REASON"
    echo "🚫 BLOCKED [psql-write-guard]: 本番DBへの直接書き込みは禁止されています。" >&2
    echo "   検知パターン: $REASON" >&2
    echo "   読み取り（-c \"SELECT ...\"）は許可されています。" >&2
    echo "   書き込みが必要な場合: bash scripts/permit-danger.sh \"psql write\"" >&2
    echo "   （1回限り有効・30分で自動失効）" >&2
    exit 2
  fi
fi

# ── permits 自己発行ブロック ────────────────────────────────────────────────
# コマンド名ではなくパス文字列で判定:
#   ~/.claude/permits / $HOME/.claude/permits / /Users/xxx/.claude/permits
#   .claude/permits（相対）いずれも対象
PERMITS_SELF=$(python3 -c "
import sys, re
cmd = sys.argv[1]
# 検出パターン（4種）:
#   P1: tilde / \$HOME / \${HOME} / 絶対パス（2段以上） → /.claude/permits
#   P2: 相対パス .claude/permits（/や\wが直前にない）
#   P3: 変数 + '/.claude/permits' 形式（home + '/.claude/permits/...'）
#   P4: os.path.join 分割形式（'.claude', 'permits'）
if re.search(
    r'(~|\$\{?HOME\}?|/[^\s/]+/[^\s/]+)/\.claude/permits'
    r'|(?<![/\w])\.claude/permits'
    r'|[\'\"]/\.claude/permits'
    r'|[\'\"]\s*\.claude\s*[\'\"]\s*,\s*[\'\"]\s*permits',
    cmd
):
    print('blocked')
" "$COMMAND" 2>/dev/null)

if [ "$PERMITS_SELF" = "blocked" ]; then
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  SESSION_NAME=$(basename "$PWD")
  BRANCH=$(git -C "$PWD" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

  printf '{"type":"permits_self_issue_blocked","session":"%s","branch":"%s","ts":"%s"}\n' \
    "$SESSION_NAME" "$BRANCH" "$TIMESTAMP" >> "$EVENTS_LOG"

  _hook_blocked_log "agent-danger-hook" "BLOCKED [permits-guard]: permits ディレクトリへの直接アクセス"
  echo "🚫 BLOCKED [permits-guard]: permits ディレクトリへの直接アクセスは禁止されています。" >&2
  echo "   permits の発行・読取は scripts/permit-danger.sh 経由のみ許可されます。" >&2
  exit 2
fi

# ── 会話記録・同意の台帳・端末への入力注入の見張り（ADR-1033 §4-5） ─────────────────
# AI が自分で同意を作れないように、次のどれかがコマンド（サニタイズ前）にあれば止める。
CONSENT_GUARD=$(python3 -c "
import sys
cmd = sys.argv[1]
if '.claude/projects/' in cmd and '.jsonl' in cmd:
    print('transcript')
elif 'consent-used' in cmd:
    print('consent-used')
elif 'tmux' in cmd and any(w in cmd for w in ('send-keys', 'paste-buffer', 'load-buffer', 'set-buffer')):
    print('tmux-inject')
elif 'osascript' in cmd and 'keystroke' in cmd:
    print('osascript-keystroke')
elif ('127.0.0.1' in cmd or 'localhost' in cmd) and '/chat/queue' in cmd:
    print('chat-queue')
" "$COMMAND" 2>/dev/null)

if [ -n "$CONSENT_GUARD" ]; then
  _consent_guard_log "$CONSENT_GUARD"
  echo "🚫 BLOCKED [consent-guard]: 会話記録・同意の台帳を Bash で触ることはできません。読むだけなら Read/Grep ツールを使ってください。突き合わせと K0 の目安は \`python3 scripts/dev/consent-audit.py\` を使ってください" >&2
  exit 2
fi

# ── スコープ認識型削除ガード（SalesAnchorのみ）────────────────────────────────
# git clean / git stash(破壊系) / git checkout -- / git restore を検出し、
# 本店（メインリポジトリ）での実行はブロック、worktree内は警告ログのみ。
if [ "$SALESANCHOR_SCOPE" = "1" ]; then
  # SCOPE_RESULT: "<label>\t<effective_dir>"
  # effective_dir は 1) マッチしたサブコマンド自身の `git -C <path>` を最優先、
  # 2) なければ先頭の `cd <path> &&`（worktree-only-guard.sh の解析方式を再利用）、
  # 3) どちらもなければ ${PWD}。
  SCOPE_RESULT=$(python3 - "$COMMAND" "$PWD" "$INPUT" <<'PYEOF'
import sys, re, os, json, shlex

cmd = sys.argv[1]
pwd = sys.argv[2]
input_json = sys.argv[3]

try:
    payload = json.loads(input_json)
except Exception:
    payload = {}
tool_input = payload.get('tool_input', {}) if isinstance(payload, dict) else {}

base = tool_input.get('workdir') or payload.get('cwd') or pwd
if not isinstance(base, str) or not os.path.isabs(base) or not os.path.isdir(base):
    base = pwd

# 先頭の literal `cd <path> &&` を解析（worktree-only-guard.sh と同じ方式）
m = re.match(
    r"^\s*cd[ \t]+(?:--[ \t]+)?(\"[^\"$`\n]*\"|'[^'\n]*'|[^\s;&|<>()$`\\]+)[ \t]*(?:&&|;|\n|$)",
    cmd,
)
if m:
    raw = m.group(1)
    try:
        path = shlex.split(raw)[0]
    except (ValueError, IndexError):
        path = raw
    if not raw.startswith(("'", "\"")):
        path = os.path.expanduser(path)
    candidate = os.path.join(base, path)
    if os.path.isdir(candidate):
        base = os.path.realpath(candidate)

BASE_DIR = base

# 破壊的 git 操作のパターン（各サブコマンド先頭で re.match）
patterns = [
    (r'git\s+clean\b',                              'git clean'),
    (r'git\s+stash\b(?!\s+(pop|show|list|apply))',  'git stash (destructive)'),
    (r'git\s+checkout\s+--\s',                      'git checkout --'),
    (r'git\s+restore\b',                            'git restore'),
]

# シェル演算子でサブコマンドに分割
sub_cmds = re.split(r'\s*(?:&&|\|\||;|\|)\s*', cmd)
for sub in sub_cmds:
    sub = sub.strip()
    for pattern, label in patterns:
        if re.match(pattern, sub, re.IGNORECASE):
            eff_dir = BASE_DIR
            # そのサブコマンド自身に `git -C <path>` があれば cd/cwd より優先
            cmatch = re.search(r"git\s+-C\s+(\"[^\"]*\"|'[^']*'|\S+)", sub)
            if cmatch:
                raw_c = cmatch.group(1)
                try:
                    cpath = shlex.split(raw_c)[0]
                except (ValueError, IndexError):
                    cpath = raw_c
                cpath = os.path.expanduser(cpath)
                if not os.path.isabs(cpath):
                    cpath = os.path.join(BASE_DIR, cpath)
                cpath = os.path.realpath(cpath)
                if os.path.isdir(cpath):
                    eff_dir = cpath
            print(f"{label}\t{eff_dir}")
            sys.exit(0)
PYEOF
  )

  SCOPE_DESTRUCT_MATCHED=""
  EFFECTIVE_DIR="$PWD"
  if [ -n "$SCOPE_RESULT" ]; then
    SCOPE_DESTRUCT_MATCHED="${SCOPE_RESULT%%$'\t'*}"
    EFFECTIVE_DIR="${SCOPE_RESULT#*$'\t'}"
  fi

  if [ -n "$SCOPE_DESTRUCT_MATCHED" ]; then
    # 本店かworktreeかを git-common-dir で判定（cd / git -C 補正済みの実効ディレクトリで判定）
    COMMON=$(git -C "$EFFECTIVE_DIR" rev-parse --git-common-dir 2>/dev/null || true)
    if [[ "$COMMON" = /* ]]; then
      # 絶対パス → worktree内 → 警告ログのみ許可
      IN_WORKTREE=1
    else
      # 相対パス(.git) → 本店 → ブロック対象
      IN_WORKTREE=0
    fi

    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    SESSION_NAME=$(basename "$PWD")
    BRANCH=$(git -C "$PWD" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

    if [ "$IN_WORKTREE" = "1" ]; then
      # worktree内: ログだけ残して通過
      printf '{"type":"scope_destruct_worktree_allowed","session":"%s","branch":"%s","op":"%s","ts":"%s"}\n' \
        "$SESSION_NAME" "$BRANCH" "$SCOPE_DESTRUCT_MATCHED" "$TIMESTAMP" >> "$EVENTS_LOG"
    else
      # 本店: ブロック（permit があれば通過）
      printf '{"type":"scope_destruct_detected","session":"%s","branch":"%s","op":"%s","ts":"%s"}\n' \
        "$SESSION_NAME" "$BRANCH" "$SCOPE_DESTRUCT_MATCHED" "$TIMESTAMP" >> "$EVENTS_LOG"

      # ワンタイム許可チケットをチェック
      PERMIT_RESULT=$(python3 - "$PERMITS_DIR" "$SCOPE_DESTRUCT_MATCHED" "$TIMESTAMP" <<'PYEOF'
import sys, json, os, glob
from datetime import datetime, timezone

permits_dir = sys.argv[1]
op_matched  = sys.argv[2].lower()
now_str     = sys.argv[3]
now = datetime.strptime(now_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)

permit_files = glob.glob(os.path.join(permits_dir, 'danger-permit-*.json'))
for pf in permit_files:
    try:
        with open(pf, encoding='utf-8') as f:
            p = json.load(f)

        # 期限切れチェック → 削除して次へ
        expires = datetime.strptime(p['expires_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        if now > expires:
            os.remove(pf)
            continue

        # 操作一致チェック（部分一致）
        if p.get('op', '').lower() in op_matched or op_matched in p.get('op', '').lower():
            os.remove(pf)   # 消費（削除）
            print('consumed')
            sys.exit(0)
    except Exception:
        pass
PYEOF
      )

      if [ "$PERMIT_RESULT" = "consumed" ]; then
        printf '{"type":"scope_destruct_permit_consumed","session":"%s","branch":"%s","op":"%s","ts":"%s"}\n' \
          "$SESSION_NAME" "$BRANCH" "$SCOPE_DESTRUCT_MATCHED" "$TIMESTAMP" >> "$EVENTS_LOG"
        echo "🔑 使い捨て許可チケットを消費しました: $SCOPE_DESTRUCT_MATCHED" >&2
        exit 0
      fi

      _hook_blocked_log "agent-danger-hook" "BLOCKED [scope-destruct-guard]: $SCOPE_DESTRUCT_MATCHED"
      echo "🚫 BLOCKED [scope-destruct-guard]: 本店での破壊的 git 操作は禁止されています。" >&2
      echo "   検知操作: $SCOPE_DESTRUCT_MATCHED" >&2
      echo "   worktree 内での実行は許可されています。" >&2
      echo "   本店での実行が必要な場合: bash scripts/permit-danger.sh \"$SCOPE_DESTRUCT_MATCHED\"" >&2
      echo "   （1回限り有効・30分で自動失効）" >&2
      exit 2
    fi
  fi
fi

# danger_ops リストと照合
# 読み取り専用の検索・表示コマンド（grep/rg/ag/sed -n/cat/head/tail/less）の
# 引用文字列引数内に危険トークンの文字列が現れただけの場合はブロックしない
# （例: grep -i "DROP TABLE" x.log）。
# awk は system()/パイプでコマンドを実行できるため read-only 扱いにしない
# （例: awk 'BEGIN{system("psql -c \"DROP TABLE x\"")}' は引き続きブロックする）。
# トークンが実際に SQL 実行文脈（psql -c/-f/< 等）で使われている場合は
# 別セクション（本番DB直接書き込みブロック）で既にブロック済み。
MATCHED=$(python3 -c "
import json, sys, re

READONLY_CMDS = {'grep', 'egrep', 'fgrep', 'rg', 'ag', 'cat', 'head', 'tail', 'less'}

def is_readonly_display_segment(seg):
    s = seg.strip()
    if not s:
        return False
    # 段2: 複数行（heredoc 本文を含む）・コマンド置換・バッククォートを含む区間は読み取り専用扱いにしない
    if '\n' in s or (chr(36) + '(') in s or chr(96) in s:
        return False
    m = re.match(r'([\w./-]+)', s)
    if not m:
        return False
    name = m.group(1).split('/')[-1]
    if name in READONLY_CMDS:
        return True
    if name == 'sed' and re.search(r'(^|\s)-n(\s|$)', s):
        return True
    return False

def strip_readonly_segments(cmd):
    # トップレベルのシェル演算子で分割（クォート非解釈の簡易分割）
    parts = re.split(r'(&&|\|\||;|\|)', cmd)
    out = []
    for part in parts:
        if part in ('&&', '||', ';', '|'):
            out.append(part)
            continue
        out.append('' if is_readonly_display_segment(part) else part)
    return ''.join(out)

try:
    tokens = json.load(open('$TOKENS'))
    danger_ops = tokens.get('danger_ops', [])
    cmd = sys.argv[1]
    scanned = strip_readonly_segments(cmd)
    for op in danger_ops:
        if op.lower() in scanned.lower():
            print(op)
            break
except:
    pass
" "$SCAN_COMMAND" 2>/dev/null)

if [ -n "$MATCHED" ]; then
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  SESSION_NAME=$(basename "$PWD")
  BRANCH=$(git -C "$PWD" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

  # イベントログに記録
  printf '{"type":"danger_detected","session":"%s","branch":"%s","op":"%s","ts":"%s"}\n' \
    "$SESSION_NAME" "$BRANCH" "$MATCHED" "$TIMESTAMP" >> "$EVENTS_LOG"

  # ── ワンタイム許可チケットをチェック ──────────────────────────────────
  PERMIT_RESULT=$(python3 - "$PERMITS_DIR" "$MATCHED" "$TIMESTAMP" <<'PYEOF'
import sys, json, os, glob
from datetime import datetime, timezone

permits_dir = sys.argv[1]
op_matched  = sys.argv[2].lower()
now_str     = sys.argv[3]
now = datetime.strptime(now_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)

permit_files = glob.glob(os.path.join(permits_dir, 'danger-permit-*.json'))
for pf in permit_files:
    try:
        with open(pf, encoding='utf-8') as f:
            p = json.load(f)

        # 期限切れチェック → 削除して次へ
        expires = datetime.strptime(p['expires_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        if now > expires:
            os.remove(pf)
            continue

        # 操作一致チェック（部分一致）
        if p.get('op', '').lower() in op_matched or op_matched in p.get('op', '').lower():
            os.remove(pf)   # 消費（削除）
            print('consumed')
            sys.exit(0)
    except Exception:
        pass
PYEOF
  )

  if [ "$PERMIT_RESULT" = "consumed" ]; then
    printf '{"type":"danger_permit_consumed","session":"%s","branch":"%s","op":"%s","ts":"%s"}\n' \
      "$SESSION_NAME" "$BRANCH" "$MATCHED" "$TIMESTAMP" >> "$EVENTS_LOG"
    echo "🔑 使い捨て許可チケットを消費しました: $MATCHED" >&2
    exit 0
  fi

  # 許可券が無いとき: 会話の同意票＋PO の「1」で通せるか（ADR-1033）
  if _consent_allows; then
    echo "🔑 会話での同意を使いました: $MATCHED" >&2
    exit 0
  fi

  # VOICEVOX で警告（非同期）
  SPEAKER=$(python3 -c "import json; print(json.load(open('$TOKENS'))['speaker_warning'])" 2>/dev/null || echo "3")
  /Users/tanizawashingo/.claude/scripts/notify.sh "危険な操作をブロックしました: $MATCHED" "$SPEAKER" &

  # ブロックメッセージを stderr に出力（Claude が読む）
  _hook_blocked_log "agent-danger-hook" "BLOCKED: '$MATCHED' は不可逆操作"
  echo "🚫 BLOCKED: '$MATCHED' は不可逆操作のためブロックされました。" >&2
  echo "   しんごさんの承認が必要です。" >&2
  echo "   許可する場合: bash scripts/permit-danger.sh \"$MATCHED\"" >&2
  echo "   （1回限り有効・30分で自動失効）" >&2

  exit 2
fi

exit 0
