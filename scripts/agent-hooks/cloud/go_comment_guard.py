# 設計: docs/handoff/tenant-owner-login-approval/design.md 便7b・card-7b.md
"""PreToolUse フック（クラウド）: 担当が GitHub に GO の文字を書く操作を exit 2 で止める。
GitHub の MCP の道具・gh・GitHub API を使う Bash・guard-files gate の名前を別の workflow に書く Write/Edit を見る。
内部エラーは exit 1（dispatch.sh が止める側に扱う）。標準ライブラリのみ。"""
import sys, os, re, json, shlex, stat

GO_RE = re.compile(r'\bGO\s*#\s*\d')
WORKFLOW_NAME = 'guard-files gate'
MSG = 'BLOCKED(cloud): クラウドの担当は GitHub に GO を書きません。GO は PO（組A）か Opus（組B）が書きます（design.md 便7b）。'
MSG_DOLLAR = 'BLOCKED(cloud): 本文はファイルに書いて --body-file で渡してください（$( や ` を使う書き込みは止めます。design.md 便7b）。'
MSG_W = ('🚫 BLOCKED [go-identity-guard]: guard-files-gate.yml 以外の workflow に「guard-files gate」の名前は書けません'
         '（便7 の判定4・便7b）。')

FILE_MARKS = ('--body-file', '-F', '--field', '--input', '-T', '-d', '--data', '--data-binary')
SHORT_MARKS = ('-F', '-T', '-d')


class Block(Exception):
    pass


def norm(s):
    return re.sub(r'\s+', ' ', s.replace("'", '').replace('"', '')).lower()


def resolve(path, cwd):
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
    if tool == 'Edit':
        edits = [(ti.get('old_string'), ti.get('new_string'), ti.get('replace_all') is True)]
    else:
        edits = [(e.get('old_string'), e.get('new_string'), e.get('replace_all') is True)
                 for e in (ti.get('edits') or []) if isinstance(e, dict)]
    if any(isinstance(n, str) and WORKFLOW_NAME in norm(n) for _, n, _ in edits):
        return True
    full = None
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


def strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from strings(v)
    elif isinstance(o, (list, tuple)):
        for v in o:
            yield from strings(v)


def file_targets(tokens):
    """(読むファイル X のリスト)。文字の値は G だけ確かめるので、ここでは出さない。"""
    xs = []
    n = len(tokens)
    for i, t in enumerate(tokens):
        mark, val = None, None
        for m in FILE_MARKS:
            if t == m:
                mark = m
                val = tokens[i + 1] if i + 1 < n else None
                break
            if m.startswith('--') and t.startswith(m + '='):
                mark, val = m, t[len(m) + 1:]
                break
            if m in SHORT_MARKS and t.startswith(m) and len(t) > 2 and not t.startswith('--'):
                mark, val = m, t[2:]
                break
        if mark is None or val is None:
            continue
        if '@' in val:
            xs.append(val.split('@', 1)[1])
        elif mark in ('--body-file', '--input', '-T'):
            xs.append(val)
        elif mark in ('-F', '--field') and '=' not in val:
            xs.append(val)
    return xs


def method_nonget(tokens):
    for i, t in enumerate(tokens):
        if t in ('-X', '--method'):
            if i + 1 < len(tokens) and tokens[i + 1] != 'GET':
                return True
        elif t.startswith('--method='):
            if t[9:] != 'GET':
                return True
        elif t.startswith('-X') and len(t) > 2 and t != '-XGET':
            return True
    return False


def has_flag(tokens, flags, prefixed=()):
    for t in tokens:
        if t in flags or any(t.startswith(p) for p in prefixed):
            return True
    return False


def write_form(command, tokens):
    if re.search(r'\bgh\s+(pr|issue)\s+(comment|review|create|edit)\b', command):
        return True
    if re.search(r'\bgh\s+api\b', command):
        if has_flag(tokens, ('-f', '-F', '--field', '--raw-field', '--input'), ('-f', '-F', '--field=', '--raw-field=', '--input=')) \
                or method_nonget(tokens):
            return True
    if 'api.github.com' in command and re.search(r'\bcurl\b', command):
        if has_flag(tokens, ('-d', '--data', '--data-binary', '-T'), ('-d', '--data=', '--data-binary=', '-T')) \
                or method_nonget(tokens):
            return True
    return False


def bash_check(command, cwd):
    if not (re.search(r'(^|[\s;|&(])gh\s', command) or 'api.github.com' in command):
        return
    if GO_RE.search(command):
        raise Block(MSG)
    try:
        tokens = shlex.split(command, posix=True)
    except Exception:
        raise Block(MSG)
    for x in file_targets(tokens):
        if x == '-':
            raise Block(MSG)
        text = read_regular(x, cwd)
        if text is None or GO_RE.search(text):
            raise Block(MSG)
    if write_form(command, tokens) and ('$(' in command or '`' in command):
        raise Block(MSG_DOLLAR)


def main():
    d = json.loads(sys.stdin.read())
    if not isinstance(d, dict):
        raise ValueError('not object')
    tool = d.get('tool_name')
    ti = d.get('tool_input')
    cwd = d.get('cwd')
    try:
        if isinstance(tool, str) and tool.startswith('mcp__github__'):
            if any(GO_RE.search(s) for s in strings(ti)):
                raise Block(MSG)
        elif tool == 'Bash':
            command = ti.get('command') if isinstance(ti, dict) else None
            if isinstance(command, str):
                bash_check(command, cwd)
        elif tool in ('Write', 'Edit', 'MultiEdit'):
            if isinstance(ti, dict) and w_hit(tool, ti, cwd):
                raise Block(MSG_W)
    except Block as b:
        sys.stderr.write(str(b) + '\n')
        return 2
    return 0


if __name__ == '__main__':
    try:
        rc = main()
    except Exception:
        sys.stderr.write('go_comment_guard: 内部エラー\n')
        rc = 1
    sys.exit(rc)
