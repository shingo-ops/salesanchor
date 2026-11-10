# 設計: docs/handoff/guard-add-by-ai/design.md §13-14
"""PreToolUse(Bash) フック: 見張りを入れる共通の台本は、決まった1行の形でだけ通す。
前に環境変数や cd を付けた形・引数が名前1つでない形・ほかの命令をつないだ形・中を読む形は exit 2 で止める。
内部エラーは止めずに exit 0（fail-open）。標準ライブラリのみ。"""
import sys, os, re, json, datetime

ALLOW = re.compile(r'bash ~/\.salesanchor-tools/scripts/agent-hooks/install-guard\.sh [a-z0-9-]+')
NEEDLES = ('install-guard', '.salesanchor-tools/scripts/agent-hooks')
MSG = ('🚫 BLOCKED [install-form-guard]: 見張りを入れる共通の台本は、決まった1行の形でだけ流します'
       '（前に環境変数や cd を付けない・引数は名前1つ・ほかの命令をつながない）。'
       '形: bash ~/.salesanchor-tools/scripts/agent-hooks/install-guard.sh <名前>。'
       '中を読むだけなら Read ツールを使ってください（決まり: docs/handoff/guard-add-by-ai/design.md §13-14）。')


def log_path():
    return os.path.expanduser(os.environ.get('INSTALL_FORM_GUARD_LOG') or '~/.claude/logs/agent-events.jsonl')


def targeted(command):
    s = command.replace("'", '').replace('"', '').replace('\\', '').lower()
    return any(n in s for n in NEEDLES)


def log_event(kind, command, reason):
    try:
        rec = {
            'ts': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'type': kind,
            'hook': 'install-form-guard',
            'reason': reason,
            'cmd_head': str(command)[:120],
        }
        with open(log_path(), 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    except Exception:
        pass


def main():
    command = ''
    try:
        d = json.loads(sys.stdin.read())
        ti = d.get('tool_input') if isinstance(d, dict) else None
        command = ti.get('command') if isinstance(ti, dict) else None
        if not isinstance(command, str):
            return 0
        if not targeted(command):
            return 0
        if ALLOW.fullmatch(command):
            return 0
    except Exception as e:
        log_event('hook_internal_error', command, type(e).__name__)
        return 0
    log_event('hook_blocked', command, 'install form mismatch')
    sys.stderr.write(MSG + '\n')
    return 2


if __name__ == '__main__':
    try:
        rc = main()
    except Exception as e:
        log_event('hook_internal_error', '', type(e).__name__)
        rc = 0
    sys.exit(rc)
