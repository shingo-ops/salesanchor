#!/usr/bin/env python3
"""consent-audit.py - 会話での同意（ADR-1033）の突き合わせ・K0 の測定・権限の週次点検。

読み取りだけ（例外: --commit-snapshot を付けたときだけ permission-snapshot.json を更新する）。
記録・台帳のパスはこのスクリプトの中で組み立てる。引数でパスは受けない。
値（権限の設定の文字列など）は出さず、項目名と件数、短いハッシュだけを出す。

使い方:
  python3 scripts/dev/consent-audit.py --probe <session_id>
      その会話の記録で、最後の人の入力が見つかるか・何秒前か・typed の「1」か（本文は出さない）
  python3 scripts/dev/consent-audit.py --audit [--permissions]
      過去7日の同意の台帳と記録の突き合わせ、consent_guard_blocked の件数（偽造の疑いと読み取りの空振りに分ける。
        異常に数えるのは疑いだけ。疑いは GUARD_SUSPECT= の行で1件ずつ出す）、許可券の消費件数、K0 の遅れの数
      --permissions を併用すると、権限の設定の増減（前回の写しとの差）を台帳（permission-changes.jsonl）と照らして出す。
        異常の理由は ABNORMAL_REASON=A〜E の行（ABNORMAL= より前）、見直し期限切れは REVIEW_DUE=。
      --commit-snapshot を付けたときだけ写しを更新する（ADR-1034。定期実行だけが付ける）
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import pwd
import re
import subprocess
import sys

TAIL_BYTES = 4 * 1024 * 1024
DAYS = 7
K0_TARGET = 20


def real_home():
    return pwd.getpwuid(os.getuid()).pw_dir


def paths(home):
    claude = os.path.join(home, ".claude")
    return {
        "events": os.path.join(claude, "logs", "agent-events.jsonl"),
        "ledger": os.path.join(claude, "logs", "consent-used.jsonl"),
        "snapshot": os.path.join(claude, "logs", "permission-snapshot.json"),
        "projects": os.path.join(claude, "projects"),
        "settings": os.path.join(claude, "settings.json"),
        "settings_local": os.path.join(claude, "settings.local.json"),
        "permits": os.path.join(claude, "permits"),
    }


def parse_ts(s):
    if not isinstance(s, str):
        return None
    try:
        dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)


def read_jsonl(path):
    out = []
    try:
        with open(path, "rb") as f:
            for raw in f:
                try:
                    out.append(json.loads(raw.decode("utf-8")))
                except Exception:
                    continue
    except OSError:
        pass
    return out


def is_human(r):
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


def is_typed_one(r):
    if r.get("type") != "user" or r.get("promptSource") != "typed":
        return False
    msg = r.get("message")
    c = msg.get("content") if isinstance(msg, dict) else None
    return isinstance(c, str) and c.strip() == "1"


def find_transcript(home, session_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", session_id or ""):
        return None
    hits = glob.glob(os.path.join(paths(home)["projects"], "*", session_id + ".jsonl"))
    return hits[0] if hits else None


# ── --probe ─────────────────────────────────────────────────────────

def read_tail_records(path):
    with open(path, "rb") as f:
        size = os.fstat(f.fileno()).st_size
        start = max(0, size - TAIL_BYTES)
        f.seek(start)
        data = f.read()
    if start > 0:
        i = data.find(b"\n")
        data = data[i + 1:] if i >= 0 else b""
    if data and not data.endswith(b"\n"):
        j = data.rfind(b"\n")
        data = data[: j + 1] if j >= 0 else b""
    recs = []
    for raw in data.split(b"\n"):
        if raw.strip():
            try:
                recs.append(json.loads(raw.decode("utf-8")))
            except Exception:
                return None
    return recs


def probe(home, session_id, now):
    tp = find_transcript(home, session_id)
    if not tp:
        return {"found_transcript": False}
    recs = read_tail_records(tp)
    if recs is None:
        return {"found_transcript": True, "parsable": False}
    for r in reversed(recs):
        if is_human(r):
            ts = parse_ts(r.get("timestamp"))
            return {
                "found_transcript": True,
                "parsable": True,
                "human_found": True,
                "h_uuid": r.get("uuid"),
                "h_timestamp": r.get("timestamp"),
                "seconds_ago": round((now - ts).total_seconds(), 1) if ts else None,
                "typed_one": is_typed_one(r),
            }
    return {"found_transcript": True, "parsable": True, "human_found": False}


# ── --audit ─────────────────────────────────────────────────────────

def load_events(home):
    return read_jsonl(paths(home)["events"])


def event_time(e):
    return parse_ts(e.get("ts"))


WINDOW_MAX_SEC = 30 * 60


def load_windows(home):
    """consent-selftest-windows.jsonl の start/end を組にし、長さが30分以内の区間だけ返す。
    end が無い・30分を超える・順序が逆の区間は除外に使わない。返り値: (使える区間のリスト, 区間の総数)"""
    path = os.path.join(home, ".claude", "logs", "consent-selftest-windows.jsonl")
    wins, total, start = [], 0, None
    for r in read_jsonl(path):
        if "start" in r:
            if start is not None:
                total += 1  # end の無い start
            start = parse_ts(r.get("start"))
            if start is None:
                total += 1
        elif "end" in r and start is not None:
            end = parse_ts(r.get("end"))
            total += 1
            if end is not None and 0 <= (end - start).total_seconds() <= WINDOW_MAX_SEC:
                wins.append((start, end))
            start = None
    if start is not None:
        total += 1
    return wins, total


_NEEDLES = (".claude/projects/", "consent-used")
_VERBS = r"(?<![\w.-])(?:cp|mv|dd|truncate|rm|ln|install|rsync|touch|chmod)(?![\w-])"
_INTERP = r"(?<![\w.-])(?:python3?|node|perl|ruby)(?![\w-])"
_WCALLS = ("write(", "write_text", "write_bytes", "writeFile", "appendFile", "os.replace", "os.rename", "shutil.")


def _redirect_targets(cmd):
    out = []
    for m in re.finditer(r">\|?>?\s*([^\s|;&<>]*)", cmd):
        out.append(m.group(1))
    for m in re.finditer(r"(?<![\w.-])tee(?![\w-])([^|;&\n]*)", cmd):
        out.extend(m.group(1).split())
    return out


def _write_words(cmd, need):
    has = any(n in cmd for n in _NEEDLES)
    for t in _redirect_targets(cmd):
        if need:
            if any(n in t for n in _NEEDLES):
                return True
        elif t and not t.startswith("&") and t != "/dev/null":
            return True
    if need and not has:
        return False
    if re.search(_VERBS, cmd):
        return True
    if re.search(r"(?<![\w.-])(?:sed|perl)(?![\w-])[^|;&\n]*\s(?:-[A-Za-z]*i|--in-place)", cmd):
        return True
    if re.search(_INTERP, cmd):
        if any(w in cmd for w in _WCALLS):
            return True
        if re.search(r"""open\([^)]*?,\s*(?:mode\s*=\s*)?['"][rwxabt+]*[wax+][rwxabt+]*['"]""", cmd):
            return True
    return False


