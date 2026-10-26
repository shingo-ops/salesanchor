#!/bin/bash
# 新規。K1〜K4・K6・K7 の確認台本（便2: B1〜B8 を追加・card-2.md §4-7）。各ケースの入力 JSON を dispatch.sh に流し、exit コードと時間を表にする。
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
# K2 別の書き方のマージ（M1〜M8）
add("M1", "curl PUT /merge", bash("curl -X PUT -H 'Authorization: token x' https://api.github.com/repos/o/r/pulls/1/merge"), 2)
add("M2", "curl --request=PUT /merge", bash("curl --request=PUT https://api.github.com/repos/o/r/pulls/1/merge"), 2)
add("M3", "gh api graphql mergePullRequest", bash("gh api graphql -f query='mutation{mergePullRequest(input:{pullRequestId:\"x\"}){clientMutationId}}'"), 2)
add("M4", "gh api graphql 自動マージ予約", bash("gh api graphql -f query='mutation{enablePullRequestAutoMerge(input:{pullRequestId:\"x\"}){clientMutationId}}'"), 2)
add("M5", "gh api repos/…/merges", bash("gh api repos/o/r/merges -f base=main -f head=x"), 2)
add("M6", "curl GET /merge(調べるだけ)", bash("curl https://api.github.com/repos/o/r/pulls/1/merge"), 0)
add("M7", "grep mergePullRequest", bash("grep -n mergePullRequest scripts/agent-hooks/cloud/guard_pre_tool.py"), 0)
add("M8", "gh api graphql 読取", bash("gh api graphql -f query='query{repository(owner:\"o\",name:\"r\"){pullRequest(number:1){mergeable}}}'"), 0)
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
# 別カード 指摘1・2: 本文・ヘッダの中の枝名を作成元と読まない（H1〜H5）
add("H1", "本文中の -H docs枝", bash(f'gh pr create --head codebr --title t --body "{GOOD} -H docsbr"', REMOTE), 2)
add("H2", "本文中の --head docs枝", bash(f'gh pr create --head codebr --title t --body "{GOOD} --head docsbr"', REMOTE), 2)
add("H3", "gh api 末尾ヘッダ X-A:docs枝", bash(f"gh api repos/o/r/pulls -f head=codebr -f title=t -f body=\"{GOOD}\" -H 'X-A:docsbr'", REMOTE), 2)
add("H4", "gh api Accept ヘッダが後ろ", bash(f"gh api repos/o/r/pulls -f head=docsbr -f base=main -f body=\"{GOOD}\" -H 'Accept: application/vnd.github+json'", REMOTE), 0)
add("H5", "引用符が閉じていない(shlex の道)", bash("gh pr create --head docsbr --body 'abc", REMOTE), 2)
# 追補 R1: 語の途中の # は shlex が以降を捨てるため止める（H7〜H10）
add("H7", "語の途中の # (--title fix#12)", bash('gh pr create --title fix#12 --head codebr --body x', REMOTE), 2)
add("H8", "gh api 語の途中の # (title=a#b)", bash('gh api repos/o/r/pulls -f title=a#b -f head=codebr', REMOTE), 2)
add("H9", "引用符の外のコメントは読めないので止める(R5)", bash(f'gh pr create --head docsbr --body "{GOOD}" # --head codebr', REMOTE), 2)
add("H10", "引用符の中の # は対象外", bash(f"gh pr create --head docsbr --body '{GOOD} see #12' ", REMOTE), 0)
# 追補 R2: コメント内の引用符・行の継ぎ目・ANSI-C 引用符（H11〜H15）。本文は GOOD で、本文欠落では止まらない形にしてある
add("H11", "コメント内の ' の後ろの行に fix#12", bash(f"# don't forget\ngh pr create --title fix#12 --head codebr --body \"{GOOD}\"", REMOTE), 2)
add("H12", "git status # it's fine の後ろの行に fix#12", bash(f"git status # it's fine\ngh pr create --title fix#12 --head codebr --body \"{GOOD}\"", REMOTE), 2)
add("H13", "行の継ぎ目の直後の #", bash(f"gh pr create --head docsbr --body \"{GOOD}\"\\\n# --head codebr", REMOTE), 2)
add("H14", "$' (ANSI-C 引用符)", bash(f"gh pr create --title $'a' --head docsbr --body \"{GOOD}\"", REMOTE), 2)
add("H15", "先頭のコメント行は読めないので止める(R5)", bash(f"# it's a note\ngh pr create --head docsbr --body \"{GOOD}\"", REMOTE), 2)
# 追補 R3: 逃がした文字の直後の # は語の途中・\r は区切りにしない（H16〜H19）
add("H16", "Fix\\ #12 (逃がした空白の直後の #)", bash(f"gh pr create --title Fix\\ #12 --head codebr --body \"{GOOD}\"", REMOTE), 2)
add("H17", "x\\;#12 (逃がした ; の直後の #)", bash(f"gh pr create --title x\\;#12 --head codebr --body \"{GOOD}\"", REMOTE), 2)
add("H18", "命令文に \\r を含む", bash(f"gh pr create --title a\r#12 --head codebr --body \"{GOOD}\"", REMOTE), 2)
add("H19", "区切り直後のコメントは読めないので止める(R5)", bash(f"gh pr create --head docsbr --body \"{GOOD}\"; # --head codebr", REMOTE), 2)
# 追補 R4: 読める形だけ読み、区切り以外の記号・作成の命令が複数に見える形は止める（H20〜H26）
add("H20", ";( の後ろに docs枝", bash(f"gh pr create --head codebr --body \"{GOOD}\";(echo --head docsbr)", REMOTE), 2)
add("H21", "&&( の後ろに docs枝", bash(f"gh pr create --head codebr --body \"{GOOD}\"&&(echo --head docsbr)", REMOTE), 2)
add("H22", "引用符の中の <<EOF から行頭 EOF までに本物の --head", bash(f"gh pr create --body \"{GOOD}\" --title '<<EOF' \\\n  --head codebr --title \\\nEOF", REMOTE), 2)
add("H23", "echo gh pr create の後ろの bash -c に本物の作成", bash(f"echo gh pr create; bash -c 'gh pr create --head codebr --body \"{GOOD}\"'", REMOTE), 2)
add("H24", "docs枝の作成の後ろの bash -c に本物の作成", bash(f"gh pr create --head docsbr --body \"{GOOD}\" && bash -c 'gh pr create --head codebr --body x'", REMOTE), 2)
add("H25", "何も足さない普通の形", bash(f"gh pr create --head docsbr --body \"{GOOD}\"", REMOTE), 0)
add("H26", "引用符の中の記号 (a <<b)", bash(f"gh pr create --head docsbr --title 'a <<b' --body \"{GOOD}\"", REMOTE), 0)
# 追補 R5: PR 作成は gh だけの1行しか読まない（H27〜H32）
add("H27", "変数 $G で本物を隠す", bash(f'G=gh; gh pr create --head docsbr --body GOOD; $G pr create --head codebr --body x', REMOTE), 2)
add("H28", "逃がした \\; で語を作る", bash(f'gh pr create --head docsbr --body GOOD --title \\; --head codebr', REMOTE), 2)
add("H29", "二重引用符の中の $(…)", bash(f'gh pr create --head docsbr --body GOOD --title "$(echo x)"', REMOTE), 2)
add("H30", "cd && gh pr create (つなぎ)", bash(f'cd /tmp && gh pr create --head docsbr --body GOOD', REMOTE), 2)
add("H31", "単引用符の中は何でもよい", bash(f"gh pr create --head docsbr --base main --title 'a; b $c' --body \"{GOOD}\"", REMOTE), 0)
add("H32", "二重引用符の本文(普通の文字+節の見出し)", bash('gh pr create --head docsbr --body "plain text ### 標準ワークフロー確認"', REMOTE), 0)
add("K1", ">( の中に危険語", bash(f"cat >({ops[0]} foo)"), 2)
# 審査指摘の止め漏れ
add("K1", "単独&の後ろに危険語", bash(f"cat a & {ops[0]} foo"), 2)
add("K1", "2>&1 の後ろに危険語", bash(f"cat a 2>&1 | {ops[0]} foo"), 2)
add("K1", "<( の中に危険語", bash(f"cat <({ops[0]} foo)"), 2)
add("K1", "ssh-keygen は通す", bash("ssh-keygen -f prod_key.pub"), 0)
# 別カード 指摘4: 並べ替えた rm の再帰削除（R1〜R14。R13 は既存ケース全件が同じ結果であること）
add("R1", "rm -fr", bash("rm -fr build"), 2)
add("R2", "rm -Rf", bash("rm -Rf build"), 2)
add("R3", "rm -f -r", bash("rm -f -r build"), 2)
add("R4", "rm --recursive", bash("rm --recursive build"), 2)
add("R5", "/bin/rm -dfr", bash("/bin/rm -dfr build"), 2)
add("R6", "env X=1 command rm -fr", bash("env X=1 command rm -fr build"), 2)
add("R7", "ls && rm -fr", bash("ls && rm -fr build"), 2)
add("R8", "rm -f (再帰なし)", bash("rm -f build.log"), 0)
add("R9", "rm -- -r (-r という名のファイル)", bash("rm -- -r"), 0)
add("R10", "grep内の rm -fr は読取り扱い", bash("grep -n 'rm -fr' notes.txt"), 0)
add("R11", "commit文中の rm -fr は対象外", bash('git commit -m "docs: rm -fr の説明"'), 0)
add("R12", "rmdir", bash("rmdir build"), 0)
add("R14", "nice -n 5 rm -fr", bash("nice -n 5 rm -fr build"), 2)
# 別カード 指摘5: 埋め込んだ命令（E1〜E18。E19 は既存ケース全件が同じ結果であること）
add("E1", "$( ) の中の rm -fr", bash("echo $(rm -fr /tmp/x)"), 2)
add("E2", "逆引用符の中の rm -fr", bash("echo `rm -fr /tmp/x`"), 2)
add("E3", "( ) 殻の中の rm -fr", bash("(rm -fr /tmp/x)"), 2)
add("E4", "bash -c の中の rm -fr", bash("bash -c 'rm -fr /tmp/x'"), 2)
add("E5", "/bin/sh -c の中の rm -Rf", bash('/bin/sh -c "rm -Rf /tmp/x"'), 2)
add("E6", "eval の中の rm -fr", bash("eval 'rm -fr /tmp/x'"), 2)
add("E7", "commit 文の $( ) の中の gh pr merge", bash('git commit -m "$(gh pr merge 1 --merge)"'), 2)
add("E8", "$( ) の中の gh api PUT merge", bash("echo $(gh api -X PUT repos/o/r/pulls/1/merge)"), 2)
add("E9", "入れ子の $( )", bash("echo $(echo $(rm -fr /tmp/x))"), 2)
add("E10", "bash -c の中の $( )", bash(r'bash -c "echo \$(rm -fr /tmp/x)"'), 2)
add("E11", "閉じ忘れの $(", bash("echo $(rm -fr /tmp/x"), 2)
add("E12", "commit 本文中の rm -fr は対象外", bash('git commit -m "fix: rm -fr の扱い"'), 0)
add("E13", 'echo "$(date)"', bash('echo "$(date)"'), 0)
add("E14", "単引用符の中の $( ) は実行されない", bash("grep -n '$(rm -fr' file.txt"), 0)
add("E15", "commit の heredoc 書き方", bash("git commit -m \"$(cat <<'EOF'\nfix: rm -fr と gh pr merge の説明\nEOF\n)\""), 0)
add("E16", "算術 $(( ))", bash("echo $((1 + 2))"), 0)
add("E17", "\\ 付きの $(", bash(r'echo \$(rm -fr x)'), 0)
add("E18", "x=$(git rev-parse HEAD)", bash("x=$(git rev-parse HEAD) && echo $x"), 0)
# 別カード 指摘5 の残り7件（E20〜E39）。E1〜E18 を含む既存ケース全件が変更前と同じ結果であること（変更前後の生出力の差で確認）
add("E20", "5段の入れ子の中に rm -fr", bash("echo $(echo $(echo $(echo $(echo $(rm -fr x)))))"), 2)
add("E21", "5段の入れ子（中身は無害・深すぎで止める）", bash("echo $(echo $(echo $(echo $(echo $(echo hi)))))"), 2)
add("E22", "then の直後の ( )", bash("if true; then (rm -fr x); fi"), 2)
add("E23", "do の直後の ( )", bash("for f in a; do (rm -fr x); done"), 2)
add("E24", "! の直後の ( )", bash("! (rm -fr x)"), 2)
add("E25", "time の直後の ( )", bash("time (rm -fr x)"), 2)
add("E26", "bash -c -- '…'", bash("bash -c -- 'rm -fr x'"), 2)
add("E27", "プロセス置換 <( )", bash("cat <(rm -fr x)"), 2)
add("E28", "$((rm …) ) の形", bash("echo $((rm -fr x) )"), 2)
add("E29", "bash -c ドル付き単引用符", bash("bash -c $'rm -fr x'"), 2)
add("E30", "ドル付き単引用符の \\x20", bash(r"bash -c $'rm\x20-fr x'"), 2)
add("E31", "引用符なし \\ 区切り", bash(r"bash -c rm\ -fr\ x"), 2)
add("E32", "then の直後の ( ) で gh pr merge", bash("if true; then (gh pr merge 1 --merge); fi"), 2)
add("E33", "4段の入れ子で無害", bash("echo $(echo $(echo $(echo $(echo hi))))"), 0)
add("E34", "if の then ( ) 無害", bash("if [ -f x ]; then (cd sub && ls); fi"), 0)
add("E35", "for の do ( ) 無害", bash("for f in a b; do (echo $f); done"), 0)
add("E36", "diff <( ) <( ) 無害", bash("diff <(sort a) <(sort b)"), 0)
add("E37", "算術の中の $( ) 無害", bash("echo $(( $(wc -l < f) + 1 ))"), 0)
add("E38", "bash -c -- 無害", bash("bash -c -- 'echo hi'"), 0)
add("E39", "ドル付き単引用符 無害", bash(r"bash -c $'echo hi\n'"), 0)
# 指摘5 の続き 便2: 埋め込みの残り15件（E40〜E54・止める）と通す側（E55〜E63）。\u の組み立ては BS（バックスラッシュ）で行う
BS = chr(92)
def u4(t): return "".join(BS + "u%04x" % ord(c) for c in t)
add("E40", "\\u 小文字の16進で rm", bash(f"bash -c $'{u4('rm')} -fr /tmp/x'"), 2)
add("E41", "\\U 大文字8桁で rm", bash("bash -c $'" + BS + "U00000072m -fr /tmp/x'"), 2)
add("E42", "then( 空白なし", bash("if true; then(rm -fr /tmp/x); fi"), 2)
add("E43", "do( 空白なし", bash("for i in 1; do(rm -fr /tmp/x); done"), 2)
add("E44", "{( 空白なし", bash("{(rm -fr /tmp/x);}"), 2)
add("E45", "!( 空白なし", bash("!(rm -fr /tmp/x)"), 2)
add("E46", "case a) の後の ( )", bash("case a in a) (rm -fr /tmp/x);; esac"), 2)
add("E47", "case (a) の後の ( )", bash("case a in (a) (rm -fr /tmp/x);; esac"), 2)
add("E48", "関数 { ( ) }", bash("f() { (rm -fr /tmp/x); }; f"), 2)
add("E49", "関数 f() ( )", bash("f() (rm -fr /tmp/x); f"), 2)
add("E50", "time -p ( )", bash("time -p (rm -fr /tmp/x)"), 2)
add("E51", "bash -c 'rm -f''r'", bash("bash -c 'rm -f''r /tmp/x'"), 2)
add("E52", "bash -c r'm -fr'", bash("bash -c r'm -fr /tmp/x'"), 2)
add("E53", "bash -c \"rm -\"'fr'", bash('bash -c "rm -"' + "'fr /tmp/x'"), 2)
add("E54", "bash -c $'rm -f'r\\ ", bash("bash -c $'rm -f'r" + BS + " /tmp/x"), 2)
add("E55", "配列 a=( ) 無害", bash("a=(1 2 3); echo ${a[0]}"), 0)
add("E56", "二重引用符の中の ( ) 無害", bash('echo "(rm -fr /tmp/x)"'), 0)
add("E57", "grep -E 'a(b)' 無害", bash("grep -E 'a(b)' f.txt"), 0)
add("E58", "関数定義 f() { } 無害", bash("f() { echo hi; }; f"), 0)
add("E59", "case 無害", bash("case a in a) echo ok;; esac"), 0)
add("E60", "then( 無害", bash("if true; then(echo ok); fi"), 0)
add("E61", "bash -c 'echo a''b' 無害", bash("bash -c 'echo a''b'"), 0)
add("E62", "bash -c $'echo A' 無害", bash("bash -c $'echo A'"), 0)
add("E63", "bash -c $'…\\u0041…' 無害", bash("bash -c $'echo " + BS + "u0041'"), 0)
add("E64", "不正な \\u \\U（サロゲート・範囲外・桁なし）は例外なく通す", bash("bash -c $'" + BS + "ud800" + BS + "U00110000" + BS + "uZZ'"), 0)
NEED_ERR = {"E21": "入れ子が深すぎて"}  # 終了コードに加え、止めた理由文にこの語を含むことまで照合する番号
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
    ok = (rc == exp) and (k not in NEED_ERR or NEED_ERR[k] in err)
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

