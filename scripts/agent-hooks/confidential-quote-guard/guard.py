#!/usr/bin/env python3
"""confidential-quote-guard guard.py — PreToolUse (matcher: Bash)

仕入元の投稿の原文を、「」『』の中に書き写したまま公開の置き場へ送るのを、送る前に止める。
  - git push        : 決まった形 `git -C <絶対パス> push [-u] origin <ref>` だけ通し、送る差分の追加行を照らす
  - gh pr create/edit/comment/review/merge, gh issue create/edit/comment, gh release create/edit, gh repo edit : 本文・題名・説明 (--body-file <絶対パス> か 一重引用符の --body だけ通す)。gh gist は止める
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

_BT = ({"--body", "-b"}, {"--body-file", "-F"}, {"--title", "-t", "--subject"})
_REL = ({"--notes", "-n"}, {"--notes-file", "-F"}, {"--title", "-t"})
# (gh の群, 操作) -> (本文の印, 本文ファイルの印, 題名の印)。印は gh の操作ごとに違う (-d は repo edit では説明、release では draft)
GH_OPS = {
    ("pr", "create"): _BT, ("pr", "edit"): _BT, ("pr", "comment"): _BT, ("pr", "review"): _BT, ("pr", "merge"): _BT,
    ("issue", "create"): _BT, ("issue", "edit"): _BT, ("issue", "comment"): _BT,
    ("release", "create"): _REL, ("release", "edit"): _REL,
    ("repo", "edit"): ({"--description", "-d"}, set(), set()),
}
# 本文の印は持たないが、repo の外へ何かを送る操作 (添付ファイルなど)。見つけたら必ず止める
GH_STOP = {("release", "upload")}
GH_ACTIONS = {}
for _g, _a in list(GH_OPS) + list(GH_STOP):
    GH_ACTIONS.setdefault(_g, set()).add(_a)
# release create/edit の値を取る印。これ以外の印は値を取らないものとして数え、残りの位置引数 (タグ名以外 = 添付ファイル) は止める
REL_VALUE_OPTS = {"--notes", "-n", "--notes-file", "-F", "--title", "-t", "--target", "--discussion-category", "--notes-start-tag"}
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
            repos.add(s[5:].strip().lower())
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

PUSH_MSG = "git push は `git -C <worktree の絶対パス> push -u origin <ブランチ>` の形で、ほかの命令とつなげずに単独で流してください"
GH_MSG = "本文は Write で作ったファイルを `--body-file <絶対パス>` で渡してください (または一重引用符の `--body '...'`)。ほかの命令とつなげずに単独で流してください"
SAFE_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_@%+=:,./-")
SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "eval", "source", "."}
REF_RE = re.compile(r"HEAD|[A-Za-z0-9][A-Za-z0-9/._-]*")
REDIR_TAIL_RE = re.compile(r"\s+(?:2>&1|>>?\s*/[A-Za-z0-9_@%+=:,./-]+)\s*$")
GH_BAD_OPTS = {"--notes-from-tag", "-f", "--fill", "--fill-first", "--fill-verbose", "--editor", "-e", "--web", "-w", "--template", "-T", "--recover"}
HIST_MSG = ("送る途中の commit に書き写しがあります。新しい commit で消しても履歴に残って送られます。"
            "該当の commit を書き直すか、origin/main から作り直したブランチで送ってください。書き直しは Opus の指示を待ってください。")
PUSH_CFG_RE = r"^(alias\.|remote\..*\.pushurl|url\..*\.pushinsteadof)"
SCOPED_CFG_RE = (r"^(alias\.|include\.|includeif\.|remote\..*\.pushurl|url\..*\.pushinsteadof"
                 r"|push\.followtags|push\.pushoption|remote\..*\.(push|mirror|tagopt))")  # --local / --worktree だけに使う
DANGER_MSG = ("repo の設定 (別名・push 先・include・タグの送り方など) や追跡ブランチ (refs/remotes)・git replace・hooks を書き換える操作、"
              "git の送信系の命令 (send-pack・http-push) は、見張りの決まりの外なので止めます。必要なら Opus に相談してください")
EXPAND_MSG = "git／gh の命令に変数や展開は使えません。値を書き出して単独で流してください"
WRITE_MARK_RE = re.compile(r"(?:>|\b(?:tee|cp|mv|sed|perl|python3?|ruby|awk|dd|install|ln|node|truncate|rsync|ed)\b)")
GIT_PATH_RE = re.compile(r"\.git(?:/[^\s'\"/;|&]+)*/(?:config(?:\.worktree)?|packed-refs)(?![\w.-])|\.git/refs/(?:remotes|replace)|\.git/hooks(?![\w.-])|config\.worktree(?![\w.-])")
SEND_RE = re.compile(r"\bgit\b[^;&|\n]*?\b(?:send-pack|http-push)\b|git-(?:send-pack|http-push)\b")
REMOTES_RE = re.compile(r"\bgit\b[^;&|\n]*?\b(?:update-ref|fetch|symbolic-ref)\b[^;&|\n]*?refs/(?:remotes|replace)")
# 書き込むと push の中身や行き先が変わる鍵。include は読む形でも止める。それ以外は --get 系・--list の読むだけを通す
CFG_INCLUDE_RE = re.compile(r"\binclude(?:if)?\.", re.I)
CFG_KEY_RE = re.compile(r"\bremote\.[^\s=]*\.(?:url|pushurl|push|mirror|tagopt)\b|\bpush\.(?:followtags|pushoption)\b"
                        r"|\burl\.[^\s=]*\.(?:insteadof|pushinsteadof)\b|\bcore\.hookspath\b", re.I)
CFG_READ_RE = re.compile(r"\s(?:--get\S*|--list|-l)(?:\s|$)")
GITGH_RE = re.compile(r"(?<![A-Za-z0-9_-])(?:git|gh)(?![A-Za-z0-9_-])")
OP_TOK_RE = re.compile(r"^[;&|()<>]+$")
WRAPPERS = {"env", "command", "exec", "time", "nohup", "sudo", "xargs", "builtin", "nice", "timeout", "stdbuf", "then", "do", "else", "if", "!"}
GIT_OPT_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix", "--config-env"}


def _lex(cmd):
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    return list(lex)


def _try_lex(cmd):
    try:
        return _lex(cmd)
    except ValueError:
        return None


def expansion(cmd, toks):
    """git／gh が出るのに、変数・展開・行末の \\ で字を隠せる形 -> True。見分けず止める (止める側に倒す)。
    生の文字と字句の両方に git／gh (G=git のような代入の右辺も含む) が出て、$・バッククォート・行末の \\ のどれかを含むとき。
    ほかに、命令の位置の字句 (代入を外した最初の字句) が $ やバッククォートで始まるとき。"""
    loose = cmd + "\n" + re.sub(r"[\\'\"]", "", cmd) + "\n" + " ".join(toks or [])
    has_exp = "$" in cmd or "`" in cmd or "\\\n" in cmd or "\\\r\n" in cmd or re.search(r"\{[^{}\s]*,[^{}\s]*\}", cmd) is not None
    if has_exp and GITGH_RE.search(loose):
        return True
    if toks:
        at_cmd = True
        for t in toks:
            if OP_TOK_RE.match(t):
                at_cmd = True
                continue
            if not at_cmd:
                continue
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t) or t in WRAPPERS or t.startswith("-"):
                continue
            if t.startswith(("$", "`")):
                return True
            at_cmd = False
    return False


def git_subs(toks):
    """字句から git の下位命令を取り出す -> [(下位命令, 後ろの字句)]。-C などの値を取る印は飛ばす。"""
    out = []
    for i, t in enumerate(toks):
        if t.rsplit("/", 1)[-1] != "git":
            continue
        j = i + 1
        while j < len(toks) and toks[j].startswith("-"):
            j += 2 if toks[j] in GIT_OPT_ARG else 1
        if j < len(toks):
            rest = []
            for x in toks[j + 1:]:
                if OP_TOK_RE.match(x):
                    break
                rest.append(x)
            out.append((toks[j], rest))
    return out


def config_write(loose):
    """git config／git -c で、include か push の中身・行き先を変える鍵を書く形。"""
    for seg in re.split(r"[;&|\n]", loose):
        if not re.search(r"\bgit\b", seg) or not re.search(r"(?:\sconfig\b|\s-c\s)", seg + " "):
            continue
        if CFG_INCLUDE_RE.search(seg):
            return True
        if CFG_KEY_RE.search(seg) and not CFG_READ_RE.search(seg + " "):
            return True
    return False


def danger(cmd):
    """repo の設定・追跡ブランチ・送信系の命令・展開で隠す形を、見張りを通らずに書き換える/使う形 -> 理由 (無ければ None)。
    生の文字と、引用符と \\ を外した文字の両方で探す。"""
    toks = _try_lex(cmd)
    if expansion(cmd, toks):
        return EXPAND_MSG
    loose = cmd + "\n" + re.sub(r"[\\'\"]", "", cmd)
    if SEND_RE.search(loose) or REMOTES_RE.search(loose) or config_write(loose):
        return DANGER_MSG
    if GIT_PATH_RE.search(loose) and WRITE_MARK_RE.search(loose):
        return DANGER_MSG
    if toks is None or any(t.rsplit("/", 1)[-1] in SHELLS for t in toks):
        # 字句に分けられない・sh -c の中身は読まないので、生の文字で探す
        if re.search(r"\bgit\b[^;&|\n]*?\breplace\b|\bgit\b[^;&|\n]*?\bremote\b[^;&|\n]*?\b(?:set-url|add)\b", loose):
            return DANGER_MSG
    else:
        for sub, rest in git_subs(toks):
            if sub == "replace":
                return DANGER_MSG
            if sub == "remote":
                first = next((x for x in rest if not x.startswith("-")), "")
                if first in ("set-url", "add"):
                    return DANGER_MSG
    return None


def detect(cmd):
    """字句として git ... push / gh pr|issue ... が現れるか -> (push, gh)。
    見分けは、生の文字と、shlex で分けた字句 (引用符と \\ を外したもの) の両方で行う。
    字句に分けられないときは、生の文字に git か gh が含まれれば止める (push と gh の両方を立てる)。"""
    try:
        toks = _lex(cmd)
    except ValueError:
        if re.search(r"git|gh", cmd):
            return True, True
        return False, False
    base = [t.rsplit("/", 1)[-1] for t in toks]
    if (any(b in SHELLS for b in base) and any(re.fullmatch(r"-\w*c\w*", t) for t in toks)) or "eval" in base:
        loose = cmd + "\n" + re.sub(r"[\\'\"]", "", cmd)  # sh -c の中身は読まない。引用符と \\ を外した形でも目印を探す
        return (re.search(r"\bgit\b[\s\S]*\bpush\b", loose) is not None,
                re.search(r"\bgh\b[\s\S]*\b(?:pr|issue|release|repo|gist)\b", loose) is not None)
    push = any(b == "git" and "push" in toks[i + 1:] for i, b in enumerate(base))
    if not push and "git" in base:
        low = [t.lower() for t in toks]
        if any("alias." in t or "pushurl" in t or "pushinsteadof" in t for t in low) or ("set-url" in low and "--push" in low):
            push = True  # push の行き先や別名を書き換える操作: 決まった形ではないので、後で止まる
    gh = False
    for i, b in enumerate(base):
        if b != "gh":
            continue
        for a in range(i + 1, len(toks)):
            if toks[a] == "gist":
                gh = True
            if a + 1 < len(toks) and toks[a] in GH_ACTIONS and toks[a + 1] in GH_ACTIONS[toks[a]]:
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
    return subprocess.run(["git", "--no-replace-objects", "-C", cwd] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)


def norm_slug(url):
    """URL の書き方 (ssh:// git@ https://・大文字・末尾の / と .git) によらず、同じ owner/name にそろえる。"""
    url = url.strip().lower()
    while url.endswith("/"):
        url = url[:-1]
    if url.endswith(".git"):
        url = url[:-4]
    while url.endswith("/"):
        url = url[:-1]
    parts = [x for x in re.split(r"[/:]", url) if x]
    return "/".join(parts[-2:]) if len(parts) >= 2 else None


def repo_slug(cwd):
    r = git(cwd, "remote", "get-url", "origin")
    if r.returncode != 0:
        return None
    return norm_slug(r.stdout)


def commit_list(top, sha, excludes):
    """送る commit の一覧 (excludes から届くものは除く)。作業場所の設定に左右されない下回りの命令で取る。"""
    r = git(top, "rev-list", sha, "--not", *excludes)
    if r.returncode != 0:
        raise Block("送る commit の一覧が取れません")
    return [x for x in r.stdout.split("\n") if re.fullmatch(r"[0-9a-f]{40}", x)]


def added_lines(top, commits):
    """送る commit のそれぞれが足した行 + 追加・改名したファイルの名前 -> [(場所, 行, 文)]。取れなければ Block。
    merge commit は --cc で、衝突を直した行だけ見る。diff.relative など作業場所の設定に左右されないよう、
    下回りの diff-tree に --no-relative・--text・--no-textconv・--no-ext-diff・明示の prefix を付けて取る。"""
    if not commits:
        return []
    r = subprocess.run(
        ["git", "--no-replace-objects", "-C", top, "-c", "core.quotePath=false", "diff-tree", "--stdin", "-p", "--cc", "--root", "-r", "-M",
         "--text", "--no-textconv", "--no-ext-diff", "--ignore-submodules=none", "-U0",
         "--src-prefix=a/", "--dst-prefix=b/", "--no-relative", "--no-color"],
        input="\n".join(commits) + "\n", capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={k: v for k, v in os.environ.items() if not k.startswith("GIT_")})
    if r.returncode != 0:
        raise Block("差分が取れません")
    out, fname, ln, in_head, ncol = [], None, 0, False, 1
    for line in r.stdout.split("\n"):
        if re.fullmatch(r"[0-9a-f]{40}", line):
            fname, in_head = None, False
            continue
        if line.startswith(("diff --git ", "diff --cc ", "diff --combined ")):
            fname, in_head = None, True  # ファイルの見出し。この中の "+++ " だけが名前
            continue
        if in_head:
            if line.startswith(("rename to ", "copy to ")):
                out.append(("ファイル名", 0, line.split(" to ", 1)[1]))
            elif line.startswith("+++ "):
                nm = line[4:].split("\t")[0]
                if nm.startswith('"b/') and nm.endswith('"'):
                    fname = nm[3:-1]
                elif nm.startswith("b/"):
                    fname = nm[2:]
                else:
                    fname = None
                if fname:
                    out.append(("ファイル名", 0, fname))
                continue
            if not line.startswith("@@"):
                continue
            in_head = False
        m = re.match(r"(@@+) (?:-\S+ )+\+(\d+)(?:,\d+)? @@+", line)
        if m:
            ncol, ln = len(m.group(1)) - 1, int(m.group(2))
            continue
        if fname and line[:ncol].find("+") >= 0 and not line.startswith("\\"):
            out.append((fname, ln, line[ncol:]))
            ln += 1
    return out


def tag_lines(top, ref, commits):
    """注釈つきタグの文面。送る ref がタグのとき (入れ子も) と、送る範囲の commit を指すタグの中身を読む。"""
    out = []

    def body(obj, label):
        r = git(top, "cat-file", "-p", obj)
        if r.returncode != 0:
            raise Block("タグの文面が取れません")
        out.extend((label, n + 1, t) for n, t in enumerate(r.stdout.split("\n")))
        return r.stdout

    obj = git(top, "rev-parse", "--verify", "--quiet", ref).stdout.strip()
    for _ in range(10):
        if not obj:
            break
        t = git(top, "cat-file", "-t", obj).stdout.strip()
        if t != "tag":
            break
        txt = body(obj, "タグ")
        m = re.match(r"object ([0-9a-f]{40})", txt)
        obj = m.group(1) if m else ""
    if commits:
        cs = set(commits)
        r = git(top, "for-each-ref", "--format=%(objecttype) %(objectname) %(*objectname)", "refs/tags")
        if r.returncode != 0:
            raise Block("タグの一覧が取れません")
        for ln in r.stdout.split("\n"):
            f = ln.split(" ")
            if len(f) >= 3 and f[0] == "tag" and f[2] in cs:
                body(f[1], "タグ")
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
    tl = git(path, "rev-parse", "--show-toplevel")
    top = tl.stdout.strip()
    if tl.returncode != 0 or not top.startswith("/"):
        raise Block("push の場所が git の repo ではありません")
    c = git(top, "config", "--get-regexp", PUSH_CFG_RE)
    if c.returncode != 1:  # 1 = 該当なし。0 (別名や push 先の差し替えがある) とそれ以外の失敗は止める
        raise Block("この repo には別名 (alias) か push 先の差し替え (pushurl など) の設定があります")
    ext = git(top, "config", "--bool", "--get", "extensions.worktreeConfig")
    if ext.returncode not in (0, 1):
        raise Block("extensions.worktreeConfig が読めません")
    scopes = ["--local"]
    if ext.returncode == 0 and ext.stdout.strip() == "true":
        scopes.append("--worktree")  # 拡張が無いと、worktree が複数あるとき --worktree は失敗する (config.worktree も読まれない)
    for scope in scopes:  # この repo だけの設定。include 先の中身も別名を持ち込めるので include も止める
        c = git(top, "config", scope, "--get-regexp", SCOPED_CFG_RE)
        if c.returncode != 1:
            raise Block("この repo の設定 (%s) に別名・push 先の差し替え・include があります" % scope)
    rp = git(top, "for-each-ref", "--count=1", "--format=%(refname)", "refs/replace")
    if rp.returncode != 0 or rp.stdout.strip():
        raise Block("この repo には git replace の置き換え (refs/replace) があります")
    slug = repo_slug(top)
    if slug is None or slug not in repos:
        return []  # 表に無い repo の push は照らさずに通す
    matched.append(slug)
    if git(top, "rev-parse", "--verify", "--quiet", "origin/main^{commit}").returncode != 0:
        raise Block("表に並んだ repo (%s) に origin/main がありません" % slug)
    r = git(top, "rev-parse", "--verify", "--quiet", ref + "^{commit}")
    if r.returncode != 0:
        raise Block("送るブランチ %s が見つかりません" % ref)
    sha = r.stdout.strip()
    name = ref
    if ref == "HEAD":
        s = git(top, "symbolic-ref", "--quiet", "--short", "HEAD")
        name = s.stdout.strip() if s.returncode == 0 else None
    excludes = ["refs/remotes/origin/main"]
    if name and git(top, "rev-parse", "--verify", "--quiet", "refs/remotes/origin/%s^{commit}" % name).returncode == 0:
        excludes.append("refs/remotes/origin/%s" % name)
    commits = commit_list(top, sha, excludes)
    return added_lines(top, commits) + tag_lines(top, ref, commits)


def read_body_file(p):
    if not p.startswith("/") or p.startswith(("/dev/", "/proc/")) or not os.path.isfile(p):
        raise Block(GH_MSG)
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return [(p, i + 1, t) for i, t in enumerate(f.read().split("\n"))]
    except OSError as e:
        raise Block("本文のファイルが読めません: %s (%s)" % (os.path.basename(p), e.strerror))


def check_gh(words):
    """本文・題名・説明の印は、gh の操作ごとの表 (GH_OPS) で、位置や前の印に関係なく字句のどこにあっても照らす。"""
    v, raws = [w[0] for w in words], [w[1] for w in words]
    if len(v) < 3 or v[0] != "gh" or (v[1], v[2]) not in GH_OPS:  # release upload も表に無いので止まる
        raise Block(GH_MSG)  # gh gist など、表に無い操作は止める
    B_STR, B_FILE, B_TITLE = GH_OPS[(v[1], v[2])]
    body, titles, i = None, [], 3
    positional = 0
    while i < len(v):
        t = v[i]
        key, eq, val = t.partition("=") if t.startswith("--") else (t, "", "")
        if t in GH_BAD_OPTS or key in GH_BAD_OPTS:
            raise Block(GH_MSG)
        if key in B_STR or key in B_FILE or key in B_TITLE:
            if eq:
                value, raw, i = val, raws[i].split("=", 1)[1], i + 1
            elif i + 1 < len(v):
                value, raw, i = v[i + 1], raws[i + 1], i + 2
            else:
                raise Block(GH_MSG)
            if key in B_TITLE:
                titles.append(value)
                continue
            if body is not None:
                raise Block(GH_MSG)
            body = ("str" if key in B_STR else "file", value, raw)
            continue
        if re.fullmatch(r"-[^-].+", t):
            raise Block(GH_MSG)  # 短い指定の束ね書きは読み分けない
        if v[1] == "release":
            if t.startswith("-"):
                i += 2 if (t in REL_VALUE_OPTS and i + 1 < len(v)) else 1
                continue
            positional += 1
            if positional > 1:
                raise Block(GH_MSG)  # タグ名のほかの位置引数 = 添付ファイル
        i += 1
    out = [("題名", n + 1, x) for n, x in enumerate(titles)]
    if body is None:
        return out
    kind, value, raw = body
    if kind == "str":
        if re.fullmatch(r"'[^']*'", raw) is None:
            raise Block(GH_MSG)
        return out + [("本文", n + 1, t) for n, t in enumerate(value.split("\n"))]
    return out + read_body_file(value)


def run(payload):
    if not isinstance(payload, dict) or payload.get("tool_name") != "Bash":
        return 0
    ti = payload.get("tool_input") or {}
    cmd = ti.get("command") or ""
    push, gh = detect(cmd)
    dg = danger(cmd)
    if dg:
        log_block("停止: 決まりの外 (設定・追跡ブランチ・送信系)")
        sys.stderr.write("%s: 止めました。理由: %s\n" % (HOOK, dg))
        return 2
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
    if push:
        sys.stderr.write(HIST_MSG + "\n")
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