def bash_write_form(cmd):
    """Bash の書き込みの形（design §13-3(a) の 1〜4）。迷う形は True（write 側）。
    agent-danger-hook.sh の CONSENT_GUARD と同じ規則。変えるときは両方。"""
    try:
        if _write_words(cmd, True):
            return True
        if re.search(r"(?<![\w.-])(?:cd|pushd)(?![\w-])[^|;&\n]*\.claude/projects/", cmd):
            return _write_words(cmd, False)
        return False
    except Exception:
        return True


def guard_kind(e):
    """行の種類を 'suspect'（疑い）か 'read'（空振り）で返す。kind の無い旧形式は design §13-3(b) のとおり。"""
    kind = e.get("kind")
    if kind in ("inject", "write"):
        return "suspect"
    if kind == "read":
        return "read"
    cond = e.get("condition")
    if cond in ("transcript", "consent-used"):
        return "suspect" if bash_write_form(str(e.get("cmd_head") or "")) else "read"
    return "suspect"  # inject 系・transcript-or-ledger-write・不明な条件は疑い側


def count_guard_split(events, since, windows):
    """consent_guard_blocked を (疑いの行のリスト, 読み取りの空振り件数, 試験の区間に入った件数) に分ける。
    区間内の行は疑い・空振りのどちらにも数えない。"""
    suspects, reads, inside = [], 0, 0
    for e in events:
        if e.get("type") != "consent_guard_blocked":
            continue
        ts = event_time(e)
        if ts is None or ts < since:
            continue
        if any(s <= ts <= en for s, en in windows):
            inside += 1
        elif guard_kind(e) == "suspect":
            suspects.append(e)
        else:
            reads += 1
    return suspects, reads, inside


def count_types(events, since, pred):
    n = {}
    for e in events:
        t = e.get("type")
        if not isinstance(t, str) or not pred(t):
            continue
        ts = event_time(e)
        if ts is None or ts < since:
            continue
        n[t] = n.get(t, 0) + 1
    return n


def match_ledger_keys(home, since):
    """過去7日の台帳の鍵ごとに、記録の中に同意票（sha256 一致）と typed の「1」（timestamp 一致）があるかを数える。"""
    keys = []
    for rec in read_jsonl(paths(home)["ledger"]):
        used = parse_ts(rec.get("used_at"))
        k = rec.get("key")
        if used and used >= since and isinstance(k, list) and len(k) == 3:
            keys.append(tuple(k))
    if not keys:
        return 0, 0
    need_ts = {k[1] for k in keys}
    need_sha = {k[0] for k in keys}
    found_ts, found_sha = set(), set()
    cutoff = since.timestamp() - 86400
    for tp in glob.glob(os.path.join(paths(home)["projects"], "*", "*.jsonl")):
        try:
            if os.path.getmtime(tp) < cutoff:
                continue
            with open(tp, "rb") as f:
                for raw in f:
                    if "同意票".encode("utf-8") in raw and b'"assistant"' in raw:
                        try:
                            r = json.loads(raw.decode("utf-8"))
                            for b in (r.get("message", {}).get("content") or []):
                                if isinstance(b, dict) and b.get("type") == "text":
                                    h = hashlib.sha256(b.get("text", "").encode("utf-8")).hexdigest()
                                    if h in need_sha:
                                        found_sha.add(h)
                        except Exception:
                            pass
                    elif b'"typed"' in raw and any(t.encode("utf-8") in raw for t in need_ts if isinstance(t, str)):
                        try:
                            r = json.loads(raw.decode("utf-8"))
                            if is_human(r) and is_typed_one(r) and r.get("timestamp") in need_ts:
                                found_ts.add(r.get("timestamp"))
                        except Exception:
                            pass
        except OSError:
            continue
    unmatched = sum(1 for k in keys if not (k[0] in found_sha and k[1] in found_ts))
    return len(keys), unmatched


