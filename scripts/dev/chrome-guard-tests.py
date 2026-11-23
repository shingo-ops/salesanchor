"""chrome-guard-tests.py - chrome-op-guard（ADR-1085 便1）の受入試験 T1〜T15・T17〜T19。

使い方: python3 -I -B scripts/dev/chrome-guard-tests.py <hooksのdir> <consent_check.pyのdir> <一時dir>
  偽の HOME（一時dirの中）だけを使う。本物の ~/.claude には触れない。
  各試験の結果を `PASS T<n> <名>` か `FAIL T<n> <名> <理由>` で1行ずつ出し、最後に `DONE pass=<n> fail=<n>`。fail>0 なら exit 1。
  T16（取り付け後の本物の置き場）・T20（取り付け直後の実物の返事）は取り付けの台本・手作業のため、ここには入れない。
"""
import datetime
import importlib.util
import json
import os
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
hookdir, consentdir, tmp = [os.path.abspath(p) for p in sys.argv[1:4]]
os.makedirs(tmp, exist_ok=True)

# ── 試験用の並び: <tmp>/scripts/consent_check.py と <tmp>/scripts/chrome-op-guard/... ─────────
SCRIPTS = os.path.join(tmp, "scripts")
GUARD_DIR = os.path.join(SCRIPTS, "chrome-op-guard")
os.makedirs(GUARD_DIR, exist_ok=True)
shutil.copy(os.path.join(consentdir, "consent_check.py"), os.path.join(SCRIPTS, "consent_check.py"))
for f in ("chrome_op_guard.py", "chrome_op_record.py", "chrome_common.py", "tiers.json"):
    shutil.copy(os.path.join(hookdir, f), os.path.join(GUARD_DIR, f))
CONSENT_LINE = os.path.join(hookdir, "..", "chrome-consent-line.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


sys.path.insert(0, GUARD_DIR)
guard = load("chrome_op_guard", os.path.join(GUARD_DIR, "chrome_op_guard.py"))
recmod = load("chrome_op_record", os.path.join(GUARD_DIR, "chrome_op_record.py"))
cm = guard.cm
PFX = cm.PREFIX
UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 11, 23, 1, 0, 0, tzinfo=UTC)
_n = [0]
_u = [0]
PASS = [0]
FAIL = [0]


def td(sec):
    return datetime.timedelta(seconds=sec)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def uid():
    _u[0] += 1
    return "uuid-%d" % _u[0]


def rep(tid, name, cond, why=""):
    if cond:
        PASS[0] += 1
        print("PASS %s %s" % (tid, name), flush=True)
    else:
        FAIL[0] += 1
        print("FAIL %s %s %s" % (tid, name, why), flush=True)


def newhome():
    _n[0] += 1
    h = os.path.join(tmp, "home%d" % _n[0])
    os.makedirs(h + "/.claude/projects/-p")
    os.makedirs(h + "/.claude/logs")
    return h


# ── 作り物の会話記録（consent-unit-tests.py の型） ───────────────────────────────────────
def common(typ, ts, **kw):
    r = {"cwd": "/x", "entrypoint": "cli", "gitBranch": "main", "isSidechain": False, "parentUuid": None,
         "sessionId": "s1", "slug": "x", "timestamp": iso(ts), "type": typ, "userType": "external",
         "uuid": uid(), "version": "2.0"}
    r.update(kw)
    return r


def human(text, ts, source="typed"):
    return common("user", ts, message={"role": "user", "content": text}, origin={"kind": "human"},
                  permissionMode="default", promptId="p", promptSource=source, turnOrigin="user", turnPosition=0)


def atext(text, ts):
    return common("assistant", ts, message={"id": "m1", "role": "assistant", "content": [{"type": "text", "text": text}]},
                  requestId="r", session_id="s1")


def ticket(ops):
    lines = ["次の操作を実行してよいか確認します。", "", "```", "[同意票]"]
    lines += ["操作%d: %s" % (i + 1, o) for i, o in enumerate(ops)]
    lines += ["```", "", "1. 上の同意票の操作を実行する【おすすめ】 選ぶと、その操作が1回だけ実行されます", "2. 実行しない"]
    return "\n".join(lines)


def write_tr(h, recs, name="s1.jsonl"):
    p = os.path.join(h, ".claude", "projects", "-p", name)
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n")
    return p


def consented(h, lines, extra_after=()):
    """lines の同意票と typed の「1」の記録を作り、transcript_path を返す。"""
    recs = [human("確認して", T0 - td(60)), atext(ticket(lines), T0), human("1", T0 + td(10))]
    recs += list(extra_after)
    return write_tr(h, recs)


def no_ticket(h):
    return write_tr(h, [human("確認して", T0 - td(60)), atext("やります", T0), human("1", T0 + td(10))])


# ── 呼び出しの道具 ───────────────────────────────────────────────────────────────────
def hook(tool, ti, h, tp=None, sid="s1", extra=None):
    hi = {"tool_name": PFX + tool, "tool_input": ti, "session_id": sid,
          "transcript_path": tp or no_ticket(h)}
    if extra:
        hi.update(extra)
    return hi


