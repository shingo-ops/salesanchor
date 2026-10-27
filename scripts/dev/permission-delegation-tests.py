#!/usr/bin/env python3
"""permission-delegation-tests.py - ADR-1034（Opus の権限の足し引きと台帳）の受け入れ試験 A1〜A14・A17・A18。

すべて一時ディレクトリの home・本店・GitHub 役の bare リポジトリ・一時の clone で行う。
本物の ~/.claude と ~/.salesanchor-tools には触らない。
使い方: python3 -I -B scripts/dev/permission-delegation-tests.py
（A15・A16 は反映後に Opus が実機で確かめる項目で、この試験には含めない）
"""
import contextlib
import datetime
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 19, 0, 0, 0, tzinfo=UTC)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


audit = load("consent_audit_t", os.path.join(HERE, "consent-audit.py"))
pc = load("perm_change_t", os.path.join(HERE, "perm-change.py"))

PASS = FAIL = 0


def chk(tid, desc, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
    print("%s %-8s %s" % ("PASS" if cond else "FAIL", tid, desc), flush=True)


def td(sec=0, **kw):
    return datetime.timedelta(seconds=sec, **kw)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sha_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def git(cwd, *args):
    r = subprocess.run(["git", "-C", cwd, "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        "-c", "commit.gpgsign=false"] + list(args), capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("git %s: %s" % (args, r.stderr.decode("utf-8", "replace")))
    return r.stdout.decode("utf-8", "replace").strip()


class Flags:
    def __init__(self, isolated=1, dont_write_bytecode=1):
        self.isolated = isolated
        self.dont_write_bytecode = dont_write_bytecode


class Env:
    """一時の home・本店・（必要なら）GitHub 役の bare と ~/.salesanchor-tools 役の clone。"""

    def __init__(self, tmp, name, with_git=False):
        self.root = os.path.join(tmp, name)
        self.home = os.path.join(self.root, "home")
        self.claude = os.path.join(self.home, ".claude")
        self.settings = os.path.join(self.claude, "settings.json")
        self.settings_local = os.path.join(self.claude, "settings.local.json")
        self.repo_local = os.path.join(self.home, "salesanchor", ".claude", "settings.local.json")
        self.tools = os.path.join(self.home, ".salesanchor-tools")
        self.tools_settings = os.path.join(self.tools, ".claude", "settings.json")
        self.tools_self = os.path.join(self.tools, "scripts", "dev", "perm-change.py")
        self.events = os.path.join(self.claude, "logs", "agent-events.jsonl")
        self.ledger = os.path.join(self.claude, "logs", "permission-changes.jsonl")
        self.consent_ledger = os.path.join(self.claude, "logs", "consent-used.jsonl")
        self.snapshot = os.path.join(self.claude, "logs", "permission-snapshot.json")
        self.reexec_calls = 0
        os.makedirs(os.path.join(self.claude, "logs"))
        os.makedirs(os.path.join(self.claude, "scripts"))
        write_json(self.settings, {
            "permissions": {"allow": ["Bash(echo hi:*)"], "deny": [], "ask": []},
            "autoMode": {"allow": ["Benign sentence one.", "SM-1 weekly sentence"], "soft_deny": [], "environment": []},
            "hooks": {},
        })
        write_json(self.repo_local, {"permissions": {"allow": []}})
        with open(os.path.join(self.claude, "scripts", "base.sh"), "w") as f:
            f.write("#!/bin/bash\n")
        self.origin = None
        if with_git:
            self.bare = os.path.join(self.root, "github.git")
            self.seed = os.path.join(self.root, "seed")
            subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.bare], check=True)
            subprocess.run(["git", "init", "-q", "-b", "main", self.seed], check=True)
            os.makedirs(os.path.join(self.seed, "scripts", "dev"))
            os.makedirs(os.path.join(self.seed, ".claude"))
            for n in ("perm-change.py", "consent-audit.py"):
                shutil.copy(os.path.join(HERE, n), os.path.join(self.seed, "scripts", "dev", n))
            write_json(os.path.join(self.seed, ".claude", "settings.json"), {"permissions": {"allow": ["Bash(echo seed:*)"]}})
            git(self.seed, "add", "-A")
            git(self.seed, "commit", "-q", "-m", "init")
            git(self.seed, "remote", "add", "origin", self.bare)
            git(self.seed, "push", "-q", "origin", "main")
            subprocess.run(["git", "clone", "-q", self.bare, self.tools], check=True)
            self.origin = self.bare

    def advance(self, name="note.txt", text="x"):
        """GitHub 側の main を1つ進める。"""
        with open(os.path.join(self.seed, name), "a") as f:
            f.write(text + "\n")
        git(self.seed, "add", "-A")
        git(self.seed, "commit", "-q", "-m", "advance")
        git(self.seed, "push", "-q", "origin", "main")
        return git(self.seed, "rev-parse", "HEAD")

    def v(self):
        return git(self.bare, "rev-parse", "refs/heads/main")

    def head(self):
        return git(self.tools, "rev-parse", "HEAD")


def run_pc(env, argv, now=T0, flags=None, self_path=None, origin_url=None, git_run=None, reexec=None, env_vars=None):
    """perm-change.py の main を呼ぶ。返り値: (終了コード, 標準出力, 標準エラー)。"""
    out, err = io.StringIO(), io.StringIO()

    def default_reexec(a, sp):
        env.reexec_calls += 1
        return pc.main(a, home=env.home, now=now, origin_url=origin_url or env.origin, flags=flags or Flags(),
                       self_path=self_path or env.tools_self, env={pc.REEXEC_ENV: "1"}, git_run=git_run,
                       reexec=lambda *x: 99)

    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = pc.main(argv, home=env.home, now=now, origin_url=origin_url or env.origin,
                       flags=flags or Flags(), self_path=self_path or env.tools_self,
                       env=env_vars if env_vars is not None else {}, git_run=git_run,
                       reexec=reexec or default_reexec)
    return code, out.getvalue(), err.getvalue()


def apply_argv(target, op, item, intent="i", reason="r", expected="e", days=None):
    a = ["apply", "--target", target, "--op", op, "--item", item, "--intent", intent, "--reason", reason,
         "--expected", expected]
    if days is not None:
        a += ["--review-days", str(days)]
    return a


def ledger_rows(env):
    return audit.read_ledger(env.home)["rows"]


def ledger_n(env):
    return audit.read_ledger(env.home)["lines_n"]


def run_audit(env, now, commit=False, gh=None, git_run=None, permissions=True):
    lines = []
    audit.run_audit(env.home, now, permissions, lines.append, commit, gh, git_run)
    return lines


def reasons(lines):
    return [x for x in lines if x.startswith("ABNORMAL_REASON=")]


def seed_row(env, now, **kw):
    f = dict(actor="opus", sub="apply", target="user-allow", op="add", item_hash="00000000", summary="s",
             intent="i", reason="r", expected="e", review_by="", category="normal", result="applied", po_ref="")
    f.update(kw)
    row = pc.make_row(now, f["actor"], f["sub"], f["target"], f["op"], f["item_hash"], f["summary"], f["intent"],
                      f["reason"], f["expected"], f["review_by"], f["category"], f["result"], f["po_ref"])
    pc.append_ledger(audit, env.home, row)


# ── A1 ───────────────────────────────────────────────────────────────

def test_a1(tmp):
    e = Env(tmp, "a1", with_git=True)
    s0 = sha_file(e.settings)
    bad = [
        ("必須欄 intent が空", apply_argv("user-allow", "add", "Bash(ls:*)x", intent="")),
        ("必須欄 reason が空白だけ", apply_argv("user-allow", "add", "Bash(ls:*)x", reason="  ")),
        ("必須欄 expected が空", apply_argv("user-allow", "add", "Bash(ls:*)x", expected="")),
        ("review-days が 0", apply_argv("user-allow", "add", "Bash(ls:*)x", days=0)),
        ("review-days が 31", apply_argv("user-allow", "add", "Bash(ls:*)x", days=31)),
        ("引数の欠け（--reason なし）", ["apply", "--target", "user-allow", "--op", "add", "--item", "x", "--intent", "i", "--expected", "e"]),
        ("record の po-ref が空の形（PR#）", ["record", "--target", "user-deny", "--op", "add", "--item-hash", "abcdef12", "--po-ref", "PR#"]),
        ("record の po-ref が形違い（PR12）", ["record", "--target", "user-deny", "--op", "add", "--item-hash", "abcdef12", "--po-ref", "PR12"]),
        ("record の po-ref が形違い（consent:x）", ["record", "--target", "user-deny", "--op", "add", "--item-hash", "abcdef12", "--po-ref", "consent:x"]),
        ("record の item-hash が8桁でない", ["record", "--target", "user-deny", "--op", "add", "--item-hash", "abc", "--po-ref", "PR#1"]),
        ("record の target が未知", ["record", "--target", "nope", "--op", "add", "--item-hash", "abcdef12", "--po-ref", "PR#1"]),
    ]
    for i, (desc, argv) in enumerate(bad):
        n0 = ledger_n(e)
        code, _, _ = run_pc(e, argv)
        chk("A1-%d" % (i + 1), "%s: exit 1・台帳の行数が変わらない" % desc, code == 1 and ledger_n(e) == n0)
    chk("A1-z", "失敗した呼び出しで設定ファイルが変わらない", sha_file(e.settings) == s0)


# ── A2 / A3 ──────────────────────────────────────────────────────────

def test_a2(tmp):
    e = Env(tmp, "a2", with_git=True)
    n0 = ledger_n(e)
    item = "Bash(wc docs)"
    code, out, _ = run_pc(e, apply_argv("user-allow", "add", item, days=7))
    allow = load_json(e.settings)["permissions"]["allow"]
    rows = ledger_rows(e)
    chk("A2-a", "user-allow の add が反映され、台帳に applied が1行増える", code == 0 and item in allow and ledger_n(e) == n0 + 1 and rows[-1]["result"] == "applied" and rows[-1]["item_hash"] == audit.item_sha8(item))
    chk("A2-b", "台帳の review_by が7日後・actor が opus・prev_sha が genesis", rows[-1]["review_by"] == (T0 + td(days=7)).strftime("%Y-%m-%d") and rows[-1]["actor"] == "opus" and rows[-1]["prev_sha"] == "genesis")
    code, _, _ = run_pc(e, apply_argv("user-allow", "remove", item))
    chk("A2-c", "user-allow の remove が反映され applied が1行増える", code == 0 and item not in load_json(e.settings)["permissions"]["allow"] and ledger_n(e) == n0 + 2)
    item2 = "Bash(wc docs2)"
    code, _, _ = run_pc(e, apply_argv("repo-local-allow", "add", item2))
    chk("A2-d", "repo-local-allow の add が反映される", code == 0 and item2 in load_json(e.repo_local)["permissions"]["allow"])
    code, _, _ = run_pc(e, apply_argv("repo-local-allow", "remove", item2))
    chk("A2-e", "repo-local-allow の remove が反映される", code == 0 and item2 not in load_json(e.repo_local)["permissions"]["allow"])
    code, _, _ = run_pc(e, apply_argv("user-automode-allow", "remove", "Benign sentence one."))
    am = load_json(e.settings)["autoMode"]["allow"]
    chk("A2-f", "user-automode-allow の remove が反映され、SM- の文は残る", code == 0 and "Benign sentence one." not in am and "SM-1 weekly sentence" in am)
    n1 = ledger_n(e)
    code, _, _ = run_pc(e, apply_argv("user-allow", "remove", "Bash(never-there:*)"))
    chk("A2-g", "remove で無い文は exit 0・noop の行", code == 0 and ledger_rows(e)[-1]["result"] == "noop" and ledger_n(e) == n1 + 1)
    chk("A2-h", "台帳の prev_sha の鎖がつながっている", audit.read_ledger(e.home)["chain_ok"])
    run_pc(e, apply_argv("user-allow", "add", "Bash(wc twice)"))
    code2, _, _ = run_pc(e, apply_argv("user-allow", "add", "Bash(wc twice)"))
    chk("A2-i", "add で既にある文は noop（exit 0）", code2 == 0 and ledger_rows(e)[-1]["result"] == "noop")
    n2 = ledger_n(e)
    code, _, _ = run_pc(e, apply_argv("user-automode-allow-sm", "add", "SM-x"))
    chk("A2-j", "apply で使えない target は exit 1・台帳は増えない", code == 1 and ledger_n(e) == n2)
    code, _, _ = run_pc(e, apply_argv("user-automode-allow", "add", "SM-y a sentence"))
    chk("A2-j2", "user-automode-allow の add は exit 3・分類は reserved:R0・台帳に held が1行増える",
        code == 3 and ledger_n(e) == n2 + 1 and ledger_rows(e)[-1]["category"] == "reserved:R0" and ledger_rows(e)[-1]["result"] == "held")
    # record: PR の差分から1要素1行
    code, _, _ = run_pc(e, ["record", "--target", "repo-hooks", "--op", "add", "--item-hash", "abcdef12", "--po-ref", "PR#4600"])
    r = ledger_rows(e)[-1]
    chk("A2-k", "record が recorded の行を書く（po_ref・reserved:R4）", code == 0 and r["result"] == "recorded" and r["po_ref"] == "PR#4600" and r["category"] == "reserved:R4")
    code, _, _ = run_pc(e, ["record", "--target", "user-deny", "--op", "add", "--item-hash", "abcdef12", "--po-ref", "consent:%s:2026-10-19T00:00:00.000Z:1" % ("a" * 64)])
    chk("A2-l", "record が consent: の po_ref（時刻に : を含む）を受ける", code == 0)


def test_a3(tmp):
    e = Env(tmp, "a3", with_git=True)
    s0 = sha_file(e.settings)
    n0 = ledger_n(e)
    real = pc.write_json_atomic

    def corrupt(path, data):
        with open(path, "w") as f:
            f.write("{broken")

    pc.write_json_atomic = corrupt
    try:
        code, _, _ = run_pc(e, apply_argv("user-allow", "add", "Bash(wc a)"))
    finally:
        pc.write_json_atomic = real
    chk("A3-a", "書いた後の読み直しに失敗すると exit 1・元のファイルと同じ sha256", code == 1 and sha_file(e.settings) == s0)
    chk("A3-b", "失敗時は台帳に applied の行が増えない", ledger_n(e) == n0)

    def raiser(path, data):
        raise OSError("disk full")

    pc.write_json_atomic = raiser
    try:
        code, _, _ = run_pc(e, apply_argv("user-allow", "add", "Bash(wc b)"))
    finally:
        pc.write_json_atomic = real
    chk("A3-c", "書き込みが例外で失敗しても exit 1・元のファイルと同じ", code == 1 and sha_file(e.settings) == s0)

    def noop_writer(path, data):
        return None  # 何も書かない（反映されない）

    pc.write_json_atomic = noop_writer
    try:
        code, _, _ = run_pc(e, apply_argv("user-allow", "add", "Bash(wc c)"))
    finally:
        pc.write_json_atomic = real
    chk("A3-d", "反映されなかった場合も exit 1・元のファイルと同じ", code == 1 and sha_file(e.settings) == s0)
    bdirs = os.listdir(os.path.join(e.claude, "logs", "perm-backup"))
    chk("A3-e", "書く前の控えが perm-backup に取られる", len(bdirs) >= 1)


# ── A4 / A18 ─────────────────────────────────────────────────────────

R_EXAMPLES = {
    "R0": ["Bash", "Bash(*)", "Bash(ls:*)", "Bash(python3 scripts/*)", "Bash(bash ~/worktrees/*)", "BASH(LS *)",
           "Edit(~/.claude/**)", "Bash(python3 scripts/dev/perm-change.py apply)",
           "Bash(ssh -F /dev/null prod1 *)", 'Bash(psql ai_ro -c "SELECT * FROM x")'],
    # R1〜R4 は受け入れの形（改6: grep・wc・git status など）の文でだけ当たる。それ以外は R0 が先
    "R1": ["Bash(grep delete docs)", "Bash(grep 削除 docs)", "Bash(grep truncate docs)", "Bash(grep prod1 docs)",
           "Bash(rm -v *)", "Bash(/bin/rm -f *)", "Bash(grep DELETE docs)"],
    "R2": ["Bash(grep push docs)", "Bash(grep main docs)", "Bash(grep develop docs)", "Bash(grep ruleset docs)",
           "Bash(grep PUSH docs)"],
    "R3": ["Bash(grep token docs)", "Bash(grep secret docs)", "Bash(grep .env docs)", "Bash(grep 合言葉 docs)",
           "Bash(grep PASSWORD docs)"],
    "R4": ["Bash(grep hook docs)", "Bash(grep settings docs)", "Bash(grep GUARD docs)", "Bash(grep 見張り docs)",
           "Bash(grep Self-Modification docs)"],
}


def test_a4(tmp):
    e = Env(tmp, "a4", with_git=True)
    s0 = sha_file(e.settings)
    for rule, items in R_EXAMPLES.items():
        for i, it in enumerate(items):
            n0 = ledger_n(e)
            code, out, _ = run_pc(e, apply_argv("user-allow", "add", it))
            row = ledger_rows(e)[-1]
            path = [x[len("PO_SCRIPT="):] for x in out.splitlines() if x.startswith("PO_SCRIPT=")]
            ok = (code == 3 and ledger_n(e) == n0 + 1 and row["result"] == "held" and row["category"] == "reserved:" + rule
                  and len(path) == 1 and os.path.isfile(path[0]) and it not in load_json(e.settings)["permissions"]["allow"])
            chk("A4-%s%d" % (rule, i + 1), "%s の例 %s は exit 3・反映なし・held の行・台本あり" % (rule, it), ok)
    chk("A4-z", "保留のあと設定ファイルが変わらない", sha_file(e.settings) == s0)
    # 外す: 例外の文
    e2 = Env(tmp, "a4b", with_git=True)
    d = load_json(e2.settings)
    exc = ["SM-2 another weekly sentence",
           "Permission self-maintenance (explicitly wanted by the PO, ADR-1011). example",
           "Running exactly `cd ~/.salesanchor-tools && python3 -I -B scripts/dev/perm-change.py apply|record|review|sync ...` is allowed"]
    d["autoMode"]["allow"] += exc
    write_json(e2.settings, d)
    for i, it in enumerate(exc):
        code, _, _ = run_pc(e2, apply_argv("user-automode-allow", "remove", it))
        chk("A4-x%d" % (i + 1), "例外の文の remove は exit 3・残る（%s…）" % it[:12], code == 3 and it in load_json(e2.settings)["autoMode"]["allow"])
    code, _, _ = run_pc(e2, apply_argv("user-automode-allow", "add", "A harmless sentence"))
    chk("A4-y1", "autoMode.allow の add は常に保留（R0）", code == 3 and ledger_rows(e2)[-1]["category"] == "reserved:R0")
    # remove は目印に当たっても通常
    d = load_json(e2.settings)
    d["permissions"]["allow"].append("Bash(git push origin x)")
    write_json(e2.settings, d)
    code, _, _ = run_pc(e2, apply_argv("user-allow", "remove", "Bash(git push origin x)"))
    chk("A4-y2", "remove は保留の目印に当たっても通常として外せる", code == 0 and "Bash(git push origin x)" not in load_json(e2.settings)["permissions"]["allow"])
    # 台本の形: PDL-1 と同じ呼び方
    code, out, _ = run_pc(e2, apply_argv("user-allow", "add", "Bash(git push origin y)"))
    path = [x[len("PO_SCRIPT="):] for x in out.splitlines() if x.startswith("PO_SCRIPT=")][0]
    body = read(path)
    chk("A4-s1", "台本が PDL-1 と同じ形で道具を呼ぶ", "cd ~/.salesanchor-tools && python3 -I -B scripts/dev/perm-change.py record" in body)
    chk("A4-s2", "台本は実行権限つきで po_ref を引数に要求する", os.access(path, os.X_OK) and "PO_REF" in body)
    chk("A4-s3", "台本が bash の構文として正しい", subprocess.run(["bash", "-n", path]).returncode == 0)


def test_a18(tmp):
    e = Env(tmp, "a18", with_git=True)
    for i, (it, rule) in enumerate([("Bash(python3 scripts/*)", "R0"), ("Bash(bash ~/worktrees/*)", "R0"),
                                    ("Bash(python3 scripts/dev/perm-change.py apply x)", "R0"),
                                    ("Bash(ssh -F /dev/null prod1 *)", "R0"),
                                    ('Bash(psql ai_ro -c "SELECT * FROM x")', "R0"),
                                    ("Bash(rm -v *)", "R1"), ("Bash(/bin/rm -f *)", "R1")]):
        code, _, _ = run_pc(e, apply_argv("user-allow", "add", it))
        chk("A18-%d" % (i + 1), "%s は exit 3（%s）" % (it, rule), code == 3 and ledger_rows(e)[-1]["category"] == "reserved:" + rule)
    code, _, _ = run_pc(e, apply_argv("user-automode-allow", "add", "Some benign sentence"))
    chk("A18-6", "autoMode.allow の add は exit 3（R0）", code == 3 and ledger_rows(e)[-1]["category"] == "reserved:R0")
    for i, it in enumerate(['Bash(psql ai_ro -c "SELECT 1")', 'Bash(ssh -F /dev/null prod1 "SELECT 1")',
                            "Bash(echo domain)", "Bash(echo keyword)", "Bash(echo navigate)", "Bash(echo api)", "Bash(ls -la docs)"]):
        chk("A18-n%d" % (i + 1), "止めすぎの例 %s は R1〜R4 に当たらない" % it,
            not any(pc.rule_hit(r, it) for r in ("R1", "R2", "R3", "R4")))
    chk("A18-w1", "api_key の key は語として当たる（_ は区切り）", pc.rule_hit("R3", "Bash(echo api_key)"))
    chk("A18-w2", "SELECT と DELETE を含む文は読み取りの印にならない", pc.rule_hit("R1", 'Bash(psql ai_ro -c "SELECT 1; DELETE x")'))
    chk("A18-w3", "-f は push と同じ文のときだけ R2 の理由になる", pc.rule_hit("R2", "git push -f") and not pc.rule_hit("R2", "ls -f"))
    counter = ["Bash(gh api *)", "Bash(gh api:*)", "Bash(docker compose *)", "Bash(git -C /x *)", "Bash(git -c x=y *)",
               "Bash(g*)", "Bash( *)", "Bash(**)", "Bash(osascript -e *)", "Bash(sudo -n *)", "Bash(command -p *)",
               "Bash(awk -f *)", "Bash(curl -X POST *)", "Bash(launchctl load *)", "Bash(python3.12 -c *)",
               "Bash(/bin/bash -c *)", "Bash(ls *)", "Bash(git config --global *)", "Bash(git log --oneline *)",
               "Bash(git log --output=x *)", "Bash(cp -f *)", "Bash(gh alias set *)", "Bash(rg --pre x *)",
               "Bash(security dump-keychain *)", "Bash(gh pr view extra *)", "Bash(/usr/bin/grep *)",
               # 改5
               "Bash(grep * ; id)", "Bash(wc * | sh)", "Bash(grep * > x)", "Bash(PYTHONPATH=x python3 y)",
               "Bash(command python3 x)", "Bash(time bash x)", "Bash(nohup sh x)", "Bash(ls && bash x)",
               "Bash(ls; python3 x)", "Bash(curl x | sh)", "Bash(echo $(id))",
               # 改6
               "Bash(find docs -exec sh docs/x {} +)", "Bash(awk -f docs/x f)", "Bash(open docs/x)",
               "Bash(launchctl load docs/x)", "Bash(git -c core.pager=x log)", "Bash(git z)", "Bash(gh alias set z x)",
               "Bash(echo $HOME)", "Bash(wc -l docs/x)", "Bash(git status --porcelain)", "Bash(/tmp/x/grep foo bar)",
               "Bash(./gh pr view 1)", "Bash(docs/tools/grep foo bar)", 'Bash(grep foo "-r")']
    for i, it in enumerate(counter):
        chk("A18-c%d" % (i + 1), "第6版の反例 %s は R0" % it, pc.classify(it, "user-allow", "add") == "R0")
    for i, it in enumerate(["Bash(rm -v *)", "Bash(/bin/rm -f *)", "Bash(rm *)"]):
        chk("A18-r%d" % (i + 1), "%s は R1（R0 より先）" % it, pc.classify(it, "user-allow", "add") == "R1")
    for i, it in enumerate(["Bash(gh pr view *)", "Bash(git status *)", "Bash(grep *)", "Bash(gh run list:*)",
                            "Bash(wc *)", "Bash(git ls-files *)", "Bash(git rev-parse *)", "Bash(gh pr checks *)"]):
        chk("A18-a%d" % (i + 1), "受け入れの例 %s は R0 にならない" % it, pc.classify(it, "user-allow", "add") is None)
    shape_r0 = [
        # 改2
        "Edit", "Write", "Read", "WebFetch", "Edit(*)", "Write(*)", "Edit(/Users/x/.claude/CLAUDE.md)",
        "Edit($HOME/.claude/CLAUDE.md)", "NotebookEdit(**)", "Bash()", "Bash( )", "Bash (curl *)", "mcp__playwright",
        # 改3
        "Edit(~/.zshrc)", "Write(~/Library/LaunchAgents/x.plist)", "Edit(~/.gitconfig)", "Edit(.git/config)",
        "Edit(../x)", "Edit(docs/)", "Edit(//etc/hosts)", "Edit(config)", "Edit(.zshrc)", "Edit(.husky/pre-commit)",
        "Edit(scripts/x.sh)", "Edit(docs/.hidden/x)", "Bash(bash scripts/x.sh)", "Bash(python3 scripts/dev/x.py)",
        "Bash(./scripts/x.sh)", "WebFetch(domain:*)", "WebSearch", "mcp__github__merge_pull_request",
        "mcp__playwright__browser_click",
        # 改4
        "Edit(docs/.claude/x)", "Edit(docs/../x)", "Edit(docs/.git/x)", "Edit(docs/x/.codex/y)", "Edit(frontend/$X/y)",
        "Edit(backend/.salesanchor-tools/y)", "Edit(docs/agent-console/y)", "Edit(x/docs/y.md)", "Edit(docs)",
        "Bash(/usr/bin/true)", "Bash(python3.12 x.py)", "Bash(env X=1 ls)", "Bash(sudo ls)", "Bash(make test)",
        "Bash(bash -c ls)", "Bash(xargs ls)", "Bash(node x.js)", "WebFetch(x.com)", "WebFetch(domain:)",
        "mcp__context7", "mcp__context7__", "mcp__context7__a b", "Foo(x)", "WebSearch(x)", "Read()",
    ]
    for i, it in enumerate(shape_r0):
        chk("A18-s%d" % (i + 1), "改2〜4 の反例 %s は R0" % it, pc.classify(it, "user-allow", "add") == "R0")
    shape_ok = ["Edit(docs/handoff/x.md)", "Write(frontend/src/a.tsx)", "MultiEdit(backend/app/x.py)", "Read(docs/**)",
                "Grep(*)", "Glob(**/*.md)", "WebFetch(domain:docs.python.org)", "mcp__context7__query-docs",
                "mcp__context7__resolve-library-id", "Bash(git status)", "Bash(gh pr view 4544)", "Bash(grep foo docs/x)", "Bash(wc docs)"]
    for i, it in enumerate(shape_ok):
        chk("A18-t%d" % (i + 1), "通る例 %s は R0 にならない" % it, pc.classify(it, "user-allow", "add") != "R0")
    code, _, _ = run_pc(e, apply_argv("user-allow", "add", "Bash(wc docs3)"))
    chk("A18-ok", "目印に当たらない文は通常で反映される", code == 0)
    # 追補4: 旧 R1〜R4 の Bash の例（コミット 2602e90b4 で消えたもの）は R0 で、保留される
    old_r = ["Bash(docker compose exec backend ls)", 'Bash(psql -c "DROP TABLE t")', "Bash(echo 削除)", "Bash(TRUNCATE t)",
             "Bash(git push origin feat)", "Bash(GIT RESET --HARD HEAD)", "Bash(gh pr merge 12)", "Bash(git checkout main)",
             "Bash(cat .env)", "Bash(echo $API_KEY)", "Bash(gh secret list)", "Bash(echo 合言葉)", "Bash(echo PASSWORD)",
             "Bash(echo hook)", "Bash(vi settings.json)", "Bash(touch GUARD)", "Bash(echo 見張り)",
             "Bash(echo Self-Modification)"]
    for i, it in enumerate(old_r):
        s0 = sha_file(e.settings)
        code, _, _ = run_pc(e, apply_argv("user-allow", "add", it))
        chk("A18-o%d" % (i + 1), "旧例 %s は R0 で exit 3・設定は変わらない" % it,
            pc.classify(it, "user-allow", "add") == "R0" and code == 3 and sha_file(e.settings) == s0)
    # 目印の句それぞれが rule_hit で当たる
    for rule in ("R1", "R2", "R3", "R4"):
        for j, ph in enumerate(pc.RULES[rule].get("phrases", []) + pc.RULES[rule].get("gated_phrases", [])):
            chk("A18-p%s%d" % (rule, j + 1), "%s の句 %s が当たる" % (rule, ph), pc.rule_hit(rule, "Bash(grep * %s)" % ph))
    # design §2-2 (a) 2.: `*` が語の途中にある文は、その語の前までが受け入れの一覧と一致すれば R0 ではない
    for i, it in enumerate(["Bash(grep foo*)", "Bash(grep -r*)"]):
        chk("A18-m%d" % (i + 1), "語の途中に * がある %s は R0 ではない" % it, pc.classify(it, "user-allow", "add") != "R0")


# ── 点検（A5〜A13） ──────────────────────────────────────────────────

def mutate(env, key):
    if key == "danger_ops":
        p = os.path.join(env.claude, "agent-tokens.json")
        d = load_json(p) if os.path.exists(p) else {"danger_ops": []}
        d["danger_ops"].append("newop")
        write_json(p, d)
        return
    if key == "hook_files":
        with open(os.path.join(env.claude, "scripts", "new_hook.sh"), "w") as f:
            f.write("#!/bin/bash\necho new\n")
        return
    prefix, rest = key.split(":", 1)
    path = {"user": env.settings, "user-local": env.settings_local, "repo": env.tools_settings,
            "repo-local": env.repo_local}[prefix]
    d = load_json(path) if os.path.exists(path) else {}
    if rest == "hooks":
        d.setdefault("hooks", {})["PostToolUse"] = [{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo new"}]}]
    elif rest == "permissions.defaultMode":
        d.setdefault("permissions", {})["defaultMode"] = "plan"
    elif rest == "skip_flags":
        d["skipDangerousModePermissionPrompt"] = True
    elif rest.startswith("permissions."):
        d.setdefault("permissions", {}).setdefault(rest.split(".")[1], []).append("Bash(zzz:*)")
    elif rest.startswith("autoMode."):
        d.setdefault("autoMode", {}).setdefault(rest.split(".")[1], []).append("zzz sentence")
    write_json(path, d)


def light_env(tmp, name, repo_dir=False):
    e = Env(tmp, name)
    if repo_dir:
        write_json(e.tools_settings, {"permissions": {"allow": ["Bash(echo seed:*)"]}, "hooks": {}})
    return e


ALL_KEYS = sorted(set(audit.TARGET_KEYS.values()))


def test_a5_a6(tmp):
    chk("A5-0", "写しのキーは設計の表の24種（ledger・tools_clean・permits を除く）に対応する", len(ALL_KEYS) == 24 and set(audit.TARGET_KEYS) >= {"danger-ops", "hook-files", "repo-allow"})
    for key in ALL_KEYS:
        e = light_env(tmp, "a5-" + key.replace(":", "_").replace(".", "_"), repo_dir=key.startswith("repo:"))
        run_audit(e, T0, commit=True)
        mutate(e, key)
        lines = run_audit(e, T0 + td(3600))
        want = "A" if key in audit.LEDGER_ONLY_KEYS else "B"
        got = [x for x in reasons(lines) if x.startswith("ABNORMAL_REASON=%s %s " % (want, key))]
        other = [x for x in reasons(lines) if " %s " % key in x and not x.startswith("ABNORMAL_REASON=%s " % want)]
        chk("A5-" + key, "台帳に無い増を作ると ABNORMAL_REASON=%s %s・ABNORMAL=yes" % (want, key),
            len(got) == 1 and not other and "ABNORMAL=yes" in lines)
    # 減（消した場合）も検出される
    e = light_env(tmp, "a5-remove")
    run_audit(e, T0, commit=True)
    d = load_json(e.settings)
    d["permissions"]["allow"] = []
    write_json(e.settings, d)
    lines = run_audit(e, T0 + td(3600))
    chk("A5-rm", "台帳に無い減も ABNORMAL_REASON=A", any(x.startswith("ABNORMAL_REASON=A user:permissions.allow ") for x in lines))
    # ABNORMAL_REASON は ABNORMAL= より前
    idx = [i for i, x in enumerate(lines) if x.startswith("ABNORMAL_REASON=")]
    chk("A5-order", "理由行は ABNORMAL= の行より前に出る", idx and max(idx) < lines.index("ABNORMAL=yes"))
    # A6: 台帳にある増減は異常にならない
    e = Env(tmp, "a6", with_git=True)
    run_audit(e, T0, commit=True)
    code, _, _ = run_pc(e, apply_argv("user-allow", "add", "Bash(wc zz)"), now=T0 + td(3600))
    code2, _, _ = run_pc(e, apply_argv("user-allow", "remove", "Bash(echo hi:*)"), now=T0 + td(3700))
    lines = run_audit(e, T0 + td(7200))
    chk("A6-a", "道具で足し引きした変化は A にならず ABNORMAL=no", code == 0 and code2 == 0 and not reasons(lines) and "ABNORMAL=no" in lines)
    chk("A6-b", "増減は PERMISSION_CHANGES に数えられる（0 でない）", any(x.startswith("PERMISSION_CHANGES=") and x != "PERMISSION_CHANGES=0" and x != "PERMISSION_CHANGES=初回" for x in lines))
    # record された B のキーも po_ref が正しければ異常にならない
    e = light_env(tmp, "a6b")
    run_audit(e, T0, commit=True)
    d = load_json(e.settings)
    d["permissions"]["deny"] = ["Bash(rm:*)"]
    write_json(e.settings, d)
    h = audit.item_sha8("Bash(rm:*)")
    seed_row(e, T0 + td(600), sub="apply", target="user-deny", item_hash=h, category="reserved:R4", result="held")
    ref = consent_ref(e, ["c" * 64, iso(T0 + td(1000)), 1], T0 + td(1000), "同意票 %s" % h)
    seed_row(e, T0 + td(1200), sub="record", target="user-deny", item_hash=h, category="reserved:R4", result="recorded", po_ref=ref, actor="po-script")
    lines = run_audit(e, T0 + td(3600))
    chk("A6-c", "reserved の変化でも po_ref が正しければ ABNORMAL=no", not reasons(lines) and "ABNORMAL=no" in lines)


def consent_ref(e, key3, used_at, text):
    """同意票の役を作る: assistant の text（sha256 が鍵の1つ目になる）を記録に置き、同意の台帳に使用の行を書く。po_ref を返す。"""
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    key3 = [sha, key3[1], key3[2]]
    with open(e.consent_ledger, "a") as f:
        f.write(json.dumps({"key": key3, "used_at": iso(used_at)}) + "\n")
    d = os.path.join(e.claude, "projects", "p1")
    os.makedirs(d, exist_ok=True)
    tp = os.path.join(d, "x.jsonl")
    with open(tp, "a", encoding="utf-8") as f:
        f.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}, ensure_ascii=False) + "\n")
        f.write(json.dumps({"type": "user", "origin": {"kind": "human"}, "promptSource": "typed",
                            "timestamp": key3[1], "message": {"content": "1"}}, ensure_ascii=False) + "\n")
    ts = used_at.timestamp()
    os.utime(tp, (ts, ts))
    return "consent:" + ":".join(str(x) for x in key3)


