#!/bin/bash
# 新規。K1〜K4・K6・K7 の確認台本。各ケースの入力 JSON を dispatch.sh に流し、exit コードと時間を表にする。
# 危険操作のケースは danger_ops.json から組み立てる（台本に危険語を直接書かない）。
# 前提: sync_danger_ops.py で danger_ops.json を作ってあること。
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$DIR/danger_ops.json" ] || { echo "danger_ops.json がありません。sync_danger_ops.py を先に実行してください"; exit 1; }
python3 - "$DIR" <<'PY'
import json, os, subprocess, sys, tempfile, time

D = sys.argv[1]
DISPATCH = os.path.join(D, "dispatch.sh")
ops = json.load(open(os.path.join(D, "danger_ops.json"), encoding="utf-8"))

def sh(*a, cwd=None):
    subprocess.run(a, cwd=cwd, check=True, capture_output=True)

def mkrepo(path, fname):
    """origin/main を持つ一時リポジトリ。fname を足した枝に居る。"""
    os.makedirs(path)
    g = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    sh(*g, "init", "-q", "-b", "main", cwd=path)
    open(os.path.join(path, "README.txt"), "w").write("x\n")
    sh(*g, "add", ".", cwd=path); sh(*g, "commit", "-qm", "base", cwd=path)
    sh("git", "update-ref", "refs/remotes/origin/main", "HEAD", cwd=path)
    sh(*g, "checkout", "-qb", "feat", cwd=path)
    fp = os.path.join(path, fname)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, "w").write("y\n")
    sh(*g, "add", ".", cwd=path); sh(*g, "commit", "-qm", "chg", cwd=path)
    return path

tmp = tempfile.mkdtemp(prefix="cloudparity-")
DOCS = mkrepo(os.path.join(tmp, "docsrepo"), "docs/a.md")
CODE = mkrepo(os.path.join(tmp, "coderepo"), "src/x.py")
def mkremote(path):
    """bare の origin を持つ clone。origin に main / codebr / docsbr がある。
    codebr・docsbr は別 clone から push するので、手元 clone には参照が無い（fetch の確認も兼ねる）。
    手元 clone は main に居て変更なし（HEAD は origin/main と同じ）。"""
    g = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    bare = path + "-origin.git"
    sh("git", "init", "-q", "--bare", "-b", "main", bare)
    work = path + "-seed"
    sh("git", "clone", "-q", bare, work)
    open(os.path.join(work, "README.txt"), "w").write("x\n")
    sh(*g, "add", ".", cwd=work); sh(*g, "commit", "-qm", "base", cwd=work)
    sh(*g, "branch", "-M", "main", cwd=work); sh(*g, "push", "-q", "origin", "main", cwd=work)
    for br, fname in (("codebr", "src/x.py"), ("docsbr", "docs/a.md")):
        sh(*g, "checkout", "-q", "-b", br, "main", cwd=work)
        fp = os.path.join(work, fname); os.makedirs(os.path.dirname(fp), exist_ok=True)
        open(fp, "w").write("y\n")
        sh(*g, "add", ".", cwd=work); sh(*g, "commit", "-qm", br, cwd=work)
        sh(*g, "push", "-q", "origin", br, cwd=work)
    sh("git", "clone", "-q", "--single-branch", "-b", "main", bare, path)
    sh("git", "config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*", cwd=path)
    return path

REMOTE = mkremote(os.path.join(tmp, "remoterepo"))
def mkstale(path):
    """staledocs 枝（docs のみ）を一度 fetch した後、別 clone からその枝にコードを足して push する。
    手元の追跡参照は古いまま残る。"""
    g = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    bare = REMOTE + "-origin.git"
    seed = REMOTE + "-seed"
    sh(*g, "checkout", "-q", "-b", "staledocs", "main", cwd=seed)
    os.makedirs(os.path.join(seed, "docs"), exist_ok=True)
    open(os.path.join(seed, "docs/s.md"), "w").write("s\n")
    sh(*g, "add", ".", cwd=seed); sh(*g, "commit", "-qm", "staledocs", cwd=seed)
    sh(*g, "push", "-q", "origin", "staledocs", cwd=seed)
    sh("git", "clone", "-q", "--single-branch", "-b", "main", bare, path)
    sh("git", "config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*", cwd=path)
    sh("git", "fetch", "-q", "origin", "staledocs", cwd=path)
    other = path + "-other"
    sh("git", "clone", "-q", bare, other)
    sh(*g, "checkout", "-q", "staledocs", cwd=other)
    fp = os.path.join(other, "src/late.py"); os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, "w").write("z\n")
    sh(*g, "add", ".", cwd=other); sh(*g, "commit", "-qm", "late code", cwd=other)
    sh(*g, "push", "-q", "origin", "staledocs", cwd=other)
    return path
