# 設計: docs/handoff/tenant-owner-login-approval/design.md 便7b・card-7b.md
"""go_comment_guard.py の試験。使い方: python3 test_go_comment_guard.py [go_comment_guard.py のパス]。標準ライブラリのみ。"""
import sys, os, json, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'go_comment_guard.py')
DISPATCH = os.path.join(HERE, 'dispatch.sh')
tmp = tempfile.mkdtemp(prefix='gcg-')
total = ok = 0
GOTXT = 'GO #1 abcdef1'


def check(label, cond):
    global total, ok
    total += 1
    if cond:
        ok += 1
    else:
        print('FAIL:', label)


def payload(tool, ti):
    return json.dumps({'hook_event_name': 'PreToolUse', 'tool_name': tool, 'tool_input': ti, 'cwd': tmp})


def run(tool, ti, via_dispatch=False, raw=None):
    inp = raw if raw is not None else payload(tool, ti)
    if via_dispatch:
        cmd, env = ['bash', DISPATCH], dict(os.environ, CLAUDE_CODE_REMOTE='true')
    else:
        cmd, env = [sys.executable, GUARD], os.environ
    return subprocess.run(cmd, input=inp, capture_output=True, text=True, env=env, cwd=tmp).returncode


def put(name, text):
    p = os.path.join(tmp, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(text)
    return p


def b(cmd):
    return run('Bash', {'command': cmd})


put('f.md', GOTXT)
put('f.json', '{"body":"GO #1 abc"}')
put('ok.md', 'CI 緑')
put('b.md', GOTXT)

check('C1', run('mcp__github__add_issue_comment', {'body': 'GO #12 abc1234'}) == 2)
check('C2', run('mcp__github__pull_request_review_write', {'body': 'ok\n> GO #12 abc1234'}) == 2)
check('C3', run('mcp__github__new_tool', {'a': {'b': [{'c': 'GO #3 abcdef1'}]}}) == 2)
check('C4', run('mcp__github__get_pull_request', {'number': 1}) == 0)
check('C5', b('gh pr comment 1 --body "GO #1 abcdef1"') == 2)
check('C6', b('curl -X POST https://api.github.com/repos/x/y/issues/1/comments -d \'{"body":"GO #1 abc"}\'') == 2)
check('C7', b('grep -n "GO #" docs/x.md') == 0)
check('C8', run('Write', {'file_path': 'scripts/tests/test-guard-files-gate.js', 'content': 'GO #12 abc1234'}) == 0)
check('C9', run('Write', {'file_path': '.github/workflows/y.yml', 'content': 'name: guard-files gate'}) == 2)
check('C10', b('grep -rn "name: guard-files gate$" .github/workflows/') == 0)
check('C11', run('mcp__github__add_issue_comment', {'body': 'GO #12 abc1234'}, via_dispatch=True) == 2)
check('C12', run('mcp__github__get_pull_request', {'number': 1}, via_dispatch=True) == 0)
check('C13', b('gh pr comment 1 --body-file f.md') == 2)
check('C14', b('gh pr comment 1 --body-file ok.md') == 0)
check('C15', b('gh pr comment 1 --body-file missing.md') == 2)
check('C16', b('gh pr comment 1 --body-file -') == 2)
check('C17', b('gh api repos/x/y/issues/1/comments -F body=@f.md') == 2)
check('C18', b('curl -X POST https://api.github.com/repos/x/y/issues/1/comments --data @f.json') == 2)
check('C19', b('gh pr comment 1 -F f.md') == 2)
check('C20', b('gh pr comment 1 --body "$(cat f.md)"') == 2)
check('C21', run('Bash', None, raw='not json') == 1)
zp = put('.github/workflows/z.yml', 'name: guard-files check\n')
check('C22', run('Edit', {'file_path': zp, 'old_string': 'check', 'new_string': 'gate'}) == 2)
check('C23', b('gh pr comment 1 --body-file b.md') == 2)
check('C24', b('gh pr view 12 --json body --jq .body | grep "GO #[0-9]"') == 0)
check('C25', b('gh api repos/x/y/issues/1/comments -F body=hi') == 0)

print('OK %d/%d' % (ok, total))
sys.exit(0 if ok == total else 1)