def merge_pr(e, edits, branch="feat"):
    """GitHub 役の側で branch を切り、edits={相対パス: 内容} を入れて --no-ff で main に取り込む。
    tools の clone を origin/main に揃え、取り込みの commit の sha を返す。"""
    git(e.seed, "checkout", "-q", "-b", branch)
    for rel, text in edits.items():
        p = os.path.join(e.seed, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
    git(e.seed, "add", "-A")
    git(e.seed, "commit", "-q", "-m", "change " + branch)
    git(e.seed, "checkout", "-q", "main")
    git(e.seed, "merge", "-q", "--no-ff", "-m", "Merge " + branch, branch)
    git(e.seed, "push", "-q", "origin", "main")
    mc = git(e.seed, "rev-parse", "HEAD")
    git(e.tools, "fetch", "-q", "origin")
    git(e.tools, "reset", "-q", "--hard", "origin/main")
    return mc


def side_commit(e):
    """main に入っていない commit を作って tools に取り込み、sha を返す。"""
    git(e.seed, "checkout", "-q", "-b", "side")
    with open(os.path.join(e.seed, "side.txt"), "w") as f:
        f.write("side\n")
    git(e.seed, "add", "-A")
    git(e.seed, "commit", "-q", "-m", "side")
    sha = git(e.seed, "rev-parse", "HEAD")
    git(e.seed, "push", "-q", "origin", "side")
    git(e.seed, "checkout", "-q", "main")
    git(e.tools, "fetch", "-q", "origin", "side")
    return sha


def pr_view(mc, state="MERGED", off=900, body=""):
    d = {"state": state, "mergedAt": iso(T0 + td(off)), "body": body}
    if mc is not None:
        d["mergeCommit"] = {"oid": mc}
    return d


def b_case(tmp, name, ref, gh_resp, git_env=False, second=False):
    e = Env(tmp, name, with_git=True) if git_env else light_env(tmp, name)
    run_audit(e, T0, commit=True)
    items = ["Bash(rm:*)"] + (["Bash(mv:*)"] if second else [])
    d = load_json(e.settings)
    d["permissions"]["deny"] = items
    write_json(e.settings, d)
    if callable(ref):
        ref = ref(e)
    for i, it in enumerate(items):
        h = audit.item_sha8(it)
        seed_row(e, T0 + td(600), sub="apply", target="user-deny", item_hash=h, category="reserved:R4", result="held")
        seed_row(e, T0 + td(1200 + i), sub="record", target="user-deny", item_hash=h, category="reserved:R4",
                 result="recorded", po_ref=ref)
    gh = (lambda n: gh_resp(e)) if callable(gh_resp) else (lambda n: gh_resp)
    return e, run_audit(e, T0 + td(3600), gh=gh), items


SETTINGS_PATH = ".claude/settings.json"
XI = "Bash(wc newrepo)"
ZI = "Bash(wc other)"
BASEI = "Bash(echo seed:*)"


def repo_pr_case(tmp, name, held=True, cite="own", **view_kw):
    """repo-allow の変更（XI を足す PR を取り込み済み）に PR# の record を付けた状態。返り値: (行の一覧, XI の hash)。"""
    e = Env(tmp, name, with_git=True)
    run_audit(e, T0, commit=True)
    mc1 = merge_pr(e, {SETTINGS_PATH: json.dumps({"permissions": {"allow": [BASEI, XI]}})}, "b1")
    mc2 = merge_pr(e, {SETTINGS_PATH: json.dumps({"permissions": {"allow": [BASEI, XI, ZI]}})}, "b2")
    mc = {"own": mc1, "other": mc2, "none": None, "side": side_commit(e)}[cite]
    h = audit.item_sha8(XI)
    if held:
        seed_row(e, T0 + td(600), sub="apply", target="repo-allow", item_hash=h, category="reserved:R4", result="held")
    seed_row(e, T0 + td(1200), sub="record", target="repo-allow", item_hash=h, category="reserved:R4", result="recorded", po_ref="PR#9")
    gh = (lambda n: None) if view_kw.get("gh_none") else (lambda n: pr_view(mc, **{k: v for k, v in view_kw.items() if k != "gh_none"}))
    return run_audit(e, T0 + td(3600), gh=gh), h


def with_reason(lines, kind, key, h):
    return "ABNORMAL_REASON=%s %s %s" % (kind, key, h) in lines


def test_a7(tmp):
    K = ["a" * 64, "2026-10-19T00:20:00.000Z", 1]
    h = audit.item_sha8("Bash(rm:*)")
    h2 = audit.item_sha8("Bash(mv:*)")
    text = "同意票 対象 %s %s" % (h, h2)
    RK = "repo:permissions.allow"
    lines, hx = repo_pr_case(tmp, "a7-ok-pr", held=True)
    chk("A7-0", "取り込み済みの PR の差分に item_hash があり、時刻も合えば異常にならない", not [x for x in reasons(lines) if hx in x])
    lines, hx = repo_pr_case(tmp, "a7-open", held=True, state="OPEN")
    chk("A7-1", "PR が MERGED でないと B", with_reason(lines, "B", RK, hx))
    lines, hx = repo_pr_case(tmp, "a7-before", held=True, off=300)
    chk("A7-2", "mergedAt が held より前だと B", with_reason(lines, "B", RK, hx))
    lines, hx = repo_pr_case(tmp, "a7-nodiff", held=True, cite="other", body="本文に %s" % audit.item_sha8(XI))
    chk("A7-3", "差分に item_hash が無ければ（本文にだけあっても）B", with_reason(lines, "B", RK, hx))
    lines, hx = repo_pr_case(tmp, "a7-nogh", held=True, gh_none=True)
    chk("A7-4", "gh が使えない（None）と B のまま", with_reason(lines, "B", RK, hx))
    lines, hx = repo_pr_case(tmp, "a7-nomc", held=True, cite="none")
    chk("A7-4b", "mergeCommit が無いと B", with_reason(lines, "B", RK, hx))
    lines, hx = repo_pr_case(tmp, "a7-side", held=True, cite="side")
    chk("A7-4c", "mergeCommit が V の祖先でないと B", with_reason(lines, "B", RK, hx))

    def pr_for_deny(e):
        return pr_view(merge_pr(e, {"docs/note.md": "x %s\n" % h}))

    _, lines, _ = b_case(tmp, "a7-deny-pr", "PR#9", pr_for_deny, git_env=True)
    chk("A7-3b", "repo-allow・repo-hooks 以外の held に PR# を使っても B", with_reason(lines, "B", "user:permissions.deny", h))
    _, lines, _ = b_case(tmp, "a7-c-none", "consent:%s" % ":".join(str(x) for x in K), None)
    chk("A7-5", "consent: の3要素が同意の台帳に無いと B", with_reason(lines, "B", "user:permissions.deny", h))
    _, lines, _ = b_case(tmp, "a7-c-nohash", lambda e: consent_ref(e, K, T0 + td(900), "同意票 別の件"), None)
    chk("A7-5b", "同意票の本文に item_hash が無いと B", with_reason(lines, "B", "user:permissions.deny", h))
    _, lines, _ = b_case(tmp, "a7-c-early", lambda e: consent_ref(e, K, T0 + td(300), text), None)
    chk("A7-6", "used_at が held より前だと B", with_reason(lines, "B", "user:permissions.deny", h))
    _, lines, _ = b_case(tmp, "a7-c-ok", lambda e: consent_ref(e, K, T0 + td(900), text), None)
    chk("A7-7", "held より後に使われ、本文に item_hash がある同意票なら異常にならない", not reasons(lines))
    _, lines, items = b_case(tmp, "a7-c-twice", lambda e: consent_ref(e, K, T0 + td(900), text), None, second=True)
    bs = [x for x in lines if x.startswith("ABNORMAL_REASON=B ")]
    chk("A7-8", "同じ po_ref の2回目は B（1回目は通る）", len(bs) == 1 and bs[0].endswith(h2))
    # repo:hooks は PR# の record を取り込みの差分で照合する
    e = Env(tmp, "a7-hooks", with_git=True)
    run_audit(e, T0, commit=True)
    hooks = {"PostToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo new"}]}]}
    mc = merge_pr(e, {SETTINGS_PATH: json.dumps({"permissions": {"allow": [BASEI]}, "hooks": hooks})})
    hh = audit.element_hash(audit.collect_permissions(e.home)["repo:hooks"][0])
    seed_row(e, T0 + td(600), sub="apply", target="repo-hooks", item_hash=hh, category="reserved:R4", result="held")
    seed_row(e, T0 + td(1200), sub="record", target="repo-hooks", item_hash=hh, category="reserved:R4", result="recorded", po_ref="PR#55", actor="opus")
    lines = run_audit(e, T0 + td(3600), gh=lambda n: pr_view(mc))
    chk("A7-9", "repo:hooks の差分は、取り込みの差分に要素があれば PR# の record で通る", not [x for x in reasons(lines) if "repo:hooks" in x])


