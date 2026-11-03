#!/usr/bin/env python3
"""prod-login-match-tests.py - consent-audit.py --prod-logins の受け入れ試験 T1〜T14。

すべて一時ディレクトリの作り物の記録・入室のファイルで行う。本物の ~/.claude・auth.log・~/.ssh には触らない。
使い方: python3 -I -B scripts/dev/prod-login-match-tests.py
"""
import contextlib
import datetime
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
UTC = datetime.timezone.utc
D0 = datetime.datetime(2026, 11, 2, 0, 0, 0, tzinfo=UTC)
MAC = "49.128.148.145"
KEY = "~/.ssh/manual-only/id_ed25519"
IDS = {"prod1": [KEY], "49.212.137.46": ["~/.ssh/salesanchor-claude"]}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


audit = load("consent_audit_pl", os.path.join(HERE, "consent-audit.py"))
PASS = FAIL = 0
TMPS = []


def report(name, ok, desc):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print("%s %s %s" % ("PASS" if ok else "FAIL", name, desc))


def resolve(h):
    return IDS.get(h, [])


def no_files(p):
    return None


def tmp():
    d = tempfile.mkdtemp(prefix="plm-")
    TMPS.append(d)
    return d


def iso(sec):
    return (D0 + datetime.timedelta(seconds=sec)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def at(sec):
    return D0 + datetime.timedelta(seconds=sec)


def use(sec, tid, cmd, name="Bash", bg=False, side=False):
    inp = {"command": cmd}
    if bg:
        inp["run_in_background"] = True
    r = {"type": "assistant", "timestamp": iso(sec),
         "message": {"content": [{"type": "tool_use", "id": tid, "name": name, "input": inp}]}}
    if side:
        r["isSidechain"] = True
    return r


def res(sec, tid, text="ok"):
    return {"type": "user", "timestamp": iso(sec),
            "message": {"content": [{"type": "tool_result", "tool_use_id": tid, "content": text}]}}


def note(sec, tid):
    return {"type": "user", "timestamp": iso(sec),
            "message": {"content": "<task-notification><tool-use-id>%s</tool-use-id></task-notification>" % tid}}


def bang(sec, text):
    return {"type": "user", "timestamp": iso(sec), "message": {"content": text}}


def write(home, rel, recs):
    p = os.path.join(home, ".claude", "projects", "proj", rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return p


def windows(home, read_file=no_files):
    since = datetime.datetime(2026, 1, 1, tzinfo=UTC)
    until = datetime.datetime(2027, 1, 1, tzinfo=UTC)
    return audit.pl_load_windows(os.path.join(home, ".claude", "projects"), since, until, resolve, read_file)


def classify(home, secs, src=MAC, read_file=no_files):
    ws, st = windows(home, read_file)
    logins = [{"t": at(s), "host": "prod1", "src": src} for s in secs]
    return [c["class"] for c in audit.pl_classify(logins, ws, MAC)], st


def uk(cmd, rf=no_files):
    return audit.pl_uses_key(cmd, resolve, rf)


def t1():
    d = tmp()
    p = os.path.join(d, "a.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write("2026-11-02T23:45:10.398968+09:00 h sshd[1]: Accepted publickey for ubuntu from 49.128.148.145 port 5 ssh2: ED25519 SHA256:x\n")
        f.write("2026-11-02T23:45:11.000000+09:00 h sshd[1]: Failed password for ubuntu from 1.2.3.4 port 5 ssh2\n")
        f.write("garbage-time h sshd[1]: Accepted publickey for ubuntu from 1.2.3.4 port 5 ssh2\n")
    r = audit.pl_parse_auth(p, "prod1")
    ok = (len(r) == 1 and r[0]["t"] == datetime.datetime(2026, 11, 2, 14, 45, 10, 398968, tzinfo=UTC)
          and r[0]["src"] == MAC and r[0]["host"] == "prod1")
    report("T1", ok, "Accepted の行だけ数え、時刻は UTC に直る（件数 %d）" % len(r))


def t2():
    d = tmp()
    write(d, "c1111111.jsonl", [use(0, "toolu_1", "ssh -i %s ubuntu@49.212.137.46 uptime" % KEY), res(10, "toolu_1")])
    c, _ = classify(d, [13.0, 13.5, -3.0, -3.5])
    ok = (c[0] == "説明済み: メインの会話" and c[1] == "要確認: 記録なし"
          and c[2] == "説明済み: メインの会話" and c[3] == "要確認: 記録なし")
    report("T2", ok, "窓の前後 3 秒の境目（%s）" % ",".join(c))


def t3():
    ok = (uk('ssh prod1 "df -h"') == "yes" and uk("ssh 49.212.137.46 x") == "no"
          and uk("ssh -o BatchMode=yes prod1 'x'") == "yes" and uk("ssh -p 22 prod1 x") == "yes"
          and uk("ssh ubuntu@prod1 x") == "yes" and uk("scp a prod1:/tmp/") == "yes"
          and uk('rsync -e "ssh -i ~/.ssh/manual-only/k" a b:/c') == "yes"
          and uk("ssh -o IdentityFile=~/.ssh/manual-only/k 1.2.3.4 x") == "yes")
    d = tmp()
    write(d, "c1111111.jsonl", [use(0, "toolu_1", "ssh 49.212.137.46 x"), res(5, "toolu_1")])
    c, _ = classify(d, [2])
    report("T3", ok and c[0] == "要確認: 関係の無い実行だけ", "別名の解決と各形（重なり: %s）" % c[0])


def t4():
    d = tmp()
    write(d, "c1111111.jsonl", [use(0, "toolu_1", "ssh prod1 sleep", bg=True), res(1, "toolu_1"), note(600, "toolu_1")])
    c, st = classify(d, [300])
    ok1 = c[0] == "説明済み: メインの会話" and st["noend"] == 0
    d2 = tmp()
    write(d2, "c1111111.jsonl", [use(0, "toolu_1", "ssh prod1 sleep", bg=True), res(1, "toolu_1"), bang(900, "x toolu_z")])
    c2, st2 = classify(d2, [300])
    ok2 = c2[0] == "説明済み: メインの会話" and st2["noend"] == 1
    report("T4", ok1 and ok2, "背景実行は知らせまで／知らせ無しはファイルの最後まで（noend=%d）" % st2["noend"])


def t5():
    d = tmp()
    write(d, "c1111111.jsonl", [use(0, "toolu_1", "ssh prod1 x"), res(1, "toolu_1", "Command moved to the background"),
                                note(600, "toolu_1")])
    c, _ = classify(d, [300])
    d2 = tmp()
    write(d2, "c1111111.jsonl", [use(0, "toolu_1", "ssh prod1 tail -f x", name="Monitor"), res(1, "toolu_1"),
                                 note(600, "toolu_1")])
    c2, _ = classify(d2, [300])
    ok = c[0] == "説明済み: メインの会話" and c2[0] == "説明済み: メインの会話"
    report("T5", ok, "moved to the background と Monitor も T4 と同じ")


def t6():
    d = tmp()
    write(d, "c1111111.jsonl", [bang(0, "<bash-input>ssh prod1 ls</bash-input>"), bang(5, "<bash-stdout>x</bash-stdout>")])
    c, _ = classify(d, [3])
    report("T6", c[0] == "説明済み: PO の !", "! の入力と出力の間（%s）" % c[0])


def t7():
    d = tmp()
    write(d, os.path.join("c2222222", "subagents", "agent-a.jsonl"), [use(0, "toolu_1", "ssh prod1 x"), res(5, "toolu_1")])
    c, _ = classify(d, [2])
    d2 = tmp()
    write(d2, "c3333333.jsonl", [use(0, "toolu_1", "ssh prod1 x", side=True), res(5, "toolu_1")])
    c2, _ = classify(d2, [2])
    d3 = tmp()
    write(d3, "c4444444.jsonl", [use(0, "toolu_1", "ssh prod1 x"), res(5, "toolu_1")])
    write(d3, os.path.join("c4444444", "subagents", "agent-a.jsonl"), [use(0, "toolu_2", "ssh prod1 y"), res(5, "toolu_2")])
    c3, _ = classify(d3, [2])
    ok = all(x[0] == "異常: 担当が使った" for x in (c, c2, c3))
    report("T7", ok, "担当は異常（%s / %s / %s）" % (c[0], c2[0], c3[0]))


def t8():
    h1 = "cat > /tmp/README.md <<'EOF'\nssh -i ~/.ssh/manual-only/k prod1\nEOF"
    h2 = "tee /tmp/a <<EOF\nssh prod1 ls\nEOF"
    ok = (uk(h1) == "no" and uk(h2) == "no" and uk("bash <<'EOF'\nssh prod1 ls\nEOF") == "yes"
          and uk('bash -c "ssh prod1 ls"') == "yes" and uk("ssh prod1 <<'EOF'\nls\nEOF") == "yes")
    report("T8", ok, "書くだけの heredoc は消し、それ以外は見る")


def t9():
    cmd = "bash /abs/run.sh"
    calls = []

    def rf_for(content):
        def rf(p):
            calls.append(p)
            return content
        return rf
    ok = (uk(cmd, rf_for("ssh -i ~/.ssh/manual-only/k 1.2.3.4 x")) == "yes"
          and uk(cmd, rf_for("ssh prod1 x")) == "yes" and uk(cmd, rf_for("echo hi")) == "no"
          and uk(cmd, rf_for(None)) == "unreadable")
    n = len(calls)
    uk("bash scripts/x.sh", rf_for("ssh prod1 x"))
    ok = ok and len(calls) == n
    d = tmp()
    write(d, "c1111111.jsonl", [use(0, "toolu_1", cmd), res(5, "toolu_1")])
    c, _ = classify(d, [2], read_file=no_files)
    report("T9", ok and c[0] == "要確認: 台本が読めない", "台本の中身を見る（読めないとき: %s）" % c[0])


def t10():
    d = tmp()
    write(d, "c1111111.jsonl", [use(0, "toolu_1", "ssh prod1 x"), res(5, "toolu_1")])
    c, _ = classify(d, [2], src="1.2.3.4")
    report("T10", c[0] == "異常: 接続元が違う", "接続元が違えば最優先で異常（%s）" % c[0])


def write_auth(d, name, secs):
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as f:
        for s in secs:
            ts = at(s).astimezone(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%dT%H:%M:%S.000000+09:00")
            f.write("%s h sshd[1]: Accepted publickey for ubuntu from %s port 5 ssh2: ED25519 SHA256:x\n" % (ts, MAC))
    return p


def t11():
    d = tmp()
    write(d, "c1111111.jsonl", [
        use(100, "toolu_1", "ssh -i %s ubuntu@1.1.1.1 df -h" % KEY), res(105, "toolu_1"),
        use(3000, "toolu_2", "bash /abs/run.sh"), res(3005, "toolu_2")])
    since, until = at(-1000), at(10000)
    deleg = at(2000)
    a1 = write_auth(d, "a1.txt", [102, 500])   # 500 は委任の前の説明できない入室
    a2 = write_auth(d, "a2.txt", [])
    lines = []
    rc = audit.run_prod_logins(d, [("prod1", a1), ("prod2", a2)], since, until, deleg, MAC, lines.append,
                               resolve=resolve, read_file=no_files)
    a3 = write_auth(d, "a3.txt", [102, 3002, 4000])  # 3002 は台本が読めない、4000 は記録なし（どちらも委任の後）
    lines2 = []
    rc2 = audit.run_prod_logins(d, [("prod1", a3), ("prod2", a2)], since, until, deleg, MAC, lines2.append,
                                resolve=resolve, read_file=no_files)
    bad = [x for ln in lines + lines2 for x in ("ssh ", "df -h", "/abs/run.sh") if x in ln]
    ok = (rc == 0 and rc2 == 1 and lines2[-1].startswith("UNEXPLAINED_AFTER_DELEGATION=")
          and lines[-1] == "UNEXPLAINED_AFTER_DELEGATION=0"
          and sum(1 for ln in lines if ln.startswith("分類: ")) == 7 and not bad)
    report("T11", ok, "全体の出力と終わりの番号（rc=%s,%s 文面の漏れ=%d）" % (rc, rc2, len(bad)))


def t12():
    d = tmp()
    ok_file = write_auth(d, "a.txt", [1])
    base = dict(auth=["prod1=" + ok_file], since="2026-11-02T00:00+09:00", until="2026-11-03T00:00+09:00",
                delegation_start="2026-11-02T18:06+09:00", mac_ip=MAC)
    cases = [("時差なし", dict(base, since="2026-11-02T18:06")),
             ("=なし", dict(base, auth=["prod1"])),
             ("ファイル無し", dict(base, auth=["prod1=" + os.path.join(d, "nothing.txt")]))]
    ok = True
    for name, kw in cases:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = audit.run_prod_logins_cli(type("A", (), kw)(), d, datetime.datetime.now(UTC))
        if rc != 2 or not buf.getvalue().startswith("STOP:"):
            ok = False
            print("  詳細 %s rc=%s" % (name, rc))
    report("T12", ok, "引数の誤りは STOP: と 2")


def t13():
    d = tmp()
    po = os.path.join(d, "CC報告ファイル-keep", "prod-ops")
    os.makedirs(po)
    with open(os.path.join(po, "20261102.md"), "w", encoding="utf-8") as f:
        f.write("a\nb\nc\n")
    write(d, "c1111111.jsonl", [use(0, "toolu_1", "ssh -i %s ubuntu@1.1.1.1 x" % KEY), res(5, "toolu_1"),
                                use(86400, "toolu_2", "ssh -i %s ubuntu@1.1.1.1 x" % KEY), res(86405, "toolu_2")])
    # 日本時間で 11/2 になる UTC 00:00:02、11/3 になる UTC 1 日後 + 2 秒
    a = write_auth(d, "a.txt", [2, 86402])
    lines = []
    audit.run_prod_logins(d, [("prod1", a)], at(-100), at(90000), at(-50), MAC, lines.append,
                          resolve=resolve, read_file=no_files)
    am = [ln for ln in lines if ln.startswith("AFTER_MAIN=")]
    ok = len(am) == 2 and am[0].endswith("prod-ops=3行") and am[1].endswith("prod-ops=なし")
    report("T13", ok, "prod-ops の行数（%s）" % " | ".join(x.split("prod-ops=")[1] for x in am))


def t14():
    d = tmp()
    old = audit.real_home
    audit.real_home = lambda: d
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            audit.main(["--audit"])
        ok = "ABNORMAL=" in buf.getvalue()
    except Exception as e:  # noqa: BLE001
        ok = False
        print("  例外 %s" % type(e).__name__)
    finally:
        audit.real_home = old
    report("T14", ok, "今の --audit が変わらず動く")


for t in (t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12, t13, t14):
    try:
        t()
    except Exception as e:  # noqa: BLE001
        report(t.__name__.upper(), False, "例外 %s: %s" % (type(e).__name__, e))
for d in TMPS:
    shutil.rmtree(d, ignore_errors=True)
print("PASS=%d FAIL=%d TOTAL=%d" % (PASS, FAIL, PASS + FAIL))
sys.exit(1 if FAIL else 0)
