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
    item = "Bash(wc -l docs:*)"
    code, out, _ = run_pc(e, apply_argv("user-allow", "add", item, days=7))
    allow = load_json(e.settings)["permissions"]["allow"]
    rows = ledger_rows(e)
    chk("A2-a", "user-allow の add が反映され、台帳に applied が1行増える", code == 0 and item in allow and ledger_n(e) == n0 + 1 and rows[-1]["result"] == "applied" and rows[-1]["item_hash"] == audit.item_sha8(item))
    chk("A2-b", "台帳の review_by が7日後・actor が opus・prev_sha が genesis", rows[-1]["review_by"] == (T0 + td(days=7)).strftime("%Y-%m-%d") and rows[-1]["actor"] == "opus" and rows[-1]["prev_sha"] == "genesis")
    code, _, _ = run_pc(e, apply_argv("user-allow", "remove", item))
    chk("A2-c", "user-allow の remove が反映され applied が1行増える", code == 0 and item not in load_json(e.settings)["permissions"]["allow"] and ledger_n(e) == n0 + 2)
    item2 = "Bash(wc -c docs:*)"
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
    code, _, _ = run_pc(e, apply_argv("user-allow", "remove", "Bash(echo hi:*)git push"))
    code2, _, _ = run_pc(e, apply_argv("user-allow", "add", "Bash(echo hi:*)"))
    chk("A2-i", "add で既にある文は noop（exit 0）", code2 == 0 and ledger_rows(e)[-1]["result"] == "noop")
    code, _, _ = run_pc(e, apply_argv("user-automode-allow-sm", "add", "SM-x"))
    chk("A2-j", "apply で使えない target は exit 1", code == 1)
    # record: PR の差分から1要素1行
    code, _, _ = run_pc(e, ["record", "--target", "repo-hooks", "--op", "add", "--item-hash", "abcdef12", "--po-ref", "PR#4600"])
    r = ledger_rows(e)[-1]
    chk("A2-k", "record が recorded の行を書く（po_ref・reserved:R4）", code == 0 and r["result"] == "recorded" and r["po_ref"] == "PR#4600" and r["category"] == "reserved:R4")
    code, _, _ = run_pc(e, ["record", "--target", "user-deny", "--op", "add", "--item-hash", "abcdef12", "--po-ref", "consent:%s:2026-10-19T00:00:00.000Z:cmd1" % ("a" * 64)])
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
        code, _, _ = run_pc(e, apply_argv("user-allow", "add", "Bash(wc -l a:*)"))
    finally:
        pc.write_json_atomic = real
    chk("A3-a", "書いた後の読み直しに失敗すると exit 1・元のファイルと同じ sha256", code == 1 and sha_file(e.settings) == s0)
    chk("A3-b", "失敗時は台帳に applied の行が増えない", ledger_n(e) == n0)

    def raiser(path, data):
        raise OSError("disk full")

    pc.write_json_atomic = raiser
    try:
        code, _, _ = run_pc(e, apply_argv("user-allow", "add", "Bash(wc -l b:*)"))
    finally:
        pc.write_json_atomic = real
    chk("A3-c", "書き込みが例外で失敗しても exit 1・元のファイルと同じ", code == 1 and sha_file(e.settings) == s0)

    def noop_writer(path, data):
        return None  # 何も書かない（反映されない）

    pc.write_json_atomic = noop_writer
    try:
        code, _, _ = run_pc(e, apply_argv("user-allow", "add", "Bash(wc -l c:*)"))
    finally:
        pc.write_json_atomic = real
    chk("A3-d", "反映されなかった場合も exit 1・元のファイルと同じ", code == 1 and sha_file(e.settings) == s0)
    bdirs = os.listdir(os.path.join(e.claude, "logs", "perm-backup"))
    chk("A3-e", "書く前の控えが perm-backup に取られる", len(bdirs) >= 1)


# ── A4 / A18 ─────────────────────────────────────────────────────────

