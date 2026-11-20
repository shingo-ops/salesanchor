# 設計: docs/handoff/tenant-owner-login-approval/design.md 便7b・card-7b.md
"""PreToolUse フック: AI が PO（shingo-ops）の名前で GitHub に書く操作を止める。
Bash: PO の鍵を使う命令は、決まった Approve の形と読むだけの gh api だけ通す。
Write/Edit/MultiEdit: guard-files-gate.yml 以外の workflow に「guard-files gate」の名前を書く形を止める。
内部エラーは止める（exit 2）。標準ライブラリのみ。"""
import sys, os, re, json, shlex, stat, datetime

APPROVE_FLAG = "--appr" + "ove"
GO_RE = re.compile(r'\bGO\s*#\s*\d')
FORM_A = re.compile(
    r'GH_TOKEN="\$\(gh auth token --user shingo-ops\)" gh pr review [0-9]+ ' + re.escape(APPROVE_FLAG)
    + r" (?:--body '([^']*)'|--body-file ([A-Za-z0-9_./-]+))")
PREFIX_B = 'GH_TOKEN="$(gh auth token --user shingo-ops)" gh api '
USER_RE = re.compile(r'(?<![\w-])(-u|--user)(\s+|=)?["\']?shingo-ops\b')
TOKEN_FLAG_RE = re.compile(r'(^|\s)(--show-token|-t)(=|\s|$)')
WORKFLOW_NAME = 'guard-files gate'

MSG = ('🚫 BLOCKED [go-identity-guard]: PO（shingo-ops）の名前で書く操作は、決まった Approve の形と読むだけの gh api だけ通します。'
       'GO は PO 本人が書きます（設計: docs/handoff/tenant-owner-login-approval/design.md 便7b）。')
MSG_W = ('🚫 BLOCKED [go-identity-guard]: guard-files-gate.yml 以外の workflow に「guard-files gate」の名前は書けません'
         '（便7 の判定4・便7b）。')


def log_path():
    return os.path.expanduser(os.environ.get('GO_IDENTITY_GUARD_LOG') or '~/.claude/logs/agent-events.jsonl')


