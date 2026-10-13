#!/usr/bin/env python3
"""S4 の道具の試験 (a)〜(e)。すべて一時ディレクトリのダミーで行う。

本物の ~/.claude/ には書かない（HOME も一時ディレクトリに差し替える）。
使い方: python3 -I test_sm_tools.py     終了コード: 0=全部合格 / 1=不合格あり
"""
import filecmp
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGN = os.path.join(HERE, os.pardir, "self-maintenance-design.md")
COUNT = os.path.join(HERE, "sm_count.py")
CHECK = os.path.join(HERE, "sm_check_entry.py")
K1K3 = os.path.join(HERE, "sm_k1_k3.py")
APPLY = os.path.join(HERE, "sm_apply.py")
TOOLS = (COUNT, CHECK, K1K3, APPLY)

TMP = tempfile.mkdtemp(prefix="sm-test-")
FAKE_HOME = os.path.join(TMP, "home")
os.makedirs(FAKE_HOME)
ENV = {**os.environ, "HOME": FAKE_HOME, "PYTHONDONTWRITEBYTECODE": "1"}
RESULTS = []

# 危険語はここで連結して作る（ファイルに直書きしない）
WORD_SSH = "ss" + "h"
WORD_ANY = "an" + "y"
WORD_DEL = "r" + "m -" + "r" + "f"
DUMMY_HOST = "198.51.100.7"
GOOD = "SM-2026-10-20-1: Allow running `git status` inside the worktree directory; matches only that command."


def run(script, *args, stdin=None):
    p = subprocess.run([sys.executable, "-I", script, *args], capture_output=True, text=True,
                       input=stdin, env=ENV)
    return p.returncode, p.stdout, p.stderr