STALE = mkstale(os.path.join(tmp, "stalerepo"))
NOGIT = os.path.join(tmp, "nogit"); os.makedirs(NOGIT)

def pre(tool, cwd=D, **ti):
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": ti, "cwd": cwd}
def bash(cmd, cwd=D):
    return pre("Bash", cwd, command=cmd)
GOOD = "## 概要\nx\n### 標準ワークフロー確認\n- ok\n"

cases = []  # (番号, 名前, 入力, 期待exit)
def add(k, name, inp, exp): cases.append((k, name, inp, exp))

# K1 止まる
add("K1", "危険語1つ目", bash(f"{ops[0]} foo"), 2)
add("K1", "危険語3つ目", bash(f"echo a && {ops[2]} bar"), 2)
add("K1", "rebase系(一覧内)", bash(next(o for o in ops if "rebase" in o) + " main"), 2)
add("K1", "psql 書込(insert)", bash('psql -c "insert into t values (1)"'), 2)
add("K1", "psql 書込(update)", bash("psql -c 'update t set a=1'"), 2)
add("K1", "psql ファイル流し込み", bash("psql < dump.sql"), 2)
add("K1", "ssh で prod へ", bash("ssh deploy@prod1 ls"), 2)
# K1 通る
add("K1", "ls", bash("ls -la"), 0)
add("K1", "git status", bash("git status"), 0)
add("K1", "grep内の語は読取り扱い", bash(f'grep -i "{ops[0]}" x.log'), 0)
add("K1", "commit文中の語は対象外", bash(f'git commit -m "docs: {ops[0]} を説明"'), 0)
add("K1", "psql 読取(select)", bash('psql -c "select 1"'), 0)
# K1 heredoc（実行される本文は検査／ファイルへ書くだけの本文は対象外）
add("K1", "bash heredoc本文に危険語", bash(f"bash <<EOF\necho hi\n{ops[0]} foo\nEOF"), 2)
add("K1", "python3 heredoc本文に危険語", bash(f"python3 - <<'PYX'\nprint(1)\n# {ops[0]}\nPYX"), 2)
add("K1", "cat>file heredoc本文は通す", bash(f"cat > note.txt <<EOF\n{ops[0]} の説明\nEOF"), 0)
add("K1", "cat>run.sh heredoc本文は通す", bash(f"cat > run.sh <<'EOF'\n{ops[0]}\nEOF"), 0)
# K2
add("K2", "MCP merge", pre("mcp__github__merge_pull_request", owner="o", repo="r", pullNumber=1), 2)
add("K2", "gh pr merge", bash("gh pr merge 12 --merge"), 2)
add("K2", "gh api PUT /merge", bash("gh api -X PUT repos/o/r/pulls/12/merge"), 2)
add("K2", "gh pr view", bash("gh pr view 12"), 0)
add("K2", "MCP get_me", pre("mcp__github__get_me"), 0)
# K3
add("K3", "MCP作成 コード枝", pre("mcp__github__create_pull_request", REMOTE, title="t", head="codebr", body=GOOD), 2)
add("K3", "gh pr create コード枝", bash(f'gh pr create --title t --body "{GOOD}"', CODE), 2)
add("K3", "gh api POST pulls コード枝", bash(f'gh api -X POST repos/o/r/pulls -f title=t -f body="{GOOD}"', CODE), 2)
add("K3", "MCP作成 docsのみ", pre("mcp__github__create_pull_request", REMOTE, title="t", head="docsbr", body=GOOD), 0)
add("K3", "gh pr create docsのみ", bash(f'gh pr create --title t --body "{GOOD}"', DOCS), 0)
add("K3", "git失敗なら止める", pre("mcp__github__create_pull_request", NOGIT, title="t", head="docsbr", body=GOOD), 2)
add("K3", "MCP head=コード枝", pre("mcp__github__create_pull_request", REMOTE, title="t", head="codebr", body=GOOD), 2)
add("K3", "MCP head=docs枝(owner:形式)", pre("mcp__github__create_pull_request", REMOTE, title="t", head="o:docsbr", body=GOOD), 0)
add("K3", "MCP head=docs枝 節なし", pre("mcp__github__create_pull_request", REMOTE, title="t", head="docsbr", body="概要だけ"), 2)
add("K3", "MCP head無し", pre("mcp__github__create_pull_request", REMOTE, title="t", body=GOOD), 2)
add("K3", "MCP head空", pre("mcp__github__create_pull_request", REMOTE, title="t", head="", body=GOOD), 2)
add("K3", "MCP head不正文字", pre("mcp__github__create_pull_request", REMOTE, title="t", head="a;b", body=GOOD), 2)
add("K3", "gh pr create --head コード枝", bash(f'gh pr create --head codebr --title t --body "{GOOD}"', REMOTE), 2)
add("K3", "gh pr create --head= docs枝", bash(f'gh pr create --head=docsbr --title t --body "{GOOD}"', REMOTE), 0)
add("K3", "gh pr create -H コード枝", bash(f'gh pr create -H codebr --title t --body "{GOOD}"', REMOTE), 2)
add("K3", "gh api head=コード枝", bash(f'gh api -X POST repos/o/r/pulls -f head=codebr -f title=t -f body="{GOOD}"', REMOTE), 2)
add("K3", "gh api --raw-field head=docs枝", bash(f'gh api -X POST repos/o/r/pulls --raw-field head=docsbr -f title=t -f body="{GOOD}"', REMOTE), 0)
add("K3", "head枝が存在しない", pre("mcp__github__create_pull_request", REMOTE, title="t", head="nosuchbr", body=GOOD), 2)
# 再審査指摘
add("K3", "追跡参照が古い(後からコード追加)", pre("mcp__github__create_pull_request", STALE, title="t", head="staledocs", body=GOOD), 2)
add("K3", "--head 2回(後がコード枝)", bash(f'gh pr create --head docsbr --head codebr --title t --body "{GOOD}"', REMOTE), 2)
add("K3", "gh api -fhead=コード枝(詰め書き)", bash(f'gh api -X POST repos/o/r/pulls -fhead=codebr -f title=t -f body="{GOOD}"', REMOTE), 2)
add("K1", ">( の中に危険語", bash(f"cat >({ops[0]} foo)"), 2)
# 審査指摘の止め漏れ
add("K1", "単独&の後ろに危険語", bash(f"cat a & {ops[0]} foo"), 2)
add("K1", "2>&1 の後ろに危険語", bash(f"cat a 2>&1 | {ops[0]} foo"), 2)
add("K1", "<( の中に危険語", bash(f"cat <({ops[0]} foo)"), 2)
add("K1", "ssh-keygen は通す", bash("ssh-keygen -f prod_key.pub"), 0)
# K4
add("K4", "本文に節なし(MCP)", pre("mcp__github__create_pull_request", REMOTE, title="t", head="docsbr", body="概要だけ"), 2)
add("K4", "本文に節なし(gh)", bash('gh pr create --title t --body "概要だけ"', DOCS), 2)
add("K4", "本文に節あり(MCP)", pre("mcp__github__create_pull_request", REMOTE, title="t", head="docsbr", body=GOOD), 0)
# K5
add("K5", "Stop 英語のみ", {"hook_event_name": "Stop", "last_assistant_message": "Done. All tests passed successfully."}, 2)
add("K5", "Stop 日本語あり", {"hook_event_name": "Stop", "last_assistant_message": "完了しました。"}, 0)
add("K5", "Stop 続行中は通す", {"hook_event_name": "Stop", "stop_hook_active": True, "last_assistant_message": "Done."}, 0)