# ---- 便2: B1〜B8（card-2.md §4-7）。商品作成の命令名は master-register-rules-guard.py の TARGETS から組み立てる ----
import hashlib, importlib.util
_spec = importlib.util.spec_from_file_location("mrr_guard", os.path.join(D, "..", "master-register-rules-guard.py"))
_mrr = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_mrr)
T0 = _mrr.TARGETS[0]
WORKTREE = os.path.abspath(os.path.join(D, "..", "..", ".."))
RULES_TMP = os.path.join(tmp, "rules.md")
open(RULES_TMP, "w", encoding="utf-8").write("# 試験用ルール\nテスト本文\n")
ACK = hashlib.sha256(open(RULES_TMP, "rb").read()).hexdigest()[:8]
PYLOG = os.path.join(tmp, "agent-events.jsonl")

def run2(inp, remote, extra=None, drop=()):
    env = dict(os.environ)
    env.pop("CLAUDE_CODE_REMOTE", None)
    for k in ("MRR_RULES_FILE", "CLAUDE_PROJECT_DIR", *drop): env.pop(k, None)
    env["PY312_GUARD_LOG"] = PYLOG
    env["SUBAGENT_BASH_WAIT_GUARD_LOG"] = PYLOG
    if remote: env["CLAUDE_CODE_REMOTE"] = "true"
    env.update(extra or {})
    t = time.time()
    p = subprocess.run(["bash", DISPATCH], input=json.dumps(inp), capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr, time.time() - t

def sub(cmd, **kw):
    d = bash(cmd); d.update(kw); return d
def prompt(text):
    return {"hook_event_name": "UserPromptSubmit", "prompt": text, "cwd": D}
MRR = {"MRR_RULES_FILE": RULES_TMP}
def hasdeny(o): return '"permissionDecision": "deny"' in o

bcases = [  # (No, 名前, 入力, 追加env, 判定関数(rc,out,err), 期待の説明)
 ("B1", "登録ルール deny(Bash)", bash(f'python3 -c "{T0}1)"'), MRR, lambda r, o, e: r == 0 and hasdeny(o), "exit0+deny"),
 ("B1b", "rules-ack あり→通す", bash(f'python3 -c "{T0}1)" # rules-ack: {ACK}'), MRR, lambda r, o, e: r == 0 and not o.strip(), "exit0+出力なし"),
 ("B1c", "origin/mainからルールを読む", bash(f'python3 -c "{T0}1)"'), {"CLAUDE_PROJECT_DIR": WORKTREE}, lambda r, o, e: r == 0 and hasdeny(o) and "共用商品マスタ 新規登録ルール" in o, "exit0+deny+本文"),
 ("B2", "Write /tmp/x.py deny", pre("Write", file_path="/tmp/x.py", content=f"x = {T0}1)"), MRR, lambda r, o, e: r == 0 and hasdeny(o), "deny"),
 ("B2b", "Write docs 配下は通す", pre("Write", file_path="/repo/docs/a.md", content=f"x = {T0}1)"), MRR, lambda r, o, e: r == 0 and not o.strip(), "出力なし"),
 ("B3", "UserPromptSubmit 登録ルール注入", prompt("マスタに商品を登録して"), MRR, lambda r, o, e: r == 0 and "additionalContext" in o, "additionalContext"),
 ("B4", "python3.11 -m venv", bash("python3.11 -m venv .venv"), None, lambda r, o, e: r == 2 and "py312-guard" in e, "exit2+py312-guard"),
 ("B4", "pip install", bash("pip install requests"), None, lambda r, o, e: r == 2 and "py312-guard" in e, "exit2+py312-guard"),
 ("B4", "virtualenv", bash("virtualenv x"), None, lambda r, o, e: r == 2 and "py312-guard" in e, "exit2+py312-guard"),
 ("B4b", "python3.12 -m venv", bash("python3.12 -m venv .venv"), None, lambda r, o, e: r == 0, "exit0"),
 ("B4b", "uv venv --python 3.12", bash("uv venv --python 3.12 .venv"), None, lambda r, o, e: r == 0, "exit0"),
 ("B4b", "git status", bash("git status"), None, lambda r, o, e: r == 0, "exit0"),
 ("B5", "担当 timeout 300000", sub("ls", agent_id="a1", tool_input={"command": "ls", "timeout": 300000}), None, lambda r, o, e: r == 2 and "subagent-bash-wait-guard" in e, "exit2+guard名"),
 ("B5b", "親 timeout 300000", sub("ls", tool_input={"command": "ls", "timeout": 300000}), None, lambda r, o, e: r == 0, "exit0"),
 ("B5b", "担当 timeout 240000", sub("ls", agent_id="a1", tool_input={"command": "ls", "timeout": 240000}), None, lambda r, o, e: r == 0, "exit0"),
 ("B6", "カード 受領確認なし", prompt("手順1\n  ls\nEND OF CARD"), None, lambda r, o, e: r == 2 and "card-lint" in e, "exit2+card-lint"),
 ("B6b", "ふつうの依頼文", prompt("こんにちは"), None, lambda r, o, e: r == 0 and not o.strip() and not e.strip(), "exit0+出力なし"),
]
print("== 便2 B1〜B6b（CLAUDE_CODE_REMOTE=true）==")
print(f"{'No':4} {'ケース':28} {'期待':18} {'実際':4} {'秒':6} 判定")
b_slow = 0
b_times = []
for no, name, inp, extra, chk, exp in bcases:
    rc, out, err, sec = run2(inp, True, extra)
    ok = chk(rc, out, err)
    fail += (not ok)
    b_times.append((no, name, sec))
    print(f"{no:4} {name:28} {exp:18} {rc:<4} {sec:6.3f} {'OK' if ok else 'NG'}")
    if not ok: print("      stdout: " + out[:200].replace("\n", " ") + " / stderr: " + err[:200].replace("\n", " "))
# B7: CLAUDE_CODE_REMOTE 未設定では全て exit 0・出力なし
b7bad = 0
for no, name, inp, extra, chk, exp in bcases:
    rc, out, err, sec = run2(inp, False, extra)
    if rc != 0 or out or err: b7bad += 1
fail += (b7bad > 0)
print(f"B7  {len(bcases)}件中 逸脱 {b7bad}件 {'OK' if b7bad == 0 else 'NG'}")
# B8: 各 1 秒以内
b8slow = [t for t in b_times if t[2] >= 1.0]
fail += (len(b8slow) > 0)
print(f"B8  1秒以上かかった件: {len(b8slow)}（最大 {max(t[2] for t in b_times):.3f} 秒） {'OK' if not b8slow else 'NG'}")

# ---- 時間切れの扱い T1〜T5（指摘5 の続き 便1）----
GUARD = os.path.join(D, "guard_pre_tool.py")
def run_guard(inp, extra=None):
    env = dict(os.environ); env.update(extra or {})
    t = time.time()
    p = subprocess.run(["python3", GUARD], input=json.dumps(inp), capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr, time.time() - t
print("== 時間切れ T1〜T5 ==")
rc, out, err, sec = run_guard(bash("echo " + "$(true)" * 10000), {"CLOUD_GUARD_DEADLINE_SEC": "1"})
ok = rc == 2 and "時間内に中身を確かめられない" in err
fail += (not ok)
print(f"T1  上限1秒で $(true) 1万個→止める+理由文  期待 2 実際 {rc} {sec:.2f}秒 {'OK' if ok else 'NG'}")
print("      止めた文言: " + err.strip().replace("\n", " ")[:160])
rc, out, err, sec = run_guard(bash("echo hi"))
ok = rc == 0 and not err.strip()
fail += (not ok)
print(f"T2  既定の上限で echo hi→通す  期待 0 実際 {rc} {sec:.2f}秒 {'OK' if ok else 'NG'}")
_st = json.load(open(os.path.join(WORKTREE, ".claude", "settings.json"), encoding="utf-8"))
_pre = _st["hooks"]["PreToolUse"]
_disp = [h for e in _pre for h in e["hooks"] if "cloud/dispatch.sh" in h.get("command", "")]
HEAD = '[ "$CLAUDE_CODE_REMOTE" = "true" ] || exit 0;'
ok = len(_disp) == 3 and all(h.get("onFailure") == "block" and h["command"].startswith(HEAD) for h in _disp)
fail += (not ok)
print(f"T3  PreToolUse の dispatch {len(_disp)}項目すべて onFailure block＋先頭判定  期待 3項目 {'OK' if ok else 'NG'}")
_cmd = _disp[0]["command"] if _disp else "exit 1"
env = dict(os.environ); env.pop("CLAUDE_CODE_REMOTE", None); env["CLAUDE_PROJECT_DIR"] = "/nonexistent"
t = time.time()
p = subprocess.run(["sh", "-c", _cmd], input="{}", capture_output=True, text=True, env=env)
ok = p.returncode == 0 and not p.stdout and not p.stderr
fail += (not ok)
print(f"T4  手元(REMOTE 未設定・PROJECT_DIR 無効)で即 exit 0  期待 0 実際 {p.returncode} {time.time()-t:.2f}秒 {'OK' if ok else 'NG'}")
env = dict(os.environ); env["CLAUDE_CODE_REMOTE"] = "true"; env["CLAUDE_PROJECT_DIR"] = WORKTREE
p = subprocess.run(["sh", "-c", _cmd], input=json.dumps(bash("echo hi")), capture_output=True, text=True, env=env)
ok = p.returncode == 0
fail += (not ok)
print(f"T5  クラウド(REMOTE=true)で無害な Bash→dispatch が呼ばれて exit 0  期待 0 実際 {p.returncode} {'OK' if ok else 'NG'}")
env["CLAUDE_PROJECT_DIR"] = tmp  # dispatch.sh が無い場所→onFailure block 側で止まる形（exec 失敗は 0 以外）
p = subprocess.run(["sh", "-c", _cmd], input=json.dumps(bash("echo hi")), capture_output=True, text=True, env=env)
ok = p.returncode not in (0,)
fail += (not ok)
print(f"T5b クラウドで dispatch.sh が見つからない→0 以外（onFailure block が効く形）  実際 {p.returncode} {'OK' if ok else 'NG'}")

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