def k0_delays(home, events):
    """K0（design §2）: 後から見て直前の人の入力が typed の「1」だった呼び出しの数と、そのうち遅れの数。

    tool_use_id があれば、記録の中のその行より前で最も近い人の入力を本当の直前とする。
    無ければ、probe の now より前の timestamp を持つ最後の人の入力を本当の直前とする。
    本当の直前の uuid が probe の h_uuid と違えば遅れ1件。
    """
    probes = [e for e in events if e.get("type") == "consent_probe"]
    by_session = {}
    for p in probes:
        by_session.setdefault(p.get("session"), []).append(p)
    total = delays = 0
    for sid, plist in by_session.items():
        tp = find_transcript(home, sid) if isinstance(sid, str) else None
        if not tp:
            continue
        ids = {p["tool_use_id"] for p in plist if p.get("tool_use_id")}
        id_re = re.compile("|".join(re.escape(i) for i in ids).encode("utf-8")) if ids else None
        humans = []          # (timestamp, uuid, typed_one)
        prev_for_tool = {}   # tool_use_id -> (uuid, typed_one)
        last = None
        with open(tp, "rb") as f:
            for raw in f:
                if b'"human"' in raw:
                    try:
                        r = json.loads(raw.decode("utf-8"))
                    except Exception:
                        r = None
                    if r is not None and is_human(r):
                        ts = parse_ts(r.get("timestamp"))
                        last = (r.get("uuid"), is_typed_one(r))
                        if ts:
                            humans.append((ts, r.get("uuid"), is_typed_one(r)))
                        continue
                if id_re is not None and b'"tool_use"' in raw:
                    m = id_re.search(raw)
                    if m:
                        tid = m.group(0).decode("utf-8")
                        prev_for_tool.setdefault(tid, last)
        for p in plist:
            true_prev = None
            tid = p.get("tool_use_id")
            if tid and tid in prev_for_tool:
                true_prev = prev_for_tool[tid]
            else:
                now = parse_ts(p.get("now"))
                cands = [h for h in humans if now and h[0] < now]
                if cands:
                    c = max(cands, key=lambda h: h[0])
                    true_prev = (c[1], c[2])
            if true_prev and true_prev[1]:
                total += 1
                if true_prev[0] != p.get("h_uuid"):
                    delays += 1
    return total, delays


# ── --permissions ───────────────────────────────────────────────────

TOOLS_DIRNAME = ".salesanchor-tools"
REPO_DIRNAME = "salesanchor"
REPO_SLUG = "shingo-ops/salesanchor"
TOOL_FILES = ("scripts/dev/perm-change.py", "scripts/dev/consent-audit.py")
CHANGE_WINDOW_SEC = 30 * 60

# 道具 perm-change.py の target の値 → 写しのキー（設計 §4-1 の表。この辞書が唯一の置き場）
TARGET_KEYS = {
    "user-allow": "user:permissions.allow",
    "repo-local-allow": "repo-local:permissions.allow",
    "user-automode-allow": "user:autoMode.allow",
    "user-automode-allow-sm": "user:autoMode.allow",
    "repo-allow": "repo:permissions.allow",
    "repo-hooks": "repo:hooks",
    "user-deny": "user:permissions.deny",
    "user-ask": "user:permissions.ask",
    "user-defaultmode": "user:permissions.defaultMode",
    "user-skip": "user:skip_flags",
    "user-hooks": "user:hooks",
    "user-automode-soft-deny": "user:autoMode.soft_deny",
    "user-automode-env": "user:autoMode.environment",
    "user-local-allow": "user-local:permissions.allow",
    "user-local-deny": "user-local:permissions.deny",
    "user-local-ask": "user-local:permissions.ask",
    "user-local-defaultmode": "user-local:permissions.defaultMode",
    "user-local-skip": "user-local:skip_flags",
    "user-local-hooks": "user-local:hooks",
    "user-local-automode-allow": "user-local:autoMode.allow",
    "user-local-automode-soft-deny": "user-local:autoMode.soft_deny",
    "user-local-automode-env": "user-local:autoMode.environment",
    "repo-local-hooks": "repo-local:hooks",
    "danger-ops": "danger_ops",
    "hook-files": "hook_files",
}

# 旧キー名 → 新キー名（初回の比較で「増減」にしないための読み替え）
LEGACY_KEYS = {
    "settings.json:permissions.allow": "user:permissions.allow",
    "settings.json:hooks": "user:hooks",
    "settings.local.json:permissions.allow": "user-local:permissions.allow",
    "settings.local.json:hooks": "user-local:hooks",
}

# A・B の照合に使わないキー（ledger は C、tools_clean は E、permits は D で見る）
NOT_MATCHED_KEYS = ("ledger", "tools_clean", "permits")
# 台帳の行だけで足りるキー（これ以外のキーの差分は PO 記録 po_ref が要る = B）
LEDGER_ONLY_KEYS = ("user:permissions.allow", "repo-local:permissions.allow", "user:autoMode.allow")


