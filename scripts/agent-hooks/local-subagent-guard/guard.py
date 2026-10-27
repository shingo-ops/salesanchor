#!/usr/bin/env python3
"""local-subagent-guard (ADR-1046) — 手元の担当（サブエージェント）の書き換え・保存・送り出しを PreToolUse で止める。
設計: docs/handoff/local-subagent-guard/design.md §5-2・§5-3。判定の例: cases.md。
"""
import datetime
import os
import re
import shlex
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
if not os.path.exists(os.path.join(_HERE, "guard_pre_tool.py")):
    sys.path.insert(0, os.path.join(_HERE, "..", "cloud"))
_IMPORT_ERR = None
try:
    import guard_pre_tool as g
except Exception as _e:  # 失敗は覚えておくだけ（本体を止めないため main で使う）
    g = None
    _IMPORT_ERR = _e

GIT_READ = {"log","status","diff","show","ls-remote","ls-files","ls-tree","rev-parse","rev-list","merge-base","merge-tree",
  "blame","grep","describe","shortlog","cat-file","for-each-ref","show-ref","name-rev","range-diff","cherry","whatchanged",
  "count-objects","version","help","var","check-ignore","check-attr","verify-commit","verify-tag","fsck","diff-tree","diff-index","diff-files"}
GIT_SUB_READ = {"stash":{"list","show"},"worktree":{"list"},"notes":{"list","show"},"commit-graph":{"verify"},
  "submodule":{"status"},"reflog":{None,"show","exists"},"remote":{None,"show","get-url"}}
GIT_OPT_ARG = {"-C","-c","--git-dir","--work-tree","--namespace","--config-env","--super-prefix"}
GIT_SAFE_C = re.compile(r"^(core\.quotepath|color\.[\w.]+)=")
LIST_FLAGS = {"-l","--list","--contains","--no-contains","--merged","--no-merged","--points-at","--all","--remotes","--show-current"}
TAG_LIST_FLAGS = LIST_FLAGS | {"-n","-v","--verify"}
BT_WRITE = {"-d","-D","-m","-M","-c","-C","-f","--delete","--move","--copy","--force","-u","--set-upstream-to","--unset-upstream","--edit-description","--track","-t","--create-reflog"}
TAG_WRITE = {"-a","--annotate","-s","--sign","-F","--file"}
CONFIG_READ = {"--get","--get-all","--get-regexp","--list","-l","--get-urlmatch"}
CONFIG_READ_SUB = {"get","list"}
CONFIG_WRITE = {"--unset","--unset-all","--add","--replace-all","--rename-section","--remove-section","-e","--edit"}
GH_READ = {"pr":{"view","list","checks","diff","status"},"issue":{"view","list","status"},"run":{"view","list","watch"},
  "repo":{"view"},"release":{"view","list"},"workflow":{"view","list"},"search":None,"auth":{"status"},"label":{"list"},
  "secret":{"list"},"variable":{"list","get"},"gist":{"view","list"},"cache":{"list"},"ruleset":{"list","view","check"},
  "status":None,"config":{"get","list"},"extension":{"list"},"alias":{"list"},"help":None,"--version":None,"version":None}
GH_OPT_ARG = {"-R","--repo"}
INTERP = re.compile(r"^(bash|sh|zsh|dash|ksh|fish|csh|tcsh|tclsh|wish|expect|swift|python|python[23](\.\d+)?|pypy3?|node|deno|bun|tsx|ts-node|ruby|perl|php|osascript)$")
SHELLS = re.compile(r"^(bash|sh|zsh|dash|ksh|fish|csh|tcsh)$")
DIRECT_C = re.compile(r"^(bash|sh|zsh|dash|ksh|fish|csh|tcsh|expect)$")
PKG_RUN = {"npx","bunx","make","just","task","rake","invoke","uv","uvx","pipx","poetry",
  "pytest","playwright","vitest","jest","tox","nox","pre-commit","docker","alembic","cargo","go",
  "script","lockf","taskpolicy","sandbox-exec","xcrun","coproc","parallel"}
