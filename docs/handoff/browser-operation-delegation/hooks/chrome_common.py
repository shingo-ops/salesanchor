#!/usr/bin/env python3
"""chrome_common.py - chrome_op_guard.py（PreToolUse）と chrome_op_record.py（PostToolUse）が共有する部品。

設計: docs/handoff/browser-operation-delegation/design.md §4・§5（ADR-1085 便1・部屋 P だけ）。
- 区分の正本は同じ場所の tiers.json（ここに書き写さない）。
- 置き場の例外・失敗は呼ぶ側が「止める（exit 2）」に倒す。ここでは例外をそのまま上げる。
"""
import hashlib
import json
import os
import re
import shutil
import time
import unicodedata
import urllib.parse

PREFIX = "mcp__claude-in-chrome__"
HERE = os.path.dirname(os.path.abspath(__file__))
LOCK_WAIT_SEC = 3.0
LOCK_STALE_SEC = 30.0


def home():
    return os.path.expanduser("~")


def logs_dir(h=None):
    return os.path.join(h or home(), ".claude", "logs")


# ── tiers.json ─────────────────────────────────────────────────────

def load_tiers(path=None):
    """tiers.json を読み、形を確かめる。形が違えば ValueError。"""
    path = path or os.path.join(HERE, "tiers.json")
    with open(path, encoding="utf-8") as f:
        t = json.load(f)
    if not isinstance(t, dict) or t.get("version") != 1:
        raise ValueError("tiers: version")
    tools = t.get("tools")
    if not isinstance(tools, dict):
        raise ValueError("tiers: tools")
    for k in ("tier1", "tier2", "special"):
        if not _is_str_list(tools.get(k)):
            raise ValueError("tiers: tools." + k)
    ca = t.get("computer_actions")
    if not isinstance(ca, dict) or not _is_str_list(ca.get("tier1")) or not _is_str_list(ca.get("tier2")):
        raise ValueError("tiers: computer_actions")
    if not _is_str_list(t.get("page_affecting")) or not _is_str_list(t.get("secret_patterns")) \
            or not _is_str_list(t.get("local_plain_keys")):
        raise ValueError("tiers: lists")
    le = t.get("local_exception")
    if not isinstance(le, list) or not all(
            isinstance(x, dict) and isinstance(x.get("scheme"), str) and isinstance(x.get("host"), str)
            and isinstance(x.get("port"), int) for x in le):
        raise ValueError("tiers: local_exception")
    t3 = t.get("tier3_urls")
    if not isinstance(t3, list) or not all(
            isinstance(x, dict) and isinstance(x.get("host"), str) and isinstance(x.get("path_regex"), str)
            and isinstance(x.get("why"), str) for x in t3):
        raise ValueError("tiers: tier3_urls")
    for x in t3:
        re.compile(x["path_regex"])
    for p in t["secret_patterns"]:
        re.compile(p)
    return t


def _is_str_list(v):
    return isinstance(v, list) and all(isinstance(x, str) for x in v)


# ── URL の整形と区分3・手元の例外 ─────────────────────────────────

_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")
_HTTP_SLASH_RE = re.compile(r"^(https?):/*", re.IGNORECASE)
_CTRL_RE =re.compile(r"[\x00-\x20\x7f]")


def _norm_host(host):
    """ホスト名の整形。止めるべきとき None。"""
    for _ in range(2):
        host = urllib.parse.unquote(host)
    host = unicodedata.normalize("NFKC", host)
    for ch in ("\u3002", "\uff0e", "\uff61"):
        host = host.replace(ch, ".")
    host = host.lower().rstrip(".")
    if not host:
        return None
    if not host.isascii():
        try:
            host = host.encode("idna").decode("ascii")
        except (UnicodeError, ValueError):
            return None
        host = host.lower().rstrip(".")
    if ":" not in host and not re.fullmatch(r"[a-z0-9.\-]+", host):
        return None
    return host


def _remove_dot_segments(path):
    """RFC 3986 5.2.4。根より上には出ない。"""
    stack = []
    segs = path.split("/")[1:]
    for seg in segs:
        if seg == ".":
            continue
        if seg == "..":
            if stack:
                stack.pop()
            continue
        stack.append(seg)
    out = "/" + "/".join(stack)
    if segs and segs[-1] in (".", "..") and not out.endswith("/"):
        out += "/"
    return out


