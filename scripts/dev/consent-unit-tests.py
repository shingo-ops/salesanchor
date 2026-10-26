import sys, os, json, importlib.util, datetime, threading

hookdir, tmp, wtroot = sys.argv[1:4]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


cc = load("consent_check", os.path.join(hookdir, "consent_check.py"))
audit = load("consent_audit", os.path.join(wtroot, "scripts", "dev", "consent-audit.py"))
UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 19, 1, 0, 0, tzinfo=UTC)
_n = [0]
_u = [0]


def td(sec):
    return datetime.timedelta(seconds=sec)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def uid():
    _u[0] += 1
    return "uuid-%d" % _u[0]


def newhome():
    _n[0] += 1
    h = os.path.join(tmp, "ch%d" % _n[0])
    os.makedirs(h + "/.claude/projects/-p")
    os.makedirs(h + "/.claude/logs")
    return h


def common(typ, ts, **kw):
    # 実物の会話記録の行のキーの組を写している（2026-10-19 に実物から採取）
    r = {"cwd": "/x", "entrypoint": "cli", "gitBranch": "main", "isSidechain": False, "parentUuid": None,
         "sessionId": "s1", "slug": "x", "timestamp": iso(ts), "type": typ, "userType": "external",
         "uuid": uid(), "version": "2.0"}
    r.update(kw)
    return r


def human(text, ts, source="typed"):
    return common("user", ts, message={"role": "user", "content": text}, origin={"kind": "human"},
                  permissionMode="default", promptId="p", promptSource=source, turnOrigin="user", turnPosition=0)


def human_image(ts):
    return common("user", ts, message={"role": "user", "content": [{"type": "text", "text": "ok"}, {"type": "image", "source": {}}]},
                  origin={"kind": "human"}, permissionMode="default", promptId="p", promptSource="typed", turnOrigin="user", turnPosition=0)


def queued_human(text, ts):
    return common("attachment", ts, attachment={"commandMode": "prompt", "delivery_id": "d", "humanTurn": 1,
                  "origin": {"kind": "human"}, "prompt": text, "source_uuid": "s", "timestamp": iso(ts), "type": "queued_command"},
                  rendered="x", renderedRole="user", session_id="s1")


def other_user(text, ts, origin, **kw):
    d = dict(message={"role": "user", "content": text}, promptSource="system", permissionMode="default", promptId="p", turnOrigin="x", turnPosition=0)
    if origin is not None:
        d["origin"] = origin
    d.update(kw)
    return common("user", ts, **d)


def atext(text, ts):
    return common("assistant", ts, message={"id": "m1", "role": "assistant", "content": [{"type": "text", "text": text}]},
                  requestId="r", session_id="s1")


def atool(inp, ts):
    return common("assistant", ts, message={"id": "m2", "role": "assistant", "content": [{"type": "tool_use", "id": "toolu_X", "name": "Bash", "input": inp}]},
                  requestId="r", session_id="s1")


def ticket(ops, rec="【おすすめ】"):
    lines = ["次の操作を実行してよいか確認します。", "", "```", "[同意票]"]
    lines += ["操作%d: %s" % (i + 1, o) for i, o in enumerate(ops)]
    lines += ["```", "", "1. 上の同意票の操作を実行する" + rec + " 選ぶと、その操作が1回だけ実行されます", "2. 実行しない"]
    return "\n".join(lines)


def write_tr(h, recs, last_newline=True, name="s1.jsonl"):
    p = os.path.join(h, ".claude", "projects", "-p", name)
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in recs)
    if last_newline:
        body += "\n"
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    return p


def std(cmd_ops, one="1", source="typed", extra_between=()):
    recs = [human("確認して", T0 - td(60)), atext(ticket(cmd_ops), T0)]
    recs += list(extra_between)
    recs.append(human(one, T0 + td(10), source))
    return recs


def run(recs, cmd, now_off=70, home=None, last_newline=True, hook_extra=None, tp=None):
    h = home or newhome()
    p = tp or write_tr(h, recs, last_newline)
    hi = {"session_id": "s1", "transcript_path": p, "tool_input": {"command": cmd}}
    if hook_extra:
        hi.update(hook_extra)
    return cc.check(hi, cmd, T0 + td(now_off), home=h), h


