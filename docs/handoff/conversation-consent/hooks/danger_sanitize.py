#!/usr/bin/env python3
"""danger_sanitize.py - 危険語照合の前に、誤検知の元になる「ただの文字」を取り除く。

設計承認チケット 段2（誤検知修正）。判定を緩めるのは次の範囲だけ。
  heredoc : cat / tee でファイルに書くヒアドキュメントの本文
  msg     : git commit -m / --message の引数
  gh      : gh pr ... の --body / --title の引数
  grep    : grep / egrep / fgrep / rg / ag の区間（検索語）
  rm      : rm -r の対象が全部「作業場所の下」または /private/tmp/claude-501/ の下のとき

bash -c / sh -c / eval の中身、コマンド置換（$(...) やバッククォート）を含む語は取り除かない。
解析できない（引用符が閉じていない等）ときは、元の文字列をそのまま返す（= 今までどおり照合される）。

使い方: 標準入力に PreToolUse の JSON を渡す。
  python3 danger_sanitize.py <モード,モード,...|all>
標準出力に、取り除いたあとのコマンド文字列を出す。失敗時は exit 1（呼び出し側は元の文字列を使う）。
"""
import json
import os
import pwd
import re
import shlex
import sys

# 環境変数 HOME ではなく、アカウントの本物のホームを使う（環境変数で行き先をずらせないように）
HOME = pwd.getpwuid(os.getuid()).pw_dir
WT_BASE = os.path.realpath(os.path.join(HOME, "worktrees", "salesanchor"))
TMP_BASE = "/private/tmp/claude-501"
ALL_MODES = {"heredoc", "msg", "gh", "grep", "rm"}
GREP_CMDS = {"grep", "egrep", "fgrep", "rg", "ag"}

# "$(cat <<'TAG' ... TAG\n)" 形（本文は引用符付きタグなので実行されない）
HD_SUB = re.compile(r"\$\(\s*cat\s+<<-?\s*'(\w+)'[ \t]*\n.*?\n[ \t]*\1[ \t]*\n?[ \t]*\)", re.S)
HD_HEAD = re.compile(r"<<(-?)[ \t]*(?:'([^'\n]+)'|\"([^\"\n]+)\"|\\?([A-Za-z_]\w*))")


class Seg:
    def __init__(self, start):
        self.start = start
        self.end = start
        self.words = []   # [start, end, unsafe]
        self.bodies = []  # (start, end, tag, quoted)


