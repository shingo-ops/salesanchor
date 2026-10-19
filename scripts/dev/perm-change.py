#!/usr/bin/env python3
"""perm-change.py - Opus の権限の足し引きと台帳（ADR-1034）。

許可の文を「台帳に記録」と「反映」の1回で行う。保留4項目（R1〜R4）と広すぎる許可（R0）は
反映せず、PO が `!` で実行する台本を出す。

呼び方（必ずこの形。~/.salesanchor-tools 以外からは動かない）:
  cd ~/.salesanchor-tools && python3 -I -B scripts/dev/perm-change.py <副命令> ...

副命令: apply / record / review / sync
終了コード: 0=成功, 1=引数・検証・書き込みの失敗, 3=保留, 4=版のずれを直せない・通信できない（設定は変えていない）
パスはこのスクリプトの中で組み立てる。引数でパスは受けない（consent-audit.py と同じ方針）。
関数は試験のために home・now・origin_url・git_run などを引数で受ける。
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import pwd
import re
import shlex
import shutil
import subprocess
import sys
import time

ORIGIN_URL = "https://github.com/shingo-ops/salesanchor.git"
TOOLS_DIRNAME = ".salesanchor-tools"
SELF_REL = "scripts/dev/perm-change.py"
AUDIT_REL = "scripts/dev/consent-audit.py"
REEXEC_ENV = "PERM_CHANGE_REEXEC"
DEFAULT_REVIEW_DAYS = 14

EXIT_OK, EXIT_FAIL, EXIT_HELD, EXIT_SYNC = 0, 1, 3, 4

# apply で扱える target: target → (設定ファイル, JSON の道, 許す操作)
APPLY_TARGETS = {
    "user-allow": ("settings", ["permissions", "allow"], ("add", "remove")),
    "repo-local-allow": ("repo_local", ["permissions", "allow"], ("add", "remove")),
    "user-automode-allow": ("settings", ["autoMode", "allow"], ("remove",)),
}

# 外せない例外の文（autoMode.allow）: SM-、ADR-1011 の例外の文、ADR-1034 の PDL-1
EXCEPTION_PREFIXES = ("SM-", "Permission self-maintenance")
EXCEPTION_CONTAINS = ("scripts/dev/perm-change.py",)

# 保留の目印（設計 §2-2。唯一の置き場）。
#   words: 英単語（前後が英数字でないときだけ当たる。_ と - は区切り）
#   phrases: 句（部分一致）／ja: 日本語（部分一致）
#   gated_*: 「読み取りの印」が無いときだけ当たる
RULES = {
    "R1": {
        "words": ["delete", "drop", "truncate", "prune"],
        "phrases": ["rm -r", "rm -rf", "volume rm"],
        "ja": ["削除", "消去"],
        "gated_words": ["ssh", "psql", "prod", "prod1", "prod2"],
        "gated_phrases": ["docker compose exec"],
        "gated_ja": ["本番"],
    },
    "R2": {
        "words": ["push", "main", "develop", "ruleset"],
        "phrases": ["reset --hard", "branch -d", "gh pr merge", "branch protection"],
        "ja": [],
        "force_words_need_push": ["--force", "-f"],
    },
    "R3": {
        "words": ["secret", "secrets", "token", "tokens", "key", "keys", "password", "passwd",
                  "credential", "credentials"],
        "phrases": [".env", "gh secret"],
        "ja": ["鍵", "合言葉", "秘密"],
    },
    "R4": {
        "words": ["hook", "hooks", "guard", "gate", "bypass", "skip", "soft_deny", "defaultmode",
                  "permission", "permissions", "settings"],
        "phrases": ["self-modification", ".claude/scripts", "agent-tokens"],
        "ja": ["例外", "見張り", "許可"],
    },
}
# Bash の文のうち R0 にしない「狭い形」の受け入れの一覧（設計 §2-2。唯一の置き場）。
# 一覧に足す（R0 を外す範囲を広げる）変更は R4。
R0_ACCEPT = {
    # Bash の受け入れの一覧（`*` の有無を問わない）: 先頭の語の並びがこのどれかと書かれたまま一致するとき
    "bash_accept": {
        ("git", "status"), ("git", "ls-files"), ("git", "rev-parse"),
        ("gh", "pr", "view"), ("gh", "pr", "list"), ("gh", "pr", "checks"), ("gh", "pr", "diff"),
        ("gh", "run", "view"), ("gh", "run", "list"),
        ("grep",), ("wc",),
    },
    # Edit 系の最初の段の受け入れ
    "edit_first_segments": {"docs", "frontend", "backend"},
    # MCP の読み取り専用サーバー
    "mcp_servers": {"context7"},
}
EDIT_TOOLS = ("edit", "write", "multiedit", "notebookedit")
READ_TOOLS = ("read", "grep", "glob")
EDIT_PATH_DENY = ("..", ".git/", "*", "$", ".claude", ".codex", ".salesanchor-tools", "agent-console")
READ_ONLY_MARKS = ["--read-only", "ai_ro", "-f /dev/null"]
READ_SELECT_BLOCKERS = ["insert", "update", "delete", "alter", "drop", "truncate", "copy"]


class Exit(Exception):
    def __init__(self, code, msg=""):
        Exception.__init__(self, msg)
        self.code = code
        self.msg = msg


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Exit(EXIT_FAIL, "引数の誤り: %s" % message)


# ── 目印の判定 ──────────────────────────────────────────────────────

def _has_word(text, word):
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(word) + r"(?![A-Za-z0-9])", text, re.I) is not None


def _has_any(text, words, phrases, ja):
    low = text.lower()
    return (any(_has_word(text, w) for w in words)
            or any(ph.lower() in low for ph in phrases)
            or any(j in text for j in ja))


def read_only_mark(text):
    """読み取りの印。`*` を含む文には効かない。"""
    if "*" in text:
        return False
    low = text.lower()
    if any(m in low for m in READ_ONLY_MARKS):
        return True
    return _has_word(text, "select") and not any(_has_word(text, w) for w in READ_SELECT_BLOCKERS)


def bash_tokens(item):
    """Bash(...) の中身を語に分ける（`:*` は ` *` とみなす）。Bash(...) の形でなければ None。"""
    m = re.fullmatch(r"\s*bash\((.*)\)\s*", item, re.I | re.S)
    if not m:
        return None
    return m.group(1).replace(":*", " *").split()


def cmd_name(tok):
    """パスを外し、末尾の数字と点を外した名前（/bin/rm→rm、python3.12→python）。"""
    return re.sub(r"[0-9.]+$", "", os.path.basename(tok)).lower()


def rm_with_star(item):
    toks = bash_tokens(item)
    return bool(toks) and cmd_name(toks[0]) == "rm" and "*" in item


BASH_SYMBOLS = (";", "&", "|", ">", "<", "`", "$", "\n", "\r", '"', "'", "\\")


def _bash_ok(content):
    """設計 §2-2 (a)（改6）: 記号が無く、先頭の語の並びが受け入れの一覧と書かれたままで一致するときだけ True。"""
    if any(c in content for c in BASH_SYMBOLS):
        return False
    toks = content.replace(":*", " *").split()
    if not toks:
        return False
    accept = R0_ACCEPT["bash_accept"]
    if "*" in content:
        prefix = []
        for t in toks:
            if "*" in t:
                break
            prefix.append(t)
        return bool(prefix) and tuple(prefix) in accept
    for n in range(len(toks), 0, -1):
        if tuple(toks[:n]) in accept:
            return not any(t.startswith("-") for t in toks[n:])
    return False


def _edit_path_ok(path):
    low = path.lower()
    if low.startswith(("~", "/")) or low.endswith("/"):
        return False
    if any(d in low for d in EDIT_PATH_DENY):
        return False
    segs = path.split("/")
    if len(segs) < 2 or segs[0] not in R0_ACCEPT["edit_first_segments"]:
        return False
    return not any(sg.startswith(".") for sg in segs)


def accepted_shape(s):
    """R0 にしない形（設計 §2-2 (a)〜(e)）に当てはまるか。"""
    m = re.fullmatch(r"mcp__([A-Za-z0-9_-]+)__([A-Za-z0-9_-]+)", s)
    if m:
        return m.group(1) in R0_ACCEPT["mcp_servers"]
    m = re.fullmatch(r"([A-Za-z][A-Za-z0-9_-]*)\((.*)\)", s, re.S)
    if not m or not m.group(2).strip():
        return False
    name, content = m.group(1).lower(), m.group(2)
    if name == "bash":
        return _bash_ok(content)
    if name in EDIT_TOOLS:
        return _edit_path_ok(content)
    if name in READ_TOOLS:
        return True
    if name == "webfetch":
        mm = re.fullmatch(r"domain:(.+)", content, re.I | re.S)
        return bool(mm) and "*" not in mm.group(1)
    return False


def r0_hit(item, target, op):
    s = item.strip()
    if target.endswith("automode-allow") and op == "add":
        return True
    if "perm-change" in s.lower():
        return True
    return not accepted_shape(s)


def rule_hit(rule, item):
    r = RULES[rule]
    if _has_any(item, r.get("words", []), r.get("phrases", []), r.get("ja", [])):
        return True
    if rule == "R1" and _has_any(item, r["gated_words"], r["gated_phrases"], r["gated_ja"]):
        return not read_only_mark(item)
    if rule == "R2" and _has_word(item, "push"):
        low = item.lower()
        return "--force" in low or re.search(r"(?<![A-Za-z0-9-])-f(?![A-Za-z0-9])", item) is not None
    return False


def classify(item, target, op):
    """足す文の保留判定。None=通常、'R0'〜'R4'=保留。"""
    if rm_with_star(item):
        return "R1"
    if r0_hit(item, target, op):
        return "R0"
    for rule in ("R1", "R2", "R3", "R4"):
        if rule_hit(rule, item):
            return rule
    return None


def is_exception_sentence(item):
    return item.startswith(EXCEPTION_PREFIXES) or any(c in item for c in EXCEPTION_CONTAINS)


# ── 下回り ──────────────────────────────────────────────────────────

def real_home():
    return pwd.getpwuid(os.getuid()).pw_dir


def run_git(args, cwd):
    try:
        p = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, timeout=120,
                           env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
        return p.returncode, p.stdout
    except Exception:
        return 127, b""


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def default_reexec(argv, self_path):
    os.environ[REEXEC_ENV] = "1"
    os.execv(sys.executable, [sys.executable, "-I", "-B", self_path] + list(argv))


def tools_dir(home):
    return os.path.join(home, TOOLS_DIRNAME)


def startup_checks(home, ctx):
    """起動時の確かめ 1〜7（設計 §4-1）。返り値: V（GitHub の main の版）。
    HEAD を V に揃え直して起動し直す場合は ('reexec', None) を返す。"""
    flags = ctx["flags"]
    git = ctx["git_run"]
    tools = tools_dir(home)
    # 1
    if not (getattr(flags, "isolated", 0) and getattr(flags, "dont_write_bytecode", 0)):
        raise Exit(EXIT_FAIL, "python3 -I -B で起動してください（isolated と dont_write_bytecode が必要）")
    # 2
    expect = os.path.join(tools, SELF_REL)
    if os.path.realpath(ctx["self_path"]) != os.path.realpath(expect):
        raise Exit(EXIT_FAIL, "~/%s/%s から起動してください" % (TOOLS_DIRNAME, SELF_REL))
    # 3
    rc, out = git(["remote", "get-url", "origin"], tools)
    if rc != 0 or out.decode("utf-8", "replace").strip() != ctx["origin_url"]:
        raise Exit(EXIT_FAIL, "~/%s の origin の URL が想定と違います" % TOOLS_DIRNAME)
    # 4
    rc, out = git(["status", "--porcelain", "--untracked-files=all"], tools)
    if rc != 0 or out.strip():
        raise Exit(EXIT_FAIL, "~/%s に変更または追跡外のファイルがあります（同期もしません）" % TOOLS_DIRNAME)
    # 5
    rc, out = git(["ls-remote", "origin", "refs/heads/main"], tools)
    parts = out.decode("utf-8", "replace").split()
    if rc != 0 or not parts:
        raise Exit(EXIT_SYNC, "GitHub の main の版を取れません（通信できない）。設定は変えていません")
    v = parts[0]
    # 6
    rc, out = git(["rev-parse", "HEAD"], tools)
    head = out.decode("utf-8", "replace").strip() if rc == 0 else ""
    if head != v:
        if ctx["env"].get(REEXEC_ENV) == "1":
            raise Exit(EXIT_SYNC, "起動し直した後も HEAD が GitHub の main の版と違います")
        rc, _ = git(["fetch", "-q", "origin", "main"], tools)
        if rc != 0:
            raise Exit(EXIT_SYNC, "fetch に失敗しました（設定は変えていません）")
        rc, out = git(["rev-parse", "FETCH_HEAD"], tools)
        if rc != 0 or out.decode("utf-8", "replace").strip() != v:
            raise Exit(EXIT_SYNC, "fetch した版が ls-remote の版と違います（その間に main が進みました）")
        rc, _ = git(["checkout", "-q", "--detach", v], tools)
        if rc != 0:
            raise Exit(EXIT_SYNC, "checkout に失敗しました（設定は変えていません）")
        return "reexec", v
    # 7
    contents = {}
    for rel, path in ((SELF_REL, ctx["self_path"]), (AUDIT_REL, os.path.join(tools, AUDIT_REL))):
        rc, ref = git(["show", "%s:%s" % (v, rel)], tools)
        try:
            with open(path, "rb") as f:
                mine = f.read()
        except OSError:
            raise Exit(EXIT_FAIL, "%s を読めません" % rel)
        if rc != 0 or sha256_bytes(mine) != sha256_bytes(ref):
            raise Exit(EXIT_FAIL, "%s の中身が GitHub の main の版と違います" % rel)
        contents[rel] = mine
    return v, contents


def load_audit(path, source):
    """照合した中身（source）をそのまま読み込む。読み直さない。"""
    spec = importlib.util.spec_from_file_location("consent_audit_verified", path)
    mod = importlib.util.module_from_spec(spec)
    exec(compile(source, path, "exec"), mod.__dict__)
    return mod


# ── 台帳・設定ファイル ───────────────────────────────────────────────

def ts_str(now):
    return now.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def acquire_lock(lock):
    os.makedirs(os.path.dirname(lock), exist_ok=True)
    for _ in range(100):
        try:
            os.mkdir(lock)
            return
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(lock) > 120:
                    os.rmdir(lock)
                    continue
            except OSError:
                pass
            time.sleep(0.1)
    raise Exit(EXIT_FAIL, "台帳のロックを取れません")


def make_row(now, actor, sub, target, op, item_hash, summary, intent, reason, expected, review_by,
             category, result, po_ref):
    return {"ts": ts_str(now), "actor": actor, "sub": sub, "target": target, "op": op,
            "item_hash": item_hash, "summary": summary, "intent": intent, "reason": reason,
            "expected_effect": expected, "review_by": review_by, "category": category,
            "result": result, "po_ref": po_ref}


def append_ledger(audit, home, row):
    """台帳に1行足す。prev_sha は直前の行の sha256 先頭16桁（1行目は genesis）。"""
    p = audit.perm_paths(home)
    acquire_lock(p["perm_lock"])
    try:
        led = audit.read_ledger(home)
        full = dict(row)
        full["prev_sha"] = led["head"]
        line = json.dumps(full, ensure_ascii=False)
        os.makedirs(os.path.dirname(p["perm_ledger"]), exist_ok=True)
        need_nl = False
        try:
            with open(p["perm_ledger"], "rb") as f:
                data = f.read()
            need_nl = bool(data) and not data.endswith(b"\n")
        except OSError:
            pass
        fd = os.open(p["perm_ledger"], os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, (("\n" if need_nl else "") + line + "\n").encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        try:
            os.rmdir(p["perm_lock"])
        except OSError:
            pass


def write_json_atomic(path, data):
    tmp = path + ".permtmp"
    try:
        mode = os.stat(path).st_mode & 0o777
    except OSError:
        mode = 0o600
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def restore_from(backup, path):
    tmp = path + ".permrestore"
    shutil.copyfile(backup, tmp)
    shutil.copymode(backup, tmp)
    os.replace(tmp, path)


def file_sha(path):
    try:
        with open(path, "rb") as f:
            return sha256_bytes(f.read())
    except OSError:
        return None


def _walk(data, keys, create):
    node = data
    for k in keys[:-1]:
        nxt = node.get(k)
        if nxt is None:
            if not create:
                return None, None
            nxt = node[k] = {}
        if not isinstance(nxt, dict):
            raise Exit(EXIT_FAIL, "設定ファイルの形が想定と違います（%s）" % k)
        node = nxt
    return node, keys[-1]


def get_list(data, keys):
    node, last = _walk(data, keys, False)
    if node is None or last not in node:
        return []
    v = node[last]
    if not isinstance(v, list):
        raise Exit(EXIT_FAIL, "設定ファイルの %s が配列ではありません" % ".".join(keys))
    return v


def summary_of(item):
    return "[R3]" if rule_hit("R3", item) else item[:80]


def write_po_script(home, now, target, op, item, item_hash, category, intent, reason, audit):
    p = audit.perm_paths(home)
    kind, keys, _ = APPLY_TARGETS[target]
    path = p[kind]
    d = os.path.join(home, "CC報告ファイル-keep", "permission-delegation")
    os.makedirs(d, exist_ok=True)
    base = "po-apply-%s" % now.astimezone(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = os.path.join(d, base + ".sh")
    n = 1
    while os.path.exists(out):
        n += 1
        out = os.path.join(d, "%s-%d.sh" % (base, n))
    body = """#!/bin/bash