def rep(tid, desc, cond):
    print("%s %-8s %s" % ("PASS" if cond else "FAIL", tid, desc), flush=True)


CMD = "rm -rf /tmp/CC報告ファイル/x"

# T1: 「1」だけで、完全一致のコマンドが通る（【おすすめ】つき・無しの両方、複数操作）
(ok, why), h1 = run(std([CMD]), CMD)
rep("T1-a", "同意票＋typed の 1 で通る（【おすすめ】つき）: %s" % why, ok)
(ok, why), _ = run([human("x", T0 - td(60)), atext(ticket([CMD], rec=""), T0), human("1", T0 + td(10))], CMD)
rep("T1-b", "【おすすめ】無しでも通る: %s" % why, ok)
(ok, why), _ = run(std(["echo a", CMD, "echo b"]), CMD)
rep("T1-c", "操作2を指定して通る: %s" % why, ok)
(ok, why), _ = run(std([CMD]), "  " + CMD + "  ")
rep("T1-d", "前後の空白は無視して通る: %s" % why, ok)
(ok, why), _ = run([human("x", T0 - td(60)), atext("```\n" + ticket([CMD]).replace("```", "") + "\n```", T0), human(" 1 ", T0 + td(10))], CMD)
rep("T1-e", "コードブロックで囲み、1 の前後に空白があっても通る: %s" % why, ok)
# probe / consumed が記録される
ev = [json.loads(x) for x in open(os.path.join(h1, ".claude/logs/agent-events.jsonl"))]
rep("T1-f", "consent_probe と consent_consumed が書かれる", any(e["type"] == "consent_probe" and e["h_typed_one"] is True for e in ev) and any(e["type"] == "consent_consumed" for e in ev))
# audit の突き合わせ（台帳の鍵に対応する同意票と typed の 1 が記録にある）
n_keys, unmatched = audit.match_ledger_keys(h1, T0 - td(86400))
rep("T1-g", "consent-audit の突き合わせ: 鍵%d件・不一致%d件" % (n_keys, unmatched), n_keys == 1 and unmatched == 0)

# T2: 同じ同意票の同じ操作は1回だけ（順次・並行）
recs = std([CMD])
h = newhome()
p = write_tr(h, recs)
hi = {"session_id": "s1", "transcript_path": p, "tool_input": {"command": CMD}}
r1 = cc.check(hi, CMD, T0 + td(70), home=h)[0]
r2 = cc.check(hi, CMD, T0 + td(71), home=h)[0]
rep("T2-a", "順次2回目は止まる", r1 is True and r2 is False)
h = newhome()
p = write_tr(h, recs)
hi = {"session_id": "s1", "transcript_path": p, "tool_input": {"command": CMD}}
res = []
ths = [threading.Thread(target=lambda: res.append(cc.check(hi, CMD, T0 + td(70), home=h)[0])) for _ in range(8)]
[x.start() for x in ths]
[x.join() for x in ths]
rep("T2-b", "並行8本で通るのは1回だけ（通った数=%d）" % sum(res), sum(res) == 1 and len(res) == 8)
(ok, why), _ = run(std([CMD, CMD]), CMD)
(ok2, why2), _ = run(std([CMD, CMD]), CMD, home=_)
rep("T2-c", "同じ操作が2行あっても1回だけ", ok is True and ok2 is False)

# T3: 30分
(ok, why), _ = run(std([CMD]), CMD, now_off=10 + 29 * 60 + 59)
rep("T3-a", "「1」から29分59秒は通る: %s" % why, ok)
(ok, why), _ = run(std([CMD]), CMD, now_off=10 + 30 * 60 + 1)
rep("T3-b", "「1」から30分1秒は止まる: %s" % why, not ok and why == "expired")

# T4: 1文字でも違えば止まる
for tid, c in (("a", CMD + "x"), ("b", "rm -rf /tmp/CC報告ファイル/"), ("c", "rm  -rf /tmp/CC報告ファイル/x"), ("d", "echo hi; " + CMD), ("e", "")):
    (ok, why), _ = run(std([CMD]), c)
    rep("T4-" + tid, "違うコマンドは止まる: %r (%s)" % (c, why), not ok)