R_EXAMPLES = {
    "R0": ["Bash", "Bash(*)", "Bash(ls:*)", "Bash(python3 scripts/*)", "Bash(bash ~/worktrees/*)", "BASH(LS *)",
           "Edit(~/.claude/**)", "Bash(python3 scripts/dev/perm-change.py apply)"],
    "R1": ["Bash(rm -rf /tmp/xx)", "Bash(docker compose exec backend ls)", 'Bash(psql -c "DROP TABLE t")',
           "Bash(echo 削除)", "Bash(ssh -F /dev/null prod1 *)", 'Bash(psql ai_ro -c "SELECT * FROM x")', "Bash(TRUNCATE t)"],
    "R2": ["Bash(git push origin feat)", "Bash(GIT RESET --HARD HEAD)", "Bash(gh pr merge 12)", "Bash(git checkout main)"],
    "R3": ["Bash(cat .env)", "Bash(echo $API_KEY)", "Bash(gh secret list)", "Bash(echo 合言葉)", "Bash(echo PASSWORD)"],
    "R4": ["Bash(echo hook)", "Bash(vi settings.json)", "Bash(touch GUARD)", "Bash(echo 見張り)", "Bash(echo Self-Modification)"],
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
                                    ("Bash(ssh -F /dev/null prod1 *)", "R1"),
                                    ('Bash(psql ai_ro -c "SELECT * FROM x")', "R1")]):
        code, _, _ = run_pc(e, apply_argv("user-allow", "add", it))
        chk("A18-%d" % (i + 1), "%s は exit 3（%s）" % (it, rule), code == 3 and ledger_rows(e)[-1]["category"] == "reserved:" + rule)
    code, _, _ = run_pc(e, apply_argv("user-automode-allow", "add", "Some benign sentence"))
    chk("A18-6", "autoMode.allow の add は exit 3（R0）", code == 3 and ledger_rows(e)[-1]["category"] == "reserved:R0")
    for i, it in enumerate(['Bash(psql ai_ro -c "SELECT 1")', 'Bash(ssh -F /dev/null prod1 "SELECT 1")',
                            "Bash(echo domain)", "Bash(echo keyword)", "Bash(echo navigate)", "Bash(echo api)", "Bash(ls -la docs)"]):
        chk("A18-n%d" % (i + 1), "止めすぎの例 %s は R1〜R4 に当たらない" % it, pc.classify(it, "user-allow", "add") is None)
    chk("A18-w1", "api_key の key は語として当たる（_ は区切り）", pc.classify("Bash(echo api_key)", "user-allow", "add") == "R3")
    chk("A18-w2", "SELECT と DELETE を含む文は読み取りの印にならない", pc.classify('Bash(psql ai_ro -c "SELECT 1; DELETE x")', "user-allow", "add") == "R1")
    chk("A18-w3", "-f は push と同じ文のときだけ R2 の理由になる", pc.rule_hit("R2", "git push -f") and not pc.rule_hit("R2", "ls -f"))
    code, _, _ = run_pc(e, apply_argv("user-allow", "add", "Bash(wc -w docs:*)"))
    chk("A18-ok", "目印に当たらない文は通常で反映される", code == 0)


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
    code, _, _ = run_pc(e, apply_argv("user-allow", "add", "Bash(wc -l zz:*)"), now=T0 + td(3600))
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
    seed_row(e, T0 + td(1200), sub="record", target="user-deny", item_hash=h, category="reserved:R4", result="recorded", po_ref="PR#77", actor="po-script")
    gh = lambda n: {"state": "MERGED", "mergedAt": iso(T0 + td(900)), "body": "x %s y" % h}
    lines = run_audit(e, T0 + td(3600), gh=gh)
    chk("A6-c", "reserved の変化でも po_ref が正しければ ABNORMAL=no", not reasons(lines) and "ABNORMAL=no" in lines)


def b_case(tmp, name, ref, gh_resp, consent_used=None, merged_offset=900, key3=None, second_ref=None):
    e = light_env(tmp, name)
    run_audit(e, T0, commit=True)
    items = ["Bash(rm:*)"] + (["Bash(mv:*)"] if second_ref else [])
    d = load_json(e.settings)
    d["permissions"]["deny"] = items
    write_json(e.settings, d)
    if consent_used is not None:
        with open(e.consent_ledger, "w") as f:
            f.write(json.dumps({"key": key3, "used_at": iso(consent_used)}) + "\n")
    for i, it in enumerate(items):
        h = audit.item_sha8(it)
        seed_row(e, T0 + td(600), sub="apply", target="user-deny", item_hash=h, category="reserved:R4", result="held")
        seed_row(e, T0 + td(1200 + i), sub="record", target="user-deny", item_hash=h, category="reserved:R4",
                 result="recorded", po_ref=ref)
    gh = (lambda n: gh_resp(items) if callable(gh_resp) else gh_resp)
    return e, run_audit(e, T0 + td(3600), gh=gh), items


