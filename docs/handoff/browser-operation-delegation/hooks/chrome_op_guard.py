#!/usr/bin/env python3
"""chrome_op_guard.py - Claude in Chrome の道具の見張り（PreToolUse）。ADR-1085 便1・部屋 P だけ。

設計: docs/handoff/browser-operation-delegation/design.md §4・§5。区分の正本は同じ場所の tiers.json。
通すとき exit 0。止めるとき標準エラーに日本語の理由1行と exit 2。壊れたときは止める側（exit 2）に倒す。
同意の判定は1つ上の階層の consent_check.py（ADR-1033）を importlib で読んで使う（この1か所だけ）。
"""
import datetime
import importlib.util
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chrome_common as cm  # noqa: E402

_CC = []


def load_consent():
    """consent_check.py を読む。読めなければ例外（呼ぶ側が止める）。"""
    if _CC:
        return _CC[0]
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "consent_check.py")
    spec = importlib.util.spec_from_file_location("consent_check", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _CC.append(mod)
    return mod


def tab_id_of(ti):
    v = ti.get("tabId") if isinstance(ti, dict) else None
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def classify(t, ti, tiers):
    """1つの道具呼び出しの区分。{tier: 1|2|3|"block", reason, lowerable, url}。"""
    tools = tiers["tools"]
    if t in tools["tier1"]:
        return {"tier": 1, "reason": "read"}
    if t == "navigate":
        url = ti.get("url")
        if url in ("back", "forward"):
            return {"tier": 2, "reason": "back_forward", "lowerable": False}
        p = cm.parse_url(url)
        if p is None:
            return {"tier": "block", "reason": "bad_url"}
        why = cm.tier3_match(p, tiers)
        if why:
            return {"tier": 3, "reason": "tier3_url:" + why, "url": p["text"], "why": why}
        return {"tier": 1, "reason": "navigate", "url": p["text"]}
    if t == "computer":
        action = ti.get("action")
        if action in tiers["computer_actions"]["tier1"]:
            return {"tier": 1, "reason": "computer_read"}
        if action in tiers["computer_actions"]["tier2"]:
            return {"tier": 2, "reason": "computer_act", "lowerable": action != "key" or key_is_plain(ti, tiers)}
        return {"tier": "block", "reason": "unknown_action"}
    if t in tools["tier2"]:
        return {"tier": 2, "reason": "tier2_tool", "lowerable": t == "form_input"}
    return {"tier": "block", "reason": "unknown_tool"}


def batch_items(ti):
    """browser_batch の actions[] を [(道具名, 入力)] にする。
    各項目は道具の定義どおり、鍵がちょうど name（str）と input（dict）の2つのときだけ読む。
    それ以外の形が1つでもあれば None（batch 全体を止める）。"""
    acts = ti.get("actions")
    if not isinstance(acts, list) or not acts:
        return None
    out = []
    for a in acts:
        if not isinstance(a, dict) or set(a.keys()) != {"name", "input"}:
            return None
        name, inp = a["name"], a["input"]
        if not isinstance(name, str) or not isinstance(inp, dict):
            return None
        if name.startswith(cm.PREFIX):
            name = name[len(cm.PREFIX):]
        out.append((name, inp))
    return out


def key_is_plain(ti, tiers):
    """手元の例外で区分1に下げてよい key か。tiers.json の local_plain_keys の語だけ許す（アドレス欄へ移る道を塞ぐ）。"""
    text = ti.get("text")
    if not isinstance(text, str) or not text.strip():
        return False
    if ti.get("modifiers") not in (None, ""):
        return False
    allowed = {k.lower() for k in tiers["local_plain_keys"]}
    return all(w.lower() in allowed for w in text.split())


def page_affecting_key(t, ti):
    return "computer:%s" % ti.get("action") if t == "computer" else t


def _iso(now):
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def decide(hi, now=None, consent_home=None):
    """(終了コード, 標準エラーの文)。記録も書く。"""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    try:
        return _decide(hi, now, consent_home)
    except Exception:
        return 2, "chrome-op-guard: 見張りの内部エラーのため止めました（安全側）"


def _decide(hi, now, consent_home):
    if not isinstance(hi, dict):
        return 2, "chrome-op-guard: 入力が読めないため止めました"
    tiers = cm.load_tiers()  # 読めない・形が違う → 例外 → decide が exit 2
    name = hi.get("tool_name")
    if not isinstance(name, str) or not name.startswith(cm.PREFIX):
        return 0, ""
    t = name[len(cm.PREFIX):]
    ti = hi.get("tool_input")
    if ti is None:
        ti = {}
    if not isinstance(ti, dict):
        return 2, "chrome-op-guard: 道具の入力が読めないため止めました"
    sid = hi.get("session_id")
    sid = sid if isinstance(sid, str) and sid else "?"
    tab_id = tab_id_of(ti)
    action = ti.get("action") if t == "computer" and isinstance(ti.get("action"), str) else None

    rec = {"ts": _iso(now), "session": sid, "tool": t, "action": action, "room": "P", "text_len": 0}
    if "agent_id" in hi:
        rec["agent_id"] = hi.get("agent_id")
    if t in ("switch_browser", "select_browser"):
        rec["room_changed"] = True
        tab_id = None  # tabId はブラウザごとの番号。入力に付いていてもセッションの全タブを不明にする
    if t == "browser_batch":
        # batch の中身は別のタブや切り替えを含みうるので、上の段の tabId は使わずセッションの全タブを不明にする
        tab_id = None

    def done(code, msg, tier, decision, reason):
        rec.update({"tier": tier, "decision": decision, "reason": reason})
        cm.append_log(rec)
        return code, msg

    # 判定（設計 §5 の表）
    items = None
    if t == "browser_batch":
        items = batch_items(ti)
        if items is None:
            return done(2, "chrome-op-guard: browser_batch の中身が読めないため止めました", 2, "block", "bad_batch")
        total_len = 0
        for it, iti in items:
            if it == "browser_batch":
                return done(2, "chrome-op-guard: browser_batch の入れ子は止めました", 2, "block", "nested_batch")
            c = classify(it, iti, tiers)
            if c["tier"] == 3:
                return done(2, "chrome-op-guard: 区分3（%s）の画面は PO 本人だけです（batch の中）" % c["why"], 3, "block", c["reason"])
            if c["tier"] == "block":
                return done(2, "chrome-op-guard: 許可表に無い操作を止めました（batch の中）", 2, "block", c["reason"])
            txt = cm.typed_text(it, iti)
            total_len += len(txt.encode("utf-8"))
            if txt and (cm.looks_like_card(txt) or cm.has_secret(txt, tiers)):
                rec["text_len"] = total_len
                return done(2, "chrome-op-guard: カード番号・鍵の形の文字を止めました（batch の中）", 2, "block", "secret_or_card")
            if c["tier"] == 2:
                rec["text_len"] = total_len
                return done(2, "chrome-op-guard: browser_batch に区分2の操作が混じっています。1操作ずつ出し直してください", 2, "block", "batch_has_tier2")
        rec["text_len"] = total_len
        cls = {"tier": 1, "reason": "batch_all_read"}
    else:
        cls = classify(t, ti, tiers)
        if cls["tier"] == 3:
            if cls.get("url"):
                rec["url"] = cls["url"]
            return done(2, "chrome-op-guard: 区分3（%s）の画面は PO 本人だけです。開きません" % cls["why"], 3, "block", cls["reason"])
        if cls["tier"] == "block":
            return done(2, "chrome-op-guard: 許可表に無い道具・action を止めました（%s）" % cls["reason"], 2, "block", cls["reason"])
        if t == "navigate" and cls.get("url"):
            rec["url"] = cls["url"]
        txt = cm.typed_text(t, ti)
        rec["text_len"] = len(txt.encode("utf-8"))
        if txt and (cm.looks_like_card(txt) or cm.has_secret(txt, tiers)):
            return done(2, "chrome-op-guard: カード番号・鍵の形の文字を止めました", cls["tier"], "block", "secret_or_card")

    tier = cls["tier"]
    reason = cls["reason"]
    affecting = page_affecting_key(t, ti) in tiers["page_affecting"]
    verified_local = False

    # 状態を見る必要があるときだけロックを取る（読む道具は状態の不調で止めない）
    if tier == 2:
        try:
            with cm.State() as st:
                if cls.get("lowerable") and tab_id is not None:
                    tabinfo = st.tab(sid, tab_id)
                    if tabinfo and tabinfo.get("status") == "verified":
                        verified_local = cm.is_local_exception(cm.parse_url(tabinfo.get("url")), tiers)
                if verified_local:
                    tier, reason = 1, "local_exception"
                else:
                    if tab_id is not None:
                        tabinfo = st.tab(sid, tab_id)
                        unsure = (tabinfo is not None and tabinfo.get("status") == "unknown") or \
                                 (tabinfo is None and bool(st.data["session_all_unknown"].get(sid)))
                    else:
                        unsure = st.session_has_unknown(sid)
                    if unsure:
                        return done(2, "chrome-op-guard: 前のページ操作の後の住所が未確認です。tabs_context_mcp を呼んでから出し直してください",
                                    2, "block", "tab_unverified")
        except cm.LockTimeout:
            return done(2, "chrome-op-guard: 状態ファイルのロックが取れないため止めました", 2, "block", "lock_timeout")

    decision = "pass"
    if tier == 2:
        if "agent_id" in hi:
            return done(2, "chrome-op-guard: サブエージェントは区分2の操作ができません", 2, "block", "agent_id")
        if t in ("computer", "form_input"):
            summ = ti.get("action_summary")
            if not isinstance(summ, str) or not summ.strip():
                return done(2, "chrome-op-guard: action_summary（何をするかの短い文）が無いため止めました", 2, "block", "no_action_summary")
            if any(c in summ for c in ("\n", "\r", "$", "`")):
                return done(2, "chrome-op-guard: action_summary に改行・$・バッククォートがあるため止めました", 2, "block", "bad_action_summary")
        line = cm.consent_line(t, ti)
        if any(c in line for c in ("\n", "\r", "$", "`")):
            return done(2, "chrome-op-guard: 同意の1行に改行・$・バッククォートが入るため止めました", 2, "block", "bad_line")
        try:
            cc = load_consent()
            ok, _why = cc.check(hi, line, now, home=consent_home) if consent_home else cc.check(hi, line, now)
        except Exception:
            return done(2, "chrome-op-guard: 同意の判定部品（consent_check.py）が読めないため止めました", 2, "block", "consent_unavailable")
        if not ok:
            return done(2, "同意票に次の1行を書いて PO の『1』をもらってください: %s" % line, 2, "block", "no_consent")
        decision = "consent_pass"

    if affecting:
        try:
            with cm.State() as st:
                st.mark_unknown(sid, tab_id)
        except Exception:
            # 「不明」の印を書けないなら通さない（止める側に倒す。同意票は使用済みになるが、それでよい）
            return done(2, "chrome-op-guard: 操作の後の覚えを残せないため止めました。~/.claude/logs/chrome-tab-state.json を確かめてください",
                        2, "block", "state_write_failed")
    return done(0, "", tier, decision, reason)


def main():
    try:
        hi = json.loads(sys.stdin.read())
    except Exception:
        sys.stderr.write("chrome-op-guard: 入力が読めないため止めました\n")
        return 2
    code, msg = decide(hi)
    if msg:
        sys.stderr.write(msg.splitlines()[0] + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
