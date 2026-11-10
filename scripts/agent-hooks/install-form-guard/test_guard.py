# 設計: docs/handoff/guard-add-by-ai/design.md §13-14
"""guard.py の試験。使い方: python3 test_guard.py [guard.py のパス]。標準ライブラリのみ。"""
import sys, os, json, subprocess, tempfile, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'guard.py')
MANIFEST = os.path.join(HERE, 'guard-manifest.json')
AUDIT = os.path.normpath(os.path.join(HERE, '..', '..', 'dev', 'consent-audit.py'))

S = 'bash ~/.salesanchor-tools/scripts/agent-hooks/install-guard.sh'

F1 = [S + ' mac-test-guard', S + ' install-form-guard', S + ' a-1']
F2 = [
    'CLAUDE_DIR=/Users/x/.claude ' + S + ' mac-test-guard',
    'PATH=/usr/bin:/bin ' + S + ' mac-test-guard',
    'HOME=/tmp/h ' + S + ' x',
    'env ' + S + ' x',
    'cd /tmp && ' + S + ' x',
    ' ' + S + ' x',
    'command ' + S + ' x',
    'sh ~/.salesanchor-tools/scripts/agent-hooks/install-guard.sh x',
    'bash $HOME/.salesanchor-tools/scripts/agent-hooks/install-guard.sh x',
    'bash /Users/x/.salesanchor-tools/scripts/agent-hooks/install-guard.sh x',
]
F3 = [
    S, S + ' ', S + ' a b', S + ' x\n', S + ' x; ls', S + ' x && ls', S + ' x | cat',
    S + ' x > /tmp/o', S + ' x 2>&1', S + ' $(echo x)', S + ' `echo x`', S + ' X', S + ' x_y', S + ' x &',
]
F4 = [
    'bash ~/.salesanchor-tools/scripts/agent-hooks/mac-test-guard/install.sh',
    'bash ~/.salesanchor-tools/scripts/agent-hooks/mac-test-guard/rollback.sh',
    'cat ~/.salesanchor-tools/scripts/agent-hooks/install-guard.sh',
    'git show origin/main:scripts/agent-hooks/install-guard.sh',
    'grep -n x scripts/agent-hooks/install-guard.sh',
    "bash ~/.salesanchor-tools/scripts/agent-hooks/install-gu''ard.sh x",
    'bash ~/.salesanchor-tools/scripts/agent-hooks/install-gu\\ard.sh x',
    'BASH ~/.salesanchor-tools/scripts/agent-hooks/install-guard.sh x',
    'bash ~/.SALESANCHOR-TOOLS/scripts/agent-hooks/x.sh',
]
F5 = [
    'git status', 'ls', 'python3 scripts/agent-hooks/test_install_guard.py',
    'python3 scripts/agent-hooks/install-form-guard/test_guard.py',
    'cd ~/.salesanchor-tools && python3 -I -B scripts/dev/perm-change.py sync',
    'git diff -- scripts/agent-hooks/mac-test-guard/', 'echo installguard',
]

tmp = tempfile.mkdtemp(prefix='ifg-')
LOG = os.path.join(tmp, 'events.jsonl')
ENV = dict(os.environ, INSTALL_FORM_GUARD_LOG=LOG)
total = ok = 0


def run(cmd, raw=None):
    inp = raw if raw is not None else json.dumps({'tool_name': 'Bash', 'tool_input': {'command': cmd}})
    p = subprocess.run([sys.executable, GUARD], input=inp, capture_output=True, text=True, env=ENV)
    return p.returncode, p.stderr


def check(label, cond):
    global total, ok
    total += 1
    if cond:
        ok += 1
    else:
        print('FAIL:', label)


def nlines():
    return len(open(LOG, encoding='utf-8').read().splitlines()) if os.path.exists(LOG) else 0


for c in F1:
    rc, err = run(c)
    check('F1 通す: ' + repr(c), rc == 0 and err == '')
for c in F2:
    rc, err = run(c)
    check('F2 止める: ' + repr(c), rc == 2 and '[install-form-guard]' in err)
for c in F3:
    check('F3 止める: ' + repr(c), run(c)[0] == 2)
for c in F4:
    check('F4 止める: ' + repr(c), run(c)[0] == 2)
for c in F5:
    rc, err = run(c)
    check('F5 止めない: ' + repr(c), rc == 0 and err == '')

# F6 記録
before = nlines()
run(F2[0])
last = open(LOG, encoding='utf-8').read().splitlines()[-1] if nlines() else '{}'
rec = json.loads(last)
check('F6 記録が1行増える', nlines() == before + 1 and rec.get('hook') == 'install-form-guard'
      and rec.get('type') == 'hook_blocked')

# F7 記録しない
before = nlines()
run(F1[0])
run(F5[0])
check('F7 記録しない', nlines() == before)

# F8 壊れた入力
for raw in ['not json', '{"tool_input": {"command": 5}}', '{"tool_input": "x"}', '[]']:
    check('F8 壊れた入力: ' + repr(raw), run('', raw=raw)[0] == 0)

# F9 札と語
try:
    spec = importlib.util.spec_from_file_location('consent_audit', AUDIT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mtext = open(MANIFEST, encoding='utf-8').read()
    gtext = open(GUARD, encoding='utf-8').read()
    check('F9 札', mod._ga_manifest(mtext, 'install-form-guard') is not None)
    check('F9 語', mod._ga_words_ok(gtext) is True)
except Exception as e:
    check('F9 読み込み失敗: ' + type(e).__name__ + ' ' + str(e), False)

print('OK %d/%d' % (ok, total))
sys.exit(0 if ok == total else 1)
