#!/usr/bin/env python3
"""confidential-quote-guard guard.py — PreToolUse (matcher: Bash)

仕入元の投稿の原文を、「」『』の中に書き写したまま公開の置き場へ送るのを、送る前に止める。
  - git push        : 決まった形 `git -C <絶対パス> push [-u] origin <ref>` だけ通し、送る差分の追加行を照らす
  - gh pr create/edit/comment/review, gh issue create/comment : 本文 (--body-file <絶対パス> か 一重引用符の --body だけ通す)
  - 決まりの外の形は、照らせないので止める (命令文から作業場所や出どころを推し量らない)

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
import math
import time
import unicodedata

HOOK = "confidential-quote-guard"
MIN_LEN = 4

GH_ACTIONS = {"pr": {"create", "edit", "comment", "review"}, "issue": {"create", "comment"}}
PHRASE_RES = (re.compile(r"「([^「」\n]*)」"), re.compile(r"『([^『』\n]*)』"))
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


def load_repos():
    """照らす repo の表だけ読む (原文の写しは読まない)。"""
    repos = set()
    for ln in _read_lines(os.path.join(table_dir(), "confidential-corpus.conf")):
        s = ln.strip()
        if s.startswith("repo:"):
            repos.add(s[5:].strip())
    return repos


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
    max_age = 2.0
    try:  # 環境変数は短くする方向だけ効く (試験用)。nan・inf・負・数でない値は無視して 2 日
        v = float(os.environ.get("CONFID_CORPUS_MAX_AGE_DAYS", "2"))
        if math.isfinite(v) and v > 0:
            max_age = min(v, 2.0)
    except ValueError:
        pass
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
# 方針: 命令文から作業場所や本文の出どころを推し量らない。
# git push と gh の本文の操作は「決まった形」だけを通し、それ以外はすべて止める。

PUSH_MSG = "git push は `git -C <worktree の絶対パス> push -u origin <ブランチ>` の形で、ほかの命令とつながずに単独で流してください"
GH_MSG = "本文は Write で作ったファイルを `--body-file <絶対パス>` で渡してください (または一重引用符の `--body '...'`)。ほかの命令とつながず単独で流してください"
SAFE_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_@%+=:,./-")
SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "eval", "source", "."}
REF_RE = re.compile(r"HEAD|[A-Za-z0-9][A-Za-z0-9/._-]*")
REDIR_TAIL_RE = re.compile(r"\s+(?:2>&1|>>?\s*/[A-Za-z0-9_@%+=:,./-]+)\s*$")
GH_VALUE_OPTS = {"-t", "--title", "-B", "--base", "-H", "--head", "-R", "--repo", "-a", "--assignee",
                 "-l", "--label", "-m", "--milestone", "-p", "--project", "-r", "--reviewer"}
GH_BAD_OPTS = {"--fill", "--fill-first", "--fill-verbose", "--editor", "-e", "--web", "-w", "--template", "-T", "--recover"}
GH_BODY_STR = {"--body", "-b"}
GH_BODY_FILE = {"--body-file", "-F"}


def _lex(cmd):
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    return list(lex)


def detect(cmd):
    """字句として git ... push / gh pr|issue ... が現れるか -> (push, gh)。読めないときは粗い目印で判断する。"""
    pre_push = re.search(r"\bgit\b[\s\S]*\bpush\b", cmd) is not None
    pre_gh = re.search(r"\bgh\b[\s\S]*\b(?:pr|issue)\b", cmd) is not None
    if not pre_push and not pre_gh:
        return False, False
    try:
        toks = _lex(cmd)
    except ValueError:
        return pre_push, pre_gh
    base = [t.rsplit("/", 1)[-1] for t in toks]
    if any(b in SHELLS for b in base) and any(re.fullmatch(r"-\w*c\w*", t) for t in toks) or "eval" in base:
        return pre_push, pre_gh  # sh -c "..." など。決まった形ではないので、後で止まる
    push = any(b == "git" and "push" in toks[i + 1:] for i, b in enumerate(base))
    gh = False
    for i, b in enumerate(base):
        if b != "gh":
            continue
        for a in range(i + 1, len(toks) - 1):
            if toks[a] in GH_ACTIONS and toks[a + 1] in GH_ACTIONS[toks[a]]:
                gh = True
    return push, gh


def scan_words(cmd):
    """決まった形の字句分け -> [(値, 元の字面)]。引用の外は安全な文字だけ。それ以外・閉じない引用は Block。"""
    words, i, n = [], 0, len(cmd)
    while i < n:
        if cmd[i] in " \t":
            i += 1
            continue
        start, val = i, []
        while i < n and cmd[i] not in " \t":
            c = cmd[i]
            if c == "'":
                j = cmd.find("'", i + 1)
                if j < 0:
                    raise Block("引用が閉じていません")
                val.append(cmd[i + 1:j])
                i = j + 1
            elif c == '"':
                j, buf = i + 1, []
                while j < n and cmd[j] != '"':
                    if cmd[j] in "$`\\!":
                        raise Block("二重引用符の中に展開文字があります")
                    buf.append(cmd[j])
                    j += 1
                if j >= n:
                    raise Block("引用が閉じていません")
                val.append("".join(buf))
                i = j + 1
            elif c in SAFE_CHARS:
                val.append(c)
                i += 1
            else:
                raise Block("引用の外に決まりの外の文字があります")
        words.append(("".join(val), cmd[start:i]))
    return words


def strict_words(cmd):
    s = cmd.strip()
    while True:
        s2 = REDIR_TAIL_RE.sub("", s)
        if s2 == s:
            break
        s = s2
    words = scan_words(s)
    try:
        toks = _lex(s)
    except ValueError:
        raise Block("字句に分けられません")
    if toks != [w[0] for w in words]:
        raise Block("字句の分け方が食い違います")
    return words


def git(cwd, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, text=True, env=env)


def repo_slug(cwd):
    r = git(cwd, "remote", "get-url", "origin")
    if r.returncode != 0:
        return None
    url = r.stdout.strip()
    if url.endswith(".git"):
        url = url[:-4]
    parts = [x for x in re.split(r"[/:]", url) if x]
    return "/".join(parts[-2:]) if len(parts) >= 2 else None


def added_lines(cwd, base, sha):
    """base から sha までの追加行 -> [(file, lineno, text)]。取れなければ Block。"""
    r = git(cwd, "-c", "core.quotePath=false", "diff", "--no-color", "--no-ext-diff", "-U0", base, sha)
    if r.returncode != 0:
        raise Block("差分が取れません")
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


def check_push(words, repos, matched):
    v = [w[0] for w in words]
    ok = (len(v) in (6, 7) and v[0] == "git" and v[1] == "-C" and v[2].startswith("/") and v[3] == "push"
          and (len(v) == 6 or v[4] in ("-u", "--set-upstream")) and v[-2] == "origin"
          and REF_RE.fullmatch(v[-1]) is not None and ".." not in v[-1])
    if not ok:
        raise Block(PUSH_MSG)
    path, ref = v[2], v[-1]
    if not os.path.isdir(path):
        raise Block("push の場所が存在しません")
    if git(path, "rev-parse", "--show-toplevel").returncode != 0:
        raise Block("push の場所が git の repo ではありません")
    slug = repo_slug(path)
    if slug is None or slug not in repos:
        return []  # 表に無い repo の push は照らさずに通す
    matched.append(slug)
    if git(path, "rev-parse", "--verify", "--quiet", "origin/main^{commit}").returncode != 0:
        raise Block("表に並んだ repo (%s) に origin/main がありません" % slug)
    r = git(path, "rev-parse", "--verify", "--quiet", ref + "^{commit}")
    if r.returncode != 0:
        raise Block("送るブランチ %s が見つかりません" % ref)
    sha = r.stdout.strip()
    name = ref
    if ref == "HEAD":
        s = git(path, "symbolic-ref", "--quiet", "--short", "HEAD")
        name = s.stdout.strip() if s.returncode == 0 else None
    base = "origin/main"
    if name and git(path, "rev-parse", "--verify", "--quiet", "refs/remotes/origin/%s^{commit}" % name).returncode == 0:
        base = "refs/remotes/origin/%s" % name
    mb = git(path, "merge-base", base, sha)
    if mb.returncode != 0 or not mb.stdout.strip():
        raise Block("送る範囲の起点が決まりません")
    return added_lines(path, mb.stdout.strip(), sha)


def read_body_file(p):
    if not p.startswith("/") or p.startswith(("/dev/", "/proc/")) or not os.path.isfile(p):
        raise Block(GH_MSG)
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return [(p, i + 1, t) for i, t in enumerate(f.read().split("\n"))]
    except OSError as e:
        raise Block("本文のファイルが読めません: %s (%s)" % (os.path.basename(p), e.strerror))


def check_gh(words):
    v, raws = [w[0] for w in words], [w[1] for w in words]
    if len(v) < 3 or v[0] != "gh" or v[1] not in GH_ACTIONS or v[2] not in GH_ACTIONS[v[1]]:
        raise Block(GH_MSG)
    body, i = None, 3
    while i < len(v):
        t = v[i]
        key, eq, val = t.partition("=") if t.startswith("--") else (t, "", "")
        if t in GH_BAD_OPTS or key in GH_BAD_OPTS:
            raise Block(GH_MSG)
        if key in GH_BODY_STR or key in GH_BODY_FILE:
            if body is not None:
                raise Block(GH_MSG)
            if eq:
                value, raw, i = val, raws[i].split("=", 1)[1], i + 1
            elif i + 1 < len(v):
                value, raw, i = v[i + 1], raws[i + 1], i + 2
            else:
                raise Block(GH_MSG)
            body = ("str" if key in GH_BODY_STR else "file", value, raw)
            continue
        if re.fullmatch(r"-[^-].+", t):
            raise Block(GH_MSG)  # 短い指定の束ね書きは読み分けない
        i += 2 if t in GH_VALUE_OPTS else 1
    if body is None:
        return []
    kind, value, raw = body
    if kind == "str":
        if re.fullmatch(r"'[^']*'", raw) is None:
            raise Block(GH_MSG)
        return [("本文", n + 1, t) for n, t in enumerate(value.split("\n"))]
    return read_body_file(value)


def run(payload):
    if not isinstance(payload, dict) or payload.get("tool_name") != "Bash":
        return 0
    ti = payload.get("tool_input") or {}
    cmd = ti.get("command") or ""
    push, gh = detect(cmd)
    if not push and not gh:
        return 0
    try:
        repos = load_repos()
        entries, matched = [], []
        try:
            words = strict_words(cmd)
        except Block as e:
            raise Block(PUSH_MSG if push else GH_MSG) from e
        if push and gh:
            raise Block(PUSH_MSG)
        if push:
            entries.extend(check_push(words, repos, matched))
            if not matched:
                return 0  # 照らす repo の push ではない: 写しが古くても止めない
        else:
            entries.extend(check_gh(words))
        _r, corpus, excl, _n = load_tables()
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
