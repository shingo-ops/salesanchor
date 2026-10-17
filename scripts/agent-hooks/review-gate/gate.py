#!/usr/bin/env python3
"""review-gate gate.py — PreToolUse
 matcher: Bash|Write|Edit|MultiEdit|NotebookEdit|Agent

 (a) 記録の置き場・記録台本への書き込み/参照を止める (R6)
 (b) reviewer を opus 以外の model で起動するのを止める (R5)
 (c) PR のマージ操作は、今の HEAD に reviewer(opus) の APPROVE 記録が無ければ止める (R1-R3)

設計: docs/handoff/review-gate-hook/design.md §5-3 / ADR-1029
止めるときは理由を stderr に出して exit 2。標準ライブラリのみ。
"""
import datetime
import json
import os
import re
import shlex
import shutil
import subprocess
import sys

PREFILTER = re.compile(r"merge|review-gate|REVIEW_GATE")
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
PYTHONS = {"python", "python3"}
SKIP_FIRST = {"(", "{", "!", "then", "do", "else", "elif", "env", "command", "exec", "time", "nohup"}
READONLY = {"grep", "rg", "cat", "head", "tail", "sed", "awk", "less", "wc", "ls", "git",
            "diff", "stat", "file", "shellcheck"}
VALUE_FLAGS = {"--repo", "-R", "--match-head-commit", "-H", "--subject", "-t", "--body", "-b",
               "--body-file", "-F", "--author-email", "-A"}
MSG_FLAGS = {"-m", "--message", "--body", "-b", "--title", "-t", "--subject"}
GUARD_WORDS = [".claude/review-gate", "review-gate/records", "review-gate/log",
               "review-gate/record.py", ".claude/scripts/review-gate",
               "REVIEW_GATE_DIR", "REVIEW_GATE_GH"]