PKG_INFO = {"--version","-V","-v","--help","-h","version"}
PKG_MGR = {"npm","pnpm","yarn"}
PKG_READ = {"ls","list","view","info","outdated","why"}
PREFIX = {"env","nohup","time","exec","nice","timeout","xargs","stdbuf","caffeinate","then","do","else","if","while","until","!","command","{","builtin","elif","arch"}
PREFIX_OPT_ARG = {"-I","-L","-n","-P","-s","-d","-E","-a","-u","-k","-C",
  "--signal","--kill-after","--max-args","--replace","--max-procs","--delimiter","--arg-file","--unset","--chdir"}
ENV_SPLIT = {"-S","--split-string"}
SYS_DIRS = ("/bin/","/usr/bin/","/usr/sbin/","/sbin/","/opt/homebrew/bin/","/usr/local/bin/")
TMP_DIRS = ("/tmp/","/private/tmp/")
AGENTS = {"claude","codex","gemini"}
GIT_ENV_SAFE = {"GIT_PAGER=cat","GIT_PAGER="}
RUN_ENV = re.compile(r"^(PAGER|GH_PAGER|MANPAGER|EDITOR|VISUAL|GH_EDITOR|BROWSER|GH_BROWSER|LESSOPEN|LESSCLOSE)=(.*)$", re.S)
RUN_ENV_SAFE = re.compile(r"^((cat|less|more)( -[A-Za-z]+)*)?$")
AGENT_INFO = {"--version","-v","--help","-h"}
OLLAMA_READ = {"list","ls","ps","show","help"}
INSPECT = {"ls","file","stat","which","du","pgrep","ps","realpath","readlink","basename","dirname","wc","echo","printf","type",
  "grep","egrep","fgrep","rg","ag","jq","cat","head","tail","cd","pushd","popd"}
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
GIT_ENV = re.compile(r"^GIT_[A-Za-z0-9_]*=")
HEREDOC = re.compile(r"(<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n).*?\n\s*\2\b", re.S)

def git_pager_ok(w):
    return w.startswith("GIT_PAGER=") and bool(RUN_ENV_SAFE.match(w[len("GIT_PAGER="):]))

def base(w): return w.rsplit("/",1)[-1]

def strip_bodies(cmd):
    """heredoc の本文は、その行にシェル（bash など）か eval・source・. があるときだけ残す。"""
    def repl(m):
        ls = cmd.rfind("\n", 0, m.start(1)) + 1
        le = cmd.find("\n", m.start(1))
        line = cmd[ls:le if le >= 0 else len(cmd)]
        try: ws = shlex.split(line)
        except ValueError: ws = line.split()
        keep = any(SHELLS.match(base(w)) or w in ("eval","source",".") for w in ws)
        return m.group(0) if keep else m.group(1)
    return HEREDOC.sub(repl, cmd)

def strip_comments(text):
    """引用符の外で、語の頭にある # から行の終わりの手前までを捨てる（bash と同じ）。"""
    out, q, i = [], None, 0
    while i < len(text):
        c = text[i]
        if q:
            out.append(c)
            if c == "\\" and q == '"' and i + 1 < len(text): out.append(text[i+1]); i += 1
            elif c == q: q = None
        elif c == "\\" and i + 1 < len(text):
            out.append(c); out.append(text[i+1]); i += 1
        elif c in "'\"":
            q = c; out.append(c)
        elif c == "#" and (i == 0 or text[i-1] in " \t\n;&|(<>"):
            while i < len(text) and text[i] != "\n": i += 1
            continue
        else:
            out.append(c)
        i += 1
    return "".join(out)

def lex(text):
    lx = shlex.shlex(text, posix=True, punctuation_chars=";&|<>()\n")
    lx.whitespace = " \t\r"
    lx.whitespace_split = True
    lx.commenters = ""
    return list(lx)

def tokens(text):
    text = strip_comments(text.replace("\\\n", " ").replace("$'", "'").replace('$"', '"'))
    try: return lex(text)
    except ValueError: return lex(re.sub(r"[\"']", "", text))

