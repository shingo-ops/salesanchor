# 設計: docs/handoff/tenant-owner-login-approval/design.md 便7b・card-7b.md
"""guard.py の試験。使い方: python3 test_guard.py [guard.py のパス]。標準ライブラリのみ。"""
import sys, os, json, subprocess, tempfile, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'guard.py')
MANIFEST = os.path.join(HERE, 'guard-manifest.json')
AUDIT = os.path.normpath(os.path.join(HERE, '..', '..', 'dev', 'consent-audit.py'))

tmp = tempfile.mkdtemp(prefix='gig-')
LOG = os.path.join(tmp, 'events.jsonl')
ENV = dict(os.environ, GO_IDENTITY_GUARD_LOG=LOG)
total = ok = 0

TOK = 'GH_TOKEN="$(gh auth token --user shingo-ops)"'
L3 = TOK + " gh pr review 12 --approve --body 'POの恒久委任に基づく Claude Opus の判断。CI 緑・審査 APPROVE・HEAD abc1234'"
L6 = TOK + ' gh pr review 12 --approve --body-file %s'
GOTXT = 'GO #12 abc1234'


def run(tool, ti, raw=None):
    inp = raw if raw is not None else json.dumps({'tool_name': tool, 'tool_input': ti, 'cwd': tmp})
    p = subprocess.run([sys.executable, GUARD], input=inp, capture_output=True, text=True, env=ENV)
    return p.returncode, p.stderr


def bash(cmd):
    return run('Bash', {'command': cmd})


def check(label, cond):
    global total, ok
    total += 1
    if cond:
        ok += 1
    else:
        print('FAIL:', label)


def put(name, text):
    p = os.path.join(tmp, name)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(text)
    return p


def passes(label, cmd):
    rc, err = bash(cmd)
    check(label + ' 通す', rc == 0 and err == '')


def stops(label, cmd):
    rc, err = bash(cmd)
    check(label + ' 止める', rc == 2 and '[go-identity-guard]' in err)


ok_file = put('ok.txt', 'CI 緑 HEAD abc1234')
go_file = put('go.txt', GOTXT)
put('b.md', 'CI 緑')
put('b2.md', GOTXT)

# 通すもの
passes('L1', 'gh pr view 1')
passes('L2', 'gh api repos/shingo-ops/salesanchor/pulls/1')
passes('L3', L3)
passes('L4', TOK + ' gh api repos/shingo-ops/salesanchor/rulesets/15777895')
passes('L5', TOK + ' gh api repos/x/y/pulls/1 --jq .state | head -1')
passes('L6', L6 % ok_file)
rc, err = run('Write', {'file_path': '/tmp/repo/scripts/tests/x.js', 'content': GOTXT})
check('L7 通す', rc == 0 and err == '')
rc, err = run('Write', {'file_path': '/tmp/repo/.github/workflows/guard-files-gate.yml', 'content': 'name: guard-files gate'})
check('L8 通す', rc == 0 and err == '')
passes('L9', 'gh pr comment 5 --body "GO #5 abcdef1"')
passes('L31', TOK + " gh api -X GET repos/x/y/pulls --paginate -q '.[].number'")
passes('L32', TOK + ' gh api --method=GET repos/x/y/rulesets/1 --jq .rules')
passes('L45', L6 % 'b.md')