def a_for(lines, key):
    return [x for x in reasons(lines) if x.startswith("ABNORMAL_REASON=A %s " % key)]


def a19_pr(tmp, name, item, target, docs_line, mode="ok", body=""):
    """台帳が normal・held 無しで PR# の record が付いた変更。mode: ok / nopr / side / ownmc。"""
    e = Env(tmp, name, with_git=True)
    run_audit(e, T0, commit=True)
    d = load_json(e.settings)
    if target == "user-allow":
        d["permissions"]["allow"].append(item)
    else:
        d["autoMode"]["allow"].append(item)
    write_json(e.settings, d)
    h = audit.item_sha8(item)
    mc = merge_pr(e, {"docs/handoff/design-approval-ticket/permission-ledger.md": docs_line.replace("HASH", h) + "\n"})
    if mode == "side":
        mc = side_commit(e)
    seed_row(e, T0 + td(1200), sub="record", target=target, item_hash=h, category="normal", result="recorded", po_ref="PR#9", actor="opus")
    gh = (lambda n: None) if mode == "nopr" else (lambda n: pr_view(mc, body=body or ("本文 %s" % h)))
    return run_audit(e, T0 + td(3600), gh=gh)


def a19_consent(tmp, name, used_off, text, earlier_row=False):
    e = light_env(tmp, name)
    item = "Bash(wc c19)"
    h = audit.item_sha8(item)
    K = ["d" * 64, iso(T0 + td(used_off)), 1]
    ref = consent_ref(e, K, T0 + td(used_off), text.replace("HASH", h))
    if earlier_row:
        seed_row(e, T0 - td(3600), sub="record", target="user-allow", item_hash=h, category="normal", result="recorded", po_ref=ref, actor="po-script")
    run_audit(e, T0, commit=True)
    d = load_json(e.settings)
    d["permissions"]["allow"].append(item)
    write_json(e.settings, d)
    seed_row(e, T0 + td(1200), sub="record", target="user-allow", item_hash=h, category="normal", result="recorded", po_ref=ref, actor="po-script")
    return run_audit(e, T0 + td(3600))