# T5: 偽の記録
def denied(tid, desc, recs, cmd=CMD, **kw):
    (ok, why), _ = run(recs, cmd, **kw)
    rep(tid, "止まる: %s (%s)" % (desc, why), not ok)


denied("T5-a", "貼り付け印つきの 1", std("", one="[Pasted text #1 +1 lines] 1") if False else std([CMD], one="[Pasted text #1 +1 lines]1"))
denied("T5-b", "貼り付けの 1（promptSource が typed 以外）", std([CMD], source="pasted"))
denied("T5-c", "queued の 1（promptSource=queued）", std([CMD], source="queued"))
denied("T5-d", "サブエージェントの報告（peer）の 1",
       [human("x", T0 - td(60)), atext(ticket([CMD]), T0), other_user("1", T0 + td(10), {"kind": "peer", "from": "a", "handback": True}, isMeta=True)])
denied("T5-e", "task-notification の 1",
       [human("x", T0 - td(60)), atext(ticket([CMD]), T0), other_user("1", T0 + td(10), {"kind": "task-notification"})])
denied("T5-f", "! の出力の 1（origin 無し）",
       [human("x", T0 - td(60)), atext(ticket([CMD]), T0), other_user("<bash-stdout>1</bash-stdout>", T0 + td(10), None, promptSource="typed")])
denied("T5-g", "channel（Discord）の 1",
       [human("x", T0 - td(60)), atext(ticket([CMD]), T0), other_user("1", T0 + td(10), {"kind": "channel", "server": "discord"}, promptSource="typed")])
denied("T5-h", "queued_command（attachment）の人の 1",
       [human("x", T0 - td(60)), atext(ticket([CMD]), T0), queued_human("1", T0 + td(10))])
(ok, why), _ = run(std([CMD]), CMD, hook_extra={"agent_id": "a1"})
rep("T5-i", "止まる: agent_id キーあり (%s)" % why, not ok and why == "agent_id")
(ok, why), _ = run(std([CMD]), CMD, hook_extra={"agent_id": ""})
rep("T5-i2", "止まる: agent_id が空でもキーがあれば (%s)" % why, not ok)
denied("T5-j", "同意票が tool_use の中にだけある",
       [human("x", T0 - td(60)), atool({"command": "echo", "note": ticket([CMD])}, T0), human("1", T0 + td(10))])
denied("T5-k", "同意票が最後の AI の text ブロックに無い",
       [human("x", T0 - td(60)), atext(ticket([CMD]), T0), atext("続けます", T0 + td(5)), human("1", T0 + td(10))])
denied("T5-l", "同意票の後、最初の人の入力が「1」でない",
       [human("x", T0 - td(60)), atext(ticket([CMD]), T0), human("あ", T0 + td(5)), human("1", T0 + td(10))])
denied("T5-m", "同意票と H の間に queued の入力",
       std([CMD], extra_between=[queued_human("待って", T0 + td(5))]))
denied("T5-n", "同意票と H の間に compact_boundary",
       std([CMD], extra_between=[common("system", T0 + td(5), subtype="compact_boundary", content="x", compactMetadata={}, level="info")]))
denied("T5-n2", "同意票と H の間に isCompactSummary",
       std([CMD], extra_between=[common("user", T0 + td(5), message={"role": "user", "content": "This session is being continued"}, isCompactSummary=True)]))
denied("T5-o", "「1」の後に画像つきの入力（最後の人の入力が配列）", std([CMD]) + [human_image(T0 + td(20))])
denied("T5-o2", "「1」の後に別の人の入力", std([CMD]) + [human("やっぱり", T0 + td(20))])
denied("T5-p", "同意票が2つ", [human("x", T0 - td(60)), atext(ticket([CMD]) + "\n\n" + ticket([CMD]), T0), human("1", T0 + td(10))])
denied("T5-q", "選択肢1の行が無い", [human("x", T0 - td(60)), atext(ticket([CMD]).replace("1. 上の同意票の操作を実行する", "1. 実行"), T0), human("1", T0 + td(10))])
denied("T5-r", "「1」より前に同意票が無い（人の入力だけ）", [human("x", T0 - td(60)), human("1", T0 + td(10))])
denied("T5-s", "人の入力が無い", [atext(ticket([CMD]), T0)])
# 記録の形
h = newhome()
good = write_tr(h, std([CMD]))
(ok, why) = cc.check({"session_id": "s1", "transcript_path": "/tmp/not-under-home.jsonl", "tool_input": {"command": CMD}}, CMD, T0 + td(70), home=h)
rep("T5-t", "止まる: transcript_path がホームの projects の外 (%s)" % why, not ok)
os.makedirs(os.path.join(tmp, "elsewhere"), exist_ok=True)
ext = os.path.join(tmp, "elsewhere", "s.jsonl")
os.symlink(good, ext)
(ok, why) = cc.check({"session_id": "s1", "transcript_path": ext, "tool_input": {"command": CMD}}, CMD, T0 + td(70), home=h)
rep("T5-t2", "通る側の確認: 外のシンボリックリンクでも実体がホームの projects の下なら (%s)" % why, ok)
h = newhome()
bad = std([CMD])
p = write_tr(h, bad)
with open(p, "a", encoding="utf-8") as f:
    f.write("not json at all\n")
