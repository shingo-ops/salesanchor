#!/usr/bin/env python3
# 作り物の AI（b13）。容器の中 127.0.0.1:18765 で動かす。ネットには出ない。
# 受けた POST /v1/chat/completions ごとに /tmp/fake.log へ 1 行:
#   時刻 path stream=<True/None> roles=<role の並び> SYS7735=<system に有るか> MARK=<MARK7735 の有無>
#   + 識別用: n_tools・max_tokens・受けた model の値・schema_lead=<1/0>（頼みの文・形の指示の文は書かない）
# 形の指示の 1 文は環境変数 FAKE_LEAD_FILE（既定 /fake/schema_lead.txt）から読む。無い・空なら fake_ai=NO_LEAD を書いて終了コード 1。
# usage は prompt_tokens=11・completion_tokens=7・total_tokens=18 で返す。
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = "/tmp/fake.log"
SYS = "SYS7735"
MARK = "MARK7735"
LEAD = ""  # 形の指示の 1 文（起動時に FAKE_LEAD_FILE から読む。文はログに書かない）


def load_lead(path):
    """読めて空白だけでなければ中身（そのまま）。無い・読めない・空白だけなら None。"""
    try:
        with open(path, encoding="utf-8") as f:
            body = f.read()
    except OSError:
        return None
    return body if body.strip() else None


def has_lead(msgs, lead):
    """受けた messages のどれか（content が配列なら text の部分を合わせたもの）に 1 文が含まれるか。"""
    return bool(lead) and any(lead in text_of(m) for m in msgs if isinstance(m, dict))


def text_of(m):
    c = m.get("content")
    if isinstance(c, list):
        return " ".join(p.get("text", "") for p in c if isinstance(p, dict))
    return c if isinstance(c, str) else ""


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        with open(LOG, "a") as f:
            f.write(f"{time.strftime('%H:%M:%S')} GET {self.path} (non-chat)\n")
        if self.path.rstrip("/").endswith("/models"):
            self._send(200, json.dumps({"object": "list", "data": [{"id": "fake-model", "object": "model"}]}))
        else:
            self._send(404, "{}")

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n).decode("utf-8", "replace")
        if not self.path.endswith("/chat/completions"):
            with open(LOG, "a") as f:
                f.write(f"{time.strftime('%H:%M:%S')} POST {self.path} (non-chat)\n")
            self._send(404, "{}")
            return
        try:
            d = json.loads(raw)
        except Exception:
            d = {}
        msgs = d.get("messages") or []
        roles = ",".join(str(m.get("role")) for m in msgs)
        sys_has = any(m.get("role") == "system" and SYS in text_of(m) for m in msgs)
        any_sys = any(SYS in text_of(m) for m in msgs)
        mark = MARK in raw
        stream = d.get("stream")
        s0 = text_of(msgs[0]) if msgs else ""
        pos = s0.find(SYS)
        syspos = f"{pos}/{len(s0)}" if pos >= 0 else "-"
        with open(LOG, "a") as f:
            f.write(
                f"{time.strftime('%H:%M:%S')} POST {self.path} stream={stream} roles=[{roles}] "
                f"SYS7735_in_system={sys_has} sys_pos(文字位置/system全長)={syspos} SYS7735_anywhere={any_sys} MARK={mark} "
                f"n_tools={len(d.get('tools') or [])} max_tokens={d.get('max_tokens') or d.get('max_completion_tokens')} "
                f"model={d.get('model')} schema_lead={1 if has_lead(msgs, LEAD) else 0}\n"
            )
        usage = {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}
        if stream:
            ch = {"id": "fake-1", "object": "chat.completion.chunk", "model": "fake-model",
                  "choices": [{"index": 0, "delta": {"role": "assistant", "content": "FAKE-REPLY-OK"}, "finish_reason": None}]}
            fin = {"id": "fake-1", "object": "chat.completion.chunk", "model": "fake-model",
                   "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
            us = {"id": "fake-1", "object": "chat.completion.chunk", "model": "fake-model", "choices": [], "usage": usage}
            body = "".join(f"data: {json.dumps(x)}\n\n" for x in (ch, fin, us)) + "data: [DONE]\n\n"
            self._send(200, body, "text/event-stream")
        else:
            self._send(200, json.dumps({
                "id": "fake-1", "object": "chat.completion", "model": "fake-model",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "FAKE-REPLY-OK"}, "finish_reason": "stop"}],
                "usage": usage}))


def main():
    global LEAD
    lead = load_lead(os.environ.get("FAKE_LEAD_FILE", "/fake/schema_lead.txt"))
    if lead is None:
        with open(LOG, "a") as f:
            f.write("fake_ai=NO_LEAD\n")
        return 1
    LEAD = lead
    with open(LOG, "a") as f:
        f.write(f"fake_ai=START lead_chars={len(lead)}\n")
    ThreadingHTTPServer(("127.0.0.1", 18765), H).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