def call(h, hi, off=70):
    """(終了コード, 標準エラー)。偽の HOME だけを使う。"""
    os.environ["HOME"] = h
    return guard.decide(hi, T0 + td(off), consent_home=h)


def ctx_reply(h, tabs, sid="s1", extra_chunks=(), raw=None, off=71):
    """tabs_context_mcp の返事を PostToolUse に流して住所を覚えさせる。"""
    os.environ["HOME"] = h
    if raw is None:
        raw = [{"type": "text", "text": json.dumps({"availableTabs": tabs}, ensure_ascii=False)}]
        raw += list(extra_chunks)
    recmod.record({"tool_name": PFX + "tabs_context_mcp", "session_id": sid, "tool_response": raw}, T0 + td(off), h)


def tab(tid, url, title="x"):
    return {"tabId": tid, "title": title, "url": url}


def click(tid=7, summary="保存を押す", **kw):
    ti = {"action": "left_click", "coordinate": [10, 10], "action_summary": summary}
    if tid is not None:
        ti["tabId"] = tid
    ti.update(kw)
    return ti


def lines_of(h):
    p = os.path.join(h, ".claude", "logs", "chrome-ops.jsonl")
    if not os.path.exists(p):
        return []
    return [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]


def raw_log(h):
    p = os.path.join(h, ".claude", "logs", "chrome-ops.jsonl")
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


LOCAL = "http://localhost:5173/"

# T1: 区分3の URL は navigate で止まる（形を変えても）
for label, url in [("そのまま", "https://dash.cloudflare.com/abc/billing"),
                   ("https:// 無し", "dash.cloudflare.com/abc/billing"),
                   ("ホスト名の大文字", "https://DASH.Cloudflare.COM/abc/billing"),
                   ("%で書き換え", "https://dash.cloudflare.com/abc/%62illing"),
                   ("%の二重書き換え", "https://dash.cloudflare.com/abc/%2562illing"),
                   ("末尾のドット", "https://dash.cloudflare.com./abc/billing"),
                   ("ユーザー情報つき", "https://x@dash.cloudflare.com/abc/billing"),
                   ("*. の型（paypal のサブドメイン）", "https://www.paypal.com/myaccount"),
                   ("GitHub の鍵", "https://github.com/settings/tokens"),
                   ("../ で戻る（github）", "https://github.com/a/../settings/tokens"),
                   ("%2e%2e で戻る（cloudflare）", "https://dash.cloudflare.com/profile/x/%2e%2e/api-tokens"),
                   ("ホストの % 書き換え", "https://pay%2Egoogle.com/"),
                   ("ホストの全角", "https://ｐａｙ.google.com/"),
                   ("ホストの句点", "https://pay。google.com/"),
                   ("パスの大文字", "https://github.com/Settings/tokens"),
                   ("パスの // 連続", "https://github.com//settings/tokens"),
                   ("https:/ 斜線1本（pay.google）", "https:/pay.google.com/"),
                   ("http:/ 斜線1本（pay.google）", "http:/pay.google.com/"),
                   ("https:/ 斜線1本（github の鍵）", "https:/github.com/settings/tokens"),
                   ("HTTPS:/ 大文字", "HTTPS:/pay.google.com/"),
                   ("https: 斜線なし", "https:pay.google.com"),
                   ("https:/// 斜線3本", "https:///pay.google.com/")]:
    h = newhome()
    code, msg = call(h, hook("navigate", {"url": url, "tabId": 1}, h))
    rep("T1", "navigate 区分3: %s" % label, code == 2 and "区分3" in msg, "code=%s msg=%s" % (code, msg))
h = newhome()
code, _ = call(h, hook("navigate", {"url": "https://example.com/", "tabId": 1}, h))
rep("T1", "navigate 普通の URL は通る（対照）", code == 0)
for label, url in [("../ をたたむと普通の道", "https://example.com/a/../b"),
                   ("GitHub の普通のリポジトリ", "https://github.com/shingo-ops/salesanchor"),
                   ("localhost:5173/（ホスト:ポートは scheme と読まない）", "localhost:5173/"),
                   ("https:/ 斜線1本の普通の道", "https:/example.com/")]:
    h = newhome()
    code, msg = call(h, hook("navigate", {"url": url, "tabId": 1}, h))
    rep("T1", "navigate 通る: %s" % label, code == 0, "code=%s msg=%s" % (code, msg))

# T2: 押す操作は同意票なしで止まる
h = newhome()
code, msg = call(h, hook("computer", click(), h))
rep("T2", "同意票なしの left_click は止まる", code == 2 and "同意票" in msg, "code=%s msg=%s" % (code, msg))