def run(inp, remote):
    env = dict(os.environ)
    env.pop("CLAUDE_CODE_REMOTE", None)
    if remote: env["CLAUDE_CODE_REMOTE"] = "true"
    t = time.time()
    p = subprocess.run(["bash", DISPATCH], input=json.dumps(inp), capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr, time.time() - t

fail = 0
slow = 0
print("== CLAUDE_CODE_REMOTE=true ==")
print(f"{'No':3} {'ケース':26} {'期待':4} {'実際':4} {'秒':6} 判定")
for k, name, inp, exp in cases:
    rc, out, err, sec = run(inp, True)
    ok = (rc == exp)
    fail += (not ok)
    slow += (sec >= 1.0)
    print(f"{k:3} {name:26} {exp:<4} {rc:<4} {sec:6.3f} {'OK' if ok else 'NG'}{' 遅' if sec >= 1.0 else ''}")
    if rc == 2: print("      止めた文言: " + err.strip().replace("\n", " ")[:160])

# fail-closed: JSON が読めない PreToolUse は止める（guard 直接）／guard が想定外の終了コードなら dispatch が止める
p = subprocess.run(["python3", os.path.join(D, "guard_pre_tool.py")], input="not json", capture_output=True, text=True)
ok = p.returncode == 2
fail += (not ok)
print(f"{'FC':3} {'JSON不正→止める(guard)':26} {2:<4} {p.returncode:<4} {'-':>6} {'OK' if ok else 'NG'}")
import shutil
stub = os.path.join(tmp, "stubdir"); os.makedirs(stub)
shutil.copy(DISPATCH, os.path.join(stub, "dispatch.sh"))
open(os.path.join(stub, "guard_pre_tool.py"), "w").write("import sys\nsys.exit(1)\n")
env = dict(os.environ); env["CLAUDE_CODE_REMOTE"] = "true"
p = subprocess.run(["bash", os.path.join(stub, "dispatch.sh")], input=json.dumps(bash("ls")), capture_output=True, text=True, env=env)
ok = p.returncode == 2 and "内部エラー" in p.stderr
fail += (not ok)
print(f"{'FC':3} {'guard異常終了→止める':26} {2:<4} {p.returncode:<4} {'-':>6} {'OK' if ok else 'NG'}")
print("      止めた文言: " + p.stderr.strip())

# dispatch: 壊れた JSON は止める（変数なしでは通す）
env = dict(os.environ); env["CLAUDE_CODE_REMOTE"] = "true"
p = subprocess.run(["bash", DISPATCH], input="not json", capture_output=True, text=True, env=env)
ok = p.returncode == 2 and "読めなかった" in p.stderr
fail += (not ok)
print(f"{'FC':3} {'JSON不正→止める(dispatch)':26} {2:<4} {p.returncode:<4} {'-':>6} {'OK' if ok else 'NG'}")
env.pop("CLAUDE_CODE_REMOTE")
p = subprocess.run(["bash", DISPATCH], input="not json", capture_output=True, text=True, env=env)
ok = p.returncode == 0 and not p.stdout and not p.stderr
fail += (not ok)
print(f"{'FC':3} {'JSON不正 変数なし→通す':26} {0:<4} {p.returncode:<4} {'-':>6} {'OK' if ok else 'NG'}")

# K5 SessionStart
rc, out, err, sec = run({"hook_event_name": "SessionStart", "source": "startup"}, True)
try:
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    ok = rc == 0 and "日本語" in ctx
except Exception:
    ok = False
fail += (not ok)
print(f"{'K5':3} {'SessionStart 決まり注入':26} {0:<4} {rc:<4} {sec:6.3f} {'OK' if ok else 'NG'}")

print("== CLAUDE_CODE_REMOTE 未設定（K6: 全件 exit 0・出力なし）==")
allinp = [c[2] for c in cases] + [{"hook_event_name": "SessionStart", "source": "startup"}]
bad = 0
for inp in allinp:
    rc, out, err, sec = run(inp, False)
    if rc != 0 or out or err: bad += 1
fail += (bad > 0)
print(f"K6  {len(allinp)}件中 逸脱 {bad}件 {'OK' if bad == 0 else 'NG'}")

print(f"K7  1秒以上かかった件: {slow}（負荷 {os.getloadavg()[0]:.1f}。負荷が高い機械では参考値）")
print(f"== 結果: {'全件OK' if fail == 0 else str(fail) + '件NG'} ==")
sys.exit(1 if fail else 0)
PY
