#!/bin/bash
# Blocks direct develop/main commits, protected-branch force pushes, and old-clone push/fetch.
# Candidate 2026-09-11: resolve tool workdir and literal cd without eval.
# Based on live SHA256 f6238554fe17f73b2c0e5430f4a3c209ba04593dc3cff0bc9f3f40feda89d10f.
# Does not replace or modify the separate CW01/CW05 guard.
INPUT=$(cat 2>/dev/null || true)

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
TOOL_NAME=$(printf '%s' "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)
# 会話記録・同意の台帳への書き込みを禁止（ADR-1033 §4-5）。Write の判定は exit 0 で終わるので、その前に置く。
# Write・Edit・MultiEdit・NotebookEdit の file_path と notebook_path の両方を、小文字の realpath で見る。
case "$TOOL_NAME" in
  Write|Edit|MultiEdit|NotebookEdit)
    CONSENT_PATH_BLOCKED=$(printf '%s' "$INPUT" | python3 -c '
import sys, os, json, pwd
try:
    ti = json.load(sys.stdin).get("tool_input", {})
    home = pwd.getpwuid(os.getuid()).pw_dir
    proj = os.path.realpath(os.path.join(home, ".claude", "projects")).lower() + "/"
    ledger = os.path.realpath(os.path.join(home, ".claude", "logs", "consent-used.jsonl")).lower()
    for k in ("file_path", "notebook_path"):
        p = ti.get(k)
        if not isinstance(p, str) or not p:
            continue
        n = os.path.realpath(os.path.expanduser(p)).lower()
        if (n.startswith(proj) and n.endswith(".jsonl")) or n == ledger:
            print("yes")
            break
except Exception:
    pass
' 2>/dev/null)
    if [ "$CONSENT_PATH_BLOCKED" = "yes" ]; then
      printf '{"type":"consent_guard_blocked","hook":"worktree-only-guard","condition":"transcript-or-ledger-write","tool":"%s","ts":"%s"}\n' "$TOOL_NAME" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$HOME/.claude/logs/agent-events.jsonl" 2>/dev/null || true
      echo 'BLOCKED: 会話記録・同意の台帳は書き込めません。(worktree-only-guard, ADR-1033)' >&2
      exit 2
    fi
    ;;
esac
# Write ツール: ~/.claude/permits/ への書き込みを禁止（PR-P1 2026-08-30）
if [ "$TOOL_NAME" = "Write" ]; then
  FILE_PATH=$(printf '%s' "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null || true)
  if [ -n "$FILE_PATH" ]; then
    BLOCKED=$(python3 - "$FILE_PATH" <<'PYEOF'
import sys, os
try:
    path = sys.argv[1]
    normalized = os.path.realpath(os.path.expanduser(path))
    permits = os.path.realpath(os.path.expanduser('~/.claude/permits'))
    if normalized == permits or normalized.startswith(permits + '/'):
        print('yes')
except:
    pass
PYEOF
    )
    if [ "$BLOCKED" = "yes" ]; then
      _hook_blocked_log "worktree-only-guard" "BLOCKED: ~/.claude/permits/ への書き込みは禁止されています。"
      echo 'BLOCKED: ~/.claude/permits/ への書き込みは禁止されています。(worktree-only-guard)' >&2
      exit 2
    fi
  fi
  exit 0
fi
[ "$TOOL_NAME" = "Bash" ] || exit 0
COMMAND=$(printf '%s' "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)
ROOT=$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null || true)
TARGET_DIR=$(printf '%s' "$INPUT" | python3 -c '
import json, os, re, shlex, sys
try:
    payload = json.load(sys.stdin)
    tool = payload.get("tool_input", {})
    base = tool.get("workdir", payload.get("cwd", os.getcwd()))
    if not isinstance(base, str) or not os.path.isabs(base) or not os.path.isdir(base):
        raise ValueError("invalid working directory")
    command = tool.get("command", "")
    if not isinstance(command, str):
        raise ValueError("invalid command")
    # Resolve only a literal leading cd. Do not evaluate shell source.
    if re.match(r"^\s*cd(?:\s|$)", command):
        match = re.match(r"^\s*cd[ \t]+(?:--[ \t]+)?(\"[^\"$`\n]*\"|'"'"'[^'"'"'\n]*'"'"'|[^\s;&|<>()$`\\]+)[ \t]*(?:&&|;|\n|$)", command)
        if not match:
            raise ValueError("unsupported directory expression")
        raw = match.group(1)
        path = shlex.split(raw)[0]
        if not raw.startswith(("'"'"'", '"'"'"'"'"')):
            path = os.path.expanduser(path)
        base = os.path.join(base, path)
    base = os.path.realpath(base)
    if not os.path.isdir(base) or "\n" in base or "\r" in base:
        raise ValueError("unavailable working directory")
    print(base)
except (ValueError, TypeError, AttributeError, OSError, IndexError):
    sys.exit(2)
' 2>/dev/null) || TARGET_DIR=""
# 設計承認チケット 段2: cd の行き先を判定できないとき（例: cd "$X" && ...）は、
# git commit / git push を含むコマンドだけ止める。それ以外は通して cwd_unresolved を記録する。
if [ -z "$TARGET_DIR" ]; then
  if echo "$COMMAND" | grep -qE '(^|[^[:alnum:]_])git[[:space:]]+(.*[[:space:]])?(commit|push)([[:space:]]|$)'; then
    _hook_blocked_log "worktree-only-guard" "BLOCKED: working directory could not be resolved safely."
    echo 'BLOCKED: working directory could not be resolved safely.' >&2
    exit 2
  fi
  printf '{"type":"cwd_unresolved","hook":"worktree-only-guard","ts":"%s"}\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$HOME/.claude/logs/agent-events.jsonl" 2>/dev/null || true
  exit 0
fi
TARGET_ROOT=$(git -C "$TARGET_DIR" rev-parse --show-toplevel 2>/dev/null || true)
BRANCH=$(git -C "$TARGET_DIR" branch --show-current 2>/dev/null || true)
if [[ -z "$BRANCH" ]] && echo "$COMMAND" | grep -qE 'git commit'; then
  _hook_blocked_log "worktree-only-guard" "BLOCKED: target branch could not be verified."
  echo 'BLOCKED: target branch could not be verified.' >&2; exit 2
fi
if [[ "$ROOT" == "/Users/tanizawashingo/crm-app-new" || "$ROOT" == /private/tmp/* || "$TARGET_ROOT" == "/Users/tanizawashingo/crm-app-new" || "$TARGET_ROOT" == /private/tmp/* ]] && echo "$COMMAND" | grep -qE 'git (push|fetch)'; then
  _hook_blocked_log "worktree-only-guard" "BLOCKED: old clone push/fetch is prohibited."
  echo 'BLOCKED: old clone push/fetch is prohibited.' >&2; exit 2
fi
if [[ "$BRANCH" == "develop" || "$BRANCH" == "main" ]] && echo "$COMMAND" | grep -qE 'git commit'; then
  _hook_blocked_log "worktree-only-guard" "BLOCKED: protected target branch ($BRANCH)."
  printf 'BLOCKED: protected target branch (%s). Target directory: %s\n' "$BRANCH" "$TARGET_DIR" >&2; exit 2
fi
if echo "$COMMAND" | grep -qE 'git push.*(--force|--force-with-lease).*(origin )?(develop|main)'; then
  _hook_blocked_log "worktree-only-guard" "BLOCKED: force push to origin develop/main is prohibited."
  echo 'BLOCKED: force push to origin develop/main is prohibited.' >&2; exit 2
fi
exit 0
