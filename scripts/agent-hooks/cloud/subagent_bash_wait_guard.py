# 元: ~/.claude/scripts/subagent-bash-wait-guard.py（クラウド用の写し）
# 設計: ~/.claude/token-reports/2026-10-20-subagent-bash-wait-guard-design.md §3
"""PreToolUse(Bash) フック: 担当（サブエージェント）の Bash で timeout が 240000ms を超えるものを exit 2 で止める。
親会話・timeout なし・240000以下・他ツール・不正JSON・内部エラーは exit 0（fail-open）。標準ライブラリのみ。"""
import sys, os, json, datetime

LIMIT_MS = 240000
MSG = ('🚫 BLOCKED [subagent-bash-wait-guard]: 担当（サブエージェント）の Bash は1回4分（timeout 240000）以内にしてください。'
       '5分を超えて止まると会話を全部書き直す費用がかかります。'
       '対処: 待機ループは `[ $SECONDS -lt 230 ]` 等で4分以内に自分で終わらせ、未完了なら次の Bash でもう一度確認する。'
       '長いテストは対象を分けて実行する。'
       'これは費用のための区切りで、区切って実行し直すのは許可された対処です（言い換えによる迂回には当たりません）。'
       'CIやデプロイの完了待ちは担当ではなく親（設計者）が行います。')


def log_path():
    return os.path.expanduser(os.environ.get('SUBAGENT_BASH_WAIT_GUARD_LOG') or '/tmp/agent-events.jsonl')


def log_event(timeout, agent_type):
    try:
        rec = {
            'type': 'hook_blocked',
            'hook': 'subagent-bash-wait-guard',
            'timeout': timeout,
            'agent_type': agent_type,
            'ts': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        with open(log_path(), 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    except Exception:
        pass


def main():
    try:
        d = json.loads(sys.stdin.read())
        if not isinstance(d, dict) or 'agent_id' not in d or d.get('tool_name') != 'Bash':
            return 0
        ti = d.get('tool_input')
        if not isinstance(ti, dict):
            return 0
        t = ti.get('timeout')
        if isinstance(t, bool) or not isinstance(t, (int, float)) or t <= LIMIT_MS:
            return 0
        timeout, agent_type = t, d.get('agent_type')
    except Exception:
        return 0
    log_event(timeout, agent_type)
    sys.stderr.write(MSG + '\n')
    return 2


if __name__ == '__main__':
    try:
        rc = main()
    except Exception:
        rc = 0
    sys.exit(rc)
