#!/usr/bin/env python3
"""consent_check.py - 会話での同意（同意票＋PO の「1」）を許可券の代わりにする判定部品。

設計: docs/handoff/conversation-consent/design.md §4-1〜4-4（ADR-1033）。

呼び方: python3 ~/.claude/scripts/consent_check.py < <フックの入力 JSON>
  通すときだけ標準出力に allow を出して終了コード 0。それ以外は何も出さず終了コード 2。
  判定の関数は check(hook_input, command, now)。単体試験はこの関数を直接呼ぶ。
  例外が起きたら必ず不可（False）。
"""
import datetime
import fcntl
import hashlib
import json
import os
import pwd
import re
import sys

TAIL_BYTES = 4 * 1024 * 1024
WINDOW = datetime.timedelta(minutes=30)
HEADING = "[同意票]"
OPTION_PREFIX = "1. 上の同意票の操作を実行する"
OP_RE = re.compile(r"^操作([1-9]|10): (.+)$")


def real_home():
    """環境変数 HOME ではなく、アカウントの本物のホーム（danger_sanitize.py と同じ）。"""
    return pwd.getpwuid(os.getuid()).pw_dir


# ── 除外（§4-4）: 同意では通さない操作 ───────────────────────────────

_MASKS = [
    re.compile(r"(?i)(token|secret|password|passwd|api_key|apikey)[A-Za-z_]*\s*[=:]\s*\S+"),
    re.compile(r"Bearer\s+\S+"),
    re.compile(r"https://discord(app)?\.com/api/webhooks/\S+"),
]


def mask(s):
    for p in _MASKS:
        s = p.sub("***", s)
    return s


def guard_reason(cmd):
    """§4-5 の Bash の見張りの5条件。当たれば条件名、無ければ None（agent-danger-hook.sh と同じ規則）。"""
    if ".claude/projects/" in cmd and ".jsonl" in cmd:
        return "transcript"
    if "consent-used" in cmd:
        return "consent-used"
    if "tmux" in cmd and any(w in cmd for w in ("send-keys", "paste-buffer", "load-buffer", "set-buffer")):
        return "tmux-inject"
    if "osascript" in cmd and "keystroke" in cmd:
        return "osascript-keystroke"
    if ("127.0.0.1" in cmd or "localhost" in cmd) and "/chat/queue" in cmd:
        return "chat-queue"
    return None


_GIT_PUSH_RE = re.compile(r"\bgit\b(?:\s+-[Cc]\s+\S+|\s+--[\w-]+(?:=\S+)?)*\s+push\b(.*)", re.S)
_SPLIT_RE = re.compile(r"&&|\|\||;|\||\n")


def _git_push_excluded(cmd):
    """git push の除外3種。コマンドを &&・||・;・|・改行で区切り、git push を含む区間ごとに引数を見る。"""
    for seg in _SPLIT_RE.split(cmd):
        m = _GIT_PUSH_RE.search(seg)
        if not m:
            continue
        toks = [t.strip("\"'") for t in m.group(1).split()]
        toks = [t for t in toks if t]
        # main / develop への push: 設計 §4-4 どおり、引数に main か develop の語が部分一致すれば除外
        # （release/fix-main-menu も当たるが、止まる側なので受け入れる）
        if re.search(r"\b(main|develop)\b", m.group(1)):
            return "git push main/develop"
        # --delete / : で始まる refspec
        if any(t in ("--delete", "-d") or t.startswith(":") for t in toks):
            return "git push delete"
        # 強制 push で refspec（ブランチ名）が無い
        force = any(
            t in ("--force", "-f") or t.startswith("--force-with-lease") or re.fullmatch(r"-[A-Za-z]*f[A-Za-z]*", t)
            for t in toks
        )
        if force:
            positional = [t for t in toks if not t.startswith("-")]
            # 先頭の位置引数は送り先（remote）、2つ目以降が refspec
            if len(positional) < 2:
                return "git push force without refspec"
    return None


_EXCLUDE_RES = [
    (re.compile(r"\bgit\b[^\n]*\breset\b[^\n]*--hard", re.I), "git reset --hard"),
    (re.compile(r"drop\s+database", re.I), "DROP DATABASE"),
    (re.compile(r"\bclasp\s+push\b", re.I), "clasp push"),
    (re.compile(r"\.claude/permits"), "permits"),
    (re.compile(r"settings(\.local)?\.json"), "settings"),
    (re.compile(r"\.claude/scripts/"), "claude scripts"),
    (re.compile(r"\.codex/salesanchor/"), "codex salesanchor"),
    (re.compile(r"\bgh\s+api\b.*(branches/.*/protection|rulesets)", re.S), "gh api protection"),
    (re.compile(r"workflow-lint\.yml"), "workflow-lint"),
    # 本店の破壊系 git（agent-danger-hook.sh:238-241 と同じ4つ）を同意の対象にしない
    (re.compile(r"git\s+clean\b", re.I), "git clean"),
    (re.compile(r"git\s+stash\b(?!\s+(pop|show|list|apply))", re.I), "git stash"),
    (re.compile(r"git\s+checkout\s+--\s", re.I), "git checkout --"),
    (re.compile(r"git\s+restore\b", re.I), "git restore"),
]