(ok, why) = cc.check({"session_id": "s1", "transcript_path": p, "tool_input": {"command": CMD}}, CMD, T0 + td(70), home=h)
rep("T5-u", "止まる: JSON でない行がある (%s)" % why, not ok)
# 最後の行が改行で終わっていない
(ok, why), _ = run(std([CMD]), CMD, last_newline=False)
rep("T5-v", "止まる: 最後の行（typed の 1）が改行で終わっていない (%s)" % why, not ok)
(ok, why), _ = run(std([CMD]) + [common("system", T0 + td(11), subtype="turn_duration")], CMD, last_newline=False)
rep("T5-v2", "通る: 改行で終わっていない最後の行が無関係な行なら捨てて判定する (%s)" % why, ok)
# 4MB の境目
filler = lambda ts: common("attachment", ts, attachment={"type": "date"}, rendered="y" * 100000, renderedRole="user")
many = [filler(T0 - td(120)) for _ in range(45)]
(ok, why), _ = run(many + std([CMD]), CMD)
rep("T5-w", "通る: 末尾 4MB の外に大きな前置きがあり、境目が行の途中でも (%s)" % why, ok)
recs = [human("x", T0 - td(60)), atext(ticket([CMD]), T0)] + [filler(T0 + td(1)) for _ in range(45)] + [human("1", T0 + td(10))]
(ok, why), _ = run(recs, CMD)
rep("T5-x", "止まる: 同意票が末尾 4MB の外 (%s)" % why, not ok)

# T6: 除外と $・バッククォート（同意があっても止まる）
for tid, c in (
    ("a", "git push origin main"), ("b", "git push -u origin HEAD:main"), ("c", "git push origin develop"),
    ("d", "git push --force origin"), ("e", "git push origin --delete foo"), ("f", "git push origin :foo"),
    ("g", "git reset --hard HEAD~1"), ("h", 'psql -c "DROP DATABASE x"'), ("i", "clasp push"),
    ("j", "cat /Users/x/.claude/settings.json"), ("k", "ls /Users/x/.claude/scripts/"), ("l", "ls /Users/x/.codex/salesanchor/"),
    ("m", "gh api repos/o/r/branches/main/protection"), ("n", "gh api repos/o/r/rulesets"), ("o", "cat .github/workflows/workflow-lint.yml"),
    ("p", "git clean -fd"), ("q", "git stash"), ("r", "git checkout -- x"), ("s", "git restore x"),
    ("t", "cat /Users/x/.claude/projects/-p/s.jsonl"), ("u", "tail consent-used.jsonl"), ("v", "tmux send-keys -t a 1 Enter"),
    ("w", "osascript -e 'keystroke \"1\"'"), ("x", "curl http://localhost:3000/chat/queue"), ("y", "ls /Users/x/.claude/permits"),
    ("z1", "git push origin HEAD:main"), ("z2", "git push origin main"), ("z3", "git push origin develop"), ("z4", "git push origin HEAD:refs/heads/main"),
    ("aa", "git push -f origin"),
    ("z5", "git push origin release/fix-main-menu"), ("z6", "git push -f origin HEAD:heads/main"),
    ("ab", "echo $HOME"), ("ac", "echo `date`"),
):
    (ok, why), _ = run(std([c]), c)
    rep("T6-" + tid, "除外は同意があっても止まる: %s (%s)" % (c, why), not ok)