def lex(cmd):
    """コマンドを区間（&& || ; | 改行で区切る）と語に分ける。閉じていなければ None。"""
    n = len(cmd)
    i = 0
    segs = []
    seg = Seg(0)
    stack = []
    state = {"ws": None, "unsafe": False}
    pending = []

    def begin_word(pos):
        if state["ws"] is None:
            state["ws"] = pos

    def close_word(pos):
        if state["ws"] is not None:
            seg.words.append([state["ws"], pos, state["unsafe"]])
            state["ws"] = None
            state["unsafe"] = False

    def close_seg(pos):
        nonlocal seg
        close_word(pos)
        seg.end = pos
        segs.append(seg)
        seg = Seg(pos)

    while i < n:
        c = cmd[i]
        if stack:
            top = stack[-1]
            if top == "sq":
                if c == "'":
                    stack.pop()
                i += 1
                continue
            if top == "dq":
                if c == "\\":
                    i += 2
                    continue
                if c == '"':
                    stack.pop()
                    i += 1
                    continue
                if c == "$" and cmd.startswith("$(", i):
                    m = HD_SUB.match(cmd, i)
                    if m:
                        i = m.end()
                        continue
                    stack.append("sub")
                    state["unsafe"] = True
                    i += 2
                    continue
                if c == "$" and cmd.startswith("${", i):
                    state["unsafe"] = True
                if c == "`":
                    stack.append("bt")
                    state["unsafe"] = True
                i += 1
                continue
            if top == "bt":
                if c == "\\":
                    i += 2
                    continue
                if c == "`":
                    stack.pop()
                i += 1
                continue
            # sub: $( ... ) の中
            if c == "\\":
                i += 2
                continue
            if c == "'":
                stack.append("sq")
            elif c == '"':
                stack.append("dq")
            elif c == "$" and cmd.startswith("$(", i):
                stack.append("sub")
                i += 1
            elif c == ")":
                stack.pop()
            i += 1
            continue
        # 最上位
        if c == "\\":
            begin_word(i)
            i += 2
            continue
        if c in " \t":
            close_word(i)
            i += 1
            continue
        if c == "\n":
            close_seg(i)
            i += 1
            for head_seg, tag, quoted, dash in pending:
                body_start = i
                while i < n:
                    j = cmd.find("\n", i)
                    line = cmd[i:] if j < 0 else cmd[i:j]
                    check = line.lstrip("\t") if dash else line
                    if check == tag:
                        break
                    i = n if j < 0 else j + 1
                head_seg.bodies.append((body_start, i, tag, quoted))
                j = cmd.find("\n", i)
                i = n if j < 0 else j + 1
            pending = []
            seg.start = i
            continue
        if c == ";":
            close_seg(i)
            i += 1
            seg.start = i
            continue
        if c == "|":
            close_seg(i)
            i += 2 if cmd.startswith("||", i) else 1
            seg.start = i
            continue
        if c == "&":
            prev = cmd[i - 1] if i > 0 else ""
            if prev in "<>" or cmd.startswith("&>", i):
                begin_word(i)
                i += 1
                continue
            close_seg(i)
            i += 2 if cmd.startswith("&&", i) else 1
            seg.start = i
            continue
        if c == "'":
            begin_word(i)
            stack.append("sq")
            i += 1
            continue
        if c == '"':
            begin_word(i)
            stack.append("dq")
            i += 1
            continue
        if c == "`":
            begin_word(i)
            state["unsafe"] = True
            stack.append("bt")
            i += 1
            continue
        if c == "$" and cmd.startswith("$(", i):
            begin_word(i)
            state["unsafe"] = True
            stack.append("sub")
            i += 2
            continue
        if c == "$" and cmd.startswith("${", i):
            begin_word(i)
            state["unsafe"] = True
            i += 2
            continue
        if c == "<" and cmd.startswith("<<", i) and not cmd.startswith("<<<", i):
            m = HD_HEAD.match(cmd, i)
            if m:
                close_word(i)
                tag = m.group(2) or m.group(3) or m.group(4)
                quoted = m.group(2) is not None or m.group(3) is not None or "\\" in m.group(0)
                pending.append((seg, tag, quoted, m.group(1) == "-"))
                i = m.end()
                continue
        begin_word(i)
        i += 1
    if stack:
        return None
    close_seg(n)
    return [s for s in segs if s.words or s.bodies]


def unquote(cmd, word):
    if word[2]:
        return None
    try:
        toks = shlex.split(cmd[word[0]:word[1]])
    except ValueError:
        return None
    return "".join(toks)


def worktree_root_of(cwd):
    """cwd を含む git worktree（~/worktrees/salesanchor/<名前>/ で、.git がファイルのもの）の根。無ければ None。

    所有判定: worktree-access-guard.sh は TTY/TERM_SESSION_ID の claims.json 照合だが、
    フックのプロセスからは「このセッション」を特定できない。代わりに入力 JSON の cwd を含む worktree に限る。
    """
    if not isinstance(cwd, str) or not os.path.isabs(cwd):
        return None
    real = os.path.realpath(cwd)
    if not real.startswith(WT_BASE + "/"):
        return None
    name = real[len(WT_BASE) + 1:].split("/")[0]
    root = os.path.join(WT_BASE, name)
    return root if os.path.isfile(os.path.join(root, ".git")) else None


# 許可する文字: ASCII の [A-Za-z0-9_./@%+,:=-] と、非ASCII文字（ord>127）だけ（ADR-1033 §4-6(a)）。
# $ * ? [ ] { } ~ \ ! とバッククォート・空白・引用符は引き続き不可。
_NON_ASCII = "\u0080-\U0010ffff"
ABS_PATH_RE = re.compile(r"/[A-Za-z0-9_./@%+,:=" + _NON_ASCII + r"-]*")
REL_PATH_RE = re.compile(r"[A-Za-z0-9_@%+,:=" + _NON_ASCII + r"-][A-Za-z0-9_./@%+,:=" + _NON_ASCII + r"-]*|\.[A-Za-z0-9_./@%+,:=" + _NON_ASCII + r"-]*")
# 許可する根（根そのものは不可）。根も realpath にする（/tmp -> /private/tmp）
CC_ROOTS = [
    os.path.realpath("/tmp/CC報告ファイル"),
    os.path.realpath("/private/tmp/CC報告ファイル"),
]
ROOTS = list(dict.fromkeys([os.path.realpath(TMP_BASE)] + CC_ROOTS))
# 相対パスを許さないコマンド（cd などで行き先が変わりうる）
REL_FORBIDDEN_RE = re.compile(r"\b(?:cd|pushd|popd|eval)\b|\(|\b(?:bash|sh)\s+-c\b")
LN_RE = re.compile(r"\bln\b")