def sha8(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


def item_sha8(item):
    """権限の1要素のハッシュ（写し・台帳の item_hash 共通の式）。"""
    return sha8(json.dumps(item, sort_keys=True, ensure_ascii=False))


def ledger_line_sha(raw):
    """台帳の1行（改行を除いたバイト列）の sha256 先頭16桁。prev_sha の鎖と head に使う。"""
    return hashlib.sha256(raw).hexdigest()[:16]


def run_git(args, cwd):
    """git を実行して (終了コード, 標準出力のバイト列) を返す。試験では差し替えられる。"""
    try:
        p = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, timeout=60,
                           env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
        return p.returncode, p.stdout
    except Exception:
        return 127, b""


def gh_pr_view(n):
    """gh で PR の state・mergedAt・mergeCommit を取る（本文は後から書き換えられるので使わない）。使えなければ None。試験では差し替えられる。"""
    try:
        p = subprocess.run(["gh", "pr", "view", str(n), "-R", REPO_SLUG, "--json", "state,mergedAt,mergeCommit"],
                           capture_output=True, timeout=60)
        if p.returncode != 0:
            return None
        return json.loads(p.stdout.decode("utf-8"))
    except Exception:
        return None


def perm_paths(home):
    p = paths(home)
    claude = os.path.join(home, ".claude")
    p.update({
        "perm_ledger": os.path.join(claude, "logs", "permission-changes.jsonl"),
        "perm_lock": os.path.join(claude, "logs", "permission-changes.lock"),
        "agent_tokens": os.path.join(claude, "agent-tokens.json"),
        "hook_dir": os.path.join(claude, "scripts"),
        "tools": os.path.join(home, TOOLS_DIRNAME),
        "tools_settings": os.path.join(home, TOOLS_DIRNAME, ".claude", "settings.json"),
        "repo_local": os.path.join(home, REPO_DIRNAME, ".claude", "settings.local.json"),
    })
    return p


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def read_ledger(home):
    """台帳を読む。返り値: dict(lines=生の各行(bytes), rows=読めた行, chain_ok, head, lines_n)。"""
    path = perm_paths(home)["perm_ledger"]
    lines, rows = [], []
    chain_ok = True
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        data = b""
    prev = "genesis"
    for raw in data.split(b"\n"):
        if not raw.strip():
            continue
        lines.append(raw)
        try:
            row = json.loads(raw.decode("utf-8"))
        except Exception:
            row = None
        if not isinstance(row, dict):
            chain_ok = False
            rows.append({})
        else:
            rows.append(row)
            if row.get("prev_sha") != prev:
                chain_ok = False
        prev = ledger_line_sha(raw)
    return {"lines": lines, "rows": rows, "chain_ok": chain_ok, "head": prev, "lines_n": len(lines)}


def tools_state(home, git_run):
    """~/.salesanchor-tools の状態（設計 §4-2 tools_clean と §4-3 E の材料）。"""
    p = perm_paths(home)
    tools = p["tools"]
    st = {"exists": os.path.isdir(tools), "offline": False, "v": None, "head_on_main": "no",
          "dirty": 0, "tool_sha": "", "sha_bad": False}
    if not st["exists"]:
        return st
    rc, out = git_run(["status", "--porcelain", "--untracked-files=all"], tools)
    if rc != 0:
        st["dirty"] = 1
    else:
        st["dirty"] = len([x for x in out.decode("utf-8", "replace").splitlines() if x.strip()])
    rc, out = git_run(["ls-remote", "origin", "refs/heads/main"], tools)
    v = out.decode("utf-8", "replace").split()[0] if rc == 0 and out.strip() else None
    st["v"] = v
    if not v:
        st["offline"] = True
    else:
        rc, _ = git_run(["merge-base", "--is-ancestor", "HEAD", v], tools)
        st["head_on_main"] = "yes" if rc == 0 else "no"
        for rel in TOOL_FILES:
            rc, content = git_run(["show", "%s:%s" % (v, rel)], tools)
            if rc != 0:
                continue
            try:
                with open(os.path.join(tools, rel), "rb") as f:
                    mine = f.read()
            except OSError:
                mine = None
            if mine is None or hashlib.sha256(mine).hexdigest() != hashlib.sha256(content).hexdigest():
                st["sha_bad"] = True
    try:
        with open(os.path.join(tools, TOOL_FILES[0]), "rb") as f:
            st["tool_sha"] = hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        pass
    return st


def _hook_items(hooks):
    items = []
    if isinstance(hooks, dict):
        for event, entries in hooks.items():
            for ent in entries if isinstance(entries, list) else []:
                matcher = ent.get("matcher", "") if isinstance(ent, dict) else ""
                items.append("%s|%s|%s" % (event, matcher, item_sha8(ent)))
    return sorted(items)


def _list_hashes(v):
    return sorted(item_sha8(a) for a in v) if isinstance(v, list) else []


def _settings_keys(prefix, d, snap, full):
    perms = d.get("permissions") if isinstance(d.get("permissions"), dict) else {}
    snap[prefix + ":permissions.allow"] = _list_hashes(perms.get("allow"))
    snap[prefix + ":hooks"] = _hook_items(d.get("hooks"))
    if not full:
        return
    snap[prefix + ":permissions.deny"] = _list_hashes(perms.get("deny"))
    snap[prefix + ":permissions.ask"] = _list_hashes(perms.get("ask"))
    snap[prefix + ":permissions.defaultMode"] = [item_sha8(perms["defaultMode"])] if "defaultMode" in perms else []
    snap[prefix + ":skip_flags"] = sorted(
        item_sha8("%s=%s" % (k, json.dumps(v, sort_keys=True, ensure_ascii=False)))
        for k, v in d.items() if isinstance(k, str) and k.startswith("skip"))
    am = d.get("autoMode") if isinstance(d.get("autoMode"), dict) else {}
    snap[prefix + ":autoMode.allow"] = _list_hashes(am.get("allow"))
    snap[prefix + ":autoMode.soft_deny"] = _list_hashes(am.get("soft_deny"))
    snap[prefix + ":autoMode.environment"] = _list_hashes(am.get("environment"))


def collect_permissions(home, git_run=None, tstate=None):
    p = perm_paths(home)
    git_run = git_run or run_git
    snap = {}
    _settings_keys("user", load_json(p["settings"]), snap, True)
    _settings_keys("user-local", load_json(p["settings_local"]), snap, True)
    _settings_keys("repo", load_json(p["tools_settings"]), snap, False)
    _settings_keys("repo-local", load_json(p["repo_local"]), snap, False)
    ops = load_json(p["agent_tokens"]).get("danger_ops")
    snap["danger_ops"] = _list_hashes(ops)
    files = []
    for root, dirs, names in os.walk(p["hook_dir"]):
        dirs.sort()
        for n in sorted(names):
            if ".backup" in n:
                continue
            fp = os.path.join(root, n)
            if os.path.islink(fp) or not os.path.isfile(fp):
                continue
            try:
                with open(fp, "rb") as f:
                    digest = hashlib.sha256(f.read()).hexdigest()[:8]
            except OSError:
                continue
            files.append("%s|%s" % (sha8(os.path.relpath(fp, p["hook_dir"])), digest))
    snap["hook_files"] = sorted(files)
    led = read_ledger(home)
    snap["ledger"] = ["lines=%d" % led["lines_n"], "head=%s" % led["head"]]
    ts = tstate if tstate is not None else tools_state(home, git_run)
    snap["tools_clean"] = (["head_on_main=%s" % ts["head_on_main"], "dirty=%d" % ts["dirty"],
                            "tool_sha=%s" % ts["tool_sha"]] if ts["exists"] else [])
    try:
        permits = sorted(sha8(n) for n in os.listdir(p["permits"]))
    except OSError:
        permits = []
    snap["permits"] = permits
    return snap


def normalize_snapshot(old):
    out = {}
    for k, v in old.items():
        nk = LEGACY_KEYS.get(k, k)
        if nk != k and nk in old:
            continue
        out[nk] = v
    return out


def diff_permissions(old, new):
    lines = []
    for k in sorted(set(old) | set(new)):
        o, n = set(old.get(k, [])), set(new.get(k, []))
        added, removed = sorted(n - o), sorted(o - n)
        lines.append((k, len(n), added, removed))
    return lines


def element_hash(el):
    """写しの1要素から台帳の item_hash に当たる部分を取り出す（hooks / hook_files は末尾の '|' の後ろ）。"""
    return el.rsplit("|", 1)[-1]


def parse_consent_ref(ref):
    m = re.fullmatch(r"consent:([0-9a-f]{64}):(.+):([1-9]|10)", ref or "")
    return [m.group(1), m.group(2), int(m.group(3))] if m else None


def consent_used_at(home, key3):
    for rec in read_jsonl(paths(home)["ledger"]):
        if rec.get("key") == key3:
            return parse_ts(rec.get("used_at"))
    return None


TICKET_HEADING = "[同意票]"
TICKET_OPTION_PREFIX = "1. 上の同意票の操作を実行する"
TICKET_OP_RE = re.compile(r"^操作([1-9]|10): (.+)$")
PO_BANG_OP_PREFIXES = (
    "bash ~/.salesanchor-tools/docs/handoff/permission-delegation/po-register-delegation.sh ",
    "bash ~/.salesanchor-tools/docs/handoff/permission-delegation/po-unregister-delegation.sh ",
    "bash ~/CC報告ファイル-keep/permission-delegation/po-apply-",
)


def _is_compact(r):
    if not isinstance(r, dict):
        return False
    if r.get("isCompactSummary"):
        return True
    return r.get("type") == "system" and r.get("subtype") == "compact_boundary"


def _parse_ticket_ops(text):
    """consent_check.py の parse_ticket と同じ規則。(sha256, [(番号, 操作)]) か None。"""
    lines = [ln.strip() for ln in text.split("\n")]
    heads = [i for i, ln in enumerate(lines) if ln == TICKET_HEADING]
    opts = [i for i, ln in enumerate(lines) if ln.startswith(TICKET_OPTION_PREFIX)]
    if len(heads) != 1 or len(opts) != 1:
        return None
    ops = []
    for ln in lines[heads[0] + 1:]:
        m = TICKET_OP_RE.match(ln)
        if m:
            ops.append((int(m.group(1)), m.group(2).strip()))
    if not ops:
        return None
    nums = [n for n, _ in ops]
    if len(set(nums)) != len(nums):
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest(), ops


def _po_bang_in_records(recs, key3):
    """1つの会話の記録の中で、設計 §4-3 改7 の (a)〜(d) が揃うか。"""
    sha, k2, k3 = key3
    for h_idx, H in enumerate(recs):
        if not (is_human(H) and is_typed_one(H) and not H.get("isSidechain") and H.get("timestamp") == k2):
            continue
        a_idx = None
        for i in range(h_idx - 1, -1, -1):
            r = recs[i]
            if isinstance(r, dict) and r.get("type") == "assistant" and not r.get("isSidechain"):
                a_idx = i
                break
        if a_idx is None:
            continue
        msg = recs[a_idx].get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(content, list) or not content:
            continue
        if any(not isinstance(b, dict) or b.get("type") != "text" for b in content):
            continue
        text = content[-1].get("text")
        if not isinstance(text, str):
            continue
        if any(is_human(r) or _is_compact(r) for r in recs[a_idx + 1:h_idx]):
            continue
        parsed = _parse_ticket_ops(text)
        if parsed is None or parsed[0] != sha:
            continue
        for n, op in parsed[1]:
            if n == k3 and op.startswith(PO_BANG_OP_PREFIXES):
                return True
    return False


def consent_po_bang_at(home, key3, row):
    """改7: PO の `!` で走らせた台本の同意。(a)〜(e) が揃えば k2 の時刻を返す。揃わなければ None。"""
    k2 = parse_ts(key3[1])
    rec_ts = parse_ts(row.get("ts"))
    if k2 is None or rec_ts is None:
        return None
    if not (k2 < rec_ts <= k2 + datetime.timedelta(hours=24)):
        return None
    cutoff = k2.timestamp() - 86400
    for tp in glob.glob(os.path.join(paths(home)["projects"], "*", "*.jsonl")):
        try:
            if os.path.getmtime(tp) < cutoff:
                continue
        except OSError:
            continue
        if _po_bang_in_records(read_jsonl(tp), key3):
            return k2
    return None


SETTINGS_REL = ".claude/settings.json"
SM_LEDGER_REL = "docs/handoff/design-approval-ticket/permission-ledger.md"
PR_ONLY_TARGETS = ("repo-allow", "repo-hooks")


def consent_ticket_has_hash(home, sha, h, used):
    """同意票（assistant の text で sha256 が一致するもの）の本文に item_hash がある。"""
    cutoff = used.timestamp() - 86400
    for tp in glob.glob(os.path.join(paths(home)["projects"], "*", "*.jsonl")):
        try:
            if os.path.getmtime(tp) < cutoff:
                continue
            with open(tp, "rb") as f:
                for raw in f:
                    if "同意票".encode("utf-8") not in raw or b'"assistant"' not in raw:
                        continue
                    try:
                        r = json.loads(raw.decode("utf-8"))
                        for b in (r.get("message", {}).get("content") or []):
                            if isinstance(b, dict) and b.get("type") == "text":
                                t = b.get("text", "")
                                if hashlib.sha256(t.encode("utf-8")).hexdigest() == sha and h in t:
                                    return True
                    except Exception:
                        pass
        except OSError:
            continue
    return False


def _git_text(git_run, tools, args):
    rc, out = git_run(args, tools)
    return out.decode("utf-8", "replace") if rc == 0 else None


def _added_lines(diff_text):
    return [x[1:] for x in diff_text.split("\n") if x.startswith("+") and not x.startswith("+++")]


def pr_diff_ok(home, row, h, v, mc, git_run):
    """取り込まれた差分（mc^1..mc）で、その要素の変更が本当に入っているか。"""
    tools = perm_paths(home)["tools"]
    rc, _ = git_run(["merge-base", "--is-ancestor", mc, v], tools)
    if rc != 0:
        return False
    target = row.get("target")
    if target in PR_ONLY_TARGETS:
        old = _git_text(git_run, tools, ["show", "%s^1:%s" % (mc, SETTINGS_REL)])
        new = _git_text(git_run, tools, ["show", "%s:%s" % (mc, SETTINGS_REL)])
        if old is None and new is None:
            return False
        try:
            od = json.loads(old) if old is not None else {}
            nd = json.loads(new) if new is not None else {}
        except ValueError:
            return False
        so, sn = {}, {}
        _settings_keys("repo", od if isinstance(od, dict) else {}, so, False)
        _settings_keys("repo", nd if isinstance(nd, dict) else {}, sn, False)
        k = TARGET_KEYS[target]
        eo = {element_hash(x) for x in so.get(k, [])}
        en = {element_hash(x) for x in sn.get(k, [])}
        return h in (eo ^ en)
    if target == "user-automode-allow-sm":
        cur = None
        for it in (load_json(perm_paths(home)["settings"]).get("autoMode") or {}).get("allow") or []:
            if isinstance(it, str) and item_sha8(it) == h:
                cur = it
        m = re.match(r"SM-([0-9]+)", cur or "")
        if not m:
            return False
        d = _git_text(git_run, tools, ["diff", "%s^1" % mc, mc, "--", SM_LEDGER_REL])
        if d is None:
            return False
        return any(re.search(r"SM-%s(?![0-9])" % m.group(1), ln) for ln in _added_lines(d))
    d = _git_text(git_run, tools, ["diff", "%s^1" % mc, mc])
    return d is not None and any(h in ln for ln in _added_lines(d))


def record_ok(home, row, held, key, h, since, rows, gh_view, git_run, v):
    """record の行の確かめ（設計 §4-3 第6版）。通ったときだけ差分の説明に使う。"""
    ref = row.get("po_ref") or ""
    held_ts = parse_ts(held.get("ts")) if held else None
    b_target = (key not in LEDGER_ONLY_KEYS) or str(row.get("category", "")).startswith("reserved") or held is not None
    if ref.startswith("PR#"):
        if not re.fullmatch(r"PR#[0-9]+", ref):
            return False
        same = [r for r in rows if r.get("sub") == "record" and r.get("po_ref") == ref and r.get("item_hash") == h]
    elif ref.startswith("consent:"):
        same = [r for r in rows if r.get("sub") == "record" and r.get("po_ref") == ref]
    else:
        return False
    if same and same[0] is not row:
        return False
    if ref.startswith("consent:"):
        key3 = parse_consent_ref(ref)
        used = consent_used_at(home, key3) if key3 else None
        if used is None and key3:
            used = consent_po_bang_at(home, key3, row)
        if used is None:
            return False
        if held_ts is not None:
            if used <= held_ts:
                return False
        elif since is not None and used <= since:
            return False
        return consent_ticket_has_hash(home, key3[0], h, used)
    if b_target and row.get("target") not in PR_ONLY_TARGETS:
        return False
    vw = gh_view(int(ref[3:]))
    if not isinstance(vw, dict) or vw.get("state") != "MERGED" or not v:
        return False
    merged = parse_ts(vw.get("mergedAt"))
    base = held_ts if held_ts is not None else since
    if merged is None or (base is not None and merged <= base):
        return False
    mc = vw.get("mergeCommit")
    mc = mc.get("oid") if isinstance(mc, dict) else None
    if not isinstance(mc, str) or not re.fullmatch(r"[0-9a-f]{7,64}", mc):
        return False
    return pr_diff_ok(home, row, h, v, mc, git_run)


def judge_change(home, key, h, op, since, rows, gh_view, git_run=None, v=None):
    """差分1件を判定する。None=説明がつく、'A'=台帳に無い、'B'=PO 記録が足りない。"""
    git_run = git_run or run_git
    cands = []
    for r in rows:
        if r.get("result") not in ("applied", "recorded"):
            continue
        t = parse_ts(r.get("ts"))
        if t is None or (since is not None and t < since):
            continue
        if TARGET_KEYS.get(r.get("target")) != key or r.get("item_hash") != h:
            continue
        if r.get("op") not in (op, "modify"):
            continue
        cands.append(r)
    must_po = key not in LEDGER_ONLY_KEYS
    if not cands:
        return "B" if must_po else "A"
    held_any = False
    for row in cands:
        row_ts = parse_ts(row.get("ts"))
        held = None
        for r in rows:
            if r.get("result") == "held" and r.get("item_hash") == h and TARGET_KEYS.get(r.get("target")) == key:
                t = parse_ts(r.get("ts"))
                if t is not None and row_ts is not None and t <= row_ts:
                    held = r
        held_any = held_any or held is not None
        if row.get("sub") != "record":
            if not must_po and not str(row.get("category", "")).startswith("reserved"):
                return None
            continue
        if record_ok(home, row, held, key, h, since, rows, gh_view, git_run, v):
            return None
    # §2-3 のキー（allow 系以外）は、通らない record の行しか無いときも B。repo:permissions.allow は
    # allow 系なので、held の行が無ければ A（design A19）。
    return "B" if (held_any or (must_po and key != "repo:permissions.allow")) else "A"


def review_due(rows, now):
    """見直し日を過ぎ、review の行が無い権限の item_hash を返す。"""
    state = {}
    for r in rows:
        k = (r.get("target"), r.get("item_hash"))
        if r.get("sub") == "review":
            if r.get("summary") == "remove":
                state.pop(k, None)
            elif r.get("review_by"):
                state[k] = r.get("review_by")
        elif r.get("result") == "applied" and r.get("op") == "add" and r.get("review_by"):
            state[k] = r.get("review_by")
        elif r.get("result") in ("applied", "recorded") and r.get("op") == "remove":
            state.pop(k, None)
    today = now.strftime("%Y-%m-%d")
    return sorted({k[1] for k, due in state.items() if due <= today})


def load_snapshot(path):
    try:
        with open(path, encoding="utf-8") as f:
            old = json.load(f)
    except Exception:
        return None, None
    if not isinstance(old, dict):
        return None, None
    ts_list = old.pop("snapshot_ts", None)
    ts = parse_ts(ts_list[0]) if isinstance(ts_list, list) and ts_list else None
    if ts is None:
        try:
            ts = datetime.datetime.fromtimestamp(os.path.getmtime(path), datetime.timezone.utc)
        except OSError:
            ts = None
    return normalize_snapshot(old), ts


def run_permissions(home, out, now=None, commit=False, gh_view=None, git_run=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    gh_view = gh_view or gh_pr_view
    git_run = git_run or run_git
    p = perm_paths(home)
    snap_path = p["snapshot"]
    tstate = tools_state(home, git_run)
    new = collect_permissions(home, git_run, tstate)
    old, old_ts = load_snapshot(snap_path)
    led = read_ledger(home)
    out("== 権限の設定の増減（値は出さない。短いハッシュのみ） ==")
    changed = 0
    reasons = {"A": [], "B": [], "C": [], "D": [], "E": []}
    if old is None:
        out("前回の写しなし（初回。比較はしない）")
        for k, v in sorted(new.items()):
            out("  %s: %d 件" % (k, len(v)))
    else:
        for k, cnt, added, removed in diff_permissions(old, new):
            if k not in old:
                out("  %s: %d 件（初回）" % (k, cnt))
                continue
            out("  %s: %d 件 / 増 %d / 減 %d" % (k, cnt, len(added), len(removed)))
            for a in added:
                out("    + %s" % a)
            for r in removed:
                out("    - %s" % r)
            changed += len(added) + len(removed)
            if k in NOT_MATCHED_KEYS or k not in new:
                continue
            for op, els in (("add", added), ("remove", removed)):
                for el in els:
                    h = element_hash(el)
                    v = judge_change(home, k, h, op, old_ts, led["rows"], gh_view, git_run, tstate.get("v"))
                    if v:
                        reasons[v].append("%s %s" % (k, h))
        # C: 台帳の鎖・行数・前回の head
        ol = old.get("ledger") or []
        old_lines = next((int(x[6:]) for x in ol if x.startswith("lines=") and x[6:].isdigit()), None)
        old_head = next((x[5:] for x in ol if x.startswith("head=")), None)
        c_bad = False
        if old_lines is not None and led["lines_n"] < old_lines:
            c_bad = True
        if old_head and old_head != "genesis" and old_lines:
            if led["lines_n"] < old_lines or ledger_line_sha(led["lines"][old_lines - 1]) != old_head:
                c_bad = True
        if c_bad:
            reasons["C"].append("ledger %s" % sha8(led["head"]))
    if old is None and not led["chain_ok"]:
        reasons["C"].append("ledger %s" % sha8(led["head"]))
    if old is not None and not led["chain_ok"] and not reasons["C"]:
        reasons["C"].append("ledger %s" % sha8(led["head"]))
    # D: permit_issued(by=ai) のうち、前後30分に同意の消費も台帳の行も無いもの
    events = load_events(home)
    since_d = old_ts or (now - datetime.timedelta(days=DAYS))
    consumed_ts = [event_time(e) for e in events if e.get("type") == "consent_consumed"]
    ledger_ts = [parse_ts(r.get("ts")) for r in led["rows"]]
    near = [t for t in consumed_ts + ledger_ts if t is not None]
    unexplained = 0
    for e in events:
        if e.get("type") != "permit_issued" or e.get("by") != "ai":
            continue
        t = event_time(e)
        if t is None or t < since_d:
            continue
        if not any(abs((t - c).total_seconds()) <= CHANGE_WINDOW_SEC for c in near):
            unexplained += 1
    if unexplained:
        reasons["D"].append("permit %d" % unexplained)
    # E: ~/.salesanchor-tools
    if tstate["exists"]:
        if tstate["offline"]:
            reasons["E"].append("tools offline")
        else:
            if tstate["head_on_main"] != "yes":
                reasons["E"].append("tools stale")
            if tstate["sha_bad"]:
                reasons["E"].append("tools sha")
        if tstate["dirty"] > 0:
            reasons["E"].append("tools dirty")
    n_reasons = 0
    for code in ("A", "B", "C", "D", "E"):
        for r in reasons[code]:
            out("ABNORMAL_REASON=%s %s" % (code, r))
            n_reasons += 1
    due = review_due(led["rows"], now)
    if commit:
        saved = dict(new)
        saved["snapshot_ts"] = [now.strftime("%Y-%m-%dT%H:%M:%SZ")]
        os.makedirs(os.path.dirname(snap_path), exist_ok=True)
        tmp = snap_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(saved, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, snap_path)
        out("写しを更新した（--commit-snapshot）")
    else:
        out("写しは更新していない（--commit-snapshot なし）")
    out("PERMISSION_CHANGES=%s" % ("初回" if old is None else changed))
    out("REVIEW_DUE=%s" % (",".join(due) if due else "0"))
    return changed, n_reasons


def run_audit(home, now, with_permissions, out, commit=False, gh_view=None, git_run=None):
    since = now - datetime.timedelta(days=DAYS)
    events = load_events(home)
    consumed = count_types(events, since, lambda t: t == "consent_consumed")
    windows, n_windows = load_windows(home)
    guard_suspects, guard_reads, guard_excluded = count_guard_split(events, since, windows)
    guard_suspect = len(guard_suspects)
    permit = count_types(events, since, lambda t: t.endswith("_permit_consumed"))
    n_keys, unmatched = match_ledger_keys(home, since)
    total, delays = k0_delays(home, events)
    out("== 同意と権限の点検（過去%d日） ==" % DAYS)
    out("1. consent_consumed: %d 件 / 台帳の鍵 %d 件 / 記録に同意票と typed の「1」が見つからない: %d 件（0件が正常）"
        % (sum(consumed.values()), n_keys, unmatched))
    out("2. consent_guard_blocked: 疑い %d 件（0件が正常）／読み取りの空振り %d 件（参考）（試験の区間 %d 個・区間内で除いた件数 %d）"
        % (guard_suspect, guard_reads, n_windows, guard_excluded))
    for e in guard_suspects:
        out("GUARD_SUSPECT=ts=%s hook=%s condition=%s cmd_sha=%s cmd_len=%s"
            % (e.get("ts", "?"), e.get("hook", "?"), e.get("condition", "?"),
               e.get("cmd_sha", "不明"), e.get("cmd_len", "不明")))
    out("3. 許可券の消費: %s" % (", ".join("%s=%d" % kv for kv in sorted(permit.items())) or "0 件"))
    out("K0: 直前の人の入力が typed の「1」だった呼び出し %d 件のうち、遅れ %d 件（目標: %d 件たまった時点で遅れ0）"
        % (total, delays, K0_TARGET))
    if total >= K0_TARGET:
        out("K0 判定: %s" % ("○" if delays == 0 else "×（案 F に切り替える設計に戻す）"))
    else:
        out("K0 判定: 対象が %d 件に届くまで保留" % K0_TARGET)
    changes, n_reasons = 0, 0
    if with_permissions:
        changes, n_reasons = run_permissions(home, out, now, commit, gh_view, git_run)
    abnormal = unmatched > 0 or guard_suspect > 0 or n_reasons > 0
    out("ABNORMAL=%s" % ("yes" if abnormal else "no"))
    return abnormal, changes


def main(argv=None):
    ap = argparse.ArgumentParser(description="会話での同意の点検（読み取りだけ）")
    ap.add_argument("--probe", metavar="SESSION_ID")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--permissions", action="store_true")
    ap.add_argument("--commit-snapshot", action="store_true",
                    help="権限の写しを更新する（定期実行だけが付ける。付けないときは比べて表示するだけ）")
    args = ap.parse_args(argv)
    home = real_home()
    now = datetime.datetime.now(datetime.timezone.utc)
    if args.probe:
        print(json.dumps(probe(home, args.probe, now), ensure_ascii=False))
        return 0
    if args.audit:
        run_audit(home, now, args.permissions, print, args.commit_snapshot)
        return 0
    if args.permissions:
        run_permissions(home, print, now, args.commit_snapshot)
        return 0
    ap.print_usage()
    return 2


if __name__ == "__main__":
    sys.exit(main())