for tid, c in (("p1", "git push origin release/foo"), ("p2", "git push --force origin release/foo"), ("p3", "git stash pop"),
               ("p4", "rm -rf /tmp/CC報告ファイル/x"), ("p5", "git push -u origin release/conversation-consent-permit")):
    (ok, why), _ = run(std([c]), c)
    rep("T6-" + tid, "除外に当たらないものは通る: %s (%s)" % (c, why), ok)

# T0: K0 の遅れの数え方（design §2、S4）
h = newhome()
hu1, hu2 = human("1", T0, "typed"), human("1", T0 + td(100), "typed")
tu_a = atool({"command": "a"}, T0 + td(110)); tu_a["message"]["content"][0]["id"] = "toolu_A"
tu_b = atool({"command": "b"}, T0 + td(120)); tu_b["message"]["content"][0]["id"] = "toolu_B"
write_tr(h, [hu1, hu2, tu_a, tu_b])
probes = [
    {"type": "consent_probe", "session": "s1", "h_uuid": hu1["uuid"], "now": (T0 + td(111)).isoformat(), "tool_use_id": "toolu_A"},  # 遅れ（H が古い）
    {"type": "consent_probe", "session": "s1", "h_uuid": hu2["uuid"], "now": (T0 + td(121)).isoformat(), "tool_use_id": "toolu_B"},  # 遅れなし
    {"type": "consent_probe", "session": "s1", "h_uuid": hu2["uuid"], "now": (T0 + td(150)).isoformat()},                          # 遅れなし（時刻で見る）
    {"type": "consent_probe", "session": "s1", "h_uuid": hu1["uuid"], "now": (T0 + td(150)).isoformat()},                          # 遅れ
    {"type": "consent_probe", "session": "s1", "h_uuid": hu1["uuid"], "now": (T0 + td(50)).isoformat()},                           # 直前が hu1 で一致
]
total, delays = audit.k0_delays(h, probes)
rep("T0-a", "K0: 対象%d件のうち遅れ%d件（期待 5 と 2）" % (total, delays), total == 5 and delays == 2)

