#!/usr/bin/env python3
"""chrome_op_record.py - Claude in Chrome の道具の返事から、タブの住所を覚える（PostToolUse）。ADR-1085 便1。

設計: docs/handoff/browser-operation-delegation/design.md §5「今のタブの住所の覚え方」。
- 覚えてよいのは tabs_context_mcp の返事の JSON（availableTabs[] の tabId と url）だけ。文の部分は読まない。
- 何があっても exit 0（記録に失敗しても道具の返事を止めない）。返事の生の中身は記録に残さない。
"""
import datetime
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chrome_common as cm  # noqa: E402

TARGET = cm.PREFIX + "tabs_context_mcp"


def response_chunks(resp):
    """tool_response（文字列・塊の並び・{"content": [...]}）から text の塊を1つずつ取り出す。"""
    if isinstance(resp, dict) and isinstance(resp.get("content"), list):
        resp = resp["content"]
    if isinstance(resp, str):
        return [resp]
    if isinstance(resp, list):
        out = []
        for c in resp:
            if isinstance(c, str):
                out.append(c)
            elif isinstance(c, dict) and c.get("type") == "text" and isinstance(c.get("text"), str):
                out.append(c["text"])
        return out
    return []


def parse_tabs(resp):
    """塊ごとに全体を json.loads。availableTabs が list の塊がちょうど1つのときだけ、その list を返す。他は None。"""
    found = []
    for ch in response_chunks(resp):
        try:
            d = json.loads(ch)
        except Exception:
            continue
        if isinstance(d, dict) and isinstance(d.get("availableTabs"), list):
            found.append(d["availableTabs"])
    return found[0] if len(found) == 1 else None


def record(hi, now=None, h=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if not isinstance(hi, dict) or hi.get("tool_name") != TARGET:
        return
    sid = hi.get("session_id")
    sid = sid if isinstance(sid, str) and sid else "?"
    tabs = parse_tabs(hi.get("tool_response"))
    entries, counts = [], {}
    if tabs is not None:
        for it in tabs:
            if isinstance(it, dict) and isinstance(it.get("tabId"), int) and not isinstance(it.get("tabId"), bool) \
                    and isinstance(it.get("url"), str):
                entries.append((it["tabId"], it["url"]))
                counts[it["tabId"]] = counts.get(it["tabId"], 0) + 1
    parsed = tabs is not None and len(entries) > 0
    logged = []
    if entries:
        try:
            with cm.State(h) as st:
                for tid, url in entries:
                    p = cm.parse_url(url)
                    text = p["text"] if p else url
                    if counts[tid] > 1 or p is None:
                        st.mark_unknown(sid, tid)
                    else:
                        st.set_verified(sid, tid, text)
                    logged.append({"tabId": tid, "url": text})
                st.clear_all_unknown_if_done(sid)
        except Exception:
            parsed = False
            logged = []
    rec = {"ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "type": "tab_context", "session": sid,
           "tab_context_parsed": bool(parsed), "tabs": logged}
    if "agent_id" in hi:
        rec["agent_id"] = hi.get("agent_id")
    cm.append_log(rec, h)


def main():
    try:
        record(json.loads(sys.stdin.read()))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