def excluded(cmd):
    """除外に当たれば理由、当たらなければ None。コマンド全体に当てる。"""
    r = _git_push_excluded(cmd)
    if r:
        return r
    for rx, label in _EXCLUDE_RES:
        if rx.search(cmd):
            return label
    g = guard_reason(cmd)
    if g:
        return "guard:" + g
    return None


# ── 会話記録の読み取り ──────────────────────────────────────────────

def _parse_ts(s):
    if not isinstance(s, str):
        return None
    try:
        dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)


def _read_tail_records(path):
    """末尾 4MB を行ごとの JSON にする。不可なら None。"""
    with open(path, "rb") as f:
        size = os.fstat(f.fileno()).st_size
        start = max(0, size - TAIL_BYTES)
        f.seek(start)
        data = f.read()
    if start > 0:
        i = data.find(b"\n")
        if i < 0:
            return []
        data = data[i + 1:]
    if data and not data.endswith(b"\n"):
        j = data.rfind(b"\n")
        data = data[: j + 1] if j >= 0 else b""
    recs = []
    for raw in data.split(b"\n"):
        if not raw.strip():
            continue
        try:
            recs.append(json.loads(raw.decode("utf-8")))
        except Exception:
            return None
    return recs


def _is_human(r):
    if not isinstance(r, dict):
        return False
    if r.get("type") == "user":
        o = r.get("origin")
        return isinstance(o, dict) and o.get("kind") == "human"
    if r.get("type") == "attachment":
        a = r.get("attachment")
        if isinstance(a, dict) and a.get("type") == "queued_command":
            o = a.get("origin")
            return isinstance(o, dict) and o.get("kind") == "human"
    return False


def _is_compact(r):
    if not isinstance(r, dict):
        return False
    if r.get("isCompactSummary"):
        return True
    return r.get("type") == "system" and r.get("subtype") == "compact_boundary"


def _is_typed_one(r):
    if r.get("type") != "user" or r.get("promptSource") != "typed":
        return False
    msg = r.get("message")
    c = msg.get("content") if isinstance(msg, dict) else None
    return isinstance(c, str) and c.strip() == "1"


def parse_ticket(text):
    """最後の text ブロックから同意票を読む。(ブロックの sha256, [(番号, 操作)]) か None。"""
    lines = [ln.strip() for ln in text.split("\n")]
    heads = [i for i, ln in enumerate(lines) if ln == HEADING]
    opts = [i for i, ln in enumerate(lines) if ln.startswith(OPTION_PREFIX)]
    if len(heads) != 1 or len(opts) != 1:
        return None
    ops = []
    for ln in lines[heads[0] + 1:]:
        m = OP_RE.match(ln)
        if m:
            ops.append((int(m.group(1)), m.group(2).strip()))
    if not ops:
        return None
    nums = [n for n, _ in ops]
    if len(set(nums)) != len(nums):
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest(), ops


# ── 台帳（消費済みの鍵） ────────────────────────────────────────────