def parse_url(url):
    """整形した URL を {scheme, host, port, path, text} で返す。読めなければ None（呼ぶ側が止める）。
    https:// が無ければ足す・ホストは unquote2回→NFKC→句点を . に→小文字→末尾の . を外す→idna・
    パスは unquote2回→/ をまとめる→. と .. をたたむ。"""
    if not isinstance(url, str):
        return None
    u = _CTRL_RE.sub("", url.strip().replace("\\", "/"))
    if not u:
        return None
    # WHATWG: http・https は「scheme:」の後ろの / の数によらず scheme:// として読む
    u = _HTTP_SLASH_RE.sub(lambda m: m.group(1).lower() + "://", u, count=1)
    if not _SCHEME_RE.match(u):
        u = "https://" + u
    try:
        sp = urllib.parse.urlsplit(u)
        host = sp.hostname
        port = sp.port
    except ValueError:
        return None
    if not host:
        return None
    host = _norm_host(host)
    if host is None:
        return None
    if ":" in host:
        host = "[" + host + "]"
    path = sp.path or "/"
    for _ in range(2):
        path = urllib.parse.unquote(path)
    path = path.replace("\\", "/")
    path = re.sub(r"/+", "/", path)
    if not path.startswith("/"):
        path = "/" + path
    path = _remove_dot_segments(path)
    hostport = host if port is None else "%s:%d" % (host, port)
    return {"scheme": sp.scheme.lower(), "host": host, "port": port, "path": path,
            "text": "%s://%s%s" % (sp.scheme.lower(), hostport, path)}


def tier3_match(parsed, tiers):
    """区分3の型に当たれば why（日本語）、当たらなければ None。"""
    if not parsed:
        return None
    host, path = parsed["host"], parsed["path"]
    for e in tiers["tier3_urls"]:
        pat = e["host"].lower()
        if pat.startswith("*."):
            suf = pat[2:]
            ok = host == suf or host.endswith("." + suf)
        else:
            ok = host == pat
        if ok and re.search(e["path_regex"], path, re.IGNORECASE):
            return e["why"]
    return None


def is_local_exception(parsed, tiers):
    """scheme・host・port が local_exception に完全一致（port 無しは http=80・https=443 扱い）。"""
    if not parsed:
        return False
    port = parsed["port"]
    if port is None:
        port = {"http": 80, "https": 443}.get(parsed["scheme"])
    for e in tiers["local_exception"]:
        if parsed["scheme"] == e["scheme"] and parsed["host"] == e["host"].lower() and port == e["port"]:
            return True
    return False


# ── 打つ文字の見張り ───────────────────────────────────────────────

def _luhn(digits):
    total, alt = 0, False
    for ch in reversed(digits):
        d = ord(ch) - 48
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


_CARD_RE = re.compile(r"\d(?:[ \-]?\d){12,18}")


def looks_like_card(text):
    for m in _CARD_RE.finditer(text):
        digits = re.sub(r"[ \-]", "", m.group())
        if 13 <= len(digits) <= 19 and _luhn(digits):
            return True
    return False


def has_secret(text, tiers):
    return any(re.search(p, text) for p in tiers["secret_patterns"])


def typed_text(t, ti):
    """打つ文字（無ければ空文字）。computer は type のときの text・form_input は value・javascript_tool は text。"""
    if not isinstance(ti, dict):
        return ""
    if t == "computer":
        v = ti.get("text") if ti.get("action") == "type" else None
    elif t == "form_input":
        v = ti.get("value")
    elif t == "javascript_tool":
        v = ti.get("text")
    else:
        v = None
    if v is None:
        return ""
    return v if isinstance(v, str) else str(v)


# ── 同意票の1行 ────────────────────────────────────────────────────

def consent_line(t, tool_input):
    """`chrome <道具> <action> <要約か url> 文字:<長さ>:<sha8> 回数:<repeat> 修飾:<modifiers>`。
    chrome_op_guard.py と chrome-consent-line.py の両方がこの1関数を呼ぶ（書き写さない・T19）。"""
    ti = tool_input if isinstance(tool_input, dict) else {}
    if t == "computer":
        action = str(ti.get("action", "-"))
        what = ti.get("action_summary")
    elif t == "navigate":
        action = str(ti.get("url", "-"))
        what = ti.get("url")
    elif t == "form_input":
        action = "-"
        what = ti.get("action_summary")
    elif t == "javascript_tool":
        action, what = "-", "js"
    else:
        action = "-"
        what = ti.get("ref") if isinstance(ti.get("ref"), str) and ti.get("ref") else "-"
    what = "" if what is None else str(what)
    text = typed_text(t, ti)
    raw = text.encode("utf-8")
    repeat = ti.get("repeat")
    mods = ti.get("modifiers")
    return "chrome %s %s %s 文字:%d:%s 回数:%s 修飾:%s" % (
        t, action, what, len(raw), hashlib.sha256(raw).hexdigest()[:8],
        1 if repeat is None else repeat, "無し" if mods in (None, "") else mods)


