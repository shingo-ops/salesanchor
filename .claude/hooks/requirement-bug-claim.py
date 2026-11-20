#!/usr/bin/env python3
"""Stop 見張り: ADR・設計書を読まずに「不具合」「バグ」と言いかけたら1回だけ止める（requirement-library design §3 便3・R4）。

どんな失敗でも終了コード 0 で何も出さない。標準ライブラリだけ。
"""
import datetime
import json
import os
import re
import sys

REASON = ("要件の書類を読んでから判定してください。docs/adr/FEATURE-INDEX.md でこの場所の ADR と設計書を引き、"
          "読んでから、決まりどおりの動きか不具合かを書き直してください。")
CLAIM_RE = re.compile("不具合|バグ")
READ_MARKS = ("docs/adr/", "docs/specs/")


def _entries(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict):
                yield obj


def _blocks(entry):
    msg = entry.get("message")
    if not isinstance(msg, dict):
        return []
    content = msg.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return [b for b in content if isinstance(b, dict)]
    return []


def analyze(path):
    """(最後の assistant の文, 読んだか) を返す。"""
    last_text = ""
    read = False
    for e in _entries(path):
        if e.get("type") != "assistant":
            continue
        texts = []
        for b in _blocks(e):
            if b.get("type") == "text" and isinstance(b.get("text"), str):
                texts.append(b["text"])
            elif b.get("type") == "tool_use":
                name = b.get("name")
                inp = b.get("input")
                if not isinstance(inp, dict):
                    continue
                if name == "Read":
                    s = str(inp.get("file_path", ""))
                elif name in ("Bash", "Grep", "Glob"):
                    s = json.dumps(inp, ensure_ascii=False)
                else:
                    continue
                if any(m in s for m in READ_MARKS):
                    read = True
        if texts:
            last_text = "\n".join(texts)
    return last_text, read


def log_path():
    p = os.environ.get("REQUIREMENT_LIBRARY_LOG")
    if p:
        return p
    return os.path.join(os.path.expanduser("~"), ".claude", "requirement-library", "bug-claims.log")


def write_log(session_id, text):
    jst = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M")
    head = re.sub(r"[\r\n\t]", " ", text)[:40]
    sid = re.sub(r"[\r\n\t]", " ", str(session_id))
    p = log_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write("%s\t%s\t%s\n" % (now, sid, head))


def main():
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict) or data.get("stop_hook_active"):
            return 0
        tp = data.get("transcript_path")
        if not tp:
            return 0
        text, read = analyze(tp)
        if not CLAIM_RE.search(text) or read:
            return 0
        try:
            write_log(data.get("session_id", ""), text)
        except Exception:
            pass
        print(json.dumps({"decision": "block", "reason": REASON}, ensure_ascii=False))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