def segments(text):
    """引用符の外の区切りで区間に分ける。各区間: (語, パイプの後ろか, < の入力, heredoc があるか, <<< の文字)"""
    toks = tokens(text)
    out = []
    cur, piped, stdin, hd, here = [], False, None, False, []
    i = 0
    def flush(next_piped):
        nonlocal cur, piped, stdin, hd, here
        out.append((cur, piped, stdin, hd, here))
        cur, piped, stdin, hd, here = [], next_piped, None, False, []
    while i < len(toks):
        t = toks[i]
        if "(" in t and ("<" in t or ">" in t):
            flush(">" in t)
        elif t and set(t) <= set(";&|\n()"):
            flush("|" in t.replace("||", ""))
        elif t.startswith("<<<"):
            if i + 1 < len(toks): here.append(toks[i+1])
            i += 1
        elif t.startswith("<<"):
            hd = True; i += 1
        elif "<" in t and ">" not in t:
            if i + 1 < len(toks) and "(" not in toks[i+1]:
                stdin = toks[i+1]; i += 1
        elif ">" in t:
            if not (i + 1 < len(toks) and "(" in toks[i+1]): i += 1
        elif t.isdigit() and i + 1 < len(toks) and set(toks[i+1]) & set("<>") and "(" not in toks[i+1]:
            pass
        else:
            cur.append(t)
        i += 1
    flush(False)
    return out

def head_index(ws):
    i = 0
    while i < len(ws):
        w = ws[i]
        if w == "function":
            i += 2; continue
        if base(w) in PREFIX or ASSIGN.match(w):
            i += 1
            while i < len(ws) and (ws[i].startswith("-") or ASSIGN.match(ws[i]) or re.match(r"^\d+[smhd]?$", ws[i])):
                i += 2 if ws[i] in PREFIX_OPT_ARG else 1
            continue
        break
    return i

def script_path_ok(p):
    return p is not None and p.startswith(TMP_DIRS) and ".." not in p.split("/")

def dyn(v): return "$(" in v or "`" in v

INTERP_OPT_ARG = {"-X","-W","-r","--require","--import","--loader","--experimental-loader"}
INTERP_LOAD = {"-r","--require","--import","--loader","--experimental-loader"}

def judge_interp(ws, n, piped, stdin, hd, here):
    sh = bool(SHELLS.match(base(ws[n])))
    j = n + 1
    while j < len(ws) and (ws[j].startswith("-") or (sh and ws[j].startswith("+"))) and ws[j] not in ("-c","-e","--eval","-"):
        w = ws[j]; k = w.split("=", 1)[0]
        if k in INTERP_LOAD:
            v = w.split("=", 1)[1] if "=" in w else (ws[j+1] if j+1 < len(ws) else "")
            if not script_path_ok(v): return "script"
        if sh and re.match(r"^-[a-zA-Z]*c$", w): j += 1; break
        if sh and w == "-n": return None
        if base(ws[n]).startswith(("perl","ruby")) and re.match(r"^-[a-zA-Z]*e$", w): j += 1; break
        mm = re.match(r"^-[bBdEhiIOPqsSuvVx]*m(.*)$", w)
        if mm and not sh and base(ws[n]).startswith(("python","pypy")):
            mod = mm.group(1) or (ws[j+1] if j+1 < len(ws) else "")
            return None if mod == "json.tool" else "script"
        if sh and re.match(r"^[-+][a-zA-Z]*o$", w): j += 2; continue
        j += 2 if (w in INTERP_OPT_ARG and "=" not in w) else 1
    if j > n + 1 and j - 1 < len(ws) and ((sh and re.match(r"^-[a-zA-Z]*c$", ws[j-1])) or
            (base(ws[n]).startswith(("perl","ruby")) and re.match(r"^-[a-zA-Z]*e$", ws[j-1]))):
        if j < len(ws) and dyn(ws[j]): return "script"
        return judge(ws[j]) if j < len(ws) and DIRECT_C.match(base(ws[n])) else None
    a = ws[j] if j < len(ws) else None
    if a in ("-c","-e","--eval"):
        if j+1 < len(ws) and dyn(ws[j+1]): return "script"
        return judge(ws[j+1]) if j+1 < len(ws) and DIRECT_C.match(base(ws[n])) else None
    if a is None or a == "-":
        if here: return "script" if any(dyn(h) for h in here) else None
        if hd: return None
        if stdin is not None: return None if script_path_ok(stdin) else "script"
        if piped: return "script"
        return None if a is None else "script"
    return None if script_path_ok(a) else "script"