# T3: 同意票＋typed の「1」で1回だけ通る
l1 = cm.consent_line("computer", click(7, "保存を押す（1回目）"))
l2 = cm.consent_line("computer", click(7, "保存を押す（2回目）"))
h = newhome()
tp = consented(h, [l1, l2])
code, msg = call(h, hook("computer", click(7, "保存を押す（1回目）"), h, tp))
rep("T3", "同意票＋「1」で通る", code == 0, "code=%s msg=%s" % (code, msg))
code, msg = call(h, hook("computer", click(8, "保存を押す（1回目）"), h, tp))
rep("T3", "同じ行の2回目は止まる（台帳で1回限り）", code == 2, "code=%s msg=%s" % (code, msg))
code, msg = call(h, hook("computer", click(7, "保存を押す（2回目）"), h, tp))
rep("T3", "間に tabs_context_mcp が無いと2つ目の行は止まる", code == 2 and "tabs_context_mcp" in msg, "code=%s msg=%s" % (code, msg))
ctx_reply(h, [tab(7, "https://example.com/")])
code, msg = call(h, hook("computer", click(7, "保存を押す（2回目）"), h, tp))
rep("T3", "間に tabs_context_mcp をはさめば2つ目も通る", code == 0, "code=%s msg=%s" % (code, msg))
h = newhome()
tp = consented(h, [l1])
code, msg = call(h, hook("computer", click(7, "保存を押す（1回目）"), h, tp), off=10 + 31 * 60)
rep("T3", "「1」から30分を過ぎると止まる", code == 2, "code=%s msg=%s" % (code, msg))
h = newhome()
tp = consented(h, [l1], extra_after=[human("やっぱり別の話", T0 + td(20))])
code, msg = call(h, hook("computer", click(7, "保存を押す（1回目）"), h, tp))
rep("T3", "「1」の後に別の入力があると止まる", code == 2, "code=%s msg=%s" % (code, msg))
h = newhome()
tp = consented(h, [l1])
code, msg = call(h, hook("computer", click(7, "別の文のボタンを押す"), h, tp))
rep("T3", "同意票と違う文の操作は止まる", code == 2, "code=%s msg=%s" % (code, msg))

# T4: 読む道具が通り、記録に1行残る
h = newhome()
n0 = len(lines_of(h))
code, _ = call(h, hook("read_page", {"tabId": 1}, h))
ls = lines_of(h)
rep("T4", "read_page が通り、記録が1行増える", code == 0 and len(ls) == n0 + 1 and ls[-1]["tool"] == "read_page"
    and ls[-1]["decision"] == "pass" and ls[-1]["tier"] == 1 and ls[-1]["room"] == "P", "code=%s lines=%s" % (code, ls))
code, _ = call(h, hook("computer", {"action": "screenshot", "tabId": 1}, h))
rep("T4", "computer の screenshot も通る", code == 0)
code, _ = call(h, hook("tabs_context_mcp", {"createIfEmpty": True}, h))
rep("T4", "tabs_context_mcp も通る", code == 0)

# T5: カード番号の形が止まり、記録に中身が残らない（同意票があっても）
card = "4111 1111 1111 1111"
for label, tool, ti in [("computer の type", "computer", {"action": "type", "text": card, "tabId": 1, "action_summary": "番号を打つ"}),
                        ("form_input の数値", "form_input", {"value": 4111111111111111, "ref": "r1", "tabId": 1, "action_summary": "番号を入れる"}),
                        ("ハイフン区切り", "computer", {"action": "type", "text": "4111-1111-1111-1111", "tabId": 1, "action_summary": "番号を打つ"})]:
    h = newhome()
    line = cm.consent_line(tool, ti)
    tp = consented(h, [line])
    code, _ = call(h, hook(tool, ti, h, tp))
    log = raw_log(h)
    rep("T5", "カード番号の形が止まる: %s" % label, code == 2 and "4111" not in log and "1111" not in log, "code=%s log=%s" % (code, log))
    last = lines_of(h)[-1]
    rep("T5", "記録は長さだけ: %s" % label, last["text_len"] > 0 and last["reason"] == "secret_or_card" and "text" not in last, str(last))
h = newhome()
code, _ = call(h, hook("computer", {"action": "type", "text": "1234 5678", "tabId": 1, "action_summary": "短い数を打つ"}, h))
rep("T5", "Luhn の合わない・桁の足りない数は、この見張りではカード扱いにしない（同意票なしで区分2として止まる）", code == 2 and lines_of(h)[-1]["reason"] == "no_consent")

# T6: 鍵の形が止まる
for label, secret in [("sk-ant-", "sk-ant-" + "a" * 20), ("ghp_", "ghp_" + "b" * 36), ("AKIA", "AKIA" + "C" * 16),
                      ("秘密鍵の見出し", "-----BEGIN RSA PRIVATE KEY-----")]:
    h = newhome()
    ti = {"action": "type", "text": "x " + secret, "tabId": 1, "action_summary": "文字を打つ"}
    tp = consented(h, [cm.consent_line("computer", ti)])
    code, _ = call(h, hook("computer", ti, h, tp))
    rep("T6", "鍵の形が止まる: %s" % label, code == 2 and secret not in raw_log(h) and lines_of(h)[-1]["reason"] == "secret_or_card")

# T7: browser_batch
h = newhome()
b = {"actions": [{"name": "read_page", "input": {"tabId": 1}},
                 {"name": "navigate", "input": {"url": "https://dash.cloudflare.com/x/billing", "tabId": 1}}]}
