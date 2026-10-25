#!/usr/bin/env python3
"""confidential-quote-guard guard.py — PreToolUse (matcher: Bash)

仕入元の投稿の原文を、「」『』の中に書き写したまま公開の置き場へ送るのを、送る前に止める。
  - git push        : 送る差分 (origin/main...<送るブランチ>) の追加行
  - gh pr create/edit/comment/review, gh issue create/comment : 本文

止める決まり (全部満たす語句が 1 つでもあれば exit 2):
  1. 「」または『』の中にあり、4 文字以上
  2. 除外表 (状態の写し・商品名の写し・一般語の表) に無い。数字と区切りだけの語句も止めない
  3. 原文の置き場のどれかのファイルに、そのまま現れる

表は Mac の社外秘フォルダにあり、repo には中身を一切入れない。
表が読めない/空/本文の出どころが決まらない/差分が取れないときは止める (全部拒否に倒す)。
止めた記録は日時・ファイル:行・件数だけ。語句は記録に書かない。

設計: docs/handoff/confidential-quote-guard/design.md §3 / ADR-1045
標準ライブラリのみ。
"""
import datetime
import glob
import json
import os
import re
import shlex
import subprocess
import sys
import time
import unicodedata

HOOK = "confidential-quote-guard"
MIN_LEN = 4

GH_SUB_RE = re.compile(
    r"(?:^|[\s;&|(`\x22\x27])(?:\S*/)?gh\b[^;&|\n]*?\b(?:pr\s+(?:create|edit|comment|review)|issue\s+(?:create|comment))\b")