def judge_exec(ws, piped, stdin, hd, here):
    i = head_index(ws)
    if i < len(ws):
        h = ws[i]; b = base(h)
        if b in ("sudo","su","doas"): return "sudo"
        if b == "security": return "keychain"
        if b == "trap" and i + 1 < len(ws):
            r = judge(ws[i+1])
            if r: return r
        if b == "eval" and any(dyn(x) for x in ws[i+1:]): return "script"
        if b == "watch":
            k = i + 1
            while k < len(ws) and ws[k].startswith("-"):
                k += 2 if ws[k] in ("-n","--interval") else 1
            if k < len(ws):
                r = judge(" ".join(ws[k:]))
                if r: return r
        if b in ("source",".") and i + 1 < len(ws): return "script"
        if h == "{}": return "script"
        if "/" in h and not h.startswith(SYS_DIRS) and b not in ("git","gh","claude","codex","gemini","ollama"):
            return None if script_path_ok(h) else "script"
        if b in PKG_RUN and not (ws[i+1:] and all(x in PKG_INFO for x in ws[i+1:])): return "script"
        if b in PKG_MGR:
            rest = [x for x in ws[i+1:] if not x.startswith("-")]
            if not (rest and rest[0] in PKG_READ) and not any(x in ("-v","--version") for x in ws[i+1:]): return "script"
    for n, w in enumerate(ws):
        if w in ("-exec","-execdir","-ok","-okdir") and n + 1 < len(ws):
            sub = ws[n+1:]
            end = next((k for k, x in enumerate(sub) if x in (";", "\\;", "+")), len(sub))
            r = judge_words(sub[:end], False, None, False, [])
            if r: return r
    if i < len(ws) and INTERP.match(base(ws[i])):
        r = judge_interp(ws, i, piped, stdin, hd, here)
        if r: return r
    return None

def judge_git(ws):
    i = 0
    while i < len(ws) and ws[i].startswith("-"):
        if ws[i] == "--config-env" or ws[i].startswith("--config-env="): return "git-config-env"
        if ws[i].startswith("--exec-path="): return "git-exec-path"
        if ws[i] == "-c":
            if i + 1 >= len(ws) or not GIT_SAFE_C.match(ws[i+1]): return "git-c"
        i += 2 if ws[i] in GIT_OPT_ARG else 1
    if i >= len(ws): return "git-noverb"
    v, rest = ws[i], ws[i+1:]
    if any(w.startswith(("--upload-pack","--receive-pack","--exec")) for w in rest): return "git-exec"
    if v == "grep" and any(w.startswith("--open-files-in-pager") or re.match(r"^-[A-Za-z]*O", w) for w in rest): return "git-grep-pager"
    if v == "fsck" and "--lost-found" in rest: return "git-fsck"
    if v in GIT_READ: return None
    if v == "fetch":
        return "git-fetch" if any(":" in w for w in rest if not w.startswith("-")) else None
    if v in GIT_SUB_READ:
        if v == "remote":
            pos = [w for w in rest if not w.startswith("-")]
            return None if (pos[0] if pos else None) in GIT_SUB_READ[v] else "git-remote"
        nx = rest[0] if rest else None
        if v == "reflog" and nx and nx.startswith("-"): return None
        return None if nx in GIT_SUB_READ[v] else f"git-{v}"
    if v in ("branch","tag"):
        wr = BT_WRITE | (TAG_WRITE if v == "tag" else set())
        if v == "tag": wr = wr - {"-v"}
        if any(w.split("=")[0] in wr for w in rest): return f"git-{v}"
        if any(re.match(r"^-[A-Za-z]", w) and any("-" + ch in wr for ch in w[1:]) for w in rest): return f"git-{v}"
        pos = [w for w in rest if not w.startswith("-")]
        lf = TAG_LIST_FLAGS if v == "tag" else LIST_FLAGS
        if pos and not any(w.split("=")[0] in lf for w in rest): return f"git-{v}"
        return None
    if v == "config":
        pos = [w for w in rest if not w.startswith("-")]
        if any(w in CONFIG_READ for w in rest) or (pos and pos[0] in CONFIG_READ_SUB): return None
        if len(pos) == 1 and not any(w.split("=")[0] in CONFIG_WRITE for w in rest): return None
        return "git-config"
    if v == "symbolic-ref":
        if any(w in ("-d","--delete") for w in rest): return "git-symbolic-ref"
        return None if len([w for w in rest if not w.startswith("-")]) <= 1 else "git-symbolic-ref"
    return f"git-{v}"

