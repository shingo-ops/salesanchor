# 設計: docs/handoff/mac-test-guard/design.md §3〜§6
"""guard.py の試験。使い方: python3 test_guard.py [guard.py のパス]。標準ライブラリのみ。"""
import sys, os, json, subprocess, tempfile, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'guard.py')

BLOCK = [
    'npm test', 'npm t', 'npm --prefix frontend test', 'npm -C agent-console test',
    'npm run test:e2e', 'npm run test:unit', 'npm run-script test', 'npx vitest run',
    'npx playwright test', 'pnpm exec vitest', 'yarn test', 'vitest run', 'playwright test',
    'pytest backend/tests', 'py.test', 'python3 -m pytest -q', 'python3.12 -m pytest',
    'uv run pytest', 'docker compose exec -T backend pytest', 'cd frontend && npm test',
    'bash -c "npm test"', '/usr/local/bin/npm test', 'FOO=1 npm test 2>&1 | tail -5',
    'timeout 600 npx vitest run', 'timeout -s KILL 10m npm test', 'nice npm test',
    'nice -n 10 pytest', 'nohup pytest', 'sudo nohup npm test', 'pnpm test',
    'yarn run test:e2e', 'docker compose run --rm -e X=1 backend python -m pytest',
    'time -p npm test', 'env -i npm test', 'sudo -u nobody npm test', 'pnpm --filter web test',
    'yarn --cwd frontend test', 'uv run --with pytest-cov pytest', 'docker-compose exec backend pytest',
    'bash -lc "npm test"', 'pnpm vitest', 'pnpm dlx vitest', 'npm exec vitest',
]
PASS = [
    'npm ci', 'npm run build', 'npm run lint', 'npm run test:e2e:install', 'npm install',
    'npx playwright install chromium', 'npx tsc --noEmit', 'playwright install',
    'python3 scripts/tests/test_x.py', 'python3 -I scripts/ci/check_doc_index.py',
    'uv run ruff check', 'docker compose ps', 'bash scripts/dev/check-before-submit.sh',
    'node --test scripts/tests/x.js', 'git push', 'git status', 'ls',
    'docker compose exec backend echo vitest', 'docker compose exec backend pip show pytest',
    'timeout 5 git status', 'nice ls', 'yarn install', 'pnpm run build',
    'echo "npm test"', 'grep -n "npm test" README.md', 'git commit -m "npm test を止める"',
    "cat <<'EOF' > /tmp/x.txt\nnpm test\nEOF",
    'time -p ls', 'env -i PATH=/usr/bin ls', 'sudo -u nobody ls', 'pnpm --filter web build', 'pnpm tsc',
    'npm exec tsc', 'uv run --with rich python scripts/x.py', 'docker-compose ps', 'bash -lc "echo hi"',
]

tmp = tempfile.mkdtemp(prefix='mtg-')
LOG = os.path.join(tmp, 'events.jsonl')
PERM = os.path.join(tmp, '.claude', 'permits')
os.makedirs(PERM, exist_ok=True)
ENV = dict(os.environ, HOME=tmp, MAC_TEST_GUARD_LOG=LOG)
total = ok = 0


def run(cmd, raw=None):
    inp = raw if raw is not None else json.dumps({'tool_input': {'command': cmd}})
    p = subprocess.run([sys.executable, GUARD], input=inp, capture_output=True, text=True, env=ENV)
    return p.returncode, p.stderr


def check(label, cond):
    global total, ok
    total += 1
    if cond:
        ok += 1
    else:
        print('FAIL:', label)


def permit(op='mac test', by='manual', hours=1):
    exp = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=hours)).strftime('%Y-%m-%dT%H:%M:%SZ')
    path = os.path.join(PERM, 'danger-permit-1.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'op': op, 'created_by': by, 'expires_at': exp}, f)
    return path


def nlines():
    return len(open(LOG, encoding='utf-8').read().splitlines()) if os.path.exists(LOG) else 0


for c in BLOCK:
    rc, err = run(c)
    check('止める: ' + repr(c), rc == 2 and 'GitHub' in err)
for c in PASS:
    rc, _ = run(c)
    check('通す: ' + repr(c), rc == 0)

# 券
p = permit()
check('券あり 1回目', run('npm test')[0] == 0)
check('券が消える', not os.path.exists(p))
check('券なし 2回目', run('npm test')[0] == 2)
for label, kw in [('op違い', dict(op='mac vm')), ('期限切れ', dict(hours=-1)), ('作成者違い', dict(by='agent'))]:
    p = permit(**kw)
    check('券 ' + label, run('npm test')[0] == 2)
    os.remove(p)

# 壊れた入力
check('壊れた入力', run('', raw='not json{')[0] == 0)

# 記録
before = nlines()
run('npm test')
check('記録が1行増える', nlines() == before + 1 and '"hook": "mac-test-guard"' in open(LOG, encoding='utf-8').read().splitlines()[-1])

print('OK %d/%d' % (ok, total))
sys.exit(0 if ok == total else 1)