code, _ = call(h, hook("browser_batch", b, h))
rep("T7", "2つ目に区分3が入ると batch 全体が止まる", code == 2 and lines_of(h)[-1]["tier"] == 3)
h = newhome()
b = {"actions": [{"name": "read_page", "input": {"tabId": 1}}, {"name": "computer", "input": click(1)}]}
code, _ = call(h, hook("browser_batch", b, h))
rep("T7", "区分2が1つでも混じると batch 全体が止まる", code == 2 and lines_of(h)[-1]["reason"] == "batch_has_tier2")
h = newhome()
b = {"actions": [{"name": "read_page", "input": {"tabId": 1}}, {"name": "computer", "input": {"action": "screenshot", "tabId": 1}}]}
code, _ = call(h, hook("browser_batch", b, h))
rep("T7", "全部区分1の batch は通る", code == 0)
h = newhome()
code, _ = call(h, hook("browser_batch", {"actions": "ばらばら"}, h))
rep("T7", "読めない batch は止まる", code == 2)

h = newhome()
b = {"actions": [{"name": "computer", "tool": "read_page", "input": {"action": "left_click", "coordinate": [1, 1], "action_summary": "x", "tabId": 1}}]}
code, _ = call(h, hook("browser_batch", b, h))
rep("T7", "name と tool の両方を持つ項目は batch 全体が止まる", code == 2 and lines_of(h)[-1]["reason"] == "bad_batch")
h = newhome()
b = {"actions": [{"name": "read_page"}]}
code, _ = call(h, hook("browser_batch", b, h))
rep("T7", "input が無い項目は batch 全体が止まる", code == 2 and lines_of(h)[-1]["reason"] == "bad_batch")
h = newhome()
b = {"actions": [{"name": "computer", "input": {"action": "left_click", "coordinate": [1, 1], "action_summary": "x", "tabId": 1}}]}
code, _ = call(h, hook("browser_batch", b, h))
rep("T7", "本物の形の押す操作は batch_has_tier2 で止まる", code == 2 and lines_of(h)[-1]["reason"] == "batch_has_tier2")
h = newhome()
b = {"actions": [{"name": PFX + "read_page", "input": {}}, {"name": "computer", "input": {"action": "screenshot"}}]}
code, _ = call(h, hook("browser_batch", b, h))
rep("T7", "頭つきの名前の read_page と screenshot だけの batch は通る", code == 0)

# T8: javascript_tool
h = newhome()
code, _ = call(h, hook("javascript_tool", {"action": "javascript_exec", "text": "document.title", "tabId": 1}, h))
rep("T8", "javascript_tool は同意票なしで止まる", code == 2)

# T9: ファイル系
for tool, ti in [("file_upload", {"paths": ["/x/a.txt"], "ref": "r1", "tabId": 1}),
                 ("upload_image", {"imageId": "i1", "ref": "r1", "tabId": 1}),
                 ("gif_creator", {"action": "export", "tabId": 1})]:
    h = newhome()
    code, _ = call(h, hook(tool, ti, h))
    rep("T9", "%s は同意票なしで止まる" % tool, code == 2)

# T10: tiers.json が壊れていると止まる（実際の呼び出し口 main を別プロセスで）
bad_root = os.path.join(tmp, "broken")
for label, body in [("JSON でない", "{not json"), ("形が違う", '{"version": 2}'), ("空のファイル", "")]:
    d = os.path.join(bad_root, label.replace(" ", "_"), "chrome-op-guard")
    os.makedirs(d, exist_ok=True)
    for f in ("chrome_op_guard.py", "chrome_common.py"):
        shutil.copy(os.path.join(GUARD_DIR, f), os.path.join(d, f))
    with open(os.path.join(d, "tiers.json"), "w", encoding="utf-8") as f:
        f.write(body)
    h = newhome()
    p = subprocess.run([sys.executable, "-I", "-B", os.path.join(d, "chrome_op_guard.py")],
                       input=json.dumps(hook("read_page", {"tabId": 1}, h)), capture_output=True, text=True,
                       env={"HOME": h, "PATH": os.environ.get("PATH", "")})
    rep("T10", "tiers.json が壊れている（%s）と exit 2" % label, p.returncode == 2, "rc=%s err=%s" % (p.returncode, p.stderr))
h = newhome()
p = subprocess.run([sys.executable, "-I", "-B", os.path.join(GUARD_DIR, "chrome_op_guard.py")], input="これは JSON ではない",
                   capture_output=True, text=True, env={"HOME": h, "PATH": os.environ.get("PATH", "")})
rep("T10", "入力が JSON でないと exit 2", p.returncode == 2)
p = subprocess.run([sys.executable, "-I", "-B", os.path.join(GUARD_DIR, "chrome_op_guard.py")],
                   input=json.dumps(hook("read_page", {"tabId": 1}, h)), capture_output=True, text=True,
                   env={"HOME": h, "PATH": os.environ.get("PATH", "")})
rep("T10", "正しい入力は別プロセスの main でも exit 0（対照）", p.returncode == 0, "rc=%s err=%s" % (p.returncode, p.stderr))
h = newhome()
code, _ = call(h, {"tool_name": "Bash", "tool_input": {"command": "ls"}, "session_id": "s1"})
rep("T10", "Chrome の道具でなければ関係なく通す", code == 0)