def judge_gh(ws, whole):
    if ws and all(x in AGENT_INFO or x == "version" for x in ws): return None
    i = 0
    while i < len(ws) and ws[i].startswith("-") and ws[i] != "--version":
        i += 2 if ws[i] in GH_OPT_ARG else 1
    if i >= len(ws): return "gh-noverb"
    gv, rest = ws[i], ws[i+1:]
    if gv == "api":
        meth = None
        for k, w in enumerate(rest):
            m = re.match(r"^(?:-X|--method)=?(\w*)$", w)
            if m: meth = (m.group(1) or (rest[k+1] if k+1 < len(rest) else "")).upper()
        if meth: return None if meth == "GET" else "gh-api"
        flds = []
        for k, w in enumerate(rest):
            m = re.match(r"^(-f|-F|--field|--raw-field|--input)(=(.*))?$", w)
            if m: flds.append(m.group(3) if m.group(2) else (rest[k+1] if k+1 < len(rest) else ""))
            elif re.match(r"^-[fF].", w): flds.append(w[2:])
        if "graphql" in rest:
            if re.search(r"\bmutation\b", whole) or any(w.startswith("--input") for w in rest): return "gh-api"
            for v in flds:
                val = v.split("=", 1)[-1]
                if val.startswith("@"): return "gh-api"
                if v.startswith("query=") and ("$(" in val or "`" in val): return "gh-api"
            return None
        return "gh-api" if flds else None
    if gv == "auth" and any(x in ("-t","--show-token") or x.startswith("--show-token=") for x in rest): return "gh-token"
    if gv not in GH_READ: return f"gh-{gv}"
    al = GH_READ[gv]
    if al is None: return None
    j = 0
    while j < len(rest) and rest[j].startswith("-"):
        j += 2 if rest[j] in GH_OPT_ARG else 1
    sub = rest[j] if j < len(rest) else None
    return None if sub in al else f"gh-{gv}"

def drop_exec_args(ws):
    """find の -exec などの後ろ（終わりの ; か + まで）は judge_exec で見たので、外の語の判定から外す。"""
    out, skip = [], False
    for w in ws:
        if skip:
            if w in (";", "\\;", "+"): skip = False
            continue
        if w in ("-exec","-execdir","-ok","-okdir"): skip = True; continue
        out.append(w)
    return out

def judge_words(ws, piped, stdin, hd, here, whole=""):
    k = 0
    while k < len(ws) and ASSIGN.match(ws[k]): k += 1
    lead = ws[:k]; ws = ws[k:]
    if not ws:
        if any((RUN_ENV.match(w) and not RUN_ENV_SAFE.match(RUN_ENV.match(w).group(2))) for w in lead): return "run-env"
        return "git-env" if any(GIT_ENV.match(w) and not git_pager_ok(w) for w in lead) else None
    hi = head_index(ws)
    for k, x in enumerate(ws[:hi + 1]):
        if base(x) == "env":
            for m, y in enumerate(ws[k+1:hi+1], k + 1):
                v = None
                if y in ENV_SPLIT: v = " ".join(ws[m+1:])
                elif y.startswith("--split-string="): v = y.split("=", 1)[1] + " " + " ".join(ws[m+1:])
                elif y.startswith("-S") and len(y) > 2: v = y[2:] + " " + " ".join(ws[m+1:])
                if v is not None:
                    r = judge(v)
                    if r: return r
    if any(GIT_ENV.match(w) and not git_pager_ok(w) for w in lead + ws[:hi]): return "git-env"
    for w in lead + ws[:hi] + (ws if ws[0] in ("export","declare","typeset","local","readonly") else []):
        m = RUN_ENV.match(w)
        if m and not RUN_ENV_SAFE.match(m.group(2)): return "run-env"
    if ws[0] in ("export","declare","typeset","local","readonly") and any(GIT_ENV.match(w) and not git_pager_ok(w) for w in ws): return "git-env"
    if ws[0] == "command" and len(ws) > 1 and ws[1] in ("-v","-V"): return None
    hb = base(ws[hi]) if hi < len(ws) else ""
    if hb in INSPECT or (hb == "command" and len(ws) > 1 and ws[1] in ("-v","-V")):
        if hb == "rg" and any(w == "--pre" or w.startswith("--pre=") for w in ws): return "script"
        return None
    r = judge_exec(ws, piped, stdin, hd, here)
    if r: return r
    ws = drop_exec_args(ws)
    for n, w in enumerate(ws):
        b = base(w)
        if b in AGENTS:
            rest = ws[n+1:]
            if not (rest and all(x in AGENT_INFO for x in rest)): return "agent"
        if b == "ollama":
            rest = ws[n+1:]
            pos = [x for x in rest if not x.startswith("-")]
            if not ((rest and all(x in AGENT_INFO for x in rest)) or (pos and pos[0] in OLLAMA_READ)): return "agent"
        if b == "git":
            r = judge_git(ws[n+1:])
            if r: return r
        if b == "gh":
            r = judge_gh(ws[n+1:], whole)
            if r: return r
    return None