def record(name, ok, detail=""):
    RESULTS.append(ok)
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  -- " + detail) if (detail and not ok) else ""))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_json(path, obj):
    write(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def jl(path, rows):
    write(path, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------- (a) 件数と試験時間帯の除外 ----------
def test_a():
    d = os.path.join(TMP, "a")
    NOW = "2026-10-13T00:00:00Z"
    reason = "Reason: [Self-Modification] blocked"
    denied = []
    for i in range(5):  # 窓の外・7日以内: 数える
        denied.append({"ts": "2026-10-12T0%d:00:00Z" % i, "tool_name": "Bash",
                       "tool_input": {"command": "cd /w && FOO=1 git push origin TOKEN=abc123"},
                       "reason": reason})
    for i in range(2):  # 試験の時間帯: 除く
        denied.append({"ts": "2026-10-11T10:0%d:00Z" % i, "tool_name": "Bash",
                       "tool_input": {"command": "git push origin x"}, "reason": reason})
    denied.append({"ts": "2026-10-01T00:00:00Z", "tool_name": "Bash",  # 7日より前: 除く
                   "tool_input": {"command": "git push origin x"}, "reason": reason})
    denied.append({"ts": "2026-10-12T09:00:00Z", "tool_name": "Bash",  # 理由なし
                   "tool_input": {"command": WORD_DEL + " /x"}})
    jl(os.path.join(d, "denied.jsonl"), denied)
    events = [{"ts": "2026-10-12T05:00:00Z", "type": "hook_blocked", "hook": "pr-body-guard",
               "reason": "BLOCKED [pr-body-guard]: x", "cmd_head": "gh pr create"} for _ in range(3)]
    events.append({"ts": "2026-10-12T05:00:00Z", "type": "other", "hook": "x"})
    events.append({"ts": "2026-10-11T10:00:30Z", "type": "hook_blocked", "hook": "pr-body-guard",
                   "reason": "BLOCKED [pr-body-guard]: x", "cmd_head": "gh pr create"})  # 窓の中
    jl(os.path.join(d, "events.jsonl"), events)
    write(os.path.join(d, "test-runs.log"),
          "2026-10-11T10:00:00Z 2026-10-11T10:30:00Z po-apply-stage2 real-home-test rc=0\n")
    base = ["--denied", os.path.join(d, "denied.jsonl"), "--events", os.path.join(d, "events.jsonl"),
            "--test-runs", os.path.join(d, "test-runs.log"), "--now", NOW]
    rc, out, err = run(COUNT, *base, "--format", "json")
    data = json.loads(out) if rc == 0 else {}
    shapes = {(s["entry"], s["reason_class"], s["command_head"]): s for s in data.get("shapes", [])}
    push = shapes.get(("permission-denied", "Self-Modification", "git push"))
    record("(a) 同じ形の件数=5（試験の窓2件・古い1件を除く）", bool(push) and push["count"] == 5, out[:300] + err)
    record("(a) 理由なしは no explanation として別の形（1件）",
           shapes.get(("permission-denied", "no explanation", WORD_DEL), {}).get("count") == 1)
    record("(a) hook_blocked の形の件数=3（窓内1件・他の型1件を除く）",
           shapes.get(("hook_blocked", "pr-body-guard", "gh pr"), {}).get("count") == 3)
    got = (data.get("total_denied"), data.get("total_hook_blocked"), data.get("excluded_test_records"))
    record("(a) 合計 denied=6・hook=3・除外=3", got == (6, 3, 3), str(got))
    record("(a) 代表例は最大3件・伏せ字（abc123 が出ない）",
           bool(push) and len(push["examples"]) == 3 and "abc123" not in out)
    rc, md, _ = run(COUNT, *base, "--format", "md")
    record("(a) Markdown の出力に表の行がある",
           rc == 0 and "| permission-denied | Self-Modification | git push | 5 |" in md, md[:300])


# ---------- (b) 足す文の判定 ----------
def test_b():
    d = os.path.join(TMP, "b")
    settings = os.path.join(d, "settings.json")
    write_json(settings, {"autoMode": {"allow": [], "environment": ["Dev host is %s (dummy)" % DUMMY_HOST]}})

    def check(text):
        return run(CHECK, "--text", text, "--design", DESIGN, "--settings", settings)[0]

    record("(b) 良い文は合格", check(GOOD) == 0)
    record("(b) allowed・install は全称の語に当たらない（単語単位）",
           check("SM-2026-10-20-2: Allow install of the allowed helper for `git status` only.") == 0)
    record("(b) 禁止語を含む文は不合格", check(GOOD + " Uses " + WORD_SSH + " too.") != 0)
    record("(b) 禁止語は部分一致で不合格（大文字でも）", check(GOOD + " " + WORD_SSH.upper() + "x") != 0)
    record("(b) 全称語を含む文は不合格", check(GOOD + " Works for " + WORD_ANY + " command.") != 0)
    long_text = "SM-2026-10-20-3: " + " ".join(["word"] * 119)
    n = len(long_text.split())
    record("(b) 120語ちょうどは合格（%d語）" % n, n == 120 and check(long_text) == 0)
    over = long_text + " extra"
    record("(b) 121語は不合格（%d語）" % len(over.split()), len(over.split()) == 121 and check(over) != 0)
    record("(b) 接頭辞が違う文は不合格", check("XX-2026-10-20-1: Allow running `git status` only.") != 0)
    record("(b) 日付の形が違う接頭辞は不合格", check("SM-2026-10-1-1: Allow running `git status` only.") != 0)
    record("(b) environment のホストのアドレスを含む文は不合格", check(GOOD + " Host " + DUMMY_HOST) != 0)
    rc, out, _ = run(CHECK, "--text", GOOD, "--design", os.path.join(d, "none.md"), "--settings", settings)
    record("(b) 設計書を読めないときは不合格に倒れる", rc != 0)
    rc, _o, _e = run(CHECK, "--design", DESIGN, "--settings", settings, stdin=GOOD)
    record("(b) 標準入力でも判定できる", rc == 0)


# ---------- (c) K1 / K3 ----------
def ledger_text(rows):
    head = ("| 日時 | 種別 | source | 結果 | 変更 | 理由 | 根拠の件数 | 報告書 | バックアップ | 試験 | PR |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|\n")
    body = ""
    for kind, result, change in rows:
        body += "| 2026-10-13 | %s | routine | %s | %s | r | - | - | - | - | - |\n" % (kind, result, change)
    return "# 台帳\n\n## 履歴\n\n| x |\n|---|\n| 履歴の行は読まない |\n\n## 記録\n\n" + head + body


def test_c():
    d = os.path.join(TMP, "c")
    base_allow = ["base one", "base two to remove", "base three"]
    baseline = {"autoMode": {"allow": base_allow, "soft_deny": ["s1"], "hard_deny": ["h1"], "environment": ["e1"]}}
    write_json(os.path.join(d, "baseline.json"), baseline)
    sm_a, sm_b = "SM-2026-10-20-1: first test entry", "SM-2026-10-20-2: second test entry"
    rows = [("結果", "適用", "add: " + sm_a), ("予定", "未適用", "add: " + sm_b),
            ("結果", "適用", "add: " + sm_b), ("結果", "戻した", "remove: " + sm_b),
            ("結果", "適用（PO）", "remove: base two to remove"),
            ("結果", "適用", "remove: " + sm_a)]
    # 「予定」「戻した」の行は当てない
    write(os.path.join(d, "ledger.md"), ledger_text(rows))
    final_allow = ["base one", "base three", sm_b]
    mode = {"allow": final_allow, "soft_deny": ["s1"], "hard_deny": ["h1"], "environment": ["e1"]}
    settings = os.path.join(d, "settings.json")
    write_json(settings, {"autoMode": mode, "permissions": {"deny": ["p"]}, "hooks": {"PreToolUse": []}})
    k1 = ["--k1", "--baseline", os.path.join(d, "baseline.json")]
    rc, out, _ = run(K1K3, *k1, "--ledger", os.path.join(d, "ledger.md"), "--settings", settings)
    record("(c) K1 は一致するとき「一致」(exit 0)", rc == 0 and json.loads(out)["k1"] == "一致", out)
    rows2 = rows + [("結果", "適用（PO）", "remove: sha256=%s 先頭20語「base three」" % sha("base three"))]
    write(os.path.join(d, "ledger2.md"), ledger_text(rows2))
    write_json(os.path.join(d, "settings2.json"), {"autoMode": {**mode, "allow": ["base one", sm_b]}})
    rc, out, _ = run(K1K3, *k1, "--ledger", os.path.join(d, "ledger2.md"),
                     "--settings", os.path.join(d, "settings2.json"))
    record("(c) K1 は remove(sha256) 行も当てて「一致」", rc == 0 and json.loads(out)["k1"] == "一致", out)
    write_json(os.path.join(d, "settings3.json"), {"autoMode": {**mode, "allow": ["base one", "base thrEE", sm_b]}})
    rc, out, _ = run(K1K3, *k1, "--ledger", os.path.join(d, "ledger.md"),
                     "--settings", os.path.join(d, "settings3.json"))
    record("(c) K1 は1件変えると「不一致」(exit 1)", rc == 1 and json.loads(out)["k1"] == "不一致", out)

    scripts = os.path.join(d, "scripts")
    write(os.path.join(scripts, "hook-a.sh"), "echo a\n")
    write(os.path.join(scripts, "sub", "b.py"), "print('b')\n")
    hooktest = os.path.join(d, "test-agent-hooks.sh")
    write(hooktest, "echo test\n")
    prev = os.path.join(d, "logs", "prev.json")
    os.makedirs(os.path.dirname(prev))
    k3 = ["--k3", "--settings", settings, "--design", DESIGN, "--scripts-dir", scripts,
          "--hook-test", hooktest, "--prev", prev]
    rc, out, _ = run(K1K3, *k3)
    record("(c) K3 初回は「初回」(exit 0)・--save なしでは書かない",
           rc == 0 and json.loads(out)["k3"] == "初回" and not os.path.exists(prev), out)
    rc, out, _ = run(K1K3, *k3, "--save")
    record("(c) K3 --save で前回の値を保存（権限 600）",
           rc == 0 and os.path.isfile(prev) and (os.stat(prev).st_mode & 0o777) == 0o600, out)
    rc, out, _ = run(K1K3, *k3)
    record("(c) K3 同じなら「同じ」(exit 0)", rc == 0 and json.loads(out)["k3"] == "同じ", out)
    write_json(settings, {"autoMode": {**mode, "allow": final_allow + ["SM-2026-10-21-1: third"]},
                          "permissions": {"deny": ["p"]}, "hooks": {"PreToolUse": []}})
    rc, out, _ = run(K1K3, *k3)
    record("(c) K3 SM- の文を足しても「同じ」", rc == 0 and json.loads(out)["k3"] == "同じ", out)
    write(os.path.join(scripts, "hook-a.sh"), "echo changed\n")
    rc, out, _ = run(K1K3, *k3)
    res = json.loads(out)
    record("(c) K3 スクリプトを変えると「変化あり」(exit 1) で名前が出る",
           rc == 1 and res["k3"] == "変化あり" and "scripts/hook-a.sh" in res["changed"], out)
    write(os.path.join(scripts, "hook-a.sh"), "echo a\n")
    write_json(settings, {"autoMode": {**mode, "allow": ["base one CHANGED", "base three", sm_b]},
                          "permissions": {"deny": ["p"]}, "hooks": {"PreToolUse": []}})
    rc, out, _ = run(K1K3, *k3)
    record("(c) K3 SM- でない allow を変えると「変化あり」",
           rc == 1 and "allow(non-SM)" in json.loads(out)["changed"], out)


# ---------- (d) add / remove / recover ----------
def test_d():
    d = os.path.join(TMP, "d")
    settings = os.path.join(d, "settings.json")
    pending = os.path.join(d, "logs", "pending.json")
    original = os.path.join(d, "original.json")
    write_json(settings, {"model": "x", "autoMode": {"allow": ["keep one", "keep two"], "soft_deny": ["s"],
                                                      "environment": ["Dev host is %s" % DUMMY_HOST]},
                          "permissions": {"deny": []}})
    shutil.copy2(settings, original)
    common = ["--settings", settings, "--pending", pending, "--design", DESIGN]

    rc, out, err = run(APPLY, "add", "--text", GOOD, *common)
    with open(settings, encoding="utf-8") as f:
        data = json.load(f)
    pend = {}
    if os.path.isfile(pending):
        with open(pending, encoding="utf-8") as f:
            pend = json.load(f)
    baks = glob.glob(settings + ".bak-*")
    record("(d) add: 追加・バックアップ・pending.json ができる",
           rc == 0 and data["autoMode"]["allow"][-1] == GOOD and len(baks) == 1
           and pend.get("statement") == GOOD, out + err)
    record("(d) add: バックアップは元と同一(cmp)", len(baks) == 1 and filecmp.cmp(baks[0], original, shallow=False))
    rc, _o, err = run(APPLY, "add", "--text", "SM-2026-10-20-9: second", *common)
    record("(d) pending.json が残っているあいだは変更を拒否", rc == 1 and "pending" in err, err)
    rc, out, err = run(APPLY, "recover", *common)
    record("(d) add → recover で元と同一(cmp)", rc == 0 and filecmp.cmp(settings, original, shallow=False), out + err)
    record("(d) recover: pending.json は .done-<日時> に改名",
           not os.path.exists(pending) and len(glob.glob(pending + ".done-*")) == 1)

    rc, _o, _e = run(APPLY, "add", "--text", GOOD, *common)
    run(APPLY, "--clear-pending", "--pending", pending)
    record("(d) --clear-pending で pending.json が消える", rc == 0 and not os.path.exists(pending))
    rc, out, err = run(APPLY, "remove", "--text", GOOD, *common)
    record("(d) add → remove で元と同一(cmp)", rc == 0 and filecmp.cmp(settings, original, shallow=False), out + err)
    run(APPLY, "--clear-pending", "--pending", pending)

    def snapshot():
        with open(settings, "rb") as f:
            return f.read()

    before = snapshot()
    rc, _o, err = run(APPLY, "remove", "--text", "keep one", *common)
    record("(d) SM- でない文の remove は拒否・ファイル不変・pending 作らない",
           rc == 1 and snapshot() == before and not os.path.exists(pending), err)
    rc, _o, err = run(APPLY, "add", "--text", "not SM prefixed", *common)
    record("(d) SM- でない文の add は拒否", rc == 1 and snapshot() == before, err)
    rc, _o, err = run(APPLY, "add", "--text", GOOD + " " + WORD_SSH, *common)
    record("(d) 禁止語を含む文の add は拒否・ファイル不変",
           rc == 1 and snapshot() == before and not os.path.exists(pending), err)
    write_json(pending, {"statement": "keep two"})
    rc, _o, err = run(APPLY, "recover", *common)
    record("(d) pending に SM- でない文があれば recover は拒否・不変", rc == 1 and snapshot() == before, err)


# ---------- (e) py_compile ----------
def test_e():
    for path in TOOLS + (os.path.abspath(__file__),):
        p = subprocess.run([sys.executable, "-I", "-m", "py_compile", path], capture_output=True, text=True,
                           env=ENV)
        record("(e) py_compile %s" % os.path.basename(path), p.returncode == 0, p.stderr)
    record("(e) 試験用 HOME に何も書かれていない", os.listdir(FAKE_HOME) == [])


def main():
    try:
        for fn in (test_a, test_b, test_c, test_d, test_e):
            fn()
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    passed = sum(1 for r in RESULTS if r)
    print("\nPASS=%d FAIL=%d" % (passed, len(RESULTS) - passed))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