# T11: action_summary・未知の action・行の形・回数
h = newhome()
ti = {"action": "left_click", "coordinate": [1, 1], "tabId": 1}
code, msg = call(h, hook("computer", ti, h))
rep("T11", "action_summary が無いと止まる", code == 2 and lines_of(h)[-1]["reason"] == "no_action_summary")
h = newhome()
code, _ = call(h, hook("computer", click(1, "   "), h))
rep("T11", "action_summary が空白だけでも止まる", code == 2 and lines_of(h)[-1]["reason"] == "no_action_summary")
h = newhome()
code, _ = call(h, hook("computer", {"action": "frobnicate", "tabId": 1, "action_summary": "謎"}, h))
rep("T11", "表に無い computer の action は止まる", code == 2 and lines_of(h)[-1]["reason"] == "unknown_action")
for label, s in [("改行", "押す\n続き"), ("$", "押す $HOME"), ("バッククォート", "押す `ls`")]:
    h = newhome()
    code, _ = call(h, hook("computer", click(1, s), h))
    rep("T11", "action_summary に%sがあると止まる" % label, code == 2 and lines_of(h)[-1]["reason"] == "bad_action_summary")
h = newhome()
tp = consented(h, [cm.consent_line("computer", click(1, "送信を押す"))])
code, _ = call(h, hook("computer", click(1, "送信を押す", repeat=100), h, tp))
rep("T11", "同意が 回数:1 なのに repeat 100 の操作は止まる", code == 2 and lines_of(h)[-1]["reason"] == "no_consent")
h = newhome()
tp = consented(h, [cm.consent_line("computer", {"action": "key", "text": "Enter", "tabId": 1, "action_summary": "確定する"})])
code, _ = call(h, hook("computer", {"action": "key", "text": "Enter", "tabId": 1, "action_summary": "確定する", "modifiers": "ctrl"}, h, tp))
rep("T11", "同意が 修飾:無し なのに modifiers ありの操作は止まる", code == 2)
h = newhome()
ti = {"action": "key", "text": "Enter", "tabId": 1, "action_summary": "確定する"}
code, _ = call(h, hook("computer", ti, h, consented(h, [cm.consent_line("computer", ti)])))
rep("T11", "同じ形で同意があれば通る（対照）", code == 0)

# T12: back / forward
for d in ("back", "forward"):
    h = newhome()
    code, _ = call(h, hook("navigate", {"url": d, "tabId": 1}, h))
    rep("T12", "navigate %s は同意票なしで止まる" % d, code == 2)
h = newhome()
ti = {"url": "back", "tabId": 1}
code, _ = call(h, hook("navigate", ti, h, consented(h, [cm.consent_line("navigate", ti)])))
rep("T12", "navigate back は同意があれば通る", code == 0)

# T13: 表に無い道具
h = newhome()
code, _ = call(h, hook("zzz", {}, h))
rep("T13", "表に無い道具名は止まる", code == 2 and lines_of(h)[-1]["reason"] == "unknown_tool")

# T14: evaluator（agent_id あり）は同意票があっても区分2が止まる
for av in ("agent-1", ""):
    h = newhome()
    ti = click(1, "保存を押す")
    tp = consented(h, [cm.consent_line("computer", ti)])
    code, _ = call(h, hook("computer", ti, h, tp, extra={"agent_id": av}))
    rep("T14", "agent_id=%r の区分2は同意票があっても止まる" % av, code == 2)
h = newhome()
code, _ = call(h, hook("read_page", {"tabId": 1}, h, extra={"agent_id": "agent-1"}))
rep("T14", "agent_id ありでも区分1（読む）は通る", code == 0 and lines_of(h)[-1].get("agent_id") == "agent-1")