def log_event(kind, command, reason):
    try:
        rec = {
            'ts': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'type': kind,
            'hook': 'go-identity-guard',
            'reason': reason,
            'cmd_head': str(command)[:120],
        }
        with open(log_path(), 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    except Exception:
        pass


def norm(s):
    return re.sub(r'\s+', ' ', s.replace("'", '').replace('"', '')).lower()


def resolve(path, cwd):
    """相対なら cwd を基に解決。cwd が無ければ None。"""
    if os.path.isabs(path):
        return path
    if not isinstance(cwd, str) or not cwd:
        return None
    return os.path.join(cwd, path)


def read_regular(path, cwd):
    """決まり R: 普通のファイルだけ読む。読めなければ None。"""
    try:
        p = resolve(path, cwd)
        if p is None:
            return None
        if not stat.S_ISREG(os.stat(p).st_mode):
            return None
        with open(p, encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception:
        return None


def w_hit(tool, ti, cwd):
    """決まり W: 同じ名前の検査を別の workflow に書く形か。"""
    fp = ti.get('file_path')
    if not isinstance(fp, str):
        return False
    if not ('/.github/workflows/' in fp or fp.startswith('.github/workflows/')):
        return False
    if os.path.basename(fp) == 'guard-files-gate.yml':
        return False
    if tool == 'Write':
        c = ti.get('content')
        return isinstance(c, str) and WORKFLOW_NAME in norm(c)
    # Edit / MultiEdit: 当てた後の全文でも比べる（読めない・普通でないときは new_string だけ）
    if tool == 'Edit':
        edits = [(ti.get('old_string'), ti.get('new_string'), ti.get('replace_all') is True)]
    else:
        edits = [(e.get('old_string'), e.get('new_string'), e.get('replace_all') is True)
                 for e in (ti.get('edits') or []) if isinstance(e, dict)]
    news = [n for _, n, _ in edits if isinstance(n, str)]
    if any(WORKFLOW_NAME in norm(n) for n in news):
        return True
    full = None
    p = None
    try:
        p = resolve(fp, cwd) or fp
        if stat.S_ISREG(os.stat(p).st_mode):
            with open(p, encoding='utf-8', errors='replace') as f:
                full = f.read()
    except Exception:
        full = None
    if full is None:
        return False
    for old, new, rall in edits:
        if not isinstance(old, str) or not isinstance(new, str) or old == '':
            continue
        full = full.replace(old, new) if rall else full.replace(old, new, 1)
    return WORKFLOW_NAME in norm(full)


def scan_rest(rest):
    """残りを引用符を見て走査。部分のリストを返す。止める形なら None。"""
    parts, cur, i, n, q = [], [], 0, len(rest), None
    while i < n:
        c = rest[i]
        if q == "'":
            cur.append(c)
            if c == "'":
                q = None
            i += 1
            continue
        if q == '"':
            cur.append(c)
            if c == '\\' and i + 1 < n:
                cur.append(rest[i + 1])
                i += 2
                continue
            if c == '"':
                q = None
            i += 1
            continue
        if c == '\\':
            cur.append(rest[i:i + 2])
            i += 2
            continue
        if c in '\'"':
            q = c
            cur.append(c)
            i += 1
            continue
        if c in ';&<>':
            return None
        if c == '|':
            if rest[i + 1:i + 2] == '|':
                return None
            parts.append(''.join(cur))
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    if q is not None:
        return None
    parts.append(''.join(cur))
    return parts


def first_part_ok(words):
    paths = 0
    i = 0
    while i < len(words):
        w = words[i]
        if not w.startswith('-'):
            paths += 1
        elif w in ('--jq', '-q'):
            if i + 1 >= len(words):
                return False
            i += 1
        elif w in ('--paginate', '--slurp', '-i', '--include', '--silent'):
            pass
        elif w == '-X' or w == '--method':
            if i + 1 >= len(words) or words[i + 1] != 'GET':
                return False
            i += 1
        elif w in ('-XGET', '--method=GET'):
            pass
        else:
            return False
        i += 1
    return paths == 1


def form_b_ok(command):
    rest = command[len(PREFIX_B):]
    if '\n' in rest or '`' in rest or '$(' in rest:
        return False
    parts = scan_rest(rest)
    if parts is None:
        return False
    for idx, part in enumerate(parts):
        try:
            words = shlex.split(part, posix=True)
        except Exception:
            return False
        if idx == 0:
            if not first_part_ok(words):
                return False
        elif any('gh' in w or 'curl' in w for w in words):
            return False
    return True


def form_a_ok(command, cwd):
    m = FORM_A.fullmatch(command)
    if not m:
        return False
    body, bfile = m.group(1), m.group(2)
    if body is not None:
        return GO_RE.search(body) is None
    text = read_regular(bfile, cwd)
    return text is not None and GO_RE.search(text) is None


def bash_blocked(command, cwd):
    if re.search(r'gh\s+auth\s+switch', command):
        return True
    if re.search(r'gh\s+auth\s+status', command) and TOKEN_FLAG_RE.search(command):
        return True
    if 'find-generic-password' in command or '.config/gh/hosts.yml' in command:
        return True
    if not (re.search(r'gh\s+auth\s+token', command) or USER_RE.search(command)):
        return False
    if command.startswith(PREFIX_B):
        return not form_b_ok(command)
    return not form_a_ok(command, cwd)


def main():
    command = ''
    try:
        d = json.loads(sys.stdin.read())
        if not isinstance(d, dict):
            raise ValueError('not object')
        tool = d.get('tool_name')
        ti = d.get('tool_input')
        cwd = d.get('cwd')
        if tool == 'Bash':
            command = ti.get('command') if isinstance(ti, dict) else None
            if not isinstance(command, str):
                return 0
            if not bash_blocked(command, cwd):
                return 0
            msg, reason = MSG, 'PO name form mismatch'
        elif tool in ('Write', 'Edit', 'MultiEdit'):
            if not isinstance(ti, dict):
                return 0
            command = str(ti.get('file_path'))
            if not w_hit(tool, ti, cwd):
                return 0
            msg, reason = MSG_W, 'workflow name'
        else:
            return 0
    except Exception as e:
        log_event('hook_internal_error', command, type(e).__name__)
        sys.stderr.write(MSG + '\n')
        return 2
    log_event('hook_blocked', command, reason)
    sys.stderr.write(msg + '\n')
    return 2


if __name__ == '__main__':
    try:
        rc = main()
    except Exception as e:
        log_event('hook_internal_error', '', type(e).__name__)
        rc = 2
    sys.exit(rc)