def target_ok(target, wt_root, cmd="", cwd=None):
    """rm の対象を除外してよいか。~・変数・glob・.. ・.git を含むものは不可。根そのものも不可。

    絶対パス: 根（ROOTS と作業場所）の下だけ。相対パス: cd 等が無いコマンドで、作業場所の下だけ。
    末尾が / の対象、コマンド全体に \\bln\\b があるものは不可（リンク経由の削除を塞ぐ）。
    """
    # 引用符処理で消える \\ を見逃さないよう、コマンド全体に \\ があれば不可
    if target.endswith("/") or LN_RE.search(cmd) or "\\" in cmd:
        return False
    if target.startswith("/"):
        if not ABS_PATH_RE.fullmatch(target):
            return False
        path = target
    else:
        if not REL_PATH_RE.fullmatch(target) or REL_FORBIDDEN_RE.search(cmd):
            return False
        if wt_root is None or not isinstance(cwd, str) or not os.path.isabs(cwd):
            return False
        path = os.path.join(cwd, target)
    parts = target.split("/")
    if ".." in parts or ".git" in parts:
        return False
    real = os.path.realpath(path)
    if target.startswith("/"):
        for root in ROOTS:
            if real.startswith(root + "/"):
                return ".git" not in real[len(root) + 1:].split("/")
    if wt_root is not None and real.startswith(wt_root + "/"):
        return ".git" not in real[len(wt_root) + 1:].split("/")
    return False


def rm_allowed(texts, words, wt_root, cmd="", cwd=None):
    if any(w[2] for w in words):
        return False
    recursive = False
    targets = []
    options_done = False
    skip_next = False
    for t in texts[1:]:
        if t is None:
            return False
        if skip_next:
            skip_next = False
            continue
        if re.fullmatch(r"\d*>>?", t):
            skip_next = True
            continue
        if re.match(r"\d*>>?\S", t) or re.match(r"\d*>&\d", t):
            continue
        if not options_done and t == "--":
            options_done = True
            continue
        if not options_done and t.startswith("--"):
            if t not in ("--recursive", "--force", "--verbose"):
                return False
            recursive = recursive or t == "--recursive"
            continue
        if not options_done and t.startswith("-") and len(t) > 1:
            if not re.fullmatch(r"-[rRfvi]+", t):
                return False
            recursive = recursive or ("r" in t or "R" in t)
            continue
        targets.append(t)
    if not recursive or not targets:
        return False
    return all(target_ok(t, wt_root, cmd, cwd) for t in targets)


HD_FORBIDDEN_RE = re.compile(r"\||>\(|<\(|;|&")
DEST_RE = re.compile(r"[A-Za-z0-9_./@%+,:=~-]+")


def heredoc_command_ok(cmd, segs):
    """heredoc 本文を除外してよいのは、コマンド全体（本文を除く）に | >( <( ; & && || が無いときだけ。"""
    bodies = sorted((b[0], b[1]) for s in segs for b in s.bodies)
    parts = []
    pos = 0
    for start, end in bodies:
        parts.append(cmd[pos:start])
        pos = end
    parts.append(cmd[pos:])
    return HD_FORBIDDEN_RE.search("".join(parts)) is None


def _dest_ok(path, cwd):
    if path is None or not DEST_RE.fullmatch(path):
        return False
    base = cwd if isinstance(cwd, str) and os.path.isabs(cwd) else "/"
    norm = os.path.normpath(os.path.join(base, path))
    for prefix in ("/dev", "/proc"):
        if norm == prefix or norm.startswith(prefix + "/"):
            return False
    return True


def heredoc_dest_ok(first, texts, cwd):
    """cat の書き先、tee のオプションでない引数が、すべて普通のパス（/dev/・/proc/ でない）か。"""
    if any(t is None for t in texts):
        return False
    if first == "cat":
        dests = []
        items = texts[1:]
        for i, t in enumerate(items):
            if t in (">", ">>"):
                if i + 1 >= len(items):
                    return False
                dests.append(items[i + 1])
            elif t.startswith(">") and not t.startswith(">&"):
                dests.append(t.lstrip(">"))
        return bool(dests) and all(_dest_ok(d, cwd) for d in dests)
    if first == "tee":
        dests = []
        for t in texts[1:]:
            if t.startswith("-"):
                if not re.fullmatch(r"-[aip]+|--append", t):
                    return False
                continue
            dests.append(t)
        return bool(dests) and all(_dest_ok(d, cwd) for d in dests)
    return False