# PO 用: 保留（%(cat)s）になった権限の変更を反映する台本（perm-change.py が生成。ADR-1034）
# 使い方: bash この台本 consent:<k1>:<k2>:<k3>   （同意票の鍵。それ以外の形なら何も変えずに終わる）
set -euo pipefail
PO_REF="${1:?usage: bash $0 consent:<k1>:<k2>:<k3>}"
case "${PO_REF}" in
  consent:*) ;;
  *) echo "ERROR: 第1引数は consent:<鍵> の形にしてください。何も変えていません。" >&2; exit 1 ;;
esac
SETTINGS=%(path)s
STAMP="$(date +%%Y%%m%%d%%H%%M%%S)"
if [ -f "${SETTINGS}" ]; then
  cp -p "${SETTINGS}" "${SETTINGS}.bak-${STAMP}"
  echo "backup: ${SETTINGS}.bak-${STAMP}"
fi
python3 - "${SETTINGS}" <<'PYEOF'
import json, os, sys
path = sys.argv[1]
KEYS = json.loads(%(keys)s)
OP = %(op)s
ITEM = json.loads(%(item)s)
try:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    data = {}
node = data
for k in KEYS[:-1]:
    node = node.setdefault(k, {})
arr = node.setdefault(KEYS[-1], [])
if OP == "add":
    if ITEM not in arr:
        arr.append(ITEM)
