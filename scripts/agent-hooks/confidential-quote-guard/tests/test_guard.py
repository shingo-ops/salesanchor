#!/usr/bin/env python3
"""confidential-quote-guard の受入試験。docs/handoff/confidential-quote-guard/design.md §4 を 1 行 1 試験にしたもの。

使い方: python3 scripts/agent-hooks/confidential-quote-guard/tests/test_guard.py [guard.py のパス]
  引数省略時は tests/ の一つ上の guard.py。install.sh は写した先の guard.py を渡して流す。

本物の表・本物の記録には触れない。表は一時フォルダに作り物の原文で作る (CONFID_GUARD_DIR /
CONFID_GUARD_EVENTS を一時フォルダへ向ける)。本物の原文・語句はこのファイルに入れない。
最後に PASS n / FAIL m を出し、FAIL>0 なら exit 1。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "guard.py")

# 作り物の語句だけ。仕入元の語句は入れない。
FAKE_QUOTE = "テスト用のつくり語句ABCD"        # 原文にある・除外表に無い -> 止まる
FAKE_QUOTE2 = "つくり語句EFGHの案内"            # 同上 (『』で使う)
FAKE_STATUS = "つくり状態ダメージXYZ"          # 状態の写しにある
FAKE_PRODUCT = "つくり商品名PQRS弾"            # 商品名の写しにある
FAKE_ALLOW = "つくり一般語MNOPの言い方"        # 一般語の表にある
FAKE_NOT_IN_CORPUS = "原文に無いつくり語句WXYZ"  # 原文に無い
FAKE_SHORT = "つくり"                           # 3 文字
FAKE_DIGITS = "2026-10-25 1,200"               # 数字と区切りだけ

results = []
T = tempfile.mkdtemp(prefix="cqg-test.")
D = os.path.join(T, "tables")
EV = os.path.join(T, "events.jsonl")
os.makedirs(D)
ORIGIN_ROOT = os.path.join(T, "origin")
WORK = os.path.join(T, "work")
OTHER = os.path.join(T, "other")
NOMAIN = os.path.join(T, "nomain")


def sh(*a, cwd=None):
    r = subprocess.run(list(a), cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("setup failed: %s %s" % (a, r.stderr[:200]))
    return r.stdout


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def make_tables(corpus_text=None, repos=("test/fake", "test/nomain")):
    for f in os.listdir(D):
        q = os.path.join(D, f)
        shutil.rmtree(q) if os.path.isdir(q) else os.remove(q)
    write(os.path.join(D, "raw", "msgs_1.tsv"),
          corpus_text if corpus_text is not None else "\n".join(
              ["1\t2026\t投稿 %s 在庫あり" % q for q in
               (FAKE_QUOTE, FAKE_QUOTE2, FAKE_STATUS, FAKE_PRODUCT, FAKE_ALLOW, FAKE_SHORT)]) + "\n")
    conf = ["# テスト用の置き場の表"] + ["repo: %s" % r for r in repos] + ["corpus: %s/raw/msgs_*.tsv" % D]
    write(os.path.join(D, "confidential-corpus.conf"), "\n".join(conf) + "\n")
    write(os.path.join(D, "status-words.txt"), FAKE_STATUS + "\n")
    write(os.path.join(D, "product-names.txt"), FAKE_PRODUCT + "\n")
    write(os.path.join(D, "confidential-allow.txt"), "# 語\t理由\n%s\tテスト用の一般語\n" % FAKE_ALLOW)


def run(cmd, cwd=None, tool="Bash"):
    env = dict(os.environ, CONFID_GUARD_DIR=D, CONFID_GUARD_EVENTS=EV, PYTHONDONTWRITEBYTECODE="1")
    payload = {"tool_name": tool, "tool_input": {"command": cmd}, "cwd": cwd or WORK}
    r = subprocess.run([sys.executable, GUARD], input=json.dumps(payload), capture_output=True, text=True, env=env)
    return r.returncode, r.stderr


def check(name, cmd, expect, cwd=None, tool="Bash"):
    rc, err = run(cmd, cwd, tool)
    ok = rc == expect
    results.append(ok)
    print("%s %-62s exit=%d (期待 %d) %s" % ("PASS" if ok else "FAIL", name, rc, expect, err.split(chr(10))[0][:48] if rc == 2 else ""))
    if not ok:
        print("     stderr: %s" % err.strip().replace("\n", " | ")[:300])
    return rc, err


def setup_repos():
    os.makedirs(ORIGIN_ROOT)
    bare = os.path.join(ORIGIN_ROOT, "test", "fake.git")
    sh("git", "init", "-q", "--bare", "-b", "main", bare)
    sh("git", "clone", "-q", bare, WORK)
    for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
        sh("git", "config", k, v, cwd=WORK)
    write(os.path.join(WORK, "README.md"), "base\n")
    sh("git", "add", "-A", cwd=WORK)
    sh("git", "commit", "-q", "-m", "base", cwd=WORK)
    sh("git", "push", "-q", "origin", "main", cwd=WORK)
    sh("git", "fetch", "-q", "origin", cwd=WORK)
    # origin/main の無い repo (表に並んだ repo)
    sh("git", "init", "-q", "-b", "main", NOMAIN)
    sh("git", "remote", "add", "origin", "https://example.invalid/test/nomain.git", cwd=NOMAIN)
    # 表に無い repo
    sh("git", "init", "-q", "-b", "main", OTHER)
    sh("git", "remote", "add", "origin", "https://example.invalid/test/other.git", cwd=OTHER)
    for r in (NOMAIN, OTHER):
        for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
            sh("git", "config", k, v, cwd=r)


def branch_with(name, text, repo=None, checkout=True):
    repo = repo or WORK
    sh("git", "checkout", "-q", "-B", name, "origin/main", cwd=repo)
    write(os.path.join(repo, "doc-%s.md" % name), text)
    sh("git", "add", "-A", cwd=repo)
    sh("git", "commit", "-q", "-m", name, cwd=repo)


def P(ref="HEAD", path=None, flags="-u "):
    """決まった形の push 命令。"""
    return "git -C %s push %sorigin %s" % (path or WORK, flags, ref)


def env_run(cmd, **extra):
    env = dict(os.environ, CONFID_GUARD_DIR=D, CONFID_GUARD_EVENTS=EV, PYTHONDONTWRITEBYTECODE="1", **extra)
    payload = {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": WORK}
    return subprocess.run([sys.executable, GUARD], input=json.dumps(payload), capture_output=True, text=True, env=env)


def main():
    setup_repos()
    make_tables()
    q = FAKE_QUOTE
    hitbody = os.path.join(T, "hitbody.md")
    cleanbody = os.path.join(T, "cleanbody.md")
    write(hitbody, "確認します。「%s」\n" % q)
    write(cleanbody, "確認します。「%s」\n" % FAKE_NOT_IN_CORPUS)
    out = os.path.join(T, "o.txt")

    print("== 1 push: 決まった形で、書き写しあり -> 止まる")
    branch_with("hit", "# 設計\n- 「%s」と書いてある\n" % q)
    check("T01 git -C <絶対> push -u origin HEAD", P(), 2, cwd=T)
    rc, err = run(P(), T)
    results.append("ABCD" in err and "doc-hit.md:2" in err)
    print("%s %-62s" % ("PASS" if results[-1] else "FAIL", "T01b 止めた表示にファイル名と行番号と語句がある"))
    check("T02 --set-upstream", P(flags="--set-upstream "), 2, cwd=T)
    check("T03 -u なし", P(flags=""), 2, cwd=T)
    branch_with("hit2", "- 『%s』\n" % FAKE_QUOTE2)
    check("T04 『』の中も照らす", P(), 2, cwd=T)
    branch_with("other-branch", "- 「%s」\n" % q)
    branch_with("current-clean", "- 「%s」\n" % FAKE_NOT_IN_CORPUS)
    check("T05 今は別ブランチ: ブランチ名で送るのを照らす", P("other-branch"), 2, cwd=T)
    check("T06 存在しないブランチ名 -> 止まる", P("no-such-branch"), 2, cwd=T)
    sh("git", "checkout", "-q", "other-branch", cwd=WORK)
    check("T07 2>&1 つき", P() + " 2>&1", 2, cwd=T)
    check("T08 > <絶対> つき", P() + " > " + out, 2, cwd=T)
    check("T09 >> <絶対> 2>&1 つき", P() + " >> " + out + " 2>&1", 2, cwd=T)

    print("== 2 push: 通る")
    branch_with("clean", "- 「%s」\n" % FAKE_NOT_IN_CORPUS)
    check("T10 原文に無い語句 -> 通る", P(), 0, cwd=T)
    check("T10b 同 2>&1 / > file つき -> 通る", P() + " 2>&1 > " + out, 0, cwd=T)
    branch_with("outside", "- %s と「の外」に書いた\n" % q)
    check("T11 「」の外の書き写しは止めない", P(), 0, cwd=T)
    branch_with("short", "- 「%s」\n" % FAKE_SHORT)
    check("T12 4 文字未満は止めない", P(), 0, cwd=T)
    branch_with("digits", "- 「%s」\n" % FAKE_DIGITS)
    check("T13 数字と区切りだけは止めない", P(), 0, cwd=T)
    check("T14 関係ないコマンドは通る", "ls -la", 0)
    check("T14b git commit の文面に push の語があっても通る", 'git commit -m "fix: push の手順"', 0)
    check("T14c git status は通る", "git status", 0)
    check("T15 Bash 以外の道具は通る", P(), 0, tool="Edit")
    for name, qt, label in (("st", FAKE_STATUS, "状態の写し"), ("pr", FAKE_PRODUCT, "商品名の写し"),
                             ("al", FAKE_ALLOW, "一般語の表")):
        branch_with("excl-" + name, "- 「%s」\n" % qt)
        check("T16 除外表 (%s) にある語句は止めない" % label, P(), 0, cwd=T)

    print("== 3 表が無い・古い・壊れている -> 止まる")
    branch_with("hit", "- 「%s」\n" % q)
    make_tables(corpus_text="")
    check("T20 原文の置き場が空", P(), 2, cwd=T)
    make_tables()
    os.remove(os.path.join(D, "confidential-corpus.conf"))
    check("T21 置き場の表が無い", P(), 2, cwd=T)
    make_tables()
    write(os.path.join(D, "confidential-corpus.conf"), "repo: test/fake\n")
    check("T22 corpus: の行が無い", P(), 2, cwd=T)
    make_tables()
    write(os.path.join(D, "confidential-corpus.conf"), "repo: test/fake\ncorpus: %s/nothing/*.tsv\n" % D)
    check("T23 置き場の行に当たるファイルが無い", P(), 2, cwd=T)
    make_tables()
    os.remove(os.path.join(D, "product-names.txt"))
    check("T24 商品名の写しが無い", P(), 2, cwd=T)
    make_tables()
    branch_with("fresh", "- 「%s」\n" % FAKE_NOT_IN_CORPUS)
    cf = os.path.join(D, "raw", "msgs_1.tsv")
    old_t = time.time() - 3 * 86400
    os.utime(cf, (old_t, old_t))
    check("T25 写しが3日前 (上限2日) -> 止まる", P(), 2, cwd=T)
    rc, err = run(P(), T)
    results.append("古い" in err)
    print("%s %-62s" % ("PASS" if results[-1] else "FAIL", "T25b 止めた理由に「古い」がある"))
    check("T26 表に無い repo の push は写しが古くても通る", P(path=OTHER), 0, cwd=T)
    for v in ("100", "nan", "inf", "-5", "abc", "0"):
        r = env_run(P(), CONFID_CORPUS_MAX_AGE_DAYS=v)
        results.append(r.returncode == 2)
        print("%s %-62s exit=%d (期待 2)" % ("PASS" if results[-1] else "FAIL", "T27 上限の環境変数が %s でも2日のまま" % v, r.returncode))
    new_t = time.time() - 1 * 86400
    os.utime(cf, (new_t, new_t))
    check("T28 写しが1日前 -> 通る", P(), 0, cwd=T)
    make_tables()

    print("== 4 場所の条件")
    write(os.path.join(OTHER, "a.md"), "- 「%s」\n" % q)
    sh("git", "add", "-A", cwd=OTHER)
    sh("git", "commit", "-q", "-m", "x", cwd=OTHER)
    check("T30 表に無い repo の push は通る", P(path=OTHER), 0, cwd=T)
    write(os.path.join(NOMAIN, "a.md"), "x\n")
    sh("git", "add", "-A", cwd=NOMAIN)
    sh("git", "commit", "-q", "-m", "x", cwd=NOMAIN)
    check("T31 表にある repo で origin/main が無い -> 止まる", P(path=NOMAIN), 2, cwd=T)
    check("T32 パスが存在しない -> 止まる", P(path=os.path.join(T, "nonexistent")), 2, cwd=T)
    plain = os.path.join(T, "plain")
    os.makedirs(plain, exist_ok=True)
    check("T33 git の repo でないパス -> 止まる", P(path=plain), 2, cwd=T)

    print("== 5 決まりの外の push はすべて止まる (中身が clean でも)")
    branch_with("clean5", "- 「%s」\n" % FAKE_NOT_IN_CORPUS)
    sh("git", "checkout", "-q", "clean5", cwd=WORK)
    W = WORK
    bad = [
        ("cd <絶対> && git push", "cd %s && git push" % W),
        ("cd <絶対> && git push -u origin HEAD", "cd %s && git push -u origin HEAD" % W),
        ("git push (引数なし)", "git push"),
        ("git push origin HEAD (-C なし)", "git push origin HEAD"),
        ("git push origin HEAD 2>&1 | tail", "git push origin HEAD 2>&1 | tail"),
        ("git -C <絶対> push ... | tail", P() + " | tail -5"),
        ("git -C <相対> push", "git -C rel push -u origin HEAD"),
        ("git -C . push", "git -C . push -u origin HEAD"),
        ("--force-with-lease", P(flags="--force-with-lease -u ")),
        ("--force", P(flags="--force ")),
        ("-f", P(flags="-f ")),
        ("--no-verify", P(flags="--no-verify ")),
        ("-n", P(flags="-n ")),
        ("--mirror", P(flags="--mirror ")),
        ("--all", "git -C %s push --all origin" % W),
        ("--tags", P(flags="--tags ")),
        ("--delete", "git -C %s push --delete origin x" % W),
        ("origin :ref (削除)", "git -C %s push origin :x" % W),
        ("origin HEAD:refs/heads/x", P("HEAD:refs/heads/x")),
        ("origin +HEAD", P("+HEAD")),
        ("refs 2 つ", "git -C %s push origin HEAD main" % W),
        ("origin の後に ref なし", "git -C %s push origin" % W),
        ("remote が origin でない", "git -C %s push upstream HEAD" % W),
        ("ref が -で始まる", P("-x")),
        ("ref に ..", P("a..b")),
        ("GIT_DIR=… git push", "GIT_DIR=%s/.git git -C %s push -u origin HEAD" % (W, W)),
        ("GIT_DIR=… git push (-C なし)", "GIT_DIR=%s/.git git push origin hit" % W),
        ("export GIT_DIR=…; git push", "export GIT_DIR=%s/.git; git push origin hit" % W),
        ("env X=1 git -C", "env X=1 " + P()),
        ("絶対パスの git", "/usr/bin/git -C %s push -u origin HEAD" % W),
        ("git -c core.hooksPath", "git -c core.hooksPath=/x -C %s push -u origin HEAD" % W),
        ("--git-dir", "git --git-dir=%s/.git push origin HEAD" % W),
        ("; で続ける", P() + "; echo ok"),
        ("&& で続ける", P() + " && echo ok"),
        ("|| で続ける", P() + " || echo ng"),
        ("& で背景", P() + " &"),
        ("| で渡す", P() + " | cat"),
        ("改行で続ける", P() + "\necho ok"),
        ("前に別命令 (改行)", "echo ok\n" + P()),
        ("前に別命令 (&&)", "echo ok && " + P()),
        ("$ を含む パス", "git -C $W push -u origin HEAD"),
        ("二重引用符の $", 'git -C "$W" push -u origin HEAD'),
        ("バッククォート", "git -C `pwd` push -u origin HEAD"),
        ("$( )", "git -C $(pwd) push -u origin HEAD"),
        ("heredoc", P() + " <<EOF\nx\nEOF"),
        ("< で入力", P() + " < /dev/null"),
        ("> 相対", P() + " > o.txt"),
        ("&> ", P() + " &> " + out),
        ("bash -c", "bash -c '%s'" % P()),
        ("sh -c", 'sh -c "%s"' % P()),
        ("eval", "eval '%s'" % P()),
        ("xargs 風 (引用の中の git push)", "echo x | xargs -I{} %s" % P()),
        ("読めない (引用が閉じない)", "git -C %s push -u origin 'HEAD" % W),
        ("(subshell)", "(%s)" % P()),
        ("{ }", "{ %s; }" % P()),
    ]
    for nm, c in bad:
        rc, err = run(c, T)
        ok = rc == 2 and ("git -C <worktree の絶対パス> push -u origin <ブランチ>" in err or "決まりの外" in err or "止めました" in err)
        results.append(ok)
        print("%s %-62s exit=%d (期待 2)" % ("PASS" if ok else "FAIL", "T40 " + nm, rc))
    rc, err = run("cd %s && git push" % W, T)
    results.append("単独で流してください" in err)
    print("%s %-62s" % ("PASS" if results[-1] else "FAIL", "T40b 止めた理由に決まった形の案内がある"))

    print("== 6 審査 (PR #4743) が使った形: すべて止まる")
    C = "git commit"
    probes = [
        ("J1 heredoc の文に 'cd してから push を直す'", C + " -m \"$(cat <<'EOF'\nfix: 作業場所\n\ncd してから push を直す\nEOF\n)\" && git push -u origin HEAD"),
        ("G1 heredoc の行 'cd /tmp'", C + " -m \"$(cat <<'EOF'\nfix\ncd /tmp\nEOF\n)\" && git push"),
        ("G2 heredoc の行 'cd docs'", C + " -m \"$(cat <<'EOF'\nfix\ncd docs\nEOF\n)\" && git push"),
        ("G3 echo 'x; cd /tmp' && git push", "echo 'x; cd /tmp' && git push"),
        ("B1 cd ../nonexist; git push", "cd ../nonexist; git push"),
        ("B2 cd /nonexist ; git push", "cd /nonexist ; git push"),
        ("B3 cd -P . && git push", "cd -P . && git push"),
        ("B4 cd -- . && git push", "cd -- . && git push"),
        ("B5 cd -P <絶対> && git push", "cd -P %s && git push" % W),
        ("A1 (cd OTHER && true) && git push", "(cd %s && true) && git push" % OTHER),
        ("A3 (cd OTHER && ls) && git push", "(cd %s && ls) && git push" % OTHER),
        ("C2 GIT_DIR=… git push origin hit", "GIT_DIR=%s/.git git push origin hit" % W),
        ("C3 export GIT_DIR=…; git push origin hit", "export GIT_DIR=%s/.git; git push origin hit" % W),
        ("E7 gh 本文の heredoc 'cd $W; pushd x' && git push",
         "gh pr create --base main --body \"$(cat <<'EOF'\n手順: cd $W; pushd x\nEOF\n)\" && git push"),
        ("E8 echo 'use; pushd' && git push", "echo 'use; pushd' && git push"),
        ("H1 gh -b 'a <<b' 改行 gh -F file", "gh pr comment 1 -b 'use a <<b'\ngh pr comment 2 -F %s" % hitbody),
        ("D1 cd ../w2 && gh --body-file 相対", "cd ../w2 && gh pr create --base main --body-file body.md"),
        ("D2 cd \"$W\" && gh --body-file 相対", 'cd "$W" && gh pr create --base main --body-file body.md'),
        ("D3 cd ../w2 && gh --body \"$(cat body.md)\"", 'cd ../w2 && gh pr create --base main --body "$(cat body.md)"'),
        ("D4 cd ../w2 && gh -F - < body.md", "cd ../w2 && gh pr comment 1 -F - < body.md"),
        ("D5 cd ../w2 && gh --body-file 相対 (中身なし)", "cd ../w2 && gh pr create --base main --body-file body.md"),
        ("F13 cat file | gh -F /dev/stdin", "cat %s | gh pr comment 1 -F /dev/stdin" % cleanbody),
        ("F14 python3 x.py | gh --body-file /dev/stdin", "python3 x.py | gh pr comment 1 --body-file /dev/stdin"),
    ]
    for nm, c in probes:
        rc, err = run(c, T)
        results.append(rc == 2)
        print("%s %-62s exit=%d (期待 2)" % ("PASS" if rc == 2 else "FAIL", "P " + nm, rc))

    print("== 7 gh の本文: 決まった形だけ照らして通す")
    GHB = "gh pr create --base main --title t "
    check("G01 (a) --body-file <絶対> 書き写しあり -> 止まる", GHB + "--body-file " + hitbody, 2)
    check("G02 (a) -F <絶対> 書き写しあり -> 止まる", "gh pr comment 1 -F " + hitbody, 2)
    check("G03 (a) --body-file=<絶対> 書き写しあり -> 止まる", GHB + "--body-file=" + hitbody, 2)
    check("G04 (a) --body-file <絶対> 中身なし -> 通る", GHB + "--body-file " + cleanbody, 0)
    check("G05 (a) -F <絶対> 中身なし -> 通る", "gh issue comment 1 -F " + cleanbody, 0)
    check("G06 (b) --body '一重' 書き写しあり -> 止まる", GHB + "--body '「%s」'" % q, 2)
    check("G07 (b) -b '一重' 書き写しあり -> 止まる", "gh pr comment 1 -b '「%s」'" % q, 2)
    check("G08 (b) --body='一重' 書き写しあり -> 止まる", GHB + "--body='「%s」'" % q, 2)
    check("G09 (b) 複数行の一重 書き写しあり -> 止まる", GHB + "--body '概要\n- 「%s」\n'" % q, 2)
    check("G10 (b) --body '一重' 中身なし -> 通る", GHB + "--body '「%s」'" % FAKE_NOT_IN_CORPUS, 0)
    check("G11 (b) -b '一重' 中身なし -> 通る", "gh pr comment 1 -b 'ok'", 0)
    check("G12 (a) 後ろに 2>&1 / > <絶対> -> 通る", GHB + "--body-file " + cleanbody + " 2>&1 > " + out, 0)
    check("G13 本文なしの gh pr edit (ラベルだけ) -> 通る", "gh pr edit 1 --add-label x", 0)
    check("G14 gh pr view は対象外", "gh pr view 1 --json title", 0)
    check("G15 gh api は対象外", "gh api repos/a/b/pulls", 0)
    nb = [
        ("相対パス", GHB + "--body-file body.md"),
        ("相対パス -F", "gh pr comment 1 -F ./body.md"),
        ("標準入力 -", "gh pr comment 1 -F -"),
        ("--body-file -", "gh pr comment 1 --body-file -"),
        ("/dev/stdin", "gh pr comment 1 -F /dev/stdin"),
        ("/dev/fd/63", "gh pr comment 1 --body-file /dev/fd/63"),
        ("/dev/null", "gh pr comment 1 --body-file /dev/null"),
        ("存在しないファイル", "gh pr create --base main --body-file %s/none.md" % T),
        ("存在しないファイル -F", "gh pr comment 1 -F %s/none.md" % T),
        ("heredoc で -F -", "gh pr comment 1 -F - <<'EOF'\nok\nEOF"),
        ("here-string", "gh pr comment 1 -F - <<< ok"),
        ("< で入力", "gh pr comment 1 -F - < " + cleanbody),
        ("$(cat file)", 'gh pr comment 1 --body "$(cat %s)"' % cleanbody),
        ("heredoc 入りの --body", "gh pr comment 1 --body \"$(cat <<'EOF'\nok\nEOF\n)\""),
        ("二重引用符", 'gh pr comment 1 --body "ok"'),
        ("二重引用符 --body=", 'gh pr create --base main --title t --body="ok"'),
        ("$ を含む", "gh pr comment 1 --body $B"),
        ("バッククォート", "gh pr comment 1 --body `date`"),
        ("引用なしの本文", "gh pr comment 1 --body ok"),
        ("一重+二重の連結", "gh pr comment 1 --body 'a'\"b\""),
        ("--fill", "gh pr create --fill"),
        ("--fill-first", "gh pr create --fill-first"),
        ("--fill-verbose", "gh pr create --fill-verbose"),
        ("--editor", "gh pr create --editor"),
        ("-e", "gh pr create -e"),
        ("--web", "gh pr create --web"),
        ("--template", "gh pr create --template t.md"),
        ("--recover", "gh pr create --recover x"),
        ("本文 2 つ", "gh pr comment 1 -b 'a' -F " + cleanbody),
        ("短い指定の束ね -dF", "gh pr create --base main -dF " + cleanbody),
        ("短い指定の束ね -bX", "gh pr comment 1 -b'ok'"),
        ("パイプ", "cat %s | gh pr comment 1 -F %s" % (hitbody, cleanbody)),
        ("&& で続ける", "gh pr comment 1 -b 'a' && gh pr comment 2 -F " + hitbody),
        ("; で続ける", "gh pr comment 1 -b 'a'; gh pr comment 2 -b 'b'"),
        ("改行で続ける", "gh pr view 1\ngh pr comment 2 -F " + hitbody),
        ("cd で始める", "cd %s && gh pr comment 1 -F %s" % (T, cleanbody)),
        ("絶対パスの gh", "/opt/homebrew/bin/gh pr comment 1 -F " + cleanbody),
        ("command gh", "command gh pr comment 1 -F " + cleanbody),
        ("bash -c", "bash -c 'gh pr comment 1 -F %s'" % cleanbody),
        ("env X=1 gh", "env X=1 gh pr comment 1 -F " + cleanbody),
        ("VAR=1 gh", "X=1 gh pr comment 1 -F " + cleanbody),
        ("push と gh の同居", P() + " && gh pr comment 1 -F " + cleanbody),
    ]
    for nm, c in nb:
        rc, err = run(c, T)
        ok = rc == 2 and ("止めました" in err)
        results.append(ok)
        print("%s %-62s exit=%d (期待 2)" % ("PASS" if ok else "FAIL", "G20 " + nm, rc))
    rc, err = run("gh pr comment 1 -F -", T)
    results.append("--body-file <絶対パス>" in err and "Write" in err)
    print("%s %-62s" % ("PASS" if results[-1] else "FAIL", "G21 止めた理由に Write と --body-file の案内がある"))

    print("== 9 審査 6 回目の指摘 (gh review の印・題名・途中の commit・差分の取り方・別名)")
    for nm, fl in (("-r", "-r"), ("-a", "-a"), ("-c", "-c"), ("--request-changes", "--request-changes"), ("--approve", "--approve")):
        check("R01 gh pr review %s -b 書き写しあり -> 止まる" % nm, "gh pr review 1 %s -b '「%s」'" % (fl, q), 2)
        check("R02 gh pr review %s -F 書き写しあり -> 止まる" % nm, "gh pr review 1 %s -F %s" % (fl, hitbody), 2)
        check("R03 gh pr review %s -b 中身なし -> 通る" % nm, "gh pr review 1 %s -b 'ok'" % fl, 0)
    check("R04 gh pr create -a x -r y -b 書き写しあり -> 止まる", "gh pr create -a x -r y -b '「%s」'" % q, 2)
    check("R05 gh pr create --title t -r --body-file 書き写しあり -> 止まる", "gh pr create --title t -r --body-file " + hitbody, 2)
    check("R06 gh pr create -f -> 止まる", "gh pr create -f", 2)
    check("R06b gh issue create -f -> 止まる", "gh issue create -f", 2)
    qt = "「%s」" % q
    check("R10 pr create --title 書き写しあり -> 止まる", "gh pr create --title '%s' --body 'x'" % qt, 2)
    check("R11 issue create -t 書き写しあり -> 止まる", "gh issue create -t '%s' -b 'x'" % qt, 2)
    check("R12 pr edit --title 書き写しあり (本文なし) -> 止まる", "gh pr edit 1 --title '%s'" % qt, 2)
    check("R13 pr edit --title=… 書き写しあり -> 止まる", "gh pr edit 1 --title='%s'" % qt, 2)
    check("R14 題名が中身なし -> 通る", "gh pr edit 1 --title '「%s」' -b 'x'" % FAKE_NOT_IN_CORPUS, 0)
    check("R15 pr edit --title 二重引用符 書き写しあり -> 止まる", 'gh pr edit 1 --title "%s"' % qt, 2)
    for nm, c in (("git の \\ 逃げ", "g\\it -C %s push -u origin hit" % W),
                  ("push の \"\" 割り", "git -C %s pus\"\"h -u origin hit" % W),
                  ("git の '' 割り", "'gi't -C %s push -u origin hit" % W),
                  ("gh の \\ 逃げ", "g\\h pr comment 1 -F " + hitbody),
                  ("pr の '' 割り", "gh p''r comment 1 -F " + hitbody),
                  ("字句に分けられない + git", "git -C %s push -u origin 'HEAD" % W),
                  ("字句に分けられない + gh", "gh pr comment 1 -b 'x")):
        rc, err = run(c, T)
        results.append(rc == 2)
        print("%s %-62s exit=%d (期待 2)" % ("PASS" if rc == 2 else "FAIL", "R20 " + nm, rc))
    check("R21 字句に分けられず git も gh も無い -> 通る", "echo 'x", 0)

    def commit_all(msg):
        sh("git", "add", "-A", cwd=WORK)
        sh("git", "commit", "-q", "-m", msg, cwd=WORK)

    # 途中の commit
    sh("git", "checkout", "-q", "-B", "hist", "origin/main", cwd=WORK)
    write(os.path.join(WORK, "hist.md"), "- 「%s」\n" % q)
    commit_all("add")
    write(os.path.join(WORK, "hist.md"), "消した\n")
    commit_all("remove")
    rc, err = check("R30 足して消す 2 つの commit -> 止まる", P("hist"), 2, cwd=T)
    results.append("書き直し" in err and "履歴に残って" in err)
    print("%s %-62s" % ("PASS" if results[-1] else "FAIL", "R30b 止めた理由に履歴と書き直しの案内がある"))
    # origin/main へ書き写し入りの commit を進め、それを取り込んだだけのブランチ
    sh("git", "checkout", "-q", "-B", "mrg", "origin/main", cwd=WORK)
    write(os.path.join(WORK, "mrg.md"), "- 「%s」\n" % FAKE_NOT_IN_CORPUS)
    commit_all("mrg")
    sh("git", "checkout", "-q", "-B", "adv", "origin/main", cwd=WORK)
    write(os.path.join(WORK, "shared.md"), "base line\n")
    write(os.path.join(WORK, "main-side.md"), "- 「%s」\n" % q)
    commit_all("adv1")
    sh("git", "push", "-q", "origin", "adv:main", cwd=WORK)
    sh("git", "fetch", "-q", "origin", cwd=WORK)
    sh("git", "checkout", "-q", "mrg", cwd=WORK)
    sh("git", "merge", "-q", "--no-edit", "origin/main", cwd=WORK)
    check("R31 origin/main を merge commit で取り込んだだけ (main 側に書き写し) -> 通る", P("mrg"), 0, cwd=T)
    # 衝突を直した行
    sh("git", "checkout", "-q", "-B", "cx", "origin/main", cwd=WORK)
    write(os.path.join(WORK, "shared.md"), "cx line\n")
    commit_all("cx")
    sh("git", "checkout", "-q", "-B", "adv", "origin/main", cwd=WORK)
    write(os.path.join(WORK, "shared.md"), "main line\n")
    commit_all("adv2")
    sh("git", "push", "-q", "origin", "adv:main", cwd=WORK)
    sh("git", "fetch", "-q", "origin", cwd=WORK)
    sh("git", "checkout", "-q", "cx", cwd=WORK)
    subprocess.run(["git", "merge", "--no-edit", "origin/main"], cwd=WORK, capture_output=True, text=True)
    write(os.path.join(WORK, "shared.md"), "- 「%s」\n" % q)
    commit_all("resolve")
    check("R32 merge の衝突を直した行に書き写し -> 止まる", P("cx"), 2, cwd=T)

    # 差分の取り方
    def one(name, files):
        sh("git", "checkout", "-q", "-B", name, "origin/main", cwd=WORK)
        for fn, txt in files.items():
            write(os.path.join(WORK, fn), txt)
        commit_all(name)
    line = "引用「%s」\n" % q
    one("bin", {".gitattributes": "*.txt binary\n", "note.txt": line})
    check("R40 .gitattributes binary -> 止まる", P("bin"), 2, cwd=T)
    one("nodiff", {".gitattributes": "*.md -diff\n", "x.md": line})
    check("R41 .gitattributes -diff -> 止まる", P("nodiff"), 2, cwd=T)
    one("nul", {"n.dat": "a\0b\n" + line})
    check("R42 NUL を含むファイル -> 止まる", P("nul"), 2, cwd=T)
    one("pref", {"pref.md": line})
    for k in ("diff.noprefix", "diff.mnemonicPrefix"):
        sh("git", "config", k, "true", cwd=WORK)
        check("R43 %s=true でも -> 止まる" % k, P("pref"), 2, cwd=T)
        sh("git", "config", "--unset", k, cwd=WORK)
    one("fname", {"「%s」.md" % q: "x\n"})
    check("R44 ファイル名に書き写し -> 止まる", P("fname"), 2, cwd=T)
    sh("git", "checkout", "-q", "-B", "ren", "origin/main", cwd=WORK)
    sh("git", "mv", "shared.md", "「%s」.md" % q, cwd=WORK)
    commit_all("ren")
    check("R45 改名だけ (中身は同じ) でも名前に書き写し -> 止まる", P("ren"), 2, cwd=T)
    one("fclean", {"clean-name.md": "- 「%s」\n" % FAKE_NOT_IN_CORPUS})
    check("R46 clean な名前と中身 -> 通る", P("fclean"), 0, cwd=T)

    # 別名・push 先の差し替え
    cfgs = (("alias.sy", "push"), ("remote.origin.pushurl", "/nonexistent/x.git"), ("url./nonexistent/.pushInsteadOf", "https://example.invalid/"))
    for k, v in cfgs:
        sh("git", "config", k, v, cwd=WORK)
        check("R50 repo の設定に %s があると -> 止まる" % k, P("fclean"), 2, cwd=T)
        sh("git", "config", "--unset", k, cwd=WORK)
    check("R51 設定を戻すと -> 通る", P("fclean"), 0, cwd=T)
    for nm, c in (("git config alias.sy push", "git config alias.sy push"),
                  ("git -C W config alias.sy push", "git -C %s config alias.sy push" % W),
                  ("git config alias.sy pu\\sh", "git config alias.sy pu\\sh"),
                  ("git config remote.origin.pushurl x", "git config remote.origin.pushurl /x"),
                  ("git config url.x.pushInsteadOf y", "git config url./x/.pushInsteadOf y"),
                  ("git remote set-url --push origin x", "git remote set-url --push origin /x"),
                  ("git -c alias.sy=push", "git -c alias.sy=push -C %s sy origin HEAD" % W)):
        rc, err = run(c, T)
        results.append(rc == 2)
        print("%s %-62s exit=%d (期待 2)" % ("PASS" if rc == 2 else "FAIL", "R52 " + nm, rc))
    check("R53 git config user.name x は通る", "git config user.name x", 0)
    check("R54 git remote -v は通る", "git remote -v", 0)

    print("== 8 止めた記録")
    open(EV, "w").close()
    check("T50 記録を取るため 1 回止める", "gh pr comment 1 -b '「%s」'" % q, 2)
    with open(EV, encoding="utf-8") as f:
        lines = [l for l in f.read().split("\n") if l]
    last = json.loads(lines[-1]) if lines else {}
    ok = (last.get("hook") == "confidential-quote-guard" and last.get("ts") and "1 件" in last.get("reason", "")
          and "ABCD" not in lines[-1] and "つくり語句" not in lines[-1])
    results.append(bool(ok))
    print("%s %-62s" % ("PASS" if ok else "FAIL", "T51 記録の最後の行に見張りの名前・日時・件数があり、語句が無い"))
    r = subprocess.run([sys.executable, GUARD, "--check"], capture_output=True, text=True,
                       env=dict(os.environ, CONFID_GUARD_DIR=D))
    results.append(r.returncode == 0 and r.stdout.startswith("OK") and "ABCD" not in r.stdout)
    print("%s %-62s" % ("PASS" if results[-1] else "FAIL", "T53 --check の表示は件数だけ (語句なし)"))

    n_ok = sum(1 for x in results if x)
    n_ng = len(results) - n_ok
    print("PASS %d / FAIL %d" % (n_ok, n_ng))
    return 1 if n_ng else 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        shutil.rmtree(T, ignore_errors=True)
    sys.exit(rc)
