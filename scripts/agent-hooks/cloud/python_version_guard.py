# 元: ~/.claude/scripts/python-version-guard.py（クラウド用の写し。作業場所の判定を外した）
# 設計: docs/handoff/py312-guard/design.md（salesanchor リポジトリ）
"""PreToolUse(Bash) フック: Sales Anchor の作業場所で 3.12 以外の venv 作成・pip install を exit 2 で止める。
内部エラーは止めずに exit 0（fail-open）。標準ライブラリのみ。"""
import sys, os, re, json, shlex, datetime

LOG = os.path.expanduser(os.environ.get('PY312_GUARD_LOG') or '/tmp/agent-events.jsonl')
MSG = '本番は Python 3.12 です。python3.12 -m venv <場所>（または uv venv --python 3.12 <場所>）で作り、その venv の pip を使ってください（py312-guard）'
SKIP_HEADS = {'docker', 'ssh', 'git', 'grep', 'rg', 'cat', 'echo', 'printf'}
PREFIXES = {'sudo', 'env', 'time'}

HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1[^\n]*\n(.*?)(?:\n[ \t]*\2[ \t]*(?=\n|$)|\Z)", re.S)


def strip_heredoc_bodies(cmd):
    def rep(m):
        return m.group(0)[: m.group(0).index('\n')] + '\n'
    return HEREDOC.sub(rep, cmd)


def split_parts(cmd):
    """引用符の外の ; && || | 改行で分ける。"""
    parts, cur, i, n, q = [], [], 0, len(cmd), None
    while i < n:
        c = cmd[i]
        if q:
            cur.append(c)
            if c == '\\' and q == '"' and i + 1 < n:
                cur.append(cmd[i + 1]); i += 2; continue
            if c == q:
                q = None
            i += 1
            continue
        if c == '\\' and i + 1 < n:
            cur.append(cmd[i:i + 2]); i += 2; continue
        if c in '\'"':
            q = c; cur.append(c); i += 1; continue
        if c in ';\n|' or (c == '&' and cmd[i + 1:i + 2] == '&' and cmd[i - 1:i] != '>'):
            parts.append(''.join(cur)); cur = []
            i += 2 if cmd[i:i + 2] in ('&&', '||') else 1
            continue
        cur.append(c); i += 1
    parts.append(''.join(cur))
    return parts


def tokens(part):
    part = part.strip().lstrip('({').strip()
    try:
        t = shlex.split(part)
    except Exception:
        t = part.split()
    while t and (t[0] in PREFIXES or re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', t[0])):
        t = t[1:]
    return t


def venv_version(head):
    """<dir>/bin/xxx の <dir>/pyvenv.cfg の version。無い・読めない・形が違うなら None。"""
    try:
        d = os.path.dirname(os.path.dirname(head))
        with open(os.path.join(d, 'pyvenv.cfg'), encoding='utf-8') as f:
            for line in f:
                m = re.match(r'\s*version\s*=\s*(\S+)', line)
                if m:
                    return m.group(1)
    except Exception:
        pass
    return None


def has_seq(args, *seq):
    n = len(seq)
    return any(tuple(args[i:i + n]) == seq for i in range(len(args) - n + 1))


def bad_part(t):
    if not t:
        return False
    head, args = t[0], t[1:]
    base = os.path.basename(head)
    if base in SKIP_HEADS:
        return False
    m_py = re.match(r'^python(\d+(?:\.(\d+))?)?$', base)
    m_pip = re.match(r'^pip(\d+(?:\.(\d+))?)?$', base)
    if '/' in head and (m_py or m_pip):
        ver = venv_version(head)
        if ver is not None:  # venv の中の実行ファイル
            if ver.startswith('3.12'):
                return False
            if m_py:
                return has_seq(args, '-m', 'pip', 'install')
            return bool(args) and args[0] == 'install'
    if m_py:
        minor = m_py.group(2)
        mv = re.search(r'/Versions/3\.(\d+)/', head)
        if mv:
            minor = mv.group(1)
        if minor == '12':
            return False
        return has_seq(args, '-m', 'venv') or has_seq(args, '-m', 'pip', 'install')
    if m_pip:
        if m_pip.group(2) == '12':
            return False
        if '/' in head:  # pyvenv.cfg の無い場所は通す
            return False
        return bool(args) and args[0] == 'install'
    if base == 'virtualenv':
        return True
    if base == 'uv' and args and args[0] == 'venv':
        rest = args[1:]
        for i, a in enumerate(rest):
            if a.startswith('--python=') and rest[i][9:].startswith('3.12'):
                return False
            if a in ('--python', '-p') and i + 1 < len(rest) and rest[i + 1].startswith('3.12'):
                return False
        return True
    return False


def decide(command, cwd):
    """拒否文言か None。"""
    if not isinstance(command, str):
        return None
    for part in split_parts(strip_heredoc_bodies(command)):
        if bad_part(tokens(part)):
            return MSG
    return None


PATS = [
    re.compile(r"(?i)(token|secret|password|passwd|api_key|apikey)[A-Za-z_]*\s*[=:]\s*\S+"),
    re.compile(r"Bearer\s+\S+"),
    re.compile(r"https://discord(app)?\.com/api/webhooks/\S+"),
]


def mask(s):
    for p in PATS:
        s = p.sub('***', s)
    return s


def log_blocked(command, reason):
    try:
        rec = {
            'ts': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'type': 'hook_blocked',
            'hook': 'python-version-guard',
            'reason': mask(reason.split('\n')[0]),
            'cmd_head': mask(str(command))[:120],
        }
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    except Exception:
        pass


def main():
    try:
        d = json.loads(sys.stdin.read())
        ti = d.get('tool_input', {}) if isinstance(d, dict) else {}
        command = ti.get('command') or ''
        reason = decide(command, d.get('cwd'))
    except Exception:
        return 0
    if reason:
        log_blocked(command, reason)
        sys.stderr.write(reason + '\n')
        return 2
    return 0


if __name__ == '__main__':
    try:
        rc = main()
    except Exception:
        rc = 0
    sys.exit(rc)