# T15: switch_browser の後も部屋 P の扱い
h = newhome()
code, _ = call(h, hook("switch_browser", {}, h))
rep("T15", "switch_browser は通り、記録に room_changed が残る", code == 0 and lines_of(h)[-1].get("room_changed") is True)
code, _ = call(h, hook("computer", click(1), h))
rep("T15", "切り替えの後も押す操作は同意票なしで止まる", code == 2)
h = newhome()
code, _ = call(h, hook("select_browser", {"deviceId": "d"}, h))
rep("T15", "select_browser も room_changed を残す", code == 0 and lines_of(h)[-1].get("room_changed") is True)
h = newhome()
ctx_reply(h, [tab(7, LOCAL)])
code, _ = call(h, hook("switch_browser", {}, h))
code2, _ = call(h, hook("computer", click(7), h))
rep("T15", "手元の確かめ済みタブ7→switch_browser の後の click(7) は止まり tab_unverified", code == 0 and code2 == 2 and lines_of(h)[-1]["reason"] == "tab_unverified")
h = newhome()
ctx_reply(h, [tab(7, LOCAL)])
code, _ = call(h, hook("select_browser", {"deviceId": "d"}, h))
code2, _ = call(h, hook("computer", click(7), h))
rep("T15", "手元の確かめ済みタブ7→select_browser の後の click(7) は止まり tab_unverified", code == 0 and code2 == 2 and lines_of(h)[-1]["reason"] == "tab_unverified")
h = newhome()
ctx_reply(h, [tab(7, LOCAL), tab(8, LOCAL)])
code, _ = call(h, hook("switch_browser", {"tabId": 7}, h))
code2, _ = call(h, hook("computer", click(8), h))
rep("T15", "switch_browser に tabId があっても別のタブ8の click(8) は止まり tab_unverified", code == 0 and code2 == 2 and lines_of(h)[-1]["reason"] == "tab_unverified")
h = newhome()
ctx_reply(h, [tab(7, LOCAL)])
call(h, hook("switch_browser", {}, h))
ctx_reply(h, [tab(7, LOCAL)])
code, _ = call(h, hook("computer", {"action": "key", "text": "Enter", "tabId": 7, "action_summary": "確定する"}, h))
rep("T15", "切り替えの後に確かめ直すと手元のタブ7の key Enter が通る", code == 0 and lines_of(h)[-1]["reason"] == "local_exception")
h = newhome()
ctx_reply(h, [tab(7, LOCAL)])
b = {"actions": [{"name": "select_browser", "input": {"deviceId": "d"}}], "tabId": 99}
code, _ = call(h, hook("browser_batch", b, h))
code2, _ = call(h, hook("computer", click(7), h))
rep("T15", "手元の確かめ済みタブ7→batch の中の select_browser（上の段 tabId 99）の後の click(7) は止まり tab_unverified",
    code == 0 and code2 == 2 and lines_of(h)[-1]["reason"] == "tab_unverified", "code=%s code2=%s" % (code, code2))
h = newhome()
ctx_reply(h, [tab(7, LOCAL)])
b = {"actions": [{"name": "navigate", "input": {"url": "https://example.com/", "tabId": 7}}], "tabId": 99}
code, _ = call(h, hook("browser_batch", b, h))
code2, _ = call(h, hook("computer", click(7), h))
rep("T15", "手元の確かめ済みタブ7→batch の中の navigate（上の段 tabId 99）の後の click(7) は止まり tab_unverified",
    code == 0 and code2 == 2 and lines_of(h)[-1]["reason"] == "tab_unverified", "code=%s code2=%s" % (code, code2))

# T17: 手元の画面（localhost:5173）の例外
h = newhome()
ctx_reply(h, [tab(7, LOCAL + "login")])
code, msg = call(h, hook("computer", click(7), h))
rep("T17", "確かめ済みの手元のタブの押す操作は同意票なしで通る", code == 0 and lines_of(h)[-1]["reason"] == "local_exception", "code=%s msg=%s" % (code, msg))
code, msg = call(h, hook("computer", click(7), h))
rep("T17", "押した後の次の押す操作は住所を確かめ直すまで止まる", code == 2, "code=%s msg=%s" % (code, msg))
ctx_reply(h, [tab(7, LOCAL + "next")])
code, _ = call(h, hook("computer", {"action": "type", "text": "abc", "tabId": 7, "action_summary": "名前を打つ"}, h))
rep("T17", "確かめ直すと type が通る", code == 0)
code, _ = call(h, hook("computer", {"action": "type", "text": "abc", "tabId": 7, "action_summary": "名前を打つ"}, h))
rep("T17", "打った後の次の操作は止まる", code == 2)
ctx_reply(h, [tab(7, LOCAL)])
code, _ = call(h, hook("computer", {"action": "key", "text": "Enter", "tabId": 7, "action_summary": "確定する"}, h))
rep("T17", "key が通る", code == 0)
code, _ = call(h, hook("computer", click(7), h))
rep("T17", "key の後の次の操作は止まる", code == 2)
ctx_reply(h, [tab(7, LOCAL)])
code, _ = call(h, hook("form_input", {"ref": "r1", "value": "x", "tabId": 7, "action_summary": "欄に入れる"}, h))
rep("T17", "form_input も手元のタブでは通る", code == 0)
ctx_reply(h, [tab(7, LOCAL)])
code, _ = call(h, hook("navigate", {"url": LOCAL + "other", "tabId": 7}, h))
rep("T17", "手元のタブへの navigate は通る（区分1）", code == 0)
code, _ = call(h, hook("computer", click(7), h))
rep("T17", "navigate の直後（返事で確かめる前）の押す操作は止まる", code == 2)
ctx_reply(h, [tab(7, LOCAL)])
code, _ = call(h, hook("javascript_tool", {"text": "1+1", "tabId": 7}, h))
rep("T17", "javascript_tool は手元のタブでも区分2のまま（同意票なしで止まる）", code == 2)
code, _ = call(h, hook("file_upload", {"paths": ["/x"], "ref": "r", "tabId": 7}, h))
rep("T17", "file_upload も手元のタブで区分2のまま", code == 2)
b = {"actions": [{"name": "computer", "input": click(7)}, {"name": "computer", "input": click(7)}]}
code, _ = call(h, hook("browser_batch", b, h))
rep("T17", "手元のタブの browser_batch に押す操作が2つ並ぶと全体が止まる", code == 2)