# L49 札と語
try:
    spec = importlib.util.spec_from_file_location('consent_audit', AUDIT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mtext = open(MANIFEST, encoding='utf-8').read()
    gtext = open(GUARD, encoding='utf-8').read()
    check('L49 札', mod._ga_manifest(mtext, 'go-identity-guard') is not None)
    check('L49 語', mod._ga_words_ok(gtext) is True)
except Exception as e:
    check('L49 読み込み失敗: ' + type(e).__name__ + ' ' + str(e), False)

# 止めるもの
stops('L10', 'gh auth switch --user shingo-ops')
stops('L11', 'gh auth switch')
stops('L12', 'gh auth token --user shingo-ops')
stops('L13', 'gh auth token -u shingo-ops')
stops('L14', TOK + ' gh pr comment 12 --body "GO #12 abc1234"')
stops('L15', TOK + " gh pr review 12 --approve --body 'POの恒久委任 GO #12 abc1234'")
stops('L16', L6 % go_file)
stops('L17', L6 % os.path.join(tmp, 'missing.txt'))
stops('L18', TOK + ' gh api -X POST repos/x/y/issues/1/comments -f body=hi')
stops('L19', TOK + ' gh api repos/x/y/issues/1/comments --method PATCH')
stops('L20', TOK + ' gh api repos/x/y/issues/1/comments -F body=@f')
stops('L21', L3 + '; gh pr merge 12')
stops('L22', 'T=$(gh auth token --user shingo-ops); curl -H "Authorization: token $T" https://api.github.com/x')
stops('L23', 'gh auth status --show-token')
stops('L24', 'security find-generic-password -s gh:github.com -w')
stops('L25', 'cat ~/.config/gh/hosts.yml')
rc, err = run('Write', {'file_path': '.github/workflows/x.yml', 'content': 'name: "Guard-Files   Gate"'})
check('L26 止める', rc == 2 and '[go-identity-guard]' in err and '便7 の判定4' in err)
rc, err = run('Edit', {'file_path': '.github/workflows/test.yml', 'old_string': 'a', 'new_string': 'name: guard-files gate'})
check('L27 止める', rc == 2 and '[go-identity-guard]' in err)
rc, err = run('Bash', None, raw='not json')
check('L28 止める', rc == 2)
stops('L29', TOK + ' gh api repos/x/y | gh pr comment 1 --body-file -')
stops('L30', TOK + ' gh pr review 12 --approve --body "ok $(gh pr comment 12 --body hi)"')
stops('L33', TOK + ' gh api repos/x/y/issues/1/comments -fbody=hi')
stops('L34', TOK + ' gh api -XPOST repos/x/y/issues/1/comments')
stops('L35', TOK + ' gh api --method=POST repos/x/y/issues/1/comments')
stops('L36', TOK + ' gh api repos/x/y/pulls/1 > /tmp/o.json')
stops('L37', 'gh auth status -t')
stops('L38', 'gh auth token --user=shingo-ops')
stops('L39', L3 + ' && gh pr merge 12')
stops('L40', L3 + ' | cat')
stops('L41', L3 + ' `id`')
stops('L42', 'gh auth token -ushingo-ops')
stops('L43', 'GH_TOKEN="$(gh auth token)" gh pr comment 1 --body hi')
stops('L44', TOK + ' gh api repos/x/y --jq "|" -X POST -f body=x')
stops('L46', L6 % 'b2.md')
stops('L47', L6 % '/dev/stdin')
os.makedirs(os.path.join(tmp, '.github', 'workflows'), exist_ok=True)
zp = put(os.path.join('.github', 'workflows', 'z.yml'), 'name: guard-files check\n')
rc, err = run('Edit', {'file_path': zp, 'old_string': 'check', 'new_string': 'gate'})
check('L48 止める', rc == 2 and '[go-identity-guard]' in err)
stops('L50', 'GH_TOKEN=$(gh auth token) gh run view 1 --log')

# 記録
n0 = len(open(LOG, encoding='utf-8').read().splitlines()) if os.path.exists(LOG) else 0
bash('gh auth switch')
lines = open(LOG, encoding='utf-8').read().splitlines()
rec = json.loads(lines[-1]) if lines else {}
check('記録が1行増える', len(lines) == n0 + 1 and rec.get('hook') == 'go-identity-guard' and rec.get('type') == 'hook_blocked')

print('OK %d/%d' % (ok, total))
sys.exit(0 if ok == total else 1)