def test_a19(tmp):
    UA, AA = "user:permissions.allow", "user:autoMode.allow"
    lines = a19_pr(tmp, "a19-ok", "Bash(wc p19)", "user-allow", "note HASH")
    chk("A19-0", "取り込み済みで差分に item_hash がある PR# の record は A にならない", not a_for(lines, UA))
    lines = a19_pr(tmp, "a19-nopr", "Bash(wc p19)", "user-allow", "note HASH", mode="nopr")
    chk("A19-1", "存在しない PR# は A", len(a_for(lines, UA)) == 1)
    lines = a19_pr(tmp, "a19-side", "Bash(wc p19)", "user-allow", "note HASH", mode="side")
    chk("A19-2", "V に取り込まれていない PR は A", len(a_for(lines, UA)) == 1)
    lines = a19_pr(tmp, "a19-body", "Bash(wc p19)", "user-allow", "unrelated")
    chk("A19-3", "PR 本文にだけ item_hash がある（差分に無い）と A", len(a_for(lines, UA)) == 1)
    lines = a19_pr(tmp, "a19-sm-ok", "SM-7 weekly check", "user-automode-allow-sm", "| SM-7 | HASH |")
    chk("A19-4a", "SM の PR は台帳の差分に同じ SM 番号の行があれば A にならない", not a_for(lines, AA))
    lines = a19_pr(tmp, "a19-sm-ng", "SM-7 weekly check", "user-automode-allow-sm", "| SM-8 | HASH |")
    chk("A19-4b", "SM の PR の台帳の差分が別の SM 番号だと A", len(a_for(lines, AA)) == 1)
    lines = a19_pr(tmp, "a19-sm-plain", "plain sentence", "user-automode-allow-sm", "| SM-7 | HASH |")
    chk("A19-5", "user-automode-allow-sm なのに文が SM- で始まらないと A", len(a_for(lines, AA)) == 1)
    lines, hx = repo_pr_case(tmp, "a19-repo-ng", held=False, cite="other")
    chk("A19-6", "repo-allow の PR の settings.json の差分に文が無いと A", with_reason(lines, "A", "repo:permissions.allow", hx))
    lines, hx = repo_pr_case(tmp, "a19-repo-ok", held=False)
    chk("A19-6b", "repo-allow の PR の差分に文があれば（held 無しでも）A にならない", not [x for x in reasons(lines) if hx in x])
    lines = a19_consent(tmp, "a19-c-old", -600, "同意票 HASH")
    chk("A19-7", "前回の写しより前の同意は A", len(a_for(lines, UA)) == 1)
    lines = a19_consent(tmp, "a19-c-nohash", 900, "同意票 無関係")
    chk("A19-8", "item_hash の無い同意票は A", len(a_for(lines, UA)) == 1)
    lines = a19_consent(tmp, "a19-c-ok", 900, "同意票 HASH")
    chk("A19-8b", "item_hash のある同意票（登録の記録）は A にならない", not reasons(lines))
    lines = a19_consent(tmp, "a19-c-twice", 900, "同意票 HASH", earlier_row=True)
    chk("A19-9", "同じ po_ref の2回目の使用は A", len(a_for(lines, UA)) == 1)
    # §2-3 のキー（deny）: held が無く、通らない record の行しか無いときも B
    e = light_env(tmp, "a19-deny-bad")
    run_audit(e, T0, commit=True)
    d = load_json(e.settings)
    d["permissions"]["deny"] = ["Bash(rm:*)"]
    write_json(e.settings, d)
    hd = audit.item_sha8("Bash(rm:*)")
    seed_row(e, T0 + td(1200), sub="record", target="user-deny", item_hash=hd, category="reserved:R4", result="recorded",
             po_ref="consent:%s:%s:1" % ("e" * 64, iso(T0 + td(1000))), actor="po-script")
    lines = run_audit(e, T0 + td(3600))
    chk("A19-10", "§2-3 のキーは held 無し・通らない record だけでも B", with_reason(lines, "B", "user:permissions.deny", hd))


