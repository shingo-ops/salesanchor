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


def main():
    setup_repos()
    make_tables()
    body = os.path.join(T, "body.md")
    stdin_hit = os.path.join(T, "stdin-hit.md")
    write(body, "確認します。「%s」\n" % FAKE_QUOTE)
    write(stdin_hit, "「%s」\n" % FAKE_QUOTE)

    print("== 1 止まる (K1 に当たる試し)")
    branch_with("hit", "# 設計\n- 「%s」と書いてある\n" % FAKE_QUOTE)
    check("T01 push: 「」に原文の語句 -> 止まる", "git push origin HEAD", 2)
    rc, err = run("git push origin HEAD")
    results.append("ABCD" in err and "doc-hit.md:2" in err)
    print("%s %-62s" % ("PASS" if results[-1] else "FAIL", "T01b 止めた表示にファイル名と行番号と語句がある"))
    check("T02 push: 引数なしの git push も照らす", "git push", 2)
    check("T03 push: cd <絶対パス> && git push", "cd %s && git push -u origin HEAD" % WORK, 2, cwd=T)
    branch_with("hit2", "- 『%s』\n" % FAKE_QUOTE2)
    check("T04 push: 『』の中も照らす", "git push origin HEAD", 2)

    print("== 2 通る (K2 に当たる試し)")
    branch_with("clean", "- 「%s」\n" % FAKE_NOT_IN_CORPUS)
    check("T05 push: 原文に無い語句 -> 通る", "git push origin HEAD", 0)
    branch_with("outside", "- %s と「の外」に書いた\n" % FAKE_QUOTE)
    check("T06 push: 「」の外の書き写しは止めない (数えるだけ)", "git push origin HEAD", 0)
    branch_with("short", "- 「%s」\n" % FAKE_SHORT)
    check("T07 push: 4 文字未満は止めない", "git push origin HEAD", 0)
    branch_with("digits", "- 「%s」\n" % FAKE_DIGITS)
    check("T08 push: 数字と区切りだけは止めない", "git push origin HEAD", 0)
    check("T09 push: 関係ないコマンドは通る", "ls -la", 0)
    check("T10 Bash 以外の道具は通る", "git push origin HEAD", 0, tool="Edit")
    check("T10b push --delete は見るものが無く通る", "git push origin --delete hit", 0)

    print("== 3 除外表")
    for name, q, label in (("st", FAKE_STATUS, "状態の写し"), ("pr", FAKE_PRODUCT, "商品名の写し"),
                            ("al", FAKE_ALLOW, "一般語の表")):
        branch_with("excl-" + name, "- 「%s」\n" % q)
        check("T11 除外表 (%s) にある語句は止めない" % label, "git push origin HEAD", 0)

    print("== 4 置き場なし -> 止まる")
    branch_with("hit", "- 「%s」\n" % FAKE_QUOTE)
    make_tables(corpus_text="")
    check("T12 原文の置き場が空 -> 止まる", "git push origin HEAD", 2)
    make_tables()
    os.remove(os.path.join(D, "confidential-corpus.conf"))
    check("T13 置き場の表が無い -> 止まる", "git push origin HEAD", 2)
    make_tables()
    write(os.path.join(D, "confidential-corpus.conf"), "repo: test/fake\n")
    check("T14 置き場の表に corpus: の行が無い -> 止まる", "git push origin HEAD", 2)
    make_tables()
    write(os.path.join(D, "confidential-corpus.conf"), "repo: test/fake\ncorpus: %s/nothing/*.tsv\n" % D)
    check("T15 置き場の行に当たるファイルが無い -> 止まる", "git push origin HEAD", 2)
    make_tables()
    os.remove(os.path.join(D, "product-names.txt"))
    check("T16 商品名の写しが無い -> 止まる", "git push origin HEAD", 2)
    make_tables()
    branch_with("fresh", "- 「%s」\n" % FAKE_NOT_IN_CORPUS)
    cf = os.path.join(D, "raw", "msgs_1.tsv")
    old_t = time.time() - 3 * 86400
    os.utime(cf, (old_t, old_t))
    check("T16b 原文の写しが3日前 (上限2日) -> 止まる", "git push origin HEAD", 2)
    rc, err = run("git push origin HEAD")
    results.append("古い" in err)
    print("%s %-62s" % ("PASS" if results[-1] else "FAIL", "T16c 止めた理由に「古い」がある"))
    new_t = time.time() - 1 * 86400
    os.utime(cf, (new_t, new_t))
    check("T16d 原文の写しが1日前 -> 通る", "git push origin HEAD", 0)
    make_tables()

    print("== 4b push の書き出し先・くっつけ書き・古さの扱い (REVISE 2)")
    branch_with("hit3", "- 「%s」\n" % FAKE_QUOTE)
    out = os.path.join(T, "o.txt")
    check("T16e push > file 2>&1 (書き写しあり) -> 止まる", "git push origin HEAD > %s 2>&1" % out, 2)
    check("T16f push 2>&1 | tail (書き写しあり) -> 止まる", "git push origin HEAD 2>&1 | tail -5", 2)
    check("T16g push 2>/dev/null (書き写しあり) -> 止まる", "git push 2>/dev/null", 2)
    check("T16h push && echo ok (書き写しあり) -> 止まる", "git push origin HEAD && echo ok", 2)
    branch_with("clean3", "- 「%s」\n" % FAKE_NOT_IN_CORPUS)
    check("T16i push > file 2>&1 (中身なし) -> 通る", "git push origin HEAD > %s 2>&1" % out, 0)
    check("T16j push 2>&1 | tail (中身なし) -> 通る", "git push origin HEAD 2>&1 | tail -5", 0)
    check("T16k push 2>/dev/null (中身なし) -> 通る", "git push 2>/dev/null", 0)
    check("T16l push &> file (中身なし) -> 通る", "git push origin HEAD &> %s" % out, 0)
    check("T16m gh pr create -b<値> (書き写しあり) -> 止まる", "gh pr create --base main -b'「%s」'" % FAKE_QUOTE, 2)
    check("T16n gh pr create -F<ファイル> (書き写しあり) -> 止まる", "gh pr create --base main -F%s" % os.path.join(T, "body.md"), 2)
    check("T16o gh pr create -F- (heredoc, 書き写しあり) -> 止まる", "gh pr create --base main -F- <<'EOF'\n「%s」\nEOF" % FAKE_QUOTE, 2)
    check("T16p gh pr create -b<値> (中身なし) -> 通る", "gh pr create --base main -b'「%s」'" % FAKE_NOT_IN_CORPUS, 0)
    os.utime(cf, (old_t, old_t))
    check("T16q 表に無い repo の push は写しが古くても通る", "git push origin HEAD", 0, cwd=OTHER)
    check("T16r 照らす repo の push は写しが古ければ止まる", "git push origin HEAD", 2)
    env = dict(os.environ, CONFID_GUARD_DIR=D, CONFID_GUARD_EVENTS=EV, PYTHONDONTWRITEBYTECODE="1", CONFID_CORPUS_MAX_AGE_DAYS="100")
    r = subprocess.run([sys.executable, GUARD], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push origin HEAD"}, "cwd": WORK}),
                       capture_output=True, text=True, env=env)
    results.append(r.returncode == 2)
    print("%s %-62s exit=%d (期待 2)" % ("PASS" if results[-1] else "FAIL", "T16s 環境変数で上限を延ばしても2日のまま -> 止まる", r.returncode))
    make_tables()

    print("== 5 表に無い repo / 差分が取れない")
    write(os.path.join(OTHER, "a.md"), "- 「%s」\n" % FAKE_QUOTE)
    sh("git", "add", "-A", cwd=OTHER)
    sh("git", "commit", "-q", "-m", "x", cwd=OTHER)
    check("T17 表に無い repo の push は通る", "git push origin HEAD", 0, cwd=OTHER)
    write(os.path.join(NOMAIN, "a.md"), "x\n")
    sh("git", "add", "-A", cwd=NOMAIN)
    sh("git", "commit", "-q", "-m", "x", cwd=NOMAIN)
    check("T18 表にある repo で origin/main が無い -> 止まる", "git push origin HEAD", 2, cwd=NOMAIN)

    print("== 6 別のブランチを送る")
    branch_with("other-branch", "- 「%s」\n" % FAKE_QUOTE)
    branch_with("current-clean", "- 「%s」\n" % FAKE_NOT_IN_CORPUS)
    check("T19 今は別ブランチにいて git push origin <別ブランチ> -> 止まる", "git push origin other-branch", 2)
    check("T19b 存在しないブランチ名 -> 止まる", "git push origin no-such-branch", 2)
    check("T19c refspec src:dst の src を照らす", "git push origin other-branch:release/x", 2)
    check("T19d git push --all は決まらず止まる", "git push --all", 2)

    print("== 7 コメントの本文 (7 通り + 変数)")
    q = FAKE_QUOTE
    check("T20 gh pr comment --body", 'gh pr comment 1 --body "「%s」"' % q, 2)
    check("T21 gh pr comment -b", "gh pr comment 1 -b '「%s」'" % q, 2)
    check("T22 gh pr review -F <file>", "gh pr review 1 --comment -F %s" % body, 2)
    check("T23 gh issue comment -F - (heredoc)", "gh issue comment 1 -F - <<'EOF'\n「%s」\nEOF" % q, 2)
    check("T24 gh pr create --body=…", 'gh pr create --base main --title t --body="「%s」"' % q, 2)
    check("T25 gh pr comment -F - < <file>", "gh pr comment 1 -F - < %s" % stdin_hit, 2)
    check("T26 gh pr comment --body \"$(cat <file>)\"", 'gh pr comment 1 --body "$(cat %s)"' % stdin_hit, 2)
    check("T27 gh pr comment --body \"$VAR\" -> 止まる", 'gh pr comment 1 --body "$VAR"', 2)
    check("T28 gh pr create --body-file <file>", "gh pr create --base main --body-file %s" % body, 2)
    check("T29 cat <file> | gh pr comment -F -", "cat %s | gh pr comment 1 -F -" % stdin_hit, 2)
    check("T30 gh pr comment --body-file - に別コマンドの出力 -> 止まる", "somecmd | gh pr comment 1 --body-file -", 2)
    check("T31 gh pr edit --body に heredoc の $(cat <<EOF)",
          "gh pr edit 1 --body \"$(cat <<'EOF'\n「%s」\nEOF\n)\"" % q, 2)
    check("T32 gh pr comment: 原文に無い語句なら通る", 'gh pr comment 1 --body "「%s」"' % FAKE_NOT_IN_CORPUS, 0)
    check("T33 gh pr comment: 本文に < を含んでも通る", 'gh pr comment 1 --body "<details>ok</details>"', 0)
    check("T34 gh issue create: 原文に無い語句なら通る", "gh issue create --title t --body 'ok'", 0)
    check("T35 gh pr view は対象外", 'gh pr view 1 --json title', 0)

    print("== 8 本文のファイルが読めない")
    check("T40 --body-file 存在しないファイル -> 止まる", "gh pr create --base main --body-file %s/none.md" % T, 2)
    check("T41 -F 存在しないファイル -> 止まる", "gh pr comment 1 -F %s/none.md" % T, 2)

    print("== 10 審査 (PR #4743) の指摘 F1〜F4 の試し P1〜P24")

    def br(name, files):
        sh("git", "checkout", "-q", "-B", name, "origin/main", cwd=WORK)
        for fn, t in files.items():
            write(os.path.join(WORK, fn), t)
        sh("git", "add", "-A", cwd=WORK)
        sh("git", "commit", "-q", "-m", name, cwd=WORK)

    qq = "「%s」\n" % FAKE_QUOTE
    br("jp", {"日本語の書類.md": "- " + qq})
    check("P1 push: 日本語ファイル名の追加行", "git push origin jp", 2)
    br("pp", {"a.md": "++ x\n- " + qq})
    check("P2 push: 追加行が '++ ' で始まった後の行", "git push origin pp", 2)
    br("hitb", {"h.md": qq})
    br("cleanb", {"c.md": "ok\n"})
    check("P3 push 2回: 1回目 clean, 2回目 hit", "git push origin cleanb && git push origin hitb", 2)
    check("P4 gh 2回: 2回目が -F file", "gh pr comment 1 -b ok && gh pr comment 2 -F %s" % body, 2)
    check("P5 echo \"$VAR\" | gh pr comment -F -", 'echo "$VAR" | gh pr comment 1 -F -', 2)
    check("P6 gh pr comment -F - <<EOF に $BODY", "gh pr comment 1 -F - <<EOF\n$BODY\nEOF", 2)
    check("P7 gh pr comment -F - <<< \"$B\"", 'gh pr comment 1 -F - <<< "$B"', 2)
    check("P8 絶対パスの gh で -F file", "/opt/homebrew/bin/gh pr comment 1 -F %s" % body, 2)
    check("P9 echo hi; python3 x.py | gh -F -", "echo hi; python3 x.py | gh pr comment 1 -F -", 2)
    check("P10 --body \"$(cat file)\"", 'gh pr comment 1 --body "$(cat %s)"' % body, 2)
    check("P11 env X=1 git push origin hitb", "env GIT_X=1 git push origin hitb", 2)
    check("P12 command gh -F file", "command gh pr comment 1 -F %s" % body, 2)
    check("P15 gh pr create --body=\"$X\"", 'gh pr create --body="$X"', 2)
    check("P17 git -C <work> push origin hitb", "git -C %s push origin hitb" % WORK, 2, cwd=T)
    check("P18 bash -c 'git push origin hitb'", "bash -c 'git push origin hitb'", 2)
    check("P19 改行で区切った 2 つ目の gh -F", "gh pr view 1\ngh pr comment 2 -F %s" % body, 2)
    check("P20 gh pr view 1 && gh pr comment 2 -F file", "gh pr view 1 && gh pr comment 2 -F %s" % body, 2)
    check("P21 git push origin hitb:refs/heads/x", "git push origin hitb:refs/heads/x", 2)
    check("P22 git push origin cleanb hitb", "git push origin cleanb hitb", 2)
    check("P23 git push origin --delete foo (削除だけ)", "git push origin --delete foo", 0)
    check("P24 git push --delete origin foo", "git push --delete origin foo", 0)
    check("P25 bash -c 'gh pr comment ... -F file' -> 止まる", "bash -c 'gh pr comment 1 -F %s'" % body, 2)
    check("P26 引用符つき heredoc の $ は本文として通る", "gh pr comment 1 -F - <<'EOF'\n$BODY ok\nEOF", 0)
    check("P27 echo の平文 | gh -F - は通る", "echo 'ok text' | gh pr comment 1 -F -", 0)
    check("P28 絶対パスの gh の原文に無い語句は通る", '/opt/homebrew/bin/gh pr comment 1 --body "「%s」"' % FAKE_NOT_IN_CORPUS, 0)

    print("== 9 止めた記録")
    open(EV, "w").close()
    check("T50 記録を取るため 1 回止める", 'gh pr comment 1 --body "「%s」"' % q, 2)
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