TEST_SCRIPT = "scripts/agent-hooks/review-gate/test_review_gate.sh"
HEREDOC_RE = re.compile(r"(?<!<)<<(?!<)(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
SHELL_VALUE_OPTS = {"-o", "-O", "+o", "+O", "--rcfile", "--init-file"}
OTHER_INTERP = {"perl", "ruby", "node", "php", "osascript"}
HERESTRING_RECV = SHELLS | PYTHONS | {"perl", "ruby", "node", "php", "source", "."}
API_MERGE_RE = re.compile(r"repos/([^/\s]+)/([^/\s]+)/pulls/(\d+)/merge")
RUNNER_SCRIPTS = {"gh-pr-merge-safe.sh", "check-pr-merge-ready.py"}
ANSI_C_SHELL_RE = re.compile(r"\b(?:bash|sh|zsh|dash|ksh)\b[^\n;|&]*\s-[A-Za-z]*c[A-Za-z]*\s+\$[\"']")
MERGE_WORD_RE = re.compile(r"(?<![A-Za-z_])merge(?![A-Za-z_])|mergePullRequest|enablePullRequestAutoMerge")
URL_RE = re.compile(r"https?://([^/]+)/([^/]+)/([^/]+)/pull/(\d+)")
SEP_CHARS = set(";&|\n")
PUNCT_CHARS = set(";&|()<>\n")
MAX_DEPTH = 5

HEAD_MSG = ("review-gate: PR #%s の今の HEAD %s に Opus 審査役の APPROVE がありません。"
            "Opus の審査役（subagent_type: reviewer）を起動し、報告の最後の行に"
            "「VERDICT: APPROVE on <40桁sha> PR #%s」を書かせてください。")


class Block(Exception):
    pass


def gate_dir():
    return os.path.abspath(
        os.path.expanduser(os.environ.get("REVIEW_GATE_DIR") or "~/.claude/review-gate"))


def gh_path():
    env = os.environ.get("REVIEW_GATE_GH")
    if env:
        return env
    return shutil.which("gh") or "/opt/homebrew/bin/gh"


def log(entry):
    try:
        d = gate_dir()
        os.makedirs(d, mode=0o700, exist_ok=True)
        entry = dict(entry)
        entry["at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        entry["hook"] = "gate"
        with open(os.path.join(d, "log.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def deny(msg, **kw):
    log(dict(decision="block", reason=msg[:300], **kw))
    sys.stderr.write(msg + "\n")
    sys.exit(2)


def base(t):
    return os.path.basename(t)


def is_punct(t):
    return bool(t) and all(c in PUNCT_CHARS for c in t)


def is_sep(t):
    return bool(t) and all(c in SEP_CHARS for c in t)


def tokenize(text):
    sh = shlex.shlex(text, posix=True, punctuation_chars=";&|()<>\n")
    sh.whitespace = " \t\r"
    sh.whitespace_split = True
    sh.commenters = ""
    return list(sh)


def strip_heredocs(text, remove_unquoted):
    """(本文を除いた文字列, [{body, quoted, recv}])。終端の無い << は何もしない。"""
    lines = text.split("\n")
    out, bodies, i = [], [], 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        for m in HEREDOC_RE.finditer(line):
            tag, dash = m.group(3), m.group(1)
            found = None
            for j in range(i, len(lines)):
                cand = lines[j].lstrip("\t") if dash else lines[j]
                if cand.rstrip("\r") == tag:
                    found = j
                    break
            if found is None:
                continue
            quoted = bool(m.group(2))
            bodies.append({"body": "\n".join(lines[i:found]), "quoted": quoted,
                           "recv": line[:m.start()]})
            if quoted or remove_unquoted:
                i = found + 1
            else:
                out.extend(lines[i:found + 1])
                i = found + 1
    return "\n".join(out), bodies


def extract_subst(s):
    res, i = [], 0
    while True:
        k = s.find("$(", i)
        if k < 0:
            break
        depth, j = 1, k + 2
        while j < len(s) and depth:
            if s[j] == "(":
                depth += 1
            elif s[j] == ")":
                depth -= 1
            j += 1
        if depth:
            raise Block("`$(` に対応する `)` がありません")
        res.append(s[k + 2:j - 1])
        i = j
    if s.count("`") % 2:
        raise Block("バッククォートが対になっていません")
    res.extend(s.split("`")[1::2])
    return res


def first_word_index(toks):
    i = 0
    while i < len(toks) and (toks[i] in SKIP_FIRST or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", toks[i])):
        i += 1
    return i


def skip_flags(toks, j):
    while j < len(toks) and toks[j].startswith("-"):
        j += 2 if toks[j] in ("-R", "--repo") else 1
    return j


def find_gh_sub(toks, sub):
    """gh [flags] sub ... の sub の位置。gh pr merge は pr の後ろの merge の位置。"""
    for i, t in enumerate(toks):
        if base(t) != "gh":
            continue
        j = skip_flags(toks, i + 1)
        if sub == "api":
            if j < len(toks) and toks[j] == "api":
                return j
        elif j < len(toks) and toks[j] == "pr":
            k = skip_flags(toks, j + 1)
            if k < len(toks) and toks[k] == "merge":
                return k
    return None


def flag_value(toks, names):
    for k, t in enumerate(toks):
        if "-R" in names and len(t) > 2 and t.startswith("-R") and not t.startswith("--"):
            return t[2:]
        if t in names and k + 1 < len(toks):
            return toks[k + 1]
        for n in names:
            if n.startswith("--") and t.startswith(n + "="):
                return t[len(n) + 1:]
    return None


def parse_merge(toks, j):
    """gh pr merge の後ろを旗と位置引数に分ける。値を取る旗の値は旗に数えない。"""
    flags, pos = set(), []
    k = j + 1
    while k < len(toks):
        t = toks[k]
        if is_punct(t):
            break
        if t.startswith("-"):
            flags.add(t)
            k += 2 if (t in VALUE_FLAGS and "=" not in t) else 1
            continue
        pos.append(t)
        k += 1
    return flags, pos


def pr_from_merge(pos, wd):
    """(番号, repo, 位置引数の状態)。状態: none=無い / ok / bad=番号でも URL でもない。"""
    if not pos:
        return pr_from_file(wd), None, "none"
    t = pos[0]
    m = re.fullmatch(r"#?(\d+)", t)
    if m:
        return int(m.group(1)), None, "ok"
    m = URL_RE.match(t)
    if m:
        host, owner, name, n = m.groups()
        repo = "%s/%s" % (owner, name) if host.lower() == "github.com" else "%s/%s/%s" % (host, owner, name)
        return int(n), repo, "ok"
    return None, None, "bad"


def pr_from_file(wd):
    try:
        r = subprocess.run(["git", "-C", wd, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return None
        with open(os.path.join(r.stdout.strip(), ".pr-number"), encoding="utf-8") as f:
            s = "".join(f.read().split())
        return int(s) if re.fullmatch(r"\d+", s) else None
    except Exception:
        return None


class Ctx:
    def __init__(self, full):
        self.full = full
        self.checks = []

    def add(self, n, repo, wd, kind, auto=False, match_head=None):
        self.checks.append({"n": n, "repo": repo, "wd": wd, "kind": kind,
                            "auto": auto, "match_head": match_head})


def check_segment(toks, sep, wd, depth, ctx, top):
    i0 = first_word_index(toks)
    fw = base(toks[i0]) if i0 < len(toks) else ""
    # 入れ子 1: bash -c <文>
    for idx, t in enumerate(toks):
        if base(t) in SHELLS:
            k = idx + 1
            while k < len(toks):
                a = toks[k]
                if re.fullmatch(r"-[A-Za-z]+", a) and re.search(r"[oO]", a):
                    # -euo / -co のように o/O を含むまとまりは、その数だけ次の語を値として飛ばす
                    nval = len(re.findall(r"[oO]", a))
                    if "c" in a and k + 1 + nval < len(toks):
                        analyze(toks[k + 1 + nval], wd, depth + 1, ctx, False, False)
                        break
                    k += 1 + nval
                    continue
                if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", a) and k + 1 < len(toks):
                    analyze(toks[k + 1], wd, depth + 1, ctx, False, False)
                    break
                if a in SHELL_VALUE_OPTS:
                    k += 2
                    continue
                if not (a.startswith("-") or a.startswith("+")):
                    break
                k += 1
    # 入れ子 5: python -c / perl -e 等の本文に merge があれば止める
    for idx, t in enumerate(toks):
        if base(t) in PYTHONS or base(t) in OTHER_INTERP:
            for k in range(idx + 1, len(toks) - 1):
                if re.fullmatch(r"-[A-Za-z]*[ceE][A-Za-z]*", toks[k]) and MERGE_WORD_RE.search(toks[k + 1]):
                    raise Block("%s の -c/-e の本文に merge を含むため止めます" % base(t))
    # 入れ子 4: 標準入力から読む bash
    if fw in SHELLS:
        args = toks[i0 + 1:]
        has_c = any(re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", a) for a in args)
        file_arg = any((not a.startswith("-")) and not is_punct(a) for a in args)
        piped = sep in ("|", "|&")
        if not has_c and "<<" not in toks and (not file_arg or piped) and "merge" in ctx.full:
            raise Block("標準入力から読む shell は中身が分からないため止めます")
    # 入れ子 6: here-string (<<<) を shell / python / perl 等に渡す
    if fw in HERESTRING_RECV and "<<<" in toks:
        hk = toks.index("<<<")
        if hk + 1 < len(toks) and MERGE_WORD_RE.search(toks[hk + 1]):
            raise Block("%s に here-string で渡す文字列に merge を含むため止めます" % fw)
    msg_idx = {k + 1 for k, t in enumerate(toks) if t in MSG_FLAGS}
    # 入れ子 7: xargs の後ろの merge 系は番号が後から足されうるので常に止める
    for xk, xt in enumerate(toks):
        if base(xt) == "xargs":
            rest = toks[xk + 1:]
            if find_gh_sub(rest, "merge") is not None or any(base(r) in RUNNER_SCRIPTS for r in rest):
                raise Block("xargs の後ろの merge 操作は PR 番号が分からないため止めます")
    repo = flag_value(toks, ("-R", "--repo"))
    # 1. gh pr merge
    m = find_gh_sub(toks, "merge")
    mflags, mpos = parse_merge(toks, m) if m is not None else (set(), [])
    if m is not None:
        nrepo = sum(1 for t in toks if t in ("--repo", "-R") or t.startswith("--repo=")
                    or (t.startswith("-R") and len(t) > 2 and not t.startswith("--")))
        nhead = sum(1 for t in toks if t == "--match-head-commit" or t.startswith("--match-head-commit="))
        if nrepo > 1 or nhead > 1:
            raise Block("--repo / -R / --match-head-commit が 2 回以上あるため止めます")
    if m is not None and ("--disable-auto" not in mflags or len(mpos) > 1):
        n, url_repo, _state = pr_from_merge(mpos, wd)
        if len(mpos) > 1:
            n = None
        if url_repo:
            if repo and repo.lower() != url_repo.lower():
                raise Block("URL の owner/repo と --repo/-R の値が一致しないため止めます")
            repo = url_repo
        ctx.add(n, repo, wd, "gh pr merge", "--auto" in toks,
                flag_value(toks, ("--match-head-commit",)))
    # 2. gh-pr-merge-safe.sh / 3. check-pr-merge-ready.py
    if fw not in READONLY:
        for k, t in enumerate(toks):
            if k in msg_idx:
                continue
            if base(t) == "gh-pr-merge-safe.sh":
                ctx.add(pr_from_file(wd), None, wd, "gh-pr-merge-safe.sh")
            elif base(t) == "check-pr-merge-ready.py":
                nxt = toks[k + 1] if k + 1 < len(toks) else ""
                ctx.add(int(nxt) if re.fullmatch(r"\d+", nxt) else None, None, wd,
                        "check-pr-merge-ready.py")
    # 4. gh api .../merge
    if find_gh_sub(toks, "api") is not None and any(
            ("/merge" in t or "mergePullRequest" in t or "enablePullRequestAutoMerge" in t)
            for t in toks):
        mm = next((API_MERGE_RE.search(t) for t in toks if API_MERGE_RE.search(t)), None)
        ctx.add(int(mm.group(3)) if mm else None,
                "%s/%s" % (mm.group(1), mm.group(2)) if mm else None, wd, "gh api merge")
    # 5. curl で api.github.com の merge
    if any(base(t) == "curl" for t in toks) and any("api.github.com" in t for t in toks) \
            and any("/merge" in t for t in toks):
        mm = next((API_MERGE_RE.search(t) for t in toks if API_MERGE_RE.search(t)), None)
        ctx.add(int(mm.group(3)) if mm else None,
                "%s/%s" % (mm.group(1), mm.group(2)) if mm else None, wd, "curl merge")


def recv_first_word(recv):
    piece = re.split(r"[;&|]", recv)[-1]
    try:
        toks = shlex.split(piece, comments=False)
    except ValueError:
        toks = piece.split()
    i = first_word_index(toks)
    return base(toks[i]) if i < len(toks) else ""


def analyze(text, wd, depth, ctx, top, lenient):
    if depth > MAX_DEPTH:
        raise Block("入れ子が深すぎます")
    if "merge" in text and ANSI_C_SHELL_RE.search(text):
        raise Block("shell -c に $'...' / $\"...\" 形式の引用があり中身を読めないため止めます")
    stripped, bodies = strip_heredocs(text, True)
    s2, _ = strip_heredocs(text, False)
    try:
        toks = tokenize(stripped)
    except ValueError:
        if lenient:
            if "merge" in text:
                raise Block("読めない文字列に merge を含むため止めます")
            return
        raise Block("command を shell として読めません（引用符の閉じ忘れ等）")
    segs, cur, sep = [], [], ""
    for t in toks:
        if is_sep(t):
            if cur:
                segs.append((sep, cur))
                cur = []
            sep = t
        else:
            cur.append(t)
    if cur:
        segs.append((sep, cur))
    seg_wd = wd
    wd_unknown = False
    for sep, st in segs:
        i0 = first_word_index(st)
        exempt = len(st) >= 2 and st[0] == "bash" and st[1] == TEST_SCRIPT
        if top and not exempt:
            joined = re.sub(r"/+", "/", " ".join(st))
            for w in guard_words():
                if w in joined:
                    raise Block("review-gate の記録・台本には触れません（%s）" % w)
        word = st[i0] if i0 < len(st) else ""
        if word in ("cd", "pushd") and i0 + 1 < len(st):
            dest = st[i0 + 1]
            if dest == "-":
                wd_unknown = True
                continue
            if under_gate_dir(dest, seg_wd):
                raise Block("review-gate の記録の置き場へ %s した後のコマンドは止めます" % word)
            seg_wd = os.path.abspath(os.path.join(seg_wd, os.path.expanduser(dest)))
            continue
        if word == "popd":
            wd_unknown = True
            continue
        before = len(ctx.checks)
        check_segment(st, sep, seg_wd, depth, ctx, top)
        if wd_unknown and len(ctx.checks) > before:
            raise Block("popd / cd - の後は作業場所が分からないため、マージ操作は止めます")
    for b in bodies:
        rfw = recv_first_word(b["recv"])
        if top:
            for w in guard_words():
                if w in re.sub(r"/+", "/", b["body"]):
                    raise Block("review-gate の記録・台本には触れません（%s）" % w)
        if rfw in SHELLS:
            analyze(b["body"], seg_wd, depth + 1, ctx, False, False)
        elif rfw in PYTHONS or rfw in OTHER_INTERP:
            if MERGE_WORD_RE.search(b["body"]):
                raise Block("%s に渡す本文に merge を含むため止めます" % rfw)
            if rfw in PYTHONS:
                analyze(b["body"], seg_wd, depth + 1, ctx, False, True)
    for inner in extract_subst(s2):
        analyze(inner, seg_wd, depth + 1, ctx, False, False)


def guard_words():
    return GUARD_WORDS + [gate_dir()]


def gh_view(n, repo, wd):
    if not os.path.isdir(wd):
        return None
    cmd = [gh_path(), "pr", "view", str(n), "--json", "headRefOid,url"]
    if repo:
        cmd += ["--repo", repo]
    try:
        r = subprocess.run(cmd, cwd=wd, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return None
        j = json.loads(r.stdout)
        m = re.match(r"https?://[^/]+/([^/]+)/([^/]+)/pull/\d+", j.get("url") or "")
        if not m or not re.fullmatch(r"[0-9a-f]{40}", j.get("headRefOid") or ""):
            return None
        return j["headRefOid"], m.group(1), m.group(2)
    except Exception:
        return None


def resolve(ctx):
    seen = {}
    if ctx.checks and re.search(r"(?<![A-Za-z0-9_])GH_(?:REPO|HOST)=", ctx.full):
        deny("review-gate: GH_REPO / GH_HOST の代入があるため止めます"
             "（gh の照合先が変わるので APPROVE 記録と照合できません）。", kind="GH_REPO")
    for c in ctx.checks:
        if c["n"] is None:
            deny("review-gate: PR 番号が取れないため止めます。PR 番号を明示してください"
                 "（Opus の審査役の APPROVE 記録を PR 番号と HEAD で照合します）。",
                 kind=c["kind"])
        key = (c["n"], c["repo"], c["wd"])
        if key not in seen:
            seen[key] = gh_view(c["n"], c["repo"], c["wd"])
        v = seen[key]
        if v is None:
            deny("review-gate: PR #%s の HEAD を gh で確認できないため止めます"
                 "（Opus の審査役の APPROVE を確認できません。再実行してください）。" % c["n"],
                 pr=c["n"], kind=c["kind"])
        head, owner, repo = v
        rec = os.path.join(gate_dir(), "records", "%s__%s-%s-%s.json" % (owner, repo, c["n"], head))
        ok = False
        try:
            with open(rec, encoding="utf-8") as f:
                r = json.load(f)
            ok = r.get("verdict") == "APPROVE" and r.get("head") == head
        except Exception:
            ok = False
        if not ok:
            deny(HEAD_MSG % (c["n"], head[:9], c["n"]), pr=c["n"], head=head, kind=c["kind"])
        if c["auto"] and c["match_head"] != head:
            deny("review-gate: --auto は --match-head-commit <今の HEAD 40桁> と一緒でなければ使えません"
                 "（PR #%s の HEAD %s）。Opus の審査役の APPROVE 済みの HEAD を指定してください。"
                 % (c["n"], head[:9]), pr=c["n"], head=head, kind=c["kind"])
        log({"decision": "allow", "pr": c["n"], "head": head, "kind": c["kind"]})


def under_gate_dir(path, cwd):
    p = os.path.expanduser(path)
    if not os.path.isabs(p):
        p = os.path.join(cwd, p)
    g = gate_dir()
    for a, b in ((os.path.abspath(p), g), (os.path.realpath(p), os.path.realpath(g))):
        if a == b or a.startswith(b + os.sep):
            return True
    return False


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tool = data.get("tool_name")
    ti = data.get("tool_input") or {}
    cwd = data.get("cwd") or os.getcwd()
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        p = ti.get("notebook_path") if tool == "NotebookEdit" else ti.get("file_path")
        if p and under_gate_dir(str(p), cwd):
            deny("review-gate: 記録の置き場には書けません（%s）。" % p, tool=tool)
        return 0
    if tool in ("Agent", "Task"):
        model = ti.get("model")
        if ti.get("subagent_type") == "reviewer" and model and "opus" not in str(model).lower():
            deny("review-gate: reviewer は model opus でだけ起動できます（指定: %s）。"
                 "model を指定しないか opus にしてください。" % model, tool=tool)
        return 0
    if tool != "Bash":
        return 0
    command = ti.get("command") or ""
    if not (PREFILTER.search(command) or gate_dir() in command):
        return 0
    ctx = Ctx(command)
    try:
        analyze(command, cwd, 0, ctx, True, False)
    except Block as e:
        deny("review-gate: %s。（マージには Opus の審査役の APPROVE が要ります。"
             "Opus の審査役を起動してください）" % e, tool="Bash")
    except Exception as e:
        deny("review-gate: 内部エラー（%s）のため止めます。Opus の審査役の APPROVE を確認できません。"
             % type(e).__name__, tool="Bash")
    resolve(ctx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