# T0-w: 試験の区間の除外（design §9）
hw = newhome()
wpath = os.path.join(hw, ".claude", "logs", "consent-selftest-windows.jsonl")
def wl(rows):
    with open(wpath, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
def iso(d):
    return d.isoformat()
since = T0 - td(86400)
ev = [{"type": "consent_guard_blocked", "ts": iso(T0 + td(60)), "kind": "inject", "condition": "tmux-inject"},     # 区間内
      {"type": "consent_guard_blocked", "ts": iso(T0 + td(5000)), "kind": "inject", "condition": "tmux-inject"}]   # 区間外（inject は疑い）
wl([{"start": iso(T0)}, {"end": iso(T0 + td(600))}])
wins, nw = audit.load_windows(hw)
sus, rd, inside = audit.count_guard_split(ev, since, wins)
real = len(sus)
rep("T0-w1", "区間内は除外・区間外は数える（疑い%d 空振り%d 除外%d、期待 1・0・1、区間%d）" % (real, rd, inside, nw), real == 1 and rd == 0 and inside == 1 and nw == 1)
wl([{"start": iso(T0)}, {"end": iso(T0 + td(1801))}])
wins, nw = audit.load_windows(hw)
sus, rd, inside = audit.count_guard_split(ev, since, wins)
real = len(sus)
rep("T0-w2", "30分を超える区間は除外に使わない（疑い%d 除外%d、期待 2 と 0）" % (real, inside), real == 2 and inside == 0)
wl([{"start": iso(T0)}])
wins, nw = audit.load_windows(hw)
sus, rd, inside = audit.count_guard_split(ev, since, wins)
real = len(sus)
rep("T0-w3", "end の無い区間は除外に使わない（疑い%d 除外%d、期待 2 と 0）" % (real, inside), real == 2 and inside == 0)

# K15: --audit の疑いと読み取りの空振りの分け（design §13-3(b)・§13-7）
def audit_run(rows, wins_rows=None):
    hk = newhome()
    with open(os.path.join(hk, ".claude", "logs", "agent-events.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    if wins_rows is not None:
        with open(os.path.join(hk, ".claude", "logs", "consent-selftest-windows.jsonl"), "w") as f:
            for r in wins_rows:
                f.write(json.dumps(r) + "\n")
    lines = []
    ab, _ = audit.run_audit(hk, T0 + td(10000), False, lines.append)
    return ab, lines

def gb(ts_sec, kind=None, cond="transcript", head="x", **kw):
    r = {"type": "consent_guard_blocked", "ts": iso(T0 + td(ts_sec)), "hook": "agent-danger-hook", "condition": cond, "cmd_head": head}
    if kind is not None:
        r["kind"] = kind
    r.update(kw)
    return r

ab, ln = audit_run([gb(1000, "read"), gb(2000, "read"), gb(3000, "read", "consent-used")])
l2 = [x for x in ln if x.startswith("2. ")][0]
rep("K15-1", "read 3件だけ: 異常なし・疑い0・空振り3・GUARD_SUSPECT なし", (not ab) and "疑い 0 件" in l2 and "空振り 3 件" in l2
    and not any(x.startswith("GUARD_SUSPECT=") for x in ln) and "ABNORMAL=no" in ln)
ab, ln = audit_run([gb(1000, "write", cmd_sha="abcd1234abcd1234", cmd_len=77)])
gs = [x for x in ln if x.startswith("GUARD_SUSPECT=")]
rep("K15-2", "write 1件: 異常あり・GUARD_SUSPECT 1行（ABNORMAL= より前・cmd_head なし）",
    ab and len(gs) == 1 and "cmd_sha=abcd1234abcd1234" in gs[0] and "cmd_len=77" in gs[0] and "cmd_head" not in gs[0]
    and ln.index(gs[0]) < ln.index("ABNORMAL=yes"))
P = "~/.claude/projects/x.jsonl"
ab, ln = audit_run([gb(1000, None, head="echo a >> " + P)])
rep("K15-3", "旧形式の Bash で書き足しの形: 疑い", ab and any(x.startswith("GUARD_SUSPECT=") for x in ln))
ab, ln = audit_run([gb(1000, None, head="grep x ~/.claude/projects/y.jsonl")])
l2 = [x for x in ln if x.startswith("2. ")][0]
rep("K15-4", "旧形式の Bash で読むだけ: 空振り・異常なし", (not ab) and "疑い 0 件" in l2 and "空振り 1 件" in l2)
ab, ln = audit_run([gb(1000, "write")], [{"start": iso(T0 + td(500))}, {"end": iso(T0 + td(1500))}])
l2 = [x for x in ln if x.startswith("2. ")][0]
rep("K15-5", "試験の区間内の write: 除外（疑い0・異常なし・除外1）", (not ab) and "疑い 0 件" in l2 and "除いた件数 1" in l2)
ab, ln = audit_run([gb(1000, None, cond="tmux-inject"), gb(2000, None, cond="transcript-or-ledger-write")])
rep("K15-6", "旧形式の inject 系・ファイル書き込みは疑い（2行）", ab and len([x for x in ln if x.startswith("GUARD_SUSPECT=")]) == 2)
# 書き込みの形の規則（迷う形は write 側）
wf = audit.bash_write_form
rep("K15-7", "書き込みの形: tee -a・sed -i・python の open 'a'・cd の後の > は write",
    wf("echo a | tee -a " + P) and wf("sed -i s/a/b/ " + P) and wf("python3 -c \"open('" + P + "','a').write('x')\"")
    and wf("cd ~/.claude/projects/-p && echo x > s.jsonl") and wf("cp " + P + " /tmp/z")
    and wf("python3 -c \"Path('" + P + "').open('a').write('x')\"") and wf("x" * 4001))
rep("K15-8", "書き込みの形: 読むだけ（grep・cat | head・python の open 読み・/dev/null への出力）は read",
    (not wf("grep x " + P)) and (not wf("cat " + P + " | head")) and (not wf("python3 -c \"print(open('" + P + "').read())\""))
    and (not wf("cat " + P + " 2>/dev/null")) and (not wf("python3 -c \"print(Path('" + P + "').open('r').read())\"")) and (not wf("cd ~/.claude/projects/-p && cat s.jsonl 2>&1")))

print("DONE", flush=True)