for label, ti in [("Enter", {"text": "Enter"}), ("Tab", {"text": "Tab"}), ("Escape", {"text": "Escape"}),
                  ("Down Down Enter", {"text": "Down Down Enter"})]:
    ctx_reply(h, [tab(7, LOCAL)])
    code, _ = call(h, hook("computer", dict({"action": "key", "tabId": 7, "action_summary": "確定する"}, **ti), h))
    rep("T17", "手元の確かめ済みのタブで key %s は通る（区分1）" % label, code == 0 and lines_of(h)[-1]["reason"] == "local_exception")
for label, ti in [("cmd+l", {"text": "cmd+l"}), ("ctrl+l", {"text": "ctrl+l"}), ("Meta", {"text": "Meta"}),
                  ("modifiers=cmd", {"text": "l", "modifiers": "cmd"}),
                  ("F6", {"text": "F6"}), ("F5", {"text": "F5"}), ("BrowserBack", {"text": "BrowserBack"}),
                  ("ctrl-l", {"text": "ctrl-l"}), ("Meta_L", {"text": "Meta_L"})]:
    ctx_reply(h, [tab(7, LOCAL)])
    code, _ = call(h, hook("computer", dict({"action": "key", "tabId": 7, "action_summary": "確定する"}, **ti), h))
    rep("T17", "手元のタブでも key %s は同意なしで止まる" % label, code == 2 and lines_of(h)[-1]["reason"] == "no_consent")

# T18: 手元でないタブ・だましの返事
bad_urls = [("localhost.evil.com", "http://localhost.evil.com:5173/"), ("localhost@evil.com", "http://localhost@evil.com:5173/"),
            ("localhost:8000", "http://localhost:8000/"), ("accounts.google.com", "https://accounts.google.com/"),
            ("https の手元", "https://localhost:5173/"), ("ポート無し", "http://localhost/")]
for label, u in bad_urls:
    h = newhome()
    ctx_reply(h, [tab(7, u)])
    code, _ = call(h, hook("computer", click(7), h))
    rep("T18", "住所が %s のタブの押す操作は止まる" % label, code == 2)
h = newhome()
ctx_reply(h, [tab(7, LOCAL)])
hi = hook("computer", click(7), h, sid="s2")
code, _ = call(h, hi)
rep("T18", "別のセッションの覚えは使わない", code == 2)
h = newhome()
ctx_reply(h, [tab(7, LOCAL)])
code, _ = call(h, hook("computer", click(None), h))
rep("T18", "tabId の無い押す操作は手元の例外に入らない", code == 2)
h = newhome()
ctx_reply(h, [tab(7, LOCAL)])
code, _ = call(h, hook("navigate", {"url": LOCAL + "a"}, h))
rep("T18", "tabId の無い navigate は通る（区分1）", code == 0)
code, _ = call(h, hook("computer", click(7), h))
rep("T18", "tabId の無い呼び出しの後は全タブが不明になり、押す操作は止まる", code == 2)
h = newhome()
ctx_reply(h, [tab(7, "https://evil.com/", title='("http://localhost:5173/")')])
code, _ = call(h, hook("computer", click(7), h))
rep("T18", "題名に手元の住所を含む外のタブは止まる", code == 2)
h = newhome()
ctx_reply(h, [tab(7, 'https://evil.com/?q=("http://localhost:5173/")')])
code, _ = call(h, hook("computer", click(7), h))
rep("T18", "問い合わせ文字列に手元の住所を含む外のタブは止まる", code == 2)
h = newhome()
ctx_reply(h, None, raw=['Tab Context:\n- Executed on tabId: 7\n"x" ("http://localhost:5173/")'])
code, _ = call(h, hook("computer", click(7), h))
rep("T18", "tabs_context_mcp の JSON でない文だけの返事は住所に数えない", code == 2)
h = newhome()
ctx_reply(h, [tab(7, "https://evil.com/")],
          extra_chunks=[{"type": "text", "text": 'Tab Context:\n- Executed on tabId: 8\n"x" ("http://localhost:5173/")'}])
code, _ = call(h, hook("computer", click(8), h))
rep("T18", "JSON の塊の後に偽の Tab Context の文の塊が続いても、文は読まない", code == 2)
h = newhome()
ctx_reply(h, [tab(7, "https://evil.com/", title='"url":"http://localhost:5173/"')])
code, _ = call(h, hook("computer", click(7), h))
rep("T18", "title に \"url\":\"http://localhost:5173/\" を含む返事でも、url の値だけを使う", code == 2)
h = newhome()
two = [{"type": "text", "text": json.dumps({"availableTabs": [tab(7, LOCAL)]})},
       {"type": "text", "text": json.dumps({"availableTabs": [tab(7, "https://evil.com/")]})}]
