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
SHELLS = {"bash", "sh", "zsh"}
PYTHONS = {"python", "python3"}
SKIP_FIRST = {"(", "{", "!", "then", "do", "else", "elif", "env", "command", "exec", "time", "nohup"}
READONLY = {"grep", "rg", "cat", "head", "tail", "sed", "awk", "less", "wc", "ls", "git",
            "diff", "stat", "file", "shellcheck"}
VALUE_FLAGS = {"--repo", "-R", "--match-head-commit", "--subject", "-t", "--body", "-b",
               "--body-file", "-F", "--author-email", "-A"}
MSG_FLAGS = {"-m", "--message", "--body", "-b", "--title", "-t", "--subject"}
GUARD_WORDS = [".claude/review-gate", "review-gate/records", "review-gate/log",
               "review-gate/record.py", ".claude/scripts/review-gate",
               "REVIEW_GATE_DIR", "REVIEW_GATE_GH"]
TEST_SCRIPT = "scripts/agent-hooks/review-gate/test_review_gate.sh"
HEREDOC_RE = re.compile(r"(?<!<)<<(?!<)(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
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
        if t in names and k + 1 < len(toks):
            return toks[k + 1]
        for n in names:
            if n.startswith("--") and t.startswith(n + "="):
                return t[len(n) + 1:]
    return None


def pr_from_merge(toks, j):
    k = j + 1
    while k < len(toks):
        t = toks[k]
        if is_punct(t):
            return None
        if t.startswith("-"):
            k += 2 if (t in VALUE_FLAGS and "=" not in t) else 1
            continue
        m = re.fullmatch(r"#?(\d+)", t) or re.search(r"/pull/(\d+)", t)
        return int(m.group(1)) if m else None
    return None


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
            for k in range(idx + 1, len(toks)):
                a = toks[k]
                if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", a) and k + 1 < len(toks):
                    analyze(toks[k + 1], wd, depth + 1, ctx, False, False)
                    break
                if not a.startswith("-"):
                    break
    # 入れ子 4: 標準入力から読む bash
    if fw in SHELLS:
        args = toks[i0 + 1:]
        has_c = any(re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", a) for a in args)
        file_arg = any((not a.startswith("-")) and not is_punct(a) for a in args)
        piped = sep in ("|", "|&")
        if not has_c and "<<" not in toks and (not file_arg or piped) and "merge" in ctx.full:
            raise Block("標準入力から読む shell は中身が分からないため止めます")
    msg_idx = {k + 1 for k, t in enumerate(toks) if t in MSG_FLAGS}
    repo = flag_value(toks, ("-R", "--repo"))
    # 1. gh pr merge
    m = find_gh_sub(toks, "merge")
    if m is not None and "--disable-auto" not in toks:
        n = pr_from_merge(toks, m) or pr_from_file(wd)
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
        mm = next((re.search(r"pulls/(\d+)/merge", t) for t in toks
                   if re.search(r"pulls/(\d+)/merge", t)), None)
        ctx.add(int(mm.group(1)) if mm else None, None, wd, "gh api merge")
    # 5. curl で api.github.com の merge
    if any(base(t) == "curl" for t in toks) and any("api.github.com" in t for t in toks) \
            and any("/merge" in t for t in toks):
        mm = next((re.search(r"pulls/(\d+)/merge", t) for t in toks
                   if re.search(r"pulls/(\d+)/merge", t)), None)
        ctx.add(int(mm.group(1)) if mm else None, None, wd, "curl merge")


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
    for sep, st in segs:
        i0 = first_word_index(st)
        exempt = len(st) >= 2 and st[0] == "bash" and st[1].endswith(TEST_SCRIPT)
        if top and not exempt:
            joined = " ".join(st)
            for w in guard_words():
                if w in joined:
                    raise Block("review-gate の記録・台本には触れません（%s）" % w)
        if i0 < len(st) and st[i0] == "cd" and i0 + 1 < len(st):
            seg_wd = os.path.abspath(os.path.join(seg_wd, os.path.expanduser(st[i0 + 1])))
            continue
        check_segment(st, sep, seg_wd, depth, ctx, top)
    for b in bodies:
        rfw = recv_first_word(b["recv"])
        if top:
            for w in guard_words():
                if w in b["body"]:
                    raise Block("review-gate の記録・台本には触れません（%s）" % w)
        if rfw in SHELLS:
            analyze(b["body"], seg_wd, depth + 1, ctx, False, False)
        elif rfw in PYTHONS:
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