def heredoc_subs(cmd):
    """印に引用符が無い heredoc の本文は bash が $( )・逆引用符を実行するので、その中身を取り出す。"""
    out = []
    for m in HEREDOC.finditer(cmd):
        if re.match(r"<<-?\s*['\"]", m.group(1)): continue
        out += g.embedded_commands(cmd[m.end(1):m.end()])
    return out

def judge_text(text, whole):
    for ws, piped, stdin, hd, here in segments(strip_bodies(text.replace("\\\n", " "))):
        r = judge_words(ws, piped, stdin, hd, here, whole)
        if r: return r
        for h in here:
            r = judge(h)
            if r: return r
    return None

def judge(cmd):
    texts = [cmd]
    for e in g.embedded_commands(cmd) + heredoc_subs(cmd.replace("\\\n", " ")):
        if e == g.TOO_DEEP: return "too-deep"
        texts.append(e)
    for t in texts:
        r = judge_text(t, cmd)
        if r: return r
    return None


BLOCK_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "EnterWorktree", "ExitWorktree"}


def block(agent_type, tool_name, rule):
    try:
        d = os.path.join(os.path.expanduser("~"), ".claude", "logs")
        os.makedirs(d, exist_ok=True)
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(os.path.join(d, "local-subagent-guard.log"), "a", encoding="utf-8") as f:
            f.write("\t".join([ts, str(agent_type or "名前なし"), str(tool_name), rule]) + "\n")
    except Exception:
        pass
    sys.stderr.write(
        "手元の担当（%s）は、ファイルの書き換え・git の作業場所や履歴の変更・GitHub への書き込み・台本の実行・別の AI の起動をしません"
        "（ADR-1046・規則 %s）。調べた結果を本体に返してください。書き換えが要る作業はクラウドで行います。\n"
        % (agent_type or "名前なし", rule))
    sys.exit(2)


def main():
    try:
        data = __import__("json").loads(sys.stdin.read())
    except Exception:
        return 0
    if not isinstance(data, dict):
        return 0
    if not data.get("agent_id"):
        return 0
    agent_type = data.get("agent_type")
    if not isinstance(agent_type, str) or not agent_type:
        agent_type = None
    tool = data.get("tool_name")
    if tool in BLOCK_TOOLS:
        block(agent_type, tool, "tool")
    if tool in ("Bash", "Monitor"):
        ti = data.get("tool_input")
        if not isinstance(ti, dict) or "command" not in ti:
            return 0
        cmd = ti["command"]
        if not isinstance(cmd, str):
            block(agent_type, tool, "command-not-string")
        if g is None:
            block(agent_type, tool, "import-failed")
        try:
            rule = judge(cmd)
        except Exception:
            rule = "judge-error"
        if rule:
            block(agent_type, tool, rule)
    return 0


if __name__ == "__main__":
    sys.exit(main())
