# 設計: docs/handoff/guard-add-by-ai/design.md §13-6・§13-8 / カード card-bin2.md §6
"""install-guard.sh の試験。使い方: python3 scripts/agent-hooks/test_install_guard.py。標準ライブラリのみ。

本物の ~/.claude・~/.salesanchor-tools・GitHub には触れない。試験ごとに一時の HOME と bare の origin を作り、
perm-change.py は偽物（受けた引数を record-calls.jsonl に足すだけ）に差し替える。
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SCRIPT_SRC = os.path.join(HERE, "install-guard.sh")
AUDIT_SRC = os.path.join(REPO, "scripts", "dev", "consent-audit.py")
PATH = os.environ["PATH"]
GIT_ID = {"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
          "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid"}

FAKE_PERM = '''import json, os, sys
home = os.environ["HOME"]
with open(os.path.join(home, "record-calls.jsonl"), "a", encoding="utf-8") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")
a = sys.argv[1:]
if os.path.exists(os.path.join(home, "fake-fail-remove")) and "--op" in a and a[a.index("--op") + 1] == "remove":
    sys.stderr.write("fake refuse\\n")
    sys.exit(1)
sys.exit(0)
'''

GUARD_PY = "import sys\nsys.stdin.read()\nsys.exit(0)\n"
TEST_PY = ("import os, sys\n"
           "sys.exit(0 if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]) else 1)\n")
VM_CMD = "/usr/bin/python3 %s/.claude/scripts/mac-vm-guard.py"

_clock = [0]
TMPS = []


def sh(cmd, cwd=None, env=None, check=True):
    e = dict(os.environ, **GIT_ID)
    e.update(env or {})
    p = subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError("コマンドが失敗: %s\n%s%s" % (cmd, p.stdout, p.stderr))
    return p


def git(cwd, *a, check=True):
    _clock[0] += 1
    d = "2026-01-01T00:%02d:%02d+00:00" % (_clock[0] // 60 % 60, _clock[0] % 60)
    return sh(["git", "-C", cwd] + list(a), env={"GIT_AUTHOR_DATE": d, "GIT_COMMITTER_DATE": d}, check=check)


def wfile(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def sha_bytes(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def tree(root):
    out = {}
    for r, _d, names in os.walk(root):
        for n in names:
            p = os.path.join(r, n)
            with open(p, "rb") as f:
                out[os.path.relpath(p, root)] = f.read()
    return out


class Env:
    def __init__(self, shallow=False, manifest=None, files=None, settings=None, name="demo-guard", build=True):
        self.home = tempfile.mkdtemp(prefix="ig-")
        TMPS.append(self.home)
        self.name = name
        self.origin = os.path.join(self.home, "origin.git")
        self.work = os.path.join(self.home, "work")
        self.tools = os.path.join(self.home, ".salesanchor-tools")
        self.claude = os.path.join(self.home, ".claude")
        self.settings = os.path.join(self.claude, "settings.json")
        self.calls = os.path.join(self.home, "record-calls.jsonl")
        self.pr = 0
        sh(["git", "init", "--bare", "-b", "main", self.origin])
        sh(["git", "clone", self.origin, self.work])
        git(self.work, "checkout", "-B", "main")
        wfile(os.path.join(self.work, "scripts/agent-hooks/install-guard.sh"), open(SCRIPT_SRC, encoding="utf-8").read())
        wfile(os.path.join(self.work, "scripts/dev/consent-audit.py"), open(AUDIT_SRC, encoding="utf-8").read())
        wfile(os.path.join(self.work, "scripts/dev/perm-change.py"), FAKE_PERM)
        git(self.work, "add", "-A")
        git(self.work, "commit", "-m", "base")
        git(self.work, "push", "-u", "origin", "main")
        if build:
            self.merge_guard(manifest, files)
        if shallow:
            sh(["git", "clone", "--depth", "1", "file://" + self.origin, self.tools])
        else:
            sh(["git", "clone", self.origin, self.tools])
        os.makedirs(self.claude, exist_ok=True)
        if settings is None:
            settings = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
                {"type": "command", "command": VM_CMD % self.home, "timeout": 5}]}]}}
        if isinstance(settings, str):
            wfile(self.settings, settings)
        else:
            wfile(self.settings, json.dumps(settings, indent=2) + "\n")

    def manifest(self, matcher="Bash", after="mac-vm-guard.py", files=("guard.py",), tests=("test_guard.py",),
                 event="PreToolUse"):
        hk = {"event": event, "interpreter": "python3", "file": files[0]}
        if matcher is not None:
            hk["matcher"] = matcher
        if after is not None:
            hk["after"] = after
        return {"name": self.name, "files": list(files), "hooks": [hk], "tests": list(tests)}

    def merge_guard(self, manifest=None, files=None, merge=True, pull=False):
        """見張りのフォルダを PR のマージの形で main に入れる。files: {相対名: 中身}"""
        self.pr += 1
        base = os.path.join(self.work, "scripts/agent-hooks", self.name)
        if files is None:
            files = {"guard.py": GUARD_PY, "test_guard.py": TEST_PY}
        if manifest is None:
            manifest = self.manifest()
        git(self.work, "checkout", "-b", "feat%d" % self.pr)
        for k, v in files.items():
            wfile(os.path.join(base, k), v)
        if manifest != "none":
            wfile(os.path.join(base, "guard-manifest.json"), json.dumps(manifest) + "\n")
        git(self.work, "add", "-A")
        git(self.work, "commit", "-m", "feat %d" % self.pr)
        git(self.work, "checkout", "main")
        if merge:
            git(self.work, "merge", "--no-ff", "-m", "Merge pull request #%d from x/y" % self.pr, "feat%d" % self.pr)
        else:
            git(self.work, "merge", "--ff-only", "feat%d" % self.pr)
        git(self.work, "push", "origin", "main")
        if pull:
            git(self.tools, "pull", "--ff-only")

    def run(self, *args, extra_env=None):
        env = {"HOME": self.home, "PATH": PATH, "GIT_CONFIG_NOSYSTEM": "1"}
        env.update(extra_env or {})
        script = os.path.join(self.tools, "scripts/agent-hooks/install-guard.sh")
        p = subprocess.run(["bash", script] + list(args or [self.name]), env=env, capture_output=True,
                           text=True, timeout=600)
        lines = [ln for ln in p.stdout.split("\n") if ln != ""]
        return p.returncode, lines, p.stdout + p.stderr

    def calls_list(self):
        if not os.path.exists(self.calls):
            return []
        with open(self.calls, encoding="utf-8") as f:
            return [json.loads(ln) for ln in f if ln.strip()]

    def snap(self):
        return {"settings": sha_bytes(self.settings),
                "scripts": tree(os.path.join(self.claude, "scripts")) if os.path.isdir(os.path.join(self.claude, "scripts")) else {}}

    def load_settings(self):
        with open(self.settings, encoding="utf-8") as f:
            return json.load(f)


def arg_of(call, flag):
    return call[call.index(flag) + 1] if flag in call else None


def assert_stopped(env, before, rc, lines, full):
    assert lines and lines[-1].startswith("INSTALL_FAILED:"), "最後の行が INSTALL_FAILED でない: %r" % full[-300:]
    assert rc == 1, "終了コード %r" % rc
    after = env.snap()
    assert after["settings"] == before["settings"], "settings.json が変わった"
    assert after["scripts"] == before["scripts"], "~/.claude/scripts が変わった"
    assert env.calls_list() == [], "記録が書かれた"


def stopped_case(env, *args, extra_env=None):
    before = env.snap()
    rc, lines, full = env.run(*args, extra_env=extra_env)
    assert_stopped(env, before, rc, lines, full)


# ── 試験 ────────────────────────────────────────────────────────────

def test_g7_a_install():
    e = Env()
    rc, lines, full = e.run()
    assert rc == 0 and lines[-1] == "INSTALL_OK", full
    assert "PR=#1" in lines
    s = e.load_settings()
    grp = s["hooks"]["PreToolUse"][0]["hooks"]
    cmd = "python3 %s/.claude/scripts/demo-guard/guard.py" % e.home
    assert [h["command"] for h in grp] == [VM_CMD % e.home, cmd], grp
    assert grp[0].get("timeout") == 5
    assert sum(1 for g in s["hooks"]["PreToolUse"] for h in g["hooks"] if h["command"] == cmd) == 1
    dst = os.path.join(e.claude, "scripts/demo-guard/guard.py")
    assert oct(os.stat(dst).st_mode & 0o777) == "0o555"
    c = e.calls_list()
    assert len(c) == 3, c
    kinds = sorted((arg_of(x, "--target"), arg_of(x, "--op")) for x in c)
    assert kinds == [("hook-files", "add"), ("user-hooks", "add"), ("user-hooks", "remove")], kinds
    for x in c:
        assert arg_of(x, "--po-ref") == "PR#1"
    ua = [x for x in c if arg_of(x, "--target") == "user-hooks" and arg_of(x, "--op") == "add"][0]
    ur = [x for x in c if arg_of(x, "--target") == "user-hooks" and arg_of(x, "--op") == "remove"][0]
    assert arg_of(ur, "--replaced-by") == arg_of(ua, "--item-hash")
    assert arg_of(ur, "--batch") and arg_of(ur, "--batch") == arg_of(ua, "--batch")
    assert arg_of(ur, "--old-json"), "old-json が無い"
    assert not any(x for x in c if arg_of(x, "--target") == "hook-files" and arg_of(x, "--op") == "remove")


def test_g7_b_second_run_no_change():
    e = Env()
    e.run()
    sha1 = sha_bytes(e.settings)
    n = len(e.calls_list())
    rc, lines, full = e.run()
    assert rc == 0 and lines[-1] == "INSTALL_OK" and "NO_CHANGE" in lines, full
    s = e.load_settings()
    cmd = "python3 %s/.claude/scripts/demo-guard/guard.py" % e.home
    assert sum(1 for g in s["hooks"]["PreToolUse"] for h in g["hooks"] if h["command"] == cmd) == 1
    assert sha_bytes(e.settings) == sha1
    assert len(e.calls_list()) == n


def test_g7_c_new_group():
    e = Env(manifest=None)
    e.merge_guard(manifest=e.manifest(matcher="Write", after="nothing.py"))
    git(e.tools, "pull", "--ff-only")
    rc, lines, full = e.run()
    assert rc == 0 and lines[-1] == "INSTALL_OK", full
    groups = e.load_settings()["hooks"]["PreToolUse"]
    assert groups[-1]["matcher"] == "Write" and len(groups[-1]["hooks"]) == 1
    assert len(groups[0]["hooks"]) == 1
    kinds = sorted((arg_of(x, "--target"), arg_of(x, "--op")) for x in e.calls_list())
    assert kinds == [("hook-files", "add"), ("user-hooks", "add")], kinds


def test_g7_d_body_change():
    e = Env()
    e.run()
    old8 = sha_bytes(os.path.join(e.claude, "scripts/demo-guard/guard.py"))[:8]
    n = len(e.calls_list())
    new_body = GUARD_PY + "# changed\n"
    e.merge_guard(files={"guard.py": new_body, "test_guard.py": TEST_PY}, pull=True)
    settings_before = sha_bytes(e.settings)
    rc, lines, full = e.run()
    assert rc == 0 and lines[-1] == "INSTALL_OK", full
    new8 = hashlib.sha256(new_body.encode()).hexdigest()[:8]
    assert any(ln.startswith("FILE demo-guard/guard.py") for ln in lines), lines
    c = e.calls_list()[n:]
    got = sorted((arg_of(x, "--target"), arg_of(x, "--op"), arg_of(x, "--item-hash")) for x in c)
    assert got == sorted([("hook-files", "remove", old8), ("hook-files", "add", new8)]), got
    assert all(arg_of(x, "--po-ref") == "PR#2" for x in c)
    assert sha_bytes(e.settings) == settings_before


def test_g9_a_untracked():
    e = Env()
    wfile(os.path.join(e.tools, "stray.txt"), "x\n")
    stopped_case(e)


def test_g9_b_head_differs():
    e = Env()
    other = os.path.join(e.home, "other")
    sh(["git", "clone", e.origin, other])
    wfile(os.path.join(other, "extra.txt"), "x\n")
    git(other, "add", "-A")
    git(other, "commit", "-m", "extra")
    git(other, "push", "origin", "main")
    stopped_case(e)


def test_g9_c_bad_names():
    e = Env()
    for a in (["Demo"], ["../x"], ["demo-guard", "demo-guard"], []):
        before = e.snap()
        rc, lines, full = e.run(*a) if a else _run_noargs(e)
        assert_stopped(e, before, rc, lines, full)


def _run_noargs(e):
    env = {"HOME": e.home, "PATH": PATH, "GIT_CONFIG_NOSYSTEM": "1"}
    p = subprocess.run(["bash", os.path.join(e.tools, "scripts/agent-hooks/install-guard.sh")], env=env,
                       capture_output=True, text=True, timeout=600)
    return p.returncode, [ln for ln in p.stdout.split("\n") if ln != ""], p.stdout + p.stderr


def test_a4_s_bad_manifests():
    def mk(**kw):
        e = Env(build=False)
        e.merge_guard(**kw)
        git(e.tools, "pull", "--ff-only", check=False)
        return e

    e = mk(manifest="none")
    stopped_case(e)
    e = Env(build=False)
    bad = dict(e.manifest(), files=["../x.py"],
               hooks=[{"event": "PreToolUse", "interpreter": "python3", "file": "../x.py"}])
    e.merge_guard(manifest=bad)
    git(e.tools, "pull", "--ff-only", check=False)
    stopped_case(e)
    e = Env(build=False)
    bad = dict(e.manifest(), files=["/x.py"],
               hooks=[{"event": "PreToolUse", "interpreter": "python3", "file": "/x.py"}])
    e.merge_guard(manifest=bad)
    git(e.tools, "pull", "--ff-only", check=False)
    stopped_case(e)
    e = Env(build=False)
    e.merge_guard(manifest=e.manifest(event="Notification"))
    git(e.tools, "pull", "--ff-only", check=False)
    stopped_case(e)
    e = Env()
    wfile(os.path.join(e.work, "scripts/agent-hooks/plainfile"), "x\n")
    git(e.work, "add", "-A")
    git(e.work, "commit", "-m", "plain")
    git(e.work, "push", "origin", "main")
    git(e.tools, "pull", "--ff-only")
    stopped_case(e, "plainfile")


def test_a8_s_bad_words():
    bodies = ['x = "permissionDecision allow"\n', "approve\n", "updatedInput\n", "updatedPermissions\n",
              "updatedToolOutput\n", "behavior\n", "additionalContext\n"]
    for b in bodies:
        e = Env(files={"guard.py": GUARD_PY + b, "test_guard.py": TEST_PY})
        stopped_case(e)


def test_a8_n_allowed_words():
    e = Env(files={"guard.py": GUARD_PY, "test_guard.py": TEST_PY + "# --approve\n"})
    rc, lines, full = e.run()
    assert rc == 0 and lines[-1] == "INSTALL_OK", full
    e = Env(files={"guard.py": GUARD_PY + "# APPROVE\n", "test_guard.py": TEST_PY})
    rc, lines, full = e.run()
    assert rc == 0 and lines[-1] == "INSTALL_OK", full


def test_a11_s_shallow():
    e = Env(shallow=True)
    stopped_case(e)


def test_s_bad_settings():
    e = Env(settings="this is not json\n")
    stopped_case(e)
    assert not os.path.exists(os.path.join(e.claude, "scripts/demo-guard"))
    assert not os.path.exists(os.path.join(e.claude, ".install-guard.lock"))


def test_p_fail_second_file():
    e = Env(manifest=None, build=False)
    mf = e.manifest(files=("guard.py", "lib.py"))
    e.merge_guard(manifest=mf, files={"guard.py": GUARD_PY, "lib.py": "X = 1\n", "test_guard.py": TEST_PY})
    git(e.tools, "pull", "--ff-only", check=False)
    os.makedirs(os.path.join(e.claude, "scripts/demo-guard/lib.py"))
    before = sha_bytes(e.settings)
    rc, lines, full = e.run()
    assert lines[-1].startswith("INSTALL_FAILED:"), full
    assert rc == 1
    assert sha_bytes(e.settings) == before
    assert not os.path.exists(os.path.join(e.claude, ".install-guard.lock"))
    c = e.calls_list()
    assert len(c) == 1 and arg_of(c[0], "--target") == "hook-files" and arg_of(c[0], "--op") == "add", c


def test_p_oserr():
    e = Env(manifest=None, build=False)
    mf = e.manifest(files=("guard.py", "sub/lib.py"))
    e.merge_guard(manifest=mf, files={"guard.py": GUARD_PY, "sub/lib.py": "X = 1\n", "test_guard.py": TEST_PY})
    git(e.tools, "pull", "--ff-only", check=False)
    os.makedirs(os.path.join(e.claude, "scripts/demo-guard"))
    wfile(os.path.join(e.claude, "scripts/demo-guard/sub"), "plain file\n")
    before = sha_bytes(e.settings)
    rc, lines, full = e.run()
    assert lines[-1].startswith("INSTALL_FAILED:"), full
    assert "想定外の止まり方" not in full, full
    assert rc == 1
    assert sha_bytes(e.settings) == before
    assert not os.path.exists(os.path.join(e.claude, ".install-guard.lock"))
    c = e.calls_list()
    assert len(c) == 1 and arg_of(c[0], "--target") == "hook-files" and arg_of(c[0], "--op") == "add", c
    g8 = hashlib.sha256(GUARD_PY.encode()).hexdigest()[:8]
    assert arg_of(c[0], "--item-hash") == g8, c


def test_t_fail_test_exit1():
    e = Env(files={"guard.py": GUARD_PY, "test_guard.py": "import sys\nsys.exit(1)\n"})
    stopped_case(e)
    assert not os.path.exists(os.path.join(e.claude, "scripts/demo-guard"))


def test_t_sub_non_merge():
    e = Env(build=False)
    e.merge_guard(merge=False)
    git(e.tools, "pull", "--ff-only", check=False)
    stopped_case(e)


def test_r_fail_record():
    e = Env()
    wfile(os.path.join(e.home, "fake-fail-remove"), "1\n")
    rc, lines, full = e.run()
    assert lines[-1] == "INSTALL_OK_RECORD_INCOMPLETE" and rc == 3, full
    assert sum(1 for ln in lines if ln.startswith("RECORD_FAILED:")) == 1, lines


def test_l_lock_preexisting():
    e = Env()
    lock = os.path.join(e.claude, ".install-guard.lock")
    os.mkdir(lock)
    before = e.snap()
    rc, lines, full = e.run()
    assert_stopped(e, before, rc, lines, full)
    assert os.path.isdir(lock), "台本が自分で作っていない lock を消した"


def test_e_env_claude_dir_ignored():
    e = Env()
    other = os.path.join(e.home, "elsewhere")
    rc, lines, full = e.run(extra_env={"CLAUDE" + "_DIR": other})
    assert rc == 0 and lines[-1] == "INSTALL_OK", full
    assert not os.path.exists(other), "別のフォルダに作られた"
    assert os.path.isfile(os.path.join(e.claude, "scripts/demo-guard/guard.py"))


def test_m_real_mac_test_guard():
    e = Env(name="mac-test-guard", build=False)
    src = os.path.join(HERE, "mac-test-guard")
    files = {}
    for n in ("guard.py", "test_guard.py"):
        with open(os.path.join(src, n), encoding="utf-8") as f:
            files[n] = f.read()
    with open(os.path.join(src, "guard-manifest.json"), encoding="utf-8") as f:
        mf = json.load(f)
    e.merge_guard(manifest=mf, files=files)
    git(e.tools, "pull", "--ff-only", check=False)
    rc, lines, full = e.run()
    assert rc == 0 and lines[-1] == "INSTALL_OK", full
    grp = e.load_settings()["hooks"]["PreToolUse"][0]["hooks"]
    assert [h["command"] for h in grp] == [VM_CMD % e.home,
                                           "python3 %s/.claude/scripts/mac-test-guard/guard.py" % e.home], grp


def main():
    p = f = 0
    for name in sorted(n for n in globals() if n.startswith("test_")):
        try:
            globals()[name]()
            p += 1
            print("ok   %s" % name)
        except Exception:
            f += 1
            print("FAIL %s" % name)
            traceback.print_exc()
    for t in TMPS:
        shutil.rmtree(t, ignore_errors=True)
    print("PASS=%d FAIL=%d" % (p, f))
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