A20_OP = "bash ~/.salesanchor-tools/docs/handoff/permission-delegation/po-register-delegation.sh consent:KEY"
A20_ITEM = "Bash(rm:*)"


def a20_text(h, op=A20_OP, heading=True, opline=True, option=True):
    parts = []
    if heading:
        parts.append("[同意票]")
    parts.append("対象 %s" % h)
    if opline:
        parts.append("操作1: %s" % op)
    if option:
        parts.append("1. 上の同意票の操作を実行する")
    return "\n".join(parts)


def a20_case(tmp, name, variant="ok", text=None, rec_off=1200, now_off=3600, k3="1", k1_cut=0, second=False):
    """PO の `!` の道: 同意の台帳に行を作らず、一時の home の会話の記録だけを置く。B の理由の行を返す。"""
    e = light_env(tmp, name)
    run_audit(e, T0, commit=True)
    items = [A20_ITEM] + (["Bash(mv:*)"] if second else [])
    d = load_json(e.settings)
    d["permissions"]["deny"] = items
    write_json(e.settings, d)
    h = audit.item_sha8(A20_ITEM)
    hh = " ".join(audit.item_sha8(x) for x in items)
    text = text if text is not None else a20_text(hh)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    k2 = iso(T0 + td(900))
    asst = {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}
    one = {"type": "user", "origin": {"kind": "human"}, "promptSource": "typed", "timestamp": k2, "message": {"content": "1"}}
    other = {"type": "user", "origin": {"kind": "human"}, "promptSource": "typed", "timestamp": iso(T0 + td(899)), "message": {"content": "x"}}
    recs = {
        "ok": [asst, one],
        "noticket": [one],
        "after": [one, asst],
        "human_between": [asst, other, one],
        "compact_between": [asst, {"type": "system", "subtype": "compact_boundary"}, one],
        "side_asst": [dict(asst, isSidechain=True), one],
        "side_one": [asst, dict(one, isSidechain=True)],
        "ai_one": [asst, dict(one, origin={"kind": "task"})],
        "not_one": [asst, dict(one, message={"content": "2"})],
        "mixed_block": [dict(asst, message={"content": [{"type": "tool_use", "name": "x"}, {"type": "text", "text": text}]}), one],
    }[variant]
    d2 = os.path.join(e.claude, "projects", "p1")
    os.makedirs(d2, exist_ok=True)
    tp = os.path.join(d2, "x.jsonl")
    with open(tp, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    ts = (T0 + td(900)).timestamp()
    os.utime(tp, (ts, ts))
    ref = "consent:%s:%s:%s" % (sha[:64 - k1_cut], k2, k3)
    for i, it in enumerate(items):
        hi = audit.item_sha8(it)
        seed_row(e, T0 + td(600), sub="apply", target="user-deny", item_hash=hi, category="reserved:R4", result="held")
        seed_row(e, T0 + td(rec_off + i), sub="record", target="user-deny", item_hash=hi, category="reserved:R4",
                 result="recorded", po_ref=ref, actor="po-script")
    return run_audit(e, T0 + td(now_off)), h


def test_a20(tmp):
    DK = "user:permissions.deny"

    def ok(name, desc, **kw):
        lines, h = a20_case(tmp, name, **kw)
        chk(name, desc, not reasons(lines))

    def ng(name, desc, **kw):
        lines, h = a20_case(tmp, name, **kw)
        chk(name, desc, with_reason(lines, "B", DK, h))

    ok("A20-ok1", "(a)〜(e) が揃った PO の `!` の同意は通る（台帳の行は無い）")
    ok("A20-ok2", "操作が po-apply- の台本で、k3 が 2 でも通る", k3="2",
       text=a20_text("HHH", op="bash ~/CC報告ファイル-keep/permission-delegation/po-apply-x.sh").replace("HHH", audit.item_sha8(A20_ITEM)).replace("操作1:", "操作2:"))
    t3 = "同意票 %s" % audit.item_sha8(A20_ITEM)
    _, lines, _ = b_case(tmp, "A20-ok3", lambda e: consent_ref(e, ["a" * 64, iso(T0 + td(900)), 3], T0 + td(900), t3), None)
    chk("A20-ok3", "台帳の行（k3 が整数）がある従来の道も通る", not reasons(lines))
    ng("A20-n1", "sha の合う同意票が会話の記録に無い", variant="noticket")
    ng("A20-n2", "同意票が「1」の後にある", variant="after")
    ng("A20-n3", "同意票と「1」の間に人の入力がある", variant="human_between")
    ng("A20-n4", "同意票と「1」の間に compact がある", variant="compact_between")
    ng("A20-n5", "直前の assistant の行が sidechain", variant="side_asst")
    ng("A20-n6", "「1」が sidechain", variant="side_one")
    ng("A20-n7", "「1」が AI の行", variant="ai_one")
    ng("A20-n8", "「1」以外の入力", variant="not_one")
    ng("A20-n9", "assistant の行に text 以外の中身がある", variant="mixed_block")
    hh = audit.item_sha8(A20_ITEM)
    ng("A20-n10", "同意票に見出しが無い", text=a20_text(hh, heading=False))
    ng("A20-n11", "同意票に選択肢の行が無い", text=a20_text(hh, option=False))
    ng("A20-n12", "`操作<k3>:` の行が無い", text=a20_text(hh, opline=False))
    ng("A20-n13", "操作が決まった台本で始まらない", text=a20_text(hh, op="bash ~/CC報告ファイル-keep/other.sh x"))
    ng("A20-n14", "別件の po-apply 台本を途中に含むだけでは通らない", text=a20_text(hh, op="bash x/po-apply-1.sh"))
    ng("A20-n15", "k3 が数字でない", k3="x")
    ng("A20-n16", "k1 が64桁でない", k1_cut=1)
    ng("A20-n17", "record が k2 より前", rec_off=800)
    ng("A20-n18", "record が k2 の24時間より後", rec_off=900 + 86400 + 60, now_off=900 + 86400 + 3600)
    ng("A20-n19", "同意票に item_hash が無い", text=a20_text("00000000"))
    lines, h = a20_case(tmp, "A20-n20", second=True)
    bs = [x for x in lines if x.startswith("ABNORMAL_REASON=B ")]
    chk("A20-n20", "同じ po_ref の2回目は B（1回目は通る）", len(bs) == 1 and bs[0].endswith(audit.item_sha8("Bash(mv:*)")))


def test_a8(tmp):
    def build(name):
        e = light_env(tmp, name)
        for i in range(3):
            seed_row(e, T0 + td(10 * i), item_hash="1000000%d" % i)
        run_audit(e, T0 + td(100), commit=True)
        return e

    e = build("a8-ok")
    seed_row(e, T0 + td(200), item_hash="10000009")
    lines = run_audit(e, T0 + td(300))
    chk("A8-0", "行が正しく足されただけなら C にならない", not [x for x in reasons(lines) if x.startswith("ABNORMAL_REASON=C")])
    e = build("a8-mid")
    rows = read(e.ledger).split("\n")
    rows[1] = rows[1].replace('"summary": "s"', '"summary": "changed"')
    with open(e.ledger, "w") as f:
        f.write("\n".join(rows))
    lines = run_audit(e, T0 + td(300))
    chk("A8-1", "途中の行を書き換えると C", any(x.startswith("ABNORMAL_REASON=C ledger ") for x in lines))
    e = build("a8-del")
    rows = [x for x in read(e.ledger).split("\n") if x]
    with open(e.ledger, "w") as f:
        f.write("\n".join(rows[:1] + rows[2:]) + "\n")
    lines = run_audit(e, T0 + td(300))
    chk("A8-2", "行を消すと C", any(x.startswith("ABNORMAL_REASON=C ledger ") for x in lines))
    e = build("a8-last")
    rows = [x for x in read(e.ledger).split("\n") if x]
    forged = json.loads(rows[-1])
    forged["summary"] = "forged"
    with open(e.ledger, "w") as f:
        f.write("\n".join(rows[:-1] + [json.dumps(forged, ensure_ascii=False)]) + "\n")
    lines = run_audit(e, T0 + td(300))
    chk("A8-3", "最後の行を書き換える（行数は同じ）と前回の head が見つからず C", any(x.startswith("ABNORMAL_REASON=C ledger ") for x in lines))
    e = build("a8-trunc")
    rows = [x for x in read(e.ledger).split("\n") if x]
    with open(e.ledger, "w") as f:
        f.write("\n".join(rows[:-1]) + "\n")
    lines = run_audit(e, T0 + td(300))
    chk("A8-4", "最後の行を消すと行数が前回より減って C", any(x.startswith("ABNORMAL_REASON=C ledger ") for x in lines))


def test_a9(tmp):
    e = Env(tmp, "a9", with_git=True)
    item = "Bash(wc review)"
    code, _, _ = run_pc(e, apply_argv("user-allow", "add", item, days=1), now=T0)
    h = audit.item_sha8(item)
    lines = run_audit(e, T0 + td(0))
    chk("A9-0", "見直し日の前は REVIEW_DUE=0", "REVIEW_DUE=0" in lines)
    lines = run_audit(e, T0 + td(days=3))
    chk("A9-1", "見直し日を過ぎると REVIEW_DUE に出る", code == 0 and "REVIEW_DUE=%s" % h in lines)
    code, out, _ = run_pc(e, ["review", "--hash", h, "--decision", "keep", "--effect", "used 5 times", "--review-days", "7"], now=T0 + td(days=3))
    lines = run_audit(e, T0 + td(days=3))
    chk("A9-2", "review の行があれば出ない", code == 0 and "REVIEW_DUE=0" in lines)
    lines = run_audit(e, T0 + td(days=11))
    chk("A9-3", "keep の新しい見直し日を過ぎるとまた出る", "REVIEW_DUE=%s" % h in lines)
    code, out, _ = run_pc(e, ["review", "--hash", h, "--decision", "remove", "--effect", "unused"], now=T0 + td(days=11))
    lines = run_audit(e, T0 + td(days=12))
    chk("A9-4", "remove の決定で設定から外れ、REVIEW_DUE から消える", code == 0 and item not in load_json(e.settings)["permissions"]["allow"] and "REVIEW_DUE=0" in lines)
    code, _, _ = run_pc(e, ["review", "--hash", "deadbeef", "--decision", "keep", "--effect", "x"])
    chk("A9-5", "台帳に無い hash の review は exit 1", code == 1)


def run_permit(env, claudecode):
    ev = dict(os.environ, HOME=env.home)
    ev.pop("CLAUDECODE", None)
    if claudecode:
        ev["CLAUDECODE"] = "1"
    return subprocess.run(["bash", os.path.join(ROOT, "scripts", "permit-danger.sh"), "gh pr merge"], env=ev, capture_output=True)


def read_events(env):
    try:
        return [json.loads(x) for x in read(env.events).splitlines() if x.strip()]
    except OSError:
        return []


def test_a10(tmp):
    e = light_env(tmp, "a10")
    r = run_permit(e, True)
    ev = [x for x in read_events(e) if x.get("type") == "permit_issued"]
    chk("A10-a", "CLAUDECODE ありで permit_issued が1行増え by=ai", r.returncode == 0 and len(ev) == 1 and ev[0]["by"] == "ai" and ev[0]["op_sha8"] == hashlib.sha256(b"gh pr merge").hexdigest()[:8])
    r = run_permit(e, False)
    ev = [x for x in read_events(e) if x.get("type") == "permit_issued"]
    chk("A10-b", "CLAUDECODE なしで by=human", r.returncode == 0 and len(ev) == 2 and ev[1]["by"] == "human")
    chk("A10-c", "券のファイルは今までどおり作られる", len([n for n in os.listdir(os.path.join(e.claude, "permits")) if n.startswith("danger-permit-")]) >= 1)
    now = datetime.datetime.now(UTC) + td(60)
    lines = run_audit(e, now)
    chk("A10-d", "説明の無い by=ai は ABNORMAL_REASON=D permit 1", "ABNORMAL_REASON=D permit 1" in lines and "ABNORMAL=yes" in lines)
    with open(e.events, "a") as f:
        f.write(json.dumps({"type": "consent_consumed", "ts": iso(datetime.datetime.now(UTC))}) + "\n")
    lines = run_audit(e, now)
    chk("A10-e", "同じ時刻の前後に consent_consumed があれば D にならない", not [x for x in lines if "REASON=D" in x])
    e2 = light_env(tmp, "a10b")
    run_permit(e2, True)
    seed_row(e2, datetime.datetime.now(UTC))
    lines = run_audit(e2, datetime.datetime.now(UTC) + td(60))
    chk("A10-f", "同じ時刻の前後に台帳の行があれば D にならない", not [x for x in lines if "REASON=D" in x])
    e3 = light_env(tmp, "a10c")
    run_permit(e3, False)
    lines = run_audit(e3, datetime.datetime.now(UTC) + td(60))
    chk("A10-g", "by=human は D にならない", not [x for x in lines if "REASON=D" in x])
    # 追記に失敗しても券は発行される
    e4 = light_env(tmp, "a10d")
    shutil.rmtree(os.path.join(e4.claude, "logs"))
    with open(os.path.join(e4.claude, "logs"), "w") as f:
        f.write("not a dir")
    r = run_permit(e4, True)
    chk("A10-h", "記録に失敗しても券の発行は止まらず、標準エラーに1行出る", r.returncode == 0 and os.path.isdir(os.path.join(e4.claude, "permits")) and b"permit_issued" in r.stderr)


def test_a11_a12_a13(tmp):
    e = light_env(tmp, "a11")
    cur = audit.collect_permissions(e.home, git_run=lambda a, c: (127, b""))
    legacy = {"settings.json:permissions.allow": cur["user:permissions.allow"], "settings.json:hooks": cur["user:hooks"],
              "settings.local.json:permissions.allow": cur["user-local:permissions.allow"],
              "settings.local.json:hooks": cur["user-local:hooks"], "permits": []}
    write_json(e.snapshot, legacy)
    lines = run_audit(e, T0 + td(3600))
    chk("A11-a", "旧キー名の写しからの読み替えは異常にならない", not reasons(lines) and "ABNORMAL=no" in lines and "PERMISSION_CHANGES=0" in lines)
    chk("A11-b", "前回の写しに無い新しいキーは「初回」と表示される", any("user:permissions.deny" in x and "初回" in x for x in lines))
    d = load_json(e.settings)
    d["permissions"]["allow"].append("Bash(zzz:*)")
    write_json(e.settings, d)
    lines = run_audit(e, T0 + td(3700))
    chk("A11-c", "旧キー名の写しでも本物の増は検出される", any(x.startswith("ABNORMAL_REASON=A user:permissions.allow ") for x in lines))
    e = light_env(tmp, "a11b")
    lines = run_audit(e, T0)
    chk("A11-d", "写しが無い最初の実行は初回で異常にならない", not reasons(lines) and "PERMISSION_CHANGES=初回" in lines)
    # A12
    e = light_env(tmp, "a12")
    run_audit(e, T0, commit=True)
    s1 = sha_file(e.snapshot)
    mutate(e, "user:permissions.allow")
    run_audit(e, T0 + td(60))
    s2 = sha_file(e.snapshot)
    chk("A12-a", "--commit-snapshot なしでは写しが変わらない（実行前後の sha256）", s1 == s2)
    run_audit(e, T0 + td(120), commit=True)
    chk("A12-b", "--commit-snapshot ありでは写しが更新される", sha_file(e.snapshot) != s2)
    lines = run_audit(e, T0 + td(180))
    chk("A12-c", "更新後は同じ状態で差分が0", "PERMISSION_CHANGES=0" in lines)
    # A13
    e = Env(tmp, "a13", with_git=True)
    secret = "Bash(echo UNIQUESECRETSTRING_9f3 token)"
    code, out, err = run_pc(e, apply_argv("user-allow", "add", secret))
    row = ledger_rows(e)[-1]
    chk("A13-a", "R3 の文の summary は [R3] だけ", code == 3 and row["summary"] == "[R3]")
    ledger_text = read(e.ledger)
    chk("A13-b", "文の中身が台帳ファイル・標準出力・標準エラーのどこにも出ない", "UNIQUESECRETSTRING_9f3" not in ledger_text + out + err)
    lines = run_audit(e, T0 + td(60))
    chk("A13-c", "点検の出力にも出ない", not any("UNIQUESECRETSTRING_9f3" in x for x in lines))
    normal = "Bash(wc x)"
    run_pc(e, apply_argv("user-allow", "add", normal))
    chk("A13-d", "通常の文の summary は先頭80字", ledger_rows(e)[-1]["summary"] == normal)


# ── A14 ──────────────────────────────────────────────────────────────

def test_a14(tmp):
    hookdir = os.path.join(ROOT, "docs", "handoff", "conversation-consent", "hooks")
    work = os.path.join(tmp, "a14")
    os.makedirs(work)
    r = subprocess.run([sys.executable, "-I", "-B", os.path.join(HERE, "consent-unit-tests.py"), hookdir, work, ROOT],
                       capture_output=True, timeout=600)
    text = r.stdout.decode("utf-8", "replace")
    p = sum(1 for x in text.splitlines() if x.startswith("PASS"))
    f = sum(1 for x in text.splitlines() if x.startswith("FAIL"))
    global PASS, FAIL
    PASS += p
    FAIL += f
    print("%s %-8s 既存の consent-audit の試験: PASS=%d FAIL=%d（rc=%d）" % ("PASS" if f == 0 and p > 0 and r.returncode == 0 else "FAIL", "A14", p, f, r.returncode), flush=True)
    if f or p == 0 or r.returncode != 0:
        FAIL += 1


# ── A17 ──────────────────────────────────────────────────────────────

def wrap_git(real, fail=None, after_ls_remote=None, noop_checkout=False):
    state = {"ls": 0}

    def g(args, cwd):
        if fail and args and args[0] == fail:
            return 128, b""
        if noop_checkout and args and args[0] == "checkout":
            return 0, b""
        rc, out = real(args, cwd)
        if args and args[0] == "ls-remote" and after_ls_remote and state["ls"] == 0:
            state["ls"] += 1
            after_ls_remote()
        return rc, out
    return g


def test_a17(tmp):
    real = pc.run_git
    e = Env(tmp, "a17", with_git=True)
    argv = ["sync"]
    # (1) exit 1 になる状態
    other = os.path.join(tmp, "elsewhere", "perm-change.py")
    os.makedirs(os.path.dirname(other))
    shutil.copy(os.path.join(HERE, "perm-change.py"), other)
    code, _, _ = run_pc(e, argv, self_path=other)
    chk("A17-1a", "~/.salesanchor-tools 以外から起動すると exit 1", code == 1)
    code, _, _ = run_pc(e, argv, flags=Flags(isolated=0, dont_write_bytecode=1))
    chk("A17-1b", "-I なしで起動すると exit 1", code == 1)
    code, _, _ = run_pc(e, argv, flags=Flags(isolated=1, dont_write_bytecode=0))
    chk("A17-1c", "-B なしで起動すると exit 1", code == 1)
    code, _, _ = run_pc(e, argv, origin_url="https://example.invalid/other.git")
    chk("A17-1d", "origin の URL が違うと exit 1", code == 1)
    untracked = os.path.join(e.tools, "stray.txt")
    with open(untracked, "w") as f:
        f.write("x")
    n0 = ledger_n(e)
    code, _, _ = run_pc(e, apply_argv("user-allow", "add", "Bash(wc a)"))
    chk("A17-1e", "追跡外のファイルがあると exit 1（設定も台帳も変えない）", code == 1 and ledger_n(e) == n0 and "Bash(wc a)" not in load_json(e.settings)["permissions"]["allow"])
    os.remove(untracked)
    ca = os.path.join(e.tools, "scripts", "dev", "consent-audit.py")
    with open(ca, "a") as f:
        f.write("\n# tampered\n")
    code, _, _ = run_pc(e, argv)
    chk("A17-1f", "consent-audit.py だけを書き換えても exit 1（同期もしない）", code == 1 and "# tampered" in read(ca))
    git(e.tools, "checkout", "--", "scripts/dev/consent-audit.py")
    # (3) exit 0: 手元でコミットして HEAD を進めた場合は V に戻ってから照合
    with open(os.path.join(e.tools, "local.txt"), "w") as f:
        f.write("local")
    git(e.tools, "add", "-A")
    git(e.tools, "commit", "-q", "-m", "local")
    e.reexec_calls = 0
    code, out, _ = run_pc(e, argv)
    chk("A17-3a", "手元でコミットして HEAD を進めても、同期して exit 0・HEAD が V・起動し直しは1回", code == 0 and e.head() == e.v() and e.reexec_calls == 1 and "TOOLS_SYNCED=%s" % e.v()[:12] in out)
    chk("A17-3b", "2つのファイルの sha が V と一致する", all(sha_file(os.path.join(e.tools, "scripts", "dev", n)) == hashlib.sha256(subprocess.run(["git", "-C", e.bare, "show", "main:scripts/dev/%s" % n], capture_output=True).stdout).hexdigest() for n in ("perm-change.py", "consent-audit.py")))
    chk("A17-3c", "同期のあと作業ツリーは clean（__pycache__ も作られない）", git(e.tools, "status", "--porcelain", "--untracked-files=all") == "")
    e.advance("note.txt", "one")
    e.reexec_calls = 0
    code, out, _ = run_pc(e, apply_argv("user-allow", "add", "Bash(wc a1)"))
    chk("A17-3d", "main が1つ進んだだけなら自分で揃えて起動し直し（1回）、そのまま実行される", code == 0 and e.reexec_calls == 1 and e.head() == e.v())
    first = git(e.tools, "rev-list", "--max-parents=0", "HEAD")
    git(e.tools, "update-ref", "refs/remotes/origin/main", first)
    e.reexec_calls = 0
    code, out, _ = run_pc(e, argv)
    chk("A17-3e", "手元の origin/main を update-ref で差し替えても基準は ls-remote なので結果は変わらない", code == 0 and e.reexec_calls == 0 and "TOOLS_SYNCED=%s" % e.v()[:12] in out)
    # (2) exit 4
    def offline(args, cwd):
        if args and args[0] == "ls-remote":
            return 128, b""
        return real(args, cwd)
    code, _, _ = run_pc(e, argv, git_run=offline)
    chk("A17-2a", "ls-remote が取れないと exit 4", code == 4)
    n0 = ledger_n(e)
    code, _, _ = run_pc(e, apply_argv("user-allow", "add", "Bash(wc a2)"), git_run=offline)
    chk("A17-2a2", "exit 4 のとき設定も台帳も変えない", code == 4 and ledger_n(e) == n0)
    e.advance("note.txt", "two")
    code, _, _ = run_pc(e, argv, git_run=wrap_git(real, fail="fetch"))
    chk("A17-2b", "fetch が失敗すると exit 4", code == 4)
    e.advance("note.txt", "three")
    code, _, _ = run_pc(e, argv, git_run=wrap_git(real, after_ls_remote=lambda: e.advance("note.txt", "racing")))
    chk("A17-2c", "ls-remote と fetch の間に main が進み FETCH_HEAD が V と違えば exit 4（V に揃え直さない）", code == 4)
    e.advance("note.txt", "four")
    e.reexec_calls = 0
    code, _, _ = run_pc(e, argv, git_run=wrap_git(real, noop_checkout=True))
    chk("A17-2d", "起動し直した後も HEAD が V と違えば exit 4・起動し直しは1回だけ", code == 4 and e.reexec_calls == 1)
    # ふたたび揃える
    code, _, _ = run_pc(e, argv)
    chk("A17-2e", "障害が消えれば次の呼び出しで揃って exit 0", code == 0 and e.head() == e.v())
    # (4) -I -B で起動して consent-audit.py の関数が読める
    code_src = ("import importlib.util,sys\n"
                "assert sys.flags.isolated and sys.flags.dont_write_bytecode\n"
                "s=importlib.util.spec_from_file_location('ca',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n"
                "print(m.item_sha8('Bash(x:*)'))\n")
    r = subprocess.run([sys.executable, "-I", "-B", "-c", code_src, os.path.join(e.tools, "scripts", "dev", "consent-audit.py")], capture_output=True)
    chk("A17-4a", "-I -B で絶対パスから consent-audit.py の関数が読める", r.returncode == 0 and r.stdout.decode().strip() == audit.item_sha8("Bash(x:*)"))
    r = subprocess.run([sys.executable, "-I", "-B", os.path.join(e.tools, "scripts", "dev", "perm-change.py"), "sync"], capture_output=True)
    chk("A17-4b", "-I -B で実際に起動した道具は、本物の ~/.salesanchor-tools 以外からでは exit 1 で止まる", r.returncode == 1)
    r = subprocess.run([sys.executable, "-I", "-B", os.path.join(e.tools, "scripts", "dev", "perm-change.py")], capture_output=True)
    chk("A17-4c", "副命令なしは exit 1", r.returncode == 1)
    chk("A17-4d", "試験のあと tools の作業ツリーは clean", git(e.tools, "status", "--porcelain", "--untracked-files=all") == "")
    # (5) 週次点検の E
    e2 = Env(tmp, "a17e", with_git=True)
    lines = run_audit(e2, T0)
    chk("A17-5z", "clean で main に揃っていれば E は出ない", not [x for x in lines if "REASON=E" in x])
    with open(os.path.join(e2.tools, "stray.txt"), "w") as f:
        f.write("x")
    lines = run_audit(e2, T0)
    chk("A17-5a", "変更・追跡外のファイルがあると ABNORMAL_REASON=E tools dirty", "ABNORMAL_REASON=E tools dirty" in lines and "ABNORMAL=yes" in lines)
    os.remove(os.path.join(e2.tools, "stray.txt"))
    with open(os.path.join(e2.tools, "local.txt"), "w") as f:
        f.write("l")
    git(e2.tools, "add", "-A")
    git(e2.tools, "commit", "-q", "-m", "local")
    lines = run_audit(e2, T0)
    chk("A17-5b", "HEAD が main の祖先でないと ABNORMAL_REASON=E tools stale", "ABNORMAL_REASON=E tools stale" in lines)
    git(e2.tools, "reset", "-q", "--hard", "origin/main")
    with open(os.path.join(e2.tools, "scripts", "dev", "perm-change.py"), "a") as f:
        f.write("\n# local edit\n")
    git(e2.tools, "add", "-A")
    git(e2.tools, "commit", "-q", "-m", "edit tool")
    lines = run_audit(e2, T0)
    chk("A17-5c", "道具の sha が V と違うと ABNORMAL_REASON=E tools sha", "ABNORMAL_REASON=E tools sha" in lines)
    git(e2.tools, "reset", "-q", "--hard", "origin/main")
    def off(args, cwd):
        return (128, b"") if args and args[0] == "ls-remote" else audit.run_git(args, cwd)
    lines = run_audit(e2, T0, git_run=off)
    chk("A17-5d", "ls-remote が取れないと ABNORMAL_REASON=E tools offline", "ABNORMAL_REASON=E tools offline" in lines)


def old_style_hook_files(env):
    """直す前の式（.backup フォルダの中も数える。ファイル名に .backup を含むものだけ除く）で hook_files を作る。"""
    base = os.path.join(env.claude, "scripts")
    out = []
    for root, dirs, names in os.walk(base):
        for n in sorted(names):
            if ".backup" in n:
                continue
            fp = os.path.join(root, n)
            if os.path.islink(fp) or not os.path.isfile(fp):
                continue
            out.append("%s|%s" % (audit.sha8(os.path.relpath(fp, base)), sha_file(fp)[:8]))
    return sorted(out)


def test_a21(tmp):
    def put(env, rel, text="#!/bin/bash\necho b\n"):
        fp = os.path.join(env.claude, "scripts", rel)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "w") as f:
            f.write(text)
        return fp

    # A21-1: .backup/<時刻>/x.sh を足しても hook_files の件数が変わらず ABNORMAL=no
    e = light_env(tmp, "a21-1")
    run_audit(e, T0, commit=True)
    n0 = len(load_json(e.snapshot)["hook_files"])
    put(e, ".backup/20261026221349/x.sh")
    lines = run_audit(e, T0 + td(3600), commit=True)
    n1 = len(load_json(e.snapshot)["hook_files"])
    chk("A21-1", ".backup/<時刻>/x.sh を足しても hook_files の件数が変わらず ABNORMAL=no",
        n0 == n1 and "ABNORMAL=no" in lines and not reasons(lines))
    # A21-5: 名前に .backup を含むファイルは数えない
    put(e, "x.sh.backup")
    lines = run_audit(e, T0 + td(7200), commit=True)
    chk("A21-5", "名前に .backup を含むファイル（x.sh.backup）は数えない",
        len(load_json(e.snapshot)["hook_files"]) == n0 and "ABNORMAL=no" in lines and not reasons(lines))
    # A21-2: 直す前の式で作った前回の写し（.backup の中の要素あり）から比べても減にならず B が出ない
    e = light_env(tmp, "a21-2")
    put(e, ".backup/20261026221349/x.sh")
    put(e, ".backup/20261026225412/y.sh", "#!/bin/bash\necho y\n")
    run_audit(e, T0, commit=True)
    snap = load_json(e.snapshot)
    snap["hook_files"] = old_style_hook_files(e)
    write_json(e.snapshot, snap)
    chk("A21-2pre", "前回の写しは .backup の要素を含む（現行の式より多い）",
        len(snap["hook_files"]) == len(audit.collect_permissions(e.home)["hook_files"]) + 2)
    lines = run_audit(e, T0 + td(3600))
    chk("A21-2", ".backup の下の要素は「減」にならず hook_files の B が出ない",
        not any("hook_files" in x for x in reasons(lines)) and "ABNORMAL=no" in lines
        and not any(x.startswith("    - ") for x in lines))
    # A21-3: 控えのフォルダを消すと、前回の写しにあった控えの要素は「減」として出る
    e = light_env(tmp, "a21-3")
    put(e, ".backup/20261026221349/x.sh")
    run_audit(e, T0, commit=True)
    snap = load_json(e.snapshot)
    snap["hook_files"] = old_style_hook_files(e)
    write_json(e.snapshot, snap)
    shutil.rmtree(os.path.join(e.claude, "scripts", ".backup"))
    lines = run_audit(e, T0 + td(3600))
    chk("A21-3", "控えのフォルダを消すと、その要素は「減」の行に出る",
        any(x.startswith("    - ") for x in lines)
        and any(x.startswith("ABNORMAL_REASON=B hook_files ") for x in lines))


def main():
    tmp = tempfile.mkdtemp(prefix="permdel-tests-")
    try:
        for fn in (test_a1, test_a2, test_a3, test_a4, test_a18, test_a5_a6, test_a7, test_a19, test_a20, test_a8, test_a9, test_a10,
                   test_a11_a12_a13, test_a14, test_a17, test_a21):
            try:
                fn(tmp)
            except Exception as ex:  # 試験自体の崩れは失敗として数える
                import traceback
                traceback.print_exc()
                chk(fn.__name__, "試験が例外で止まった: %s" % ex, False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS=%d FAIL=%d TOTAL=%d" % (PASS, FAIL, PASS + FAIL))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
