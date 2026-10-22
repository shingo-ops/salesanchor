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
# K2
add("K2", "MCP merge", pre("mcp__github__merge_pull_request", owner="o", repo="r", pullNumber=1), 2)
add("K2", "gh pr merge", bash("gh pr merge 12 --merge"), 2)
add("K2", "gh api PUT /merge", bash("gh api -X PUT repos/o/r/pulls/12/merge"), 2)
add("K2", "gh pr view", bash("gh pr view 12"), 0)
add("K2", "MCP get_me", pre("mcp__github__get_me"), 0)
# K3
add("K3", "MCP作成 コード枝", pre("mcp__github__create_pull_request", CODE, title="t", body=GOOD), 2)
add("K3", "gh pr create コード枝", bash(f'gh pr create --title t --body "{GOOD}"', CODE), 2)
add("K3", "gh api POST pulls コード枝", bash(f'gh api -X POST repos/o/r/pulls -f title=t -f body="{GOOD}"', CODE), 2)
add("K3", "MCP作成 docsのみ", pre("mcp__github__create_pull_request", DOCS, title="t", body=GOOD), 0)
add("K3", "gh pr create docsのみ", bash(f'gh pr create --title t --body "{GOOD}"', DOCS), 0)
add("K3", "git失敗なら止める", pre("mcp__github__create_pull_request", NOGIT, title="t", body=GOOD), 2)
# K4
add("K4", "本文に節なし(MCP)", pre("mcp__github__create_pull_request", DOCS, title="t", body="概要だけ"), 2)
add("K4", "本文に節なし(gh)", bash('gh pr create --title t --body "概要だけ"', DOCS), 2)
add("K4", "本文に節あり(MCP)", pre("mcp__github__create_pull_request", DOCS, title="t", body=GOOD), 0)
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