def _ledger_consume(ledger_path, key, now):
    """鍵がまだ無ければ追記して True。あれば False。flock で排他。追記できなければ False。"""
    os.makedirs(os.path.dirname(ledger_path), mode=0o700, exist_ok=True)
    fd = os.open(ledger_path, os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    try:
        if os.fstat(fd).st_uid != os.getuid():
            return False
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.lseek(fd, 0, os.SEEK_SET)
        chunks = []
        while True:
            b = os.read(fd, 1 << 20)
            if not b:
                break
            chunks.append(b)
        for raw in b"".join(chunks).split(b"\n"):
            if not raw.strip():
                continue
            try:
                if json.loads(raw.decode("utf-8")).get("key") == key:
                    return False
            except Exception:
                continue
        rec = {"key": key, "used_at": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
        os.write(fd, (json.dumps(rec, ensure_ascii=False) + "\n").encode("utf-8"))
        os.fsync(fd)
        return True
    finally:
        os.close(fd)  # close で flock も外れる


def _append_event(events_path, rec):
    try:
        os.makedirs(os.path.dirname(events_path), mode=0o700, exist_ok=True)
        with open(events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ── 判定本体 ────────────────────────────────────────────────────────

def _check_inner(hook_input, command, now, home, info):
    # 1. サブエージェントからの呼び出し（agent_id キーがあれば値が空でも不可）
    if "agent_id" in hook_input:
        return False, "agent_id"
    # 2. transcript_path が本物のホームの .claude/projects/ の下の .jsonl
    tp = hook_input.get("transcript_path")
    if not isinstance(tp, str) or not tp.endswith(".jsonl"):
        return False, "transcript_path"
    root = os.path.realpath(os.path.join(home, ".claude", "projects"))
    real_tp = os.path.realpath(tp)
    if not real_tp.startswith(root + os.sep) or not real_tp.endswith(".jsonl") or not os.path.isfile(real_tp):
        return False, "transcript_path"
    # 3. 末尾 4MB
    recs = _read_tail_records(real_tp)
    if recs is None:
        return False, "transcript_unparsable"
    # 4. 最後の人の入力 H
    h_idx = None
    for i in range(len(recs) - 1, -1, -1):
        if _is_human(recs[i]):
            h_idx = i
            break
    if h_idx is None:
        return False, "no_human_input"
    H = recs[h_idx]
    info["h_uuid"] = H.get("uuid")
    info["h_timestamp"] = H.get("timestamp")
    info["h_typed_one"] = _is_typed_one(H)
    # 5. H が typed の「1」
    if not info["h_typed_one"]:
        return False, "h_not_typed_one"
    # 6. H の直前の AI の行が、同意票つきの text ブロック
    a_idx = None
    for i in range(h_idx - 1, -1, -1):
        r = recs[i]
        if isinstance(r, dict) and r.get("type") == "assistant" and not r.get("isSidechain"):
            a_idx = i
            break
    if a_idx is None:
        return False, "no_assistant_text"
    msg = recs[a_idx].get("message")
    content = msg.get("content") if isinstance(msg, dict) else None
    if not isinstance(content, list) or not content:
        return False, "ticket_not_text_block"
    if any(not isinstance(b, dict) or b.get("type") != "text" for b in content):
        return False, "ticket_not_text_block"
    text = content[-1].get("text")
    if not isinstance(text, str):
        return False, "ticket_not_text_block"
    for r in recs[a_idx + 1:h_idx]:
        if _is_human(r) or _is_compact(r):
            return False, "input_between_ticket_and_one"
    parsed = parse_ticket(text)
    if parsed is None:
        return False, "ticket_format"
    sha, ops = parsed
    # 7. H から 30 分以内
    h_ts = _parse_ts(H.get("timestamp"))
    if h_ts is None:
        return False, "h_timestamp"
    if now - h_ts > WINDOW:
        return False, "expired"
    # 8. コマンドが操作のどれかと完全一致（`$`・バッククォートを含む操作は不可）
    cmd = command.strip()
    opnum = None
    for n, op in sorted(ops):
        if op == cmd:
            opnum = n
            break
    if opnum is None:
        return False, "command_mismatch"
    if "$" in cmd or "`" in cmd:
        return False, "dollar_or_backtick"
    # 9. 除外
    ex = excluded(command)
    if ex:
        return False, "excluded:" + ex
    # 10. 台帳（session_id は鍵に入れない）
    key = [sha, H.get("timestamp"), opnum]
    ledger = os.path.join(home, ".claude", "logs", "consent-used.jsonl")
    if not _ledger_consume(ledger, key, now):
        return False, "already_used"
    info["consumed_key"] = key
    return True, "ok"


def check(hook_input, command, now, home=None):
    """(通すか, 理由)。例外は必ず False。probe は結果に関係なく finally で1行書く（K0）。"""
    home = home or real_home()
    events = os.path.join(home, ".claude", "logs", "agent-events.jsonl")
    info = {"h_uuid": None, "h_timestamp": None, "h_typed_one": None}
    ok, reason = False, "exception"
    try:
        if not isinstance(hook_input, dict) or not isinstance(command, str):
            ok, reason = False, "bad_input"
        else:
            ok, reason = _check_inner(hook_input, command, now, home, info)
    except Exception:
        ok, reason = False, "exception"
    finally:
        try:
            hi = hook_input if isinstance(hook_input, dict) else {}
            probe = {
                "ts": _iso(now),
                "type": "consent_probe",
                "session": hi.get("session_id"),
                "h_uuid": info["h_uuid"],
                "h_timestamp": info["h_timestamp"],
                "h_typed_one": info["h_typed_one"],
                "now": now.isoformat(),
                "result": bool(ok),
                "reason": reason,
            }
            if hi.get("tool_use_id"):
                probe["tool_use_id"] = hi.get("tool_use_id")
            _append_event(events, probe)
            if ok:
                _append_event(events, {
                    "ts": _iso(now),
                    "type": "consent_consumed",
                    "session": hi.get("session_id"),
                    "key": info.get("consumed_key"),
                    "cmd_head": mask(command.strip())[:120],
                })
        except Exception:
            pass
    return bool(ok), reason


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
        ti = hook_input.get("tool_input", {}) if isinstance(hook_input, dict) else {}
        command = ti.get("command", "") if isinstance(ti, dict) else ""
        now = datetime.datetime.now(datetime.timezone.utc)
        ok, _reason = check(hook_input, command, now)
    except Exception:
        ok = False
    if ok:
        sys.stdout.write("allow\n")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