GH_ACTIONS = {"pr": {"create", "edit", "comment", "review"}, "issue": {"create", "comment"}}
PUSH_RE = re.compile(r"(?:^|[\s;&|(`\x22\x27])(?:\S*/)?git\b[^;&|\n]*?\bpush\b")
HEREDOC_RE = re.compile(r"(?<!<)<<(?!<)(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
PHRASE_RES = (re.compile(r"「([^「」\n]*)」"), re.compile(r"『([^『』\n]*)』"))
SEP_CHARS = set(";&|()\n")
PUSH_VALUE_FLAGS = {"-o", "--push-option", "--receive-pack", "--exec", "--repo"}
EXPLAIN = ("仕入元の原文の書き写しは、公開の置き場へ送れません。"
           "該当の語句を消し、「形の説明」(例: 値段の行・在庫数の行・見出しの行) に書き換えてから、もう一度送ってください。"
           "誤って止まった一般語は、Opus が一般語の表 (confidential-allow.txt) に理由つきで足します。")


class Block(Exception):
    pass


def table_dir():
    return os.path.expanduser(os.environ.get("CONFID_GUARD_DIR") or "~/CC報告ファイル-keep/confid-guard")


def events_path():
    return os.path.expanduser(os.environ.get("CONFID_GUARD_EVENTS") or "~/.claude/logs/agent-events.jsonl")


def log_block(reason):
    """止めた記録 (日時・見張りの名前・件数と場所だけ。語句は書かない)。"""
    try:
        p = events_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        rec = {
            "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "type": "hook_blocked",
            "hook": HOOK,
            "reason": reason,
            "cmd_head": "",
        }
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------- tables

def _read_lines(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().splitlines()
    except OSError as e:
        raise Block("表が読めません: %s (%s)" % (os.path.basename(path), e.strerror))


def load_wordlist(path, allow_tab_reason=False):
    words = set()
    for ln in _read_lines(path):
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        w = ln.split("\t", 1)[0] if allow_tab_reason else ln
        w = w.strip()
        if w:
            words.add(w)
    return words


def load_tables():
    d = table_dir()
    conf = os.path.join(d, "confidential-corpus.conf")
    repos, patterns = set(), []
    for ln in _read_lines(conf):
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("repo:"):
            repos.add(s[5:].strip())
        elif s.startswith("corpus:"):
            patterns.append(s[7:].strip())
    if not patterns:
        raise Block("原文の置き場の表 (confidential-corpus.conf) に corpus: の行がありません")
    files = []
    for pat in patterns:
        m = sorted(glob.glob(os.path.expanduser(pat)))
        if not m:
            raise Block("原文の置き場の表の行に当たるファイルがありません: 表の %d 行目以降を確かめてください" % (patterns.index(pat) + 1))
        files.extend(m)
    # 写しが古いと、新しい投稿を照らせないまま通してしまう。古ければ止める (取り直しは fetch_corpus.py)
    try:
        max_age = float(os.environ.get("CONFID_CORPUS_MAX_AGE_DAYS", "2"))
    except ValueError:
        raise Block("原文の写しの古さの上限が読めません")
    now = time.time()
    for f in files:
        try:
            age = (now - os.path.getmtime(f)) / 86400.0
        except OSError as e:
            raise Block("原文のファイルが読めません: %s" % e.strerror)
        if age > max_age:
            raise Block("原文の写しが古い (%.1f 日前。上限 %g 日)。fetch_corpus.py で取り直してください" % (age, max_age))
    parts = []
    for f in files:
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                parts.append(fh.read())
        except OSError as e:
            raise Block("原文のファイルが読めません: %s" % e.strerror)
    corpus = "\n".join(parts)
    if not corpus.strip():
        raise Block("原文の置き場が空です")
    excl = set()
    excl |= load_wordlist(os.path.join(d, "status-words.txt"))
    excl |= load_wordlist(os.path.join(d, "product-names.txt"))
    excl |= load_wordlist(os.path.join(d, "confidential-allow.txt"), allow_tab_reason=True)
    return repos, corpus, excl, len(files)


# ---------------------------------------------------------------- phrase check

def only_digits_punct(p):
    for ch in p:
        if unicodedata.category(ch)[0] not in ("N", "P", "S", "Z", "C"):
            return False
    return True


def find_hits(entries, corpus, excl):
    """entries: [(label, lineno, text)] -> [(label, lineno, phrase)] (重複語句は場所ごとに 1 件)"""
    cache = {}
    hits = []
    for label, no, text in entries:
        for rx in PHRASE_RES:
            for m in rx.finditer(text):
                p = m.group(1).strip()
                if len(p) < MIN_LEN or only_digits_punct(p) or p in excl:
                    continue
                if p not in cache:
                    cache[p] = p in corpus
                if cache[p]:
                    hits.append((label, no, p))
    return hits


# ---------------------------------------------------------------- command parsing

def strip_heredocs(cmd):
    lines = cmd.split("\n")
    out, tag, dash = [], None, False
    for ln in lines:
        if tag is not None:
            chk = ln.strip() if dash else ln
            if chk == tag:
                tag = None
                out.append(ln)
            continue
        out.append(ln)
        m = HEREDOC_RE.search(ln)
        if m:
            dash, tag = m.group(1) == "-", m.group(3)
    return "\n".join(out)


def tokenize_all(cmd):
    """字句に分ける。改行も区切りの字句にする (改行で区切った 2 つ目の操作も読むため)。"""
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|()<>\n")
    lex.whitespace_split = True
    lex.whitespace = " \t\r"
    lex.commenters = ""
    return list(lex)


def resolve_cwd(cmd, payload_cwd, upto=None):
    s = cmd if upto is None else cmd[:upto]
    cwd = payload_cwd or os.getcwd()
    for m in re.finditer(r"(?:^|[;&|\n(]\s*)cd\s+(?:\"([^\"]+)\"|'([^']+)'|([^\s;&|)]+))", s):
        p = os.path.expanduser(m.group(1) or m.group(2) or m.group(3))
        if p.startswith("/"):
            cwd = p
    return cwd


def git(cwd, *args):
    return subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, text=True)


def repo_slug(cwd):
    r = git(cwd, "remote", "get-url", "origin")
    if r.returncode != 0:
        return None
    url = r.stdout.strip()
    if url.endswith(".git"):
        url = url[:-4]
    parts = [x for x in re.split(r"[/:]", url) if x]
    return "/".join(parts[-2:]) if len(parts) >= 2 else None


def added_lines(cwd, ref):
    """origin/main...ref の追加行 -> [(file, lineno, text)]。取れなければ Block。"""
    r = git(cwd, "-c", "core.quotePath=false", "diff", "--no-color", "--no-ext-diff", "-U0", "origin/main...%s" % ref)
    if r.returncode != 0:
        raise Block("差分が取れません (origin/main...%s)" % ref)
    out, fname, ln, in_head = [], None, 0, False
    for line in r.stdout.split("\n"):
        if line.startswith("diff --git "):
            fname, in_head = None, True  # ファイルの見出し。この中の "+++ " だけが名前
            continue
        if in_head:
            if line.startswith("+++ "):
                nm = line[4:].split("\t")[0]
                if nm.startswith('"b/') and nm.endswith('"'):
                    fname = nm[3:-1]
                elif nm.startswith("b/"):
                    fname = nm[2:]
                else:
                    fname = None
                continue
            if not line.startswith("@@"):
                continue
            in_head = False
        m = re.match(r"@@ -\S+ \+(\d+)(?:,\d+)? @@", line)
        if m:
            ln = int(m.group(1))
            continue
        if line.startswith("+") and fname:
            out.append((fname, ln, line[1:]))
            ln += 1
    return out


def push_refs(cmd, m):
    """git push の送るブランチを決める。決まらなければ Block。-> [ref] (空なら削除だけ=見るものなし)"""
    seg = re.split(r"[;&|\n)]", cmd[m.end():], maxsplit=1)[0]
    try:
        toks = shlex.split(seg)
    except ValueError:
        raise Block("git push の引数を読めません")
    pos, delete = [], False
    i = 0
    while i < len(toks):
        t = toks[i]
        if t in ("--delete", "-d"):
            delete = True
        elif t in ("--all", "--mirror"):
            raise Block("%s で送るブランチが決まりません" % t)
        elif t in PUSH_VALUE_FLAGS:
            i += 1
        elif t.startswith("-"):
            pass
        else:
            pos.append(t)
        i += 1
    if delete:
        return []
    specs = pos[1:]
    if not specs:
        return ["HEAD"]
    refs = []
    for s in specs:
        s = s.lstrip("+")
        src = s.split(":", 1)[0]
        if s.startswith(":") or src == "":
            continue
        if re.search(r"[$*`?]", src):
            raise Block("送るブランチが決まりません")
        refs.append(src)
    return refs


def check_push(cmd, m, payload_cwd, repos):
    cwd = resolve_cwd(cmd, payload_cwd, m.start())
    c = re.search(r"\bgit\s+-C\s+(?:\"([^\"]+)\"|'([^']+)'|(\S+))", cmd[m.start():m.end()])
    if c:
        cwd = os.path.expanduser(c.group(1) or c.group(2) or c.group(3))
    slug = repo_slug(cwd)
    if slug is None or slug not in repos:
        return []  # 表に無い repo の push は照らさずに通す
    if git(cwd, "rev-parse", "--verify", "--quiet", "origin/main").returncode != 0:
        raise Block("表に並んだ repo (%s) に origin/main がありません" % slug)
    entries = []
    for ref in push_refs(cmd, m):
        ok = git(cwd, "rev-parse", "--verify", "--quiet", ref + "^{commit}").returncode == 0
        if not ok:
            raise Block("送るブランチ %s が見つかりません" % ref)
        entries.extend(added_lines(cwd, ref))
    return entries


def _plain_path(p, cwd):
    p = p.strip().strip("'\"")
    if re.search(r"[$`*?]", p):
        raise Block("本文のファイルの場所が決まりません")
    p = os.path.expanduser(p)
    return p if os.path.isabs(p) else os.path.join(cwd, p)


def read_body_file(p):
    if p == "/dev/null":
        return []
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return [(p, i + 1, t) for i, t in enumerate(f.read().split("\n"))]
    except OSError as e:
        raise Block("本文のファイルが読めません: %s (%s)" % (os.path.basename(p), e.strerror))


def heredoc_infos(cmd):
    """heredoc ごとの (印が引用符つきか, 本文) -> [(bool, str)]"""
    infos = []
    tag, dash, quoted, buf = None, False, False, []
    for ln in cmd.split("\n"):
        if tag is not None:
            chk = ln.strip() if dash else ln
            if chk == tag:
                infos.append((quoted, "\n".join(buf)))
                tag, buf = None, []
            else:
                buf.append(ln)
            continue
        m = HEREDOC_RE.search(ln)
        if m:
            dash, quoted, tag = m.group(1) == "-", bool(m.group(2)), m.group(3)
    if tag is not None:
        infos.append((quoted, "\n".join(buf)))
    return infos


def _is_sep(t):
    return bool(t) and all(c in SEP_CHARS for c in t)


def _split_segments(toks):
    """字句を区切りで切る -> [(区切り記号, 字句のリスト)]"""
    segs, cur, sep = [], [], None
    for t in toks:
        if _is_sep(t):
            segs.append((sep, cur))
            cur, sep = [], t
        else:
            cur.append(t)
    segs.append((sep, cur))
    return segs


def _gh_target(seg):
    """この段が gh の本文つき操作なら gh より後ろの字句を返す。違えば None。"""
    for i, t in enumerate(seg):
        if os.path.basename(t) == "gh":
            rest = seg[i + 1:]
            for j in range(len(rest) - 1):
                if rest[j] in GH_ACTIONS and rest[j + 1] in GH_ACTIONS[rest[j]]:
                    return rest
            return None
    return None


def _stdin_source(seg, prev_sep, prev_seg, cwd, files, heredocs):
    """gh -F - の標準入力の出どころ。照らせる形ならファイルを files に足す。決まらなければ Block。"""
    redirected = False
    for i, t in enumerate(seg):
        if t == "<" and i + 1 < len(seg):
            files.append(_plain_path(seg[i + 1], cwd))
            redirected = True
        elif t == "<<<":
            redirected = True
            arg = seg[i + 1] if i + 1 < len(seg) else ""
            if re.search(r"[$`]", arg):
                raise Block("標準入力 (<<<) の本文の出どころが決まりません (変数・コマンド置換)")
        elif t.startswith("<<") and t != "<<<":
            redirected = True
            if any((not q) and re.search(r"[$`]", b) for q, b in heredocs):
                raise Block("引用符なしの heredoc の本文に変数・コマンド置換があります")
    if redirected:
        return
    if prev_sep == "|" and prev_seg:
        head = os.path.basename(prev_seg[0])
        args = prev_seg[1:]
        if head == "cat":
            got, i = [], 0
            while i < len(args):
                if args[i] == "<" and i + 1 < len(args):
                    got.append(args[i + 1]); i += 1
                elif not args[i].startswith("-") and not _is_sep(args[i]):
                    got.append(args[i])
                i += 1
            if got:
                for g in got:
                    files.append(_plain_path(g, cwd))
                return
        elif head in ("echo", "printf"):
            if not any(re.search(r"[$`]", a) for a in args):
                return
            raise Block("echo/printf の本文に変数・コマンド置換があります")
    raise Block("標準入力で渡す本文の出どころが決まりません")


def check_gh(cmd, payload_cwd):
    """gh の本文。(a) コマンド全体 (b) 本文ファイル (c) 外から来る本文 (d) 決まらなければ Block
    コマンド中の gh の操作は全部読む (区切りごとに字句に分けて、本文の付け方を見る)。"""
    base = strip_heredocs(cmd)
    try:
        toks = tokenize_all(base)
    except ValueError:
        raise Block("コマンドの本文の付け方を読めません")
    heredocs = heredoc_infos(cmd)
    entries = [("コマンド本文", i + 1, t) for i, t in enumerate(cmd.split("\n"))]  # (a)
    files = []
    cwd = payload_cwd or os.getcwd()
    prev_seg, prev_sep = None, None
    for k, t in enumerate(toks):
        if k and toks[k - 1] in ("-c", "eval") and GH_SUB_RE.search(t):
            raise Block("文字列の中の gh の操作は読めません")
    for sep, seg in _split_segments(toks):
        if seg and seg[0] == "cd" and len(seg) > 1:
            p = os.path.expanduser(seg[1])
            if p.startswith("/"):
                cwd = p
        rest = _gh_target(seg)
        if rest is not None:
            i = 0
            while i < len(rest):
                t = rest[i]
                val, kind = None, None
                if t in ("--body", "-b"):
                    kind, val = "body", (rest[i + 1] if i + 1 < len(rest) else None)
                    i += 1
                elif t.startswith("--body="):
                    kind, val = "body", t[7:]
                elif t in ("--body-file", "-F"):
                    kind, val = "file", (rest[i + 1] if i + 1 < len(rest) else None)
                    i += 1
                elif t.startswith("--body-file="):
                    kind, val = "file", t[12:]
                i += 1
                if kind is None:
                    continue
                if val is None:
                    raise Block("本文の指定の値がありません")
                if kind == "file":
                    if val == "-":
                        _stdin_source(seg, sep, prev_seg, cwd, files, heredocs)
                    else:
                        files.append(_plain_path(val, cwd))
                else:
                    if "<<" in val:
                        continue  # heredoc の本文は (a) に含まれる
                    cm = re.search(r"\$\(\s*cat\s+([^\s)]+)\s*\)", val)
                    if cm:
                        files.append(_plain_path(cm.group(1), cwd))
                    elif re.search(r"\$[A-Za-z_{(]|`", val):
                        raise Block("本文の出どころが決まりません (変数・コマンド置換)")
            for j, t in enumerate(seg):  # --body "$(cat f)" 以外の < file も読む
                if t == "<" and j + 1 < len(seg):
                    files.append(_plain_path(seg[j + 1], cwd))
        prev_sep, prev_seg = sep, seg
    for cm in re.finditer(r"\$\(\s*cat\s+([^\s)]+)\s*\)", base):
        files.append(_plain_path(cm.group(1), cwd))
    seen = set()
    for f in files:
        if f in seen:
            continue
        seen.add(f)
        entries.extend(read_body_file(f))  # (b)(c) 読めなければ Block
    return entries


# ---------------------------------------------------------------- main

def run(payload):
    if not isinstance(payload, dict) or payload.get("tool_name") != "Bash":
        return 0
    ti = payload.get("tool_input") or {}
    cmd = ti.get("command") or ""
    pms = list(PUSH_RE.finditer(cmd))
    gh_on = GH_SUB_RE.search(cmd) is not None
    if not pms and not gh_on:
        return 0
    try:
        repos, corpus, excl, _n = load_tables()
        entries = []
        for pm in pms:
            entries.extend(check_push(cmd, pm, payload.get("cwd"), repos))
        if gh_on:
            entries.extend(check_gh(cmd, payload.get("cwd")))
        hits = find_hits(entries, corpus, excl)
    except Block as e:
        log_block("停止: %s" % e)
        sys.stderr.write("%s: 止めました (照合できないため全部拒否に倒します)。理由: %s\n" % (HOOK, e))
        return 2
    except Exception as e:  # 想定外は拒否に倒す
        log_block("停止: 想定外の失敗 %s" % type(e).__name__)
        sys.stderr.write("%s: 止めました。想定外の失敗 (%s)\n" % (HOOK, type(e).__name__))
        return 2
    if not hits:
        return 0
    kinds = sorted({p for _, _, p in hits})
    where = sorted({"%s:%d" % (l, n) for l, n, _ in hits})
    log_block("原文と同じ語句 %d 件 (%d か所): %s" % (len(kinds), len(where), ", ".join(where[:20])))
    sys.stderr.write("%s: 仕入元の原文と同じ語句を %d 件見つけたため止めました。\n" % (HOOK, len(kinds)))
    for l, n, p in hits[:30]:
        sys.stderr.write("  %s:%d 「%s」\n" % (l, n, p))
    sys.stderr.write(EXPLAIN + "\n")
    return 2


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        try:
            repos, corpus, excl, n = load_tables()
        except Block as e:
            sys.stderr.write("%s --check: NG %s\n" % (HOOK, e))
            return 2
        print("OK repos=%d corpus_files=%d corpus_bytes=%d exclusions=%d" % (len(repos), n, len(corpus.encode()), len(excl)))
        return 0
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        return 0
    return run(payload)


if __name__ == "__main__":
    sys.exit(main())