def writes_file(first, texts):
    if any(t is None for t in texts):
        return False
    if first == "cat":
        return any(t.startswith(">") and not t.startswith(">&") for t in texts[1:])
    if first == "tee":
        return any(not t.startswith("-") for t in texts[1:])
    return False


def git_subcommand_index(texts):
    k = 1
    while k < len(texts) and texts[k] is not None and texts[k].startswith("-"):
        k += 2 if texts[k] in ("-C", "-c", "--git-dir", "--work-tree") else 1
    return k if k < len(texts) else None


def replace_value_after(words, texts, index, flags, long_prefixes, reps, cmd):
    """texts[index] が flags なら次の語を、long_prefixes= で始まるならその値を "" にする。"""
    t = texts[index]
    if t is None:
        return
    if t in flags and index + 1 < len(words) and not words[index + 1][2]:
        reps.append((words[index + 1][0], words[index + 1][1], '""'))
        return
    for prefix in long_prefixes:
        if t.startswith(prefix) and not words[index][2]:
            reps.append((words[index][0], words[index][1], prefix + '""'))
            return


def sanitize(cmd, cwd, modes):
    segs = lex(cmd)
    if segs is None:
        return cmd
    reps = []
    # rm の除外は絶対パスに加え、相対パスも許す（ADR-1033）。ただしコマンドに cd/pushd/popd/eval/`(`/bash -c が
    # あるときは cwd を信用できないので相対パスは不可（追跡はしない）。根は worktree・/tmp/CC報告ファイル 等。
    wt_root = worktree_root_of(cwd)
    heredoc_global_ok = heredoc_command_ok(cmd, segs)
    for seg in segs:
        words = seg.words
        texts = [unquote(cmd, w) for w in words]
        first = texts[0] if texts else None
        if first is not None:
            first = os.path.basename(first)
        if (
            "heredoc" in modes
            and heredoc_global_ok
            and seg.bodies
            and first in ("cat", "tee")
            and writes_file(first, texts)
            and heredoc_dest_ok(first, texts, cwd)
        ):
            for body_start, body_end, _tag, quoted in seg.bodies:
                body = cmd[body_start:body_end]
                if quoted or ("$(" not in body and "`" not in body and "${" not in body):
                    reps.append((body_start, body_end, ""))
        if not words:
            continue
        if "msg" in modes and first == "git":
            k = git_subcommand_index(texts)
            if k is not None and texts[k] == "commit":
                for j in range(k + 1, len(words)):
                    t = texts[j]
                    if t is None:
                        continue
                    if t == "--message" or re.fullmatch(r"-[A-Za-z]*m", t):
                        replace_value_after(words, texts, j, {t}, [], reps, cmd)
                    elif t.startswith("--message="):
                        replace_value_after(words, texts, j, set(), ["--message="], reps, cmd)
        if "gh" in modes and first == "gh" and len(texts) > 1 and texts[1] == "pr":
            for j in range(2, len(words)):
                t = texts[j]
                if t is None:
                    continue
                replace_value_after(words, texts, j, {"--body", "-b", "--title", "-t"}, ["--body=", "--title="], reps, cmd)
        if "grep" in modes and first in GREP_CMDS:
            if not any(w[2] for w in words) and not any(t is not None and t.startswith("--pre") for t in texts):
                reps.append((words[0][0], words[-1][1], " "))
        if "rm" in modes and first == "rm" and rm_allowed(texts, words, wt_root, cmd, cwd):
            reps.append((words[0][0], words[-1][1], " "))
    accepted = []
    for start, end, text in sorted(reps, key=lambda r: (r[0], r[1])):
        if accepted and start < accepted[-1][1]:
            continue
        accepted.append((start, end, text))
    out = cmd
    for start, end, text in reversed(accepted):
        out = out[:start] + text + out[end:]
    return out


def main():
    spec = sys.argv[1] if len(sys.argv) > 1 else "all"
    modes = ALL_MODES if spec == "all" else set(spec.split(","))
    payload = json.loads(sys.stdin.read())
    tool_input = payload.get("tool_input", {}) if isinstance(payload, dict) else {}
    cmd = tool_input.get("command", "")
    if not isinstance(cmd, str):
        sys.exit(1)
    cwd = tool_input.get("workdir") or payload.get("cwd") or os.getcwd()
    sys.stdout.write(sanitize(cmd, cwd, modes))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(1)
