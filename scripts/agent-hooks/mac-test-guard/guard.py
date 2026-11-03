# 設計: docs/handoff/mac-test-guard/design.md §3〜§6
"""PreToolUse(Bash) フック: Mac で重い試験（npm test・vitest・playwright test・pytest など）を
打つ命令を exit 2 で止める。例外は許可券 op "mac test"（1回限り）。
内部エラーは止めずに exit 0（fail-open）。標準ライブラリのみ。"""
import sys, os, re, json, shlex, glob, datetime

MSG = ('🚫 BLOCKED [mac-test-guard]: この Mac では重い試験を回しません（8コア・8GB で時間切れが毎回出るため。PO 決定 2026-11-02）。'
       '試験は GitHub の確かめ（PR を push すると自動で回る）か、クラウドの担当に頼んでください'
       '（決まり: docs/handoff/mac-test-guard/design.md）。Mac でしか試せない場合は PO に許可券 "mac test" を依頼してください。')
PREFIXES = {'sudo', 'env', 'time', 'nohup'}
PREFIX_VALUE_FLAGS = {'sudo': {'-u', '-g', '-h', '-p', '-C', '-D', '-U', '-r', '-t'}, 'env': {'-u', '-C'},
                      'time': {'-f', '-o'}}
UV_VALUE_FLAGS = {'--with', '--project', '--directory', '--python', '-p', '--package', '--extra', '--group',
                  '--env-file', '--with-requirements', '--with-editable', '--index'}
TIMEOUT_VALUE_FLAGS = {'-s', '--signal', '-k', '--kill-after'}
DOCKER_VALUE_FLAGS = {'-e', '--env', '-u', '--user', '-w', '--workdir', '-v', '--volume', '--name',
                      '--entrypoint', '-p', '--publish', '-l', '--label', '--index'}
SHELLS = {'bash', 'sh', 'zsh'}
PERMIT_OP = 'mac test'
NPM_VALUE_FLAGS = {'--prefix', '-C', '-w', '--workspace', '--filter', '-F', '--dir', '--cwd'}

HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1[^\n]*\n(.*?)(?:\n[ \t]*\2[ \t]*(?=\n|$)|\Z)", re.S)


def log_path():
    return os.path.expanduser(os.environ.get('MAC_TEST_GUARD_LOG') or '~/.claude/logs/agent-events.jsonl')


def permits_dir():
    return os.path.expanduser('~/.claude/permits')


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


def skip_timeout(t):
    """timeout の旗（-s/--signal/-k/--kill-after は値も）と時間の1語を飛ばす。"""
    i = 0
    while i < len(t) and t[i].startswith('-'):
        i += 2 if t[i] in TIMEOUT_VALUE_FLAGS else 1
    return t[i + 1:]


def skip_nice(t):
    """nice の -n 値・-数・--adjustment=x を飛ばす。"""
    i = 0
    while i < len(t):
        if t[i] == '-n':
            i += 2
        elif t[i].startswith('-') and (t[i][1:].isdigit() or t[i].startswith('--adjustment=')):
            i += 1
        else:
            break
    return t[i:]


def tokens(part):
    """(環境変数の dict, 先頭語以降の語のリスト)。sudo/env/time と VAR= は飛ばす。"""
    part = part.strip().lstrip('({').strip()
    try:
        t = shlex.split(part)
    except Exception:
        t = part.split()
    env = {}
    while t:
        w = t[0]
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', w)
        if m:
            env[m.group(1)] = m.group(2)
            t = t[1:]
        elif w in PREFIXES:
            t = t[1:]
            if w != 'nohup':
                while t and t[0].startswith('-'):
                    t = t[2:] if t[0] in PREFIX_VALUE_FLAGS.get(w, ()) else t[1:]
        elif w == 'timeout':
            t = skip_timeout(t[1:])
        elif w == 'nice':
            t = skip_nice(t[1:])
        else:
            break
    return env, t


REDIRECT = re.compile(r'^(\d+|&)?(>>?|>\||<<<|<>|<|>&|<&)(.*)$')


def drop_redirections(args):
    """リダイレクト（2>&1・>file・&> など。後ろが空なら次の1語＝リダイレクト先も）、単独の &、
    語末の ) } を取り除く。設計: design.md §11-3-2"""
    out, skip = [], False
    for w in args:
        if skip:
            skip = False
            continue
        w = w.rstrip(')}')
        if not w or w == '&':
            continue
        m = REDIRECT.match(w)
        if m:
            if m.group(3) == '':
                skip = True
            continue
        out.append(w)
    return out


def skip_flags(args):
    """先頭の旗（- で始まる語。NPM_VALUE_FLAGS は次の1語も）を飛ばした残りを返す。"""
    i, n = 0, len(args)
    while i < n and args[i].startswith('-'):
        i += 2 if args[i] in NPM_VALUE_FLAGS else 1
    return args[i:]


def skip_uv_flags(args):
    """uv の旗（UV_VALUE_FLAGS は次の1語も）を飛ばした残りを返す。"""
    i, n = 0, len(args)
    while i < n and args[i].startswith('-'):
        i += 2 if args[i] in UV_VALUE_FLAGS else 1
    return args[i:]