# ── 記録 ───────────────────────────────────────────────────────────

def append_log(rec, h=None):
    """chrome-ops.jsonl に1行足す。失敗しても道具を止めない（呼ぶ側の判定を変えない）。"""
    try:
        d = logs_dir(h)
        os.makedirs(d, mode=0o700, exist_ok=True)
        with open(os.path.join(d, "chrome-ops.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ── タブの状態（鍵 "<session_id>:<tabId>"） ─────────────────────────

class LockTimeout(Exception):
    pass


class State:
    """~/.claude/logs/chrome-tab-state.json の読み書き。mkdir のロック（最大3秒）。with 文で使う。"""

    def __init__(self, h=None):
        self.dir = logs_dir(h)
        self.path = os.path.join(self.dir, "chrome-tab-state.json")
        self.lock = os.path.join(self.dir, "chrome-tab-state.lock")
        self.data = None
        self.dirty = False
        self.locked = False

    def __enter__(self):
        os.makedirs(self.dir, mode=0o700, exist_ok=True)
        deadline = time.monotonic() + LOCK_WAIT_SEC
        while True:
            try:
                os.mkdir(self.lock)
                self.locked = True
                break
            except FileExistsError:
                try:
                    if time.time() - os.stat(self.lock).st_mtime > LOCK_STALE_SEC:
                        os.rmdir(self.lock)
                        continue
                except OSError:
                    pass
                if time.monotonic() >= deadline:
                    raise LockTimeout()
                time.sleep(0.02)
        try:
            self.data = self._load()
        except Exception:
            self._unlock()
            raise
        return self

    def __exit__(self, *exc):
        try:
            if exc[0] is None and self.dirty:
                tmp = self.path + ".%d.tmp" % os.getpid()
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, ensure_ascii=False)
                os.replace(tmp, self.path)
        finally:
            self._unlock()
        return False

    def _unlock(self):
        if self.locked:
            self.locked = False
            try:
                os.rmdir(self.lock)
            except OSError:
                shutil.rmtree(self.lock, ignore_errors=True)

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                d = json.load(f)
        except FileNotFoundError:
            d = {}
        if not isinstance(d, dict):
            raise ValueError("state")
        if not isinstance(d.get("tabs"), dict):
            d["tabs"] = {}
        if not isinstance(d.get("session_all_unknown"), dict):
            d["session_all_unknown"] = {}
        return d

    # 住所の覚え
    @staticmethod
    def key(sid, tab_id):
        return "%s:%s" % (sid, tab_id)

    def mark_unknown(self, sid, tab_id):
        """ページに効く操作の後。tabId があればそのタブ、無ければセッションの全タブを不明にする。"""
        tabs = self.data["tabs"]
        if isinstance(tab_id, int) and not isinstance(tab_id, bool):
            tabs[self.key(sid, tab_id)] = {"status": "unknown", "url": None, "ts": time.time()}
        else:
            for k in list(tabs):
                if k.startswith(str(sid) + ":"):
                    tabs[k] = {"status": "unknown", "url": None, "ts": time.time()}
            self.data["session_all_unknown"][str(sid)] = True
        self.dirty = True

    def set_verified(self, sid, tab_id, url_text):
        self.data["tabs"][self.key(sid, tab_id)] = {"status": "verified", "url": url_text, "ts": time.time()}
        self.dirty = True

    def clear_all_unknown_if_done(self, sid):
        """そのセッションの「不明」のタブが無くなったら session_all_unknown の印を外す。"""
        pre = str(sid) + ":"
        if any(v.get("status") == "unknown" for k, v in self.data["tabs"].items() if k.startswith(pre)):
            return
        if self.data["session_all_unknown"].pop(str(sid), None) is not None:
            self.dirty = True

    def tab(self, sid, tab_id):
        return self.data["tabs"].get(self.key(sid, tab_id))

    def session_has_unknown(self, sid):
        pre = str(sid) + ":"
        if self.data["session_all_unknown"].get(str(sid)):
            return True
        return any(v.get("status") == "unknown" for k, v in self.data["tabs"].items() if k.startswith(pre))