def test_a7(tmp):
    K = ["a" * 64, "2026-10-19T00:20:00.000Z", "cmd1"]
    ref = "consent:%s" % ":".join(K)
    h = audit.item_sha8("Bash(rm:*)")

    def merged(off=900, body=None, state="MERGED"):
        return lambda items: {"state": state, "mergedAt": iso(T0 + td(off)), "body": body if body is not None else "ok %s" % h}

    _, lines, _ = b_case(tmp, "a7-ok-pr", "PR#9", merged())
    chk("A7-0", "条件がそろった PR は異常にならない", not reasons(lines))
    _, lines, _ = b_case(tmp, "a7-open", "PR#9", merged(state="OPEN"))
    chk("A7-1", "PR が MERGED でないと B", "ABNORMAL_REASON=B user:permissions.deny %s" % h in lines)
    _, lines, _ = b_case(tmp, "a7-before", "PR#9", merged(off=300))
    chk("A7-2", "mergedAt が held より前だと B", "ABNORMAL_REASON=B user:permissions.deny %s" % h in lines)
    _, lines, _ = b_case(tmp, "a7-nobody", "PR#9", merged(body="no hash here"))
    chk("A7-3", "本文に item_hash が無いと B", "ABNORMAL_REASON=B user:permissions.deny %s" % h in lines)
    _, lines, _ = b_case(tmp, "a7-nogh", "PR#9", None)
    chk("A7-4", "gh が使えない（None）と B のまま", "ABNORMAL_REASON=B user:permissions.deny %s" % h in lines)
    _, lines, _ = b_case(tmp, "a7-c-none", ref, None)
    chk("A7-5", "consent: の3要素が同意の台帳に無いと B", "ABNORMAL_REASON=B user:permissions.deny %s" % h in lines)
    _, lines, _ = b_case(tmp, "a7-c-early", ref, None, consent_used=T0 + td(300), key3=K)
    chk("A7-6", "used_at が held より前だと B", "ABNORMAL_REASON=B user:permissions.deny %s" % h in lines)
    _, lines, _ = b_case(tmp, "a7-c-ok", ref, None, consent_used=T0 + td(900), key3=K)
    chk("A7-7", "同意の台帳に held より後の行があれば異常にならない", not reasons(lines))
    _, lines, items = b_case(tmp, "a7-c-twice", ref, None, consent_used=T0 + td(900), key3=K, second_ref=True)
    h2 = audit.item_sha8("Bash(mv:*)")
    bs = [x for x in lines if x.startswith("ABNORMAL_REASON=B ")]
    chk("A7-8", "同じ po_ref の2回目は B（1回目は通る）", len(bs) == 1 and bs[0].endswith(h2))
    # 追跡された repo: の差分は本文の item_hash を要らない
    e = light_env(tmp, "a7-repo", repo_dir=True)
    run_audit(e, T0, commit=True)
    mutate(e, "repo:hooks")
    hk = audit.read_ledger(e.home)
    snap_hooks = audit.collect_permissions(e.home, git_run=lambda a, c: (127, b""))["repo:hooks"]
    hh = audit.element_hash(snap_hooks[0])
    seed_row(e, T0 + td(600), sub="record", target="repo-hooks", item_hash=hh, category="reserved:R4", result="recorded", po_ref="PR#55", actor="opus")
    gh = lambda n: {"state": "MERGED", "mergedAt": iso(T0 + td(900)), "body": "no hash"}
    lines = run_audit(e, T0 + td(3600), gh=gh)
    chk("A7-9", "repo: の差分は PR 番号の record で照合し、本文の item_hash は要らない", not [x for x in reasons(lines) if "repo:hooks" in x])


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
    item = "Bash(wc -l review:*)"
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
    normal = "Bash(wc -l x:*)"
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
    code, _, _ = run_pc(e, apply_argv("user-allow", "add", "Bash(wc -l a:*)"))
    chk("A17-1e", "追跡外のファイルがあると exit 1（設定も台帳も変えない）", code == 1 and ledger_n(e) == n0 and "Bash(wc -l a:*)" not in load_json(e.settings)["permissions"]["allow"])
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
    code, out, _ = run_pc(e, apply_argv("user-allow", "add", "Bash(wc -l a1:*)"))
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
    code, _, _ = run_pc(e, apply_argv("user-allow", "add", "Bash(wc -l a2:*)"), git_run=offline)
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


def main():
    tmp = tempfile.mkdtemp(prefix="permdel-tests-")
    try:
        for fn in (test_a1, test_a2, test_a3, test_a4, test_a18, test_a5_a6, test_a7, test_a8, test_a9, test_a10,
                   test_a11_a12_a13, test_a14, test_a17):
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