def is_npx_test(args):
    """npx 形: 旗を飛ばした次の語が vitest、または playwright の次が test。"""
    rest = skip_flags(args)
    if not rest:
        return False
    if rest[0] == 'vitest':
        return True
    return rest[0] == 'playwright' and rest[1:2] == ['test']


def is_npm_test(args):
    """npm 形: test/t/tst、または run/run-script の次が test で始まり :install で終わらない。"""
    rest = skip_flags(args)
    if not rest:
        return False
    if rest[0] in ('exec', 'x'):
        return is_npx_test(rest[1:])
    if rest[0] in ('test', 't', 'tst'):
        return True
    if rest[0] in ('run', 'run-script'):
        nxt = skip_flags(rest[1:])
        return bool(nxt) and nxt[0].startswith('test') and not nxt[0].endswith(':install')
    return False


def is_pytest_module(args):
    return any(a == '-m' and i + 1 < len(args) and args[i + 1] == 'pytest' for i, a in enumerate(args))


PYTHON = re.compile(r'^python[0-9.]*$')


def heavy(base, args, allow_docker=True):
    """試験を回す形なら True（design.md §3 の表）。"""
    if base == 'npm':
        return is_npm_test(args)
    if base == 'npx':
        return is_npx_test(args)
    if base == 'pnpm':
        rest = skip_flags(args)
        if rest and rest[0] in ('exec', 'dlx'):
            return is_npx_test(rest[1:])
        return is_npm_test(args) or is_npx_test(args)
    if base == 'yarn':
        return is_npx_test(args) or is_npm_test(args)
    if base == 'vitest':
        return True
    if base == 'playwright':
        return args[:1] == ['test']
    if base in ('pytest', 'py.test'):
        return True
    if PYTHON.match(base):
        return is_pytest_module(args)
    if base == 'uv':
        rest = skip_flags(args)
        if not rest or rest[0] != 'run':
            return False
        rest = skip_uv_flags(rest[1:])
        if not rest:
            return False
        b = os.path.basename(rest[0])
        return b in ('pytest', 'py.test') or (bool(PYTHON.match(b)) and is_pytest_module(rest[1:]))
    if base in ('docker', 'docker-compose') and allow_docker:
        if base == 'docker' and 'compose' not in args:
            return False
        idx = [i for i, a in enumerate(args) if a in ('exec', 'run')]
        if not idx:
            return False
        sub, i = args[idx[0] + 1:], 0
        while i < len(sub) and sub[i].startswith('-'):
            i += 2 if sub[i] in DOCKER_VALUE_FLAGS else 1
        sub = sub[i + 1:]
        return bool(sub) and heavy(os.path.basename(sub[0]), sub[1:], False)
    return False


def bad_part(env, t, depth, part=''):
    """止める部分の文字列を返す。止めないなら None。"""
    if not t:
        return None
    base = os.path.basename(t[0])
    args = drop_redirections(t[1:])
    ci = next((k for k, a in enumerate(args) if a == '-c' or re.fullmatch(r'-[A-Za-z]*c[A-Za-z]*', a)), None) \
        if base in SHELLS and depth < 1 else None
    if ci is not None:
        i = ci
        if i + 1 < len(args):
            return bad_command(args[i + 1], depth + 1)
        return None
    return part.strip() if heavy(base, args) else None


def bad_command(command, depth=0):
    """止める部分の文字列を返す。止めないなら None。"""
    for part in split_parts(strip_heredoc_bodies(command)):
        env, t = tokens(part)
        r = bad_part(env, t, depth, part)
        if r:
            return r
    return None


def log_event(kind, command, reason, part=None):
    try:
        rec = {
            'ts': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'type': kind,
            'hook': 'mac-test-guard',
            'reason': reason,
            'cmd_head': str(command)[:120],
        }
        if part is not None:
            rec['matched_part'] = str(part)[:300]
        with open(log_path(), 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    except Exception:
        pass


def consume_permit():
    """op "mac test"・created_by manual・期限内の券を1つ削除して True。無ければ False。"""
    now = datetime.datetime.now(datetime.timezone.utc)
    for p in sorted(glob.glob(os.path.join(permits_dir(), 'danger-permit-*.json'))):
        try:
            with open(p, encoding='utf-8') as f:
                d = json.load(f)
            if d.get('op') != PERMIT_OP or d.get('created_by') != 'manual':
                continue
            exp = datetime.datetime.strptime(d.get('expires_at', ''), '%Y-%m-%dT%H:%M:%SZ').replace(
                tzinfo=datetime.timezone.utc)
            if exp <= now:
                continue
            os.remove(p)
            return True
        except Exception:
            continue
    return False


def main():
    command = ''
    try:
        d = json.loads(sys.stdin.read())
        ti = d.get('tool_input', {}) if isinstance(d, dict) else {}
        command = ti.get('command') or ''
        matched = bad_command(command) if isinstance(command, str) else None
        if not matched:
            return 0
        if consume_permit():
            log_event('hook_permit_consumed', command, 'mac test permit consumed', matched)
            return 0
    except Exception as e:
        log_event('hook_internal_error', command, type(e).__name__)
        return 0
    log_event('hook_blocked', command, MSG.split('\n')[0][:80], matched)
    sys.stderr.write(MSG + '\n')
    return 2


if __name__ == '__main__':
    try:
        rc = main()
    except Exception as e:
        log_event('hook_internal_error', '', type(e).__name__)
        rc = 0
    sys.exit(rc)