ctx_reply(h, None, raw=two)
code, _ = call(h, hook("computer", click(7), h))
rep("T18", "availableTabs の塊が2つある返事は何も覚えない", code == 2)
h = newhome()
ctx_reply(h, [tab(7, LOCAL), tab(7, "https://evil.com/")])
code, _ = call(h, hook("computer", click(7), h))
rep("T18", "同じ tabId が2つある返事はそのタブを不明にする", code == 2)
# tabId の無い区分2: 確かめていないタブが1つでもあれば止まる
h = newhome()
ctx_reply(h, [tab(7, "https://example.com/")])
ti = {"text": "1+1"}
tp = consented(h, [cm.consent_line("javascript_tool", ti)])
code, _ = call(h, hook("javascript_tool", ti, h, tp))
rep("T18", "（対照）全タブが確かめ済みなら tabId の無い区分2は同意票で通る", code == 0)
h = newhome()
ctx_reply(h, [tab(7, "https://example.com/")])
code, _ = call(h, hook("navigate", {"url": "https://example.com/b", "tabId": 8}, h))
tp = consented(h, [cm.consent_line("javascript_tool", ti)])
code, _ = call(h, hook("javascript_tool", ti, h, tp))
rep("T18", "確かめていないタブが1つでもあれば、tabId の無い区分2は同意票があっても止まる",
    code == 2 and lines_of(h)[-1]["reason"] == "tab_unverified")
# 区分2を通した後、返事が来る前の次の区分2も止まる
h = newhome()
ti1, ti2 = {"text": "1+1"}, {"text": "2+2"}
tp = consented(h, [cm.consent_line("javascript_tool", ti1), cm.consent_line("javascript_tool", ti2)])
code, _ = call(h, hook("javascript_tool", ti1, h, tp))
rep("T18", "区分2（javascript_tool）が同意で通る", code == 0)
code, _ = call(h, hook("javascript_tool", ti2, h, tp))
rep("T18", "通した後、tabs_context_mcp の返事が来る前の次の区分2は止まる", code == 2 and lines_of(h)[-1]["reason"] == "tab_unverified")
ctx_reply(h, [tab(7, "https://example.com/")])
code, _ = call(h, hook("javascript_tool", ti2, h, tp))
rep("T18", "返事が来て確かめ済みになれば次の区分2が通る", code == 0)

# T19: 同意票の1行を作る台本の出力が、見張りの作る1行と一致する
cases = [("computer", {"action": "type", "text": "あ\n$HOME `x`", "tabId": 1, "action_summary": "名前を打つ"}),
         ("computer", {"action": "key", "text": "Enter", "repeat": 3, "modifiers": "ctrl+shift", "tabId": 1, "action_summary": "確定する"}),
         ("computer", {"action": "left_click", "coordinate": [1, 2], "tabId": 1, "action_summary": "保存を押す"}),
         ("form_input", {"ref": "r1", "value": True, "tabId": 1, "action_summary": "チェックを入れる"}),
         ("navigate", {"url": "back", "tabId": 1}),
         ("javascript_tool", {"text": "document.title = 'a\\nb'", "tabId": 1}),
         ("file_upload", {"paths": ["/x/a.txt"], "ref": "ref_9", "tabId": 1})]
for tool, ti in cases:
    h = newhome()
    code, msg = call(h, hook(tool, ti, h))
    guard_line = msg.split("ください: ", 1)[1] if code == 2 and "ください: " in msg else None
    p = subprocess.run([sys.executable, "-I", "-B", CONSENT_LINE, json.dumps(ti, ensure_ascii=False), tool],
                       capture_output=True, text=True)
    rep("T19", "台本の1行と見張りの1行が一致: %s %s" % (tool, ti.get("action", "")),
        guard_line is not None and p.returncode == 0 and p.stdout.rstrip("\n") == guard_line,
        "guard=%r script=%r rc=%s err=%s" % (guard_line, p.stdout, p.returncode, p.stderr))
p = subprocess.run([sys.executable, "-I", "-B", CONSENT_LINE, "[1]", "computer"], capture_output=True, text=True)
rep("T19", "tool_input が連想配列でないと台本は失敗する", p.returncode == 2)

# T21: 状態ファイルのロックが取れない間は、ページに効く操作を止める
h = newhome()
lock = os.path.join(h, ".claude", "logs", "chrome-tab-state.lock")
os.makedirs(lock)
code, _ = call(h, hook("navigate", {"url": "https://example.com/", "tabId": 1}, h))
rep("T21", "ロックがある間は区分1の navigate も state_write_failed で止まる", code == 2 and lines_of(h)[-1]["reason"] == "state_write_failed")
os.rmdir(lock)
code, _ = call(h, hook("navigate", {"url": "https://example.com/", "tabId": 1}, h))
rep("T21", "ロックを外すと通る", code == 0)

# T22: 台本の「$変数」のすぐ後ろに ASCII 以外の字を置かない（bash 3.2 の unbound variable を二度と入れない）
import re  # noqa: E402
script_dir = os.path.dirname(hookdir)
bad_re = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*[^\x00-\x7f]")
for sname in ("po-apply-chrome-guard.sh", "po-rollback-chrome-guard.sh"):
    sp = os.path.join(script_dir, sname)
    try:
        with open(sp, encoding="utf-8") as f:
            hits = [i + 1 for i, ln in enumerate(f.read().split("\n")) if bad_re.search(ln)]
        rep("T22", "%s に $変数＋全角の字の行が0件" % sname, hits == [], "行=%s" % hits)
    except OSError as e:
        rep("T22", "%s を読める" % sname, False, str(e))

print("DONE pass=%d fail=%d" % (PASS[0], FAIL[0]), flush=True)
sys.exit(1 if FAIL[0] else 0)