else:
    arr[:] = [x for x in arr if x != ITEM]
tmp = path + ".potmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\\n")
os.replace(tmp, path)
with open(path, encoding="utf-8") as f:
    chk = json.load(f)
n = chk
for k in KEYS:
    n = n[k]
ok = (ITEM in n) if OP == "add" else (ITEM not in n)
if not ok:
    sys.exit("ERROR: 読み直しで反映を確認できません。控え(.bak-*)から戻してください")
print("applied: " + OP)
PYEOF
cd ~/.salesanchor-tools && python3 -I -B scripts/dev/perm-change.py record --target %(target)s --op %(op_arg)s --item-hash %(hash)s --po-ref "${PO_REF}" --actor po-script --intent %(intent)s --reason %(reason)s
""" % {
        "cat": category, "path": shlex.quote(path),
        "keys": repr(json.dumps(keys)), "op": repr(op),
        "item": repr(json.dumps(item, ensure_ascii=False)),
        "target": shlex.quote(target), "op_arg": shlex.quote(op), "hash": shlex.quote(item_hash),
        "intent": shlex.quote(intent), "reason": shlex.quote(reason),
    }
    with open(out, "w", encoding="utf-8") as f:
        f.write(body)
    os.chmod(out, 0o700)
    return out


# ── 副命令 ──────────────────────────────────────────────────────────

def _review_by(now, days):
    return (now + datetime.timedelta(days=days)).strftime("%Y-%m-%d")


def _check_apply_fields(a):
    for name in ("intent", "reason", "expected"):
        if not (getattr(a, name) or "").strip():
            raise Exit(EXIT_FAIL, "--%s が空です" % name)
    if not (a.item or "").strip():
        raise Exit(EXIT_FAIL, "--item が空です")
    if not 1 <= a.review_days <= 30:
        raise Exit(EXIT_FAIL, "--review-days は 1〜30 です")


def cmd_apply(a, home, now, audit):
    _check_apply_fields(a)
    if a.target not in APPLY_TARGETS:
        raise Exit(EXIT_FAIL, "この target は apply で扱えません（record のみ）")
    kind, keys, ops = APPLY_TARGETS[a.target]
    if a.op not in ops:
        if a.op == "add":
            pass  # autoMode.allow の add は R0 として保留にする（下）
        else:
            raise Exit(EXIT_FAIL, "この target では %s は使えません" % a.op)
    h = audit.item_sha8(a.item)
    summary = summary_of(a.item)
    review_by = _review_by(now, a.review_days)
    category = None
    if a.op == "add":
        r = classify(a.item, a.target, "add")
        category = "reserved:%s" % r if r else None
    elif a.target == "user-automode-allow" and is_exception_sentence(a.item):
        category = "reserved:R4"
    if category:
        script = write_po_script(home, now, a.target, a.op, a.item, h, category, a.intent, a.reason, audit)
        append_ledger(audit, home, make_row(now, "opus", "apply", a.target, a.op, h, summary, a.intent,
                                            a.reason, a.expected, review_by, category, "held", ""))
        print("RESULT=held category=%s item_hash=%s" % (category, h))
        print("PO_SCRIPT=%s" % script)
        return EXIT_HELD
    return _do_apply(a.target, a.op, a.item, h, summary, a.intent, a.reason, a.expected, review_by,
                     home, now, audit)


def _do_apply(target, op, item, h, summary, intent, reason, expected, review_by, home, now, audit):
    p = audit.perm_paths(home)
    kind, keys, _ = APPLY_TARGETS[target]
    path = p[kind]
    exists = os.path.exists(path)
    if exists:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            raise Exit(EXIT_FAIL, "設定ファイルを JSON として読めません")
        if not isinstance(data, dict):
            raise Exit(EXIT_FAIL, "設定ファイルの形が想定と違います")
    else:
        if op == "remove":
            data = {}
        elif not os.path.isdir(os.path.dirname(path)):
            raise Exit(EXIT_FAIL, "設定ファイルの置き場がありません")
        else:
            data = {}
    arr = get_list(data, keys)
    present = item in arr
    if (op == "add" and present) or (op == "remove" and not present):
        append_ledger(audit, home, make_row(now, "opus", "apply", target, op, h, summary, intent, reason,
                                            expected, review_by, "normal", "noop", ""))
        print("RESULT=noop item_hash=%s" % h)
        return EXIT_OK
    backup = None
    if exists:
        stamp = now.astimezone(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        bdir = os.path.join(home, ".claude", "logs", "perm-backup",
                            "%s-%d-%s" % (stamp, os.getpid(), os.urandom(4).hex()))
        os.makedirs(os.path.dirname(bdir), exist_ok=True)
        os.makedirs(bdir, exist_ok=False)
        backup = os.path.join(bdir, os.path.basename(path))
        shutil.copy2(path, backup)
    if op == "add":
        node, last = _walk(data, keys, True)
        node.setdefault(last, [])
        node[last].append(item)
    else:
        node, last = _walk(data, keys, False)
        node[last] = [x for x in node[last] if x != item]
    try:
        write_json_atomic(path, data)
        with open(path, encoding="utf-8") as f:
            chk = json.load(f)
        got = get_list(chk, keys)
        ok = (item in got) if op == "add" else (item not in got)
    except Exception:
        ok = False
    if not ok:
        _restore(backup, path, exists)
        raise Exit(EXIT_FAIL, "書いた後の読み直しで反映を確認できませんでした。元に戻しました")
    try:
        append_ledger(audit, home, make_row(now, "opus", "apply", target, op, h, summary, intent, reason,
                                            expected, review_by, "normal", "applied", ""))
    except Exception as e:
        _restore(backup, path, exists)
        raise Exit(EXIT_FAIL, "台帳に書けませんでした。元に戻しました（%s）" % type(e).__name__)
    print("RESULT=applied target=%s op=%s item_hash=%s review_by=%s" % (target, op, h, review_by))
    return EXIT_OK


def _restore(backup, path, existed):
    try:
        if existed and backup:
            restore_from(backup, path)
        elif not existed and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


PO_REF_RE = re.compile(r"PR#[0-9]+")


def cmd_record(a, home, now, audit):
    if a.target not in audit.TARGET_KEYS:
        raise Exit(EXIT_FAIL, "未知の target です")
    if not re.fullmatch(r"[0-9a-f]{8}", a.item_hash or ""):
        raise Exit(EXIT_FAIL, "--item-hash は8桁の16進数です")
    ref = a.po_ref or ""
    if not (PO_REF_RE.fullmatch(ref) or audit.parse_consent_ref(ref)):
        raise Exit(EXIT_FAIL, "--po-ref は PR#<数字> か consent:<k1>:<k2>:<k3> の形です")
    key = audit.TARGET_KEYS[a.target]
    category = "normal" if key in audit.LEDGER_ONLY_KEYS else "reserved:R4"
    append_ledger(audit, home, make_row(now, a.actor, "record", a.target, a.op, a.item_hash,
                                        "(record) %s" % a.target, a.intent or "", a.reason or "", "", "",
                                        category, "recorded", ref))
    print("RESULT=recorded target=%s op=%s item_hash=%s" % (a.target, a.op, a.item_hash))
    return EXIT_OK


def cmd_review(a, home, now, audit):
    if not re.fullmatch(r"[0-9a-f]{8}", a.hash or ""):
        raise Exit(EXIT_FAIL, "--hash は8桁の16進数です")
    if not (a.effect or "").strip():
        raise Exit(EXIT_FAIL, "--effect が空です")
    if not 1 <= a.review_days <= 30:
        raise Exit(EXIT_FAIL, "--review-days は 1〜30 です")
    led = audit.read_ledger(home)
    target = None
    for r in led["rows"]:
        if r.get("item_hash") == a.hash and r.get("result") in ("applied", "recorded") and r.get("op") == "add":
            target = r.get("target")
    if not target:
        raise Exit(EXIT_FAIL, "台帳にその item_hash の追加の行がありません")
    if a.decision == "keep":
        by = _review_by(now, a.review_days)
        append_ledger(audit, home, make_row(now, "opus", "review", target, "review", a.hash, "keep", "",
                                            a.effect, "", by, "normal", "reviewed", ""))
        print("RESULT=reviewed decision=keep item_hash=%s review_by=%s" % (a.hash, by))
        return EXIT_OK
    if target not in APPLY_TARGETS or "remove" not in APPLY_TARGETS[target][2]:
        raise Exit(EXIT_FAIL, "この target は道具では外せません")
    p = audit.perm_paths(home)
    kind, keys, _ = APPLY_TARGETS[target]
    try:
        with open(p[kind], encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        raise Exit(EXIT_FAIL, "設定ファイルを JSON として読めません")
    found = [x for x in get_list(data, keys) if audit.item_sha8(x) == a.hash]
    if not found:
        raise Exit(EXIT_FAIL, "設定ファイルにその item_hash の文がありません")
    item = found[0]
    if is_exception_sentence(item):
        raise Exit(EXIT_HELD, "例外の文は外せません（保留 R4）")
    code = _do_apply(target, "remove", item, a.hash, summary_of(item), "review: remove", a.effect,
                     a.effect, "", home, now, audit)
    if code == EXIT_OK:
        append_ledger(audit, home, make_row(now, "opus", "review", target, "review", a.hash, "remove", "",
                                            a.effect, "", "", "normal", "reviewed", ""))
    return code


def cmd_sync(v):
    print("TOOLS_SYNCED=%s" % v[:12])
    return EXIT_OK


# ── 入口 ────────────────────────────────────────────────────────────

def build_parser():
    ap = _Parser(description="Opus の権限の足し引きと台帳（ADR-1034）")
    sub = ap.add_subparsers(dest="cmd", parser_class=_Parser)
    a = sub.add_parser("apply")
    a.add_argument("--target", required=True)
    a.add_argument("--op", required=True, choices=["add", "remove"])
    a.add_argument("--item", required=True)
    a.add_argument("--intent", required=True)
    a.add_argument("--reason", required=True)
    a.add_argument("--expected", required=True)
    a.add_argument("--review-days", type=int, default=DEFAULT_REVIEW_DAYS)
    r = sub.add_parser("record")
    r.add_argument("--target", required=True)
    r.add_argument("--op", required=True, choices=["add", "remove", "modify"])
    r.add_argument("--item-hash", required=True)
    r.add_argument("--po-ref", required=True)
    r.add_argument("--intent", default="")
    r.add_argument("--reason", default="")
    r.add_argument("--actor", default="opus", choices=["opus", "po-script"])
    v = sub.add_parser("review")
    v.add_argument("--hash", required=True)
    v.add_argument("--decision", required=True, choices=["keep", "remove"])
    v.add_argument("--effect", required=True)
    v.add_argument("--review-days", type=int, default=DEFAULT_REVIEW_DAYS)
    sub.add_parser("sync")
    return ap


def main(argv=None, *, home=None, now=None, origin_url=None, git_run=None, flags=None, self_path=None,
         env=None, reexec=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    home = home or real_home()
    now = now or datetime.datetime.now(datetime.timezone.utc)
    ctx = {
        "flags": flags if flags is not None else sys.flags,
        "self_path": self_path or os.path.abspath(__file__),
        "origin_url": origin_url or ORIGIN_URL,
        "git_run": git_run or run_git,
        "env": env if env is not None else os.environ,
    }
    reexec = reexec or default_reexec
    try:
        args = build_parser().parse_args(argv)
        if not args.cmd:
            raise Exit(EXIT_FAIL, "副命令（apply / record / review / sync）が要ります")
        # 引数の検査は、何も書かない段階で先に行う
        if args.cmd == "apply":
            _check_apply_fields(args)
        res = startup_checks(home, ctx)
        if res[0] == "reexec":
            return reexec(argv, ctx["self_path"])
        v, contents = res
        audit = load_audit(os.path.join(tools_dir(home), AUDIT_REL), contents[AUDIT_REL])
        if args.cmd == "sync":
            return cmd_sync(v)
        if args.cmd == "apply":
            return cmd_apply(args, home, now, audit)
        if args.cmd == "record":
            return cmd_record(args, home, now, audit)
        return cmd_review(args, home, now, audit)
    except Exit as e:
        if e.msg:
            print("ERROR: %s" % e.msg, file=sys.stderr)
        return e.code


if __name__ == "__main__":
    sys.exit(main())
