#!/usr/bin/env bash
# 入口の文書の「図書館」点検（library-design §4-1・§4-2・§5・実装カード library-stage0-card.md §2）。
# 読むだけ。1項目1行を出す。終了コードは常に 0（合格の判定は doc-entry-weekly-check.sh がする）。
# 使い方: bash scripts/dev/doc-library-check.sh
set -u

# 合格線の正本（判定は weekly-check 側。ここは基準の置き場）
export PASS_L2=0
export PASS_L2_UNTAGGED=0
export PASS_L3_MATCH=yes
export PASS_BOOKS_IMPORTED=0

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="${DOC_ENTRY_HOME:-$HOME}"
REPO="${DOC_ENTRY_REPO:-$(cd "$SELF_DIR/../.." && pwd)}"
LEDGER="${DOC_LIBRARY_LEDGER:-$REPO/docs/handoff/doc-agenda-nav/library-ledger.md}"
HOOK="${DOC_LIBRARY_HOOK:-$HOME_DIR/kb/scripts/hooks/plain-lang/hook.py}"
export HOME_DIR REPO LEDGER HOOK

read -r -d '' PY <<'PYEOF'
import os, re, sys, glob

HOME = os.environ["HOME_DIR"]
REPO = os.environ["REPO"]
LEDGER = os.environ["LEDGER"]
HOOK = os.environ["HOOK"]
MAX_DEPTH = 4


def rp(p):
    return os.path.realpath(p)


def disp(p):
    if p == HOME or p.startswith(HOME + "/"):
        return "~" + p[len(HOME):]
    return p


def read_text(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def has_paths(p):
    L = read_text(p).split("\n")
    if not L or L[0].strip() != "---":
        return False
    for l in L[1:]:
        if l.strip() == "---":
            return False
        if l.startswith("paths:"):
            return True
    return False


AT_RE = re.compile(r"(?:^|\s)@(\S+)")


def is_import(tok):
    return tok.startswith(("~/", "/", "./")) or "/" in tok or ".md" in tok


def scan_lines(text):
    """(行番号, 行) を、``` の囲みの外だけ返す。"""
    fence = False
    for i, line in enumerate(text.split("\n")):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        yield i, line


def imports_in(text):
    """囲みの外・バッククォートの外にある取り込みとみなす @ の (行番号, パス文字列) の並び。"""
    out = []
    for i, line in scan_lines(text):
        stripped = re.sub(r"`[^`]*`", "", line)
        for m in AT_RE.finditer(stripped):
            tok = m.group(1)
            if is_import(tok):
                out.append((i, tok))
    return out


def resolve(tok, base_file):
    if tok.startswith("~/"):
        return os.path.normpath(os.path.join(HOME, tok[2:]))
    if tok.startswith("/"):
        return os.path.normpath(tok)
    return os.path.normpath(os.path.join(os.path.dirname(base_file), tok))


# ---------- K1_DEF ----------
roots = []
missing = []
home_claude = os.path.join(HOME, ".claude", "CLAUDE.md")
repo_claude = os.path.join(REPO, "CLAUDE.md")
repo_agents = os.path.join(REPO, "AGENTS.md")
rules_dir = os.path.join(HOME, ".claude", "rules")
rules_all = []
if os.path.isdir(rules_dir):
    for dp, dn, fn in os.walk(rules_dir):
        for n in fn:
            if n.endswith(".md"):
                rules_all.append(os.path.join(dp, n))
rules_all.sort()
rules_nopaths = [f for f in rules_all if not has_paths(f)]
rules_paths = [f for f in rules_all if has_paths(f)]

for f in [home_claude, repo_claude] + rules_nopaths + [repo_agents]:
    if os.path.isfile(f):
        roots.append(f)
    else:
        missing.append(disp(f))

seen = {}        # realpath -> 表示用パス
order = []       # 数えたファイル（実パス）
depth_of = {}
imported = set() # @ の取り込み先として数えられたファイルの実パス
queue = []
for f in roots:
    r = rp(f)
    if r not in seen:
        seen[r] = f
        order.append(r)
        depth_of[r] = 0
        queue.append(r)
root_real = set(queue)
qi = 0
while qi < len(queue):
    cur = queue[qi]
    qi += 1
    d = depth_of[cur]
    if d >= MAX_DEPTH:
        continue
    src = seen[cur]
    for _, tok in imports_in(read_text(cur)):
        t = resolve(tok, src)
        if not os.path.isfile(t):
            if disp(t) not in missing:
                missing.append(disp(t))
            continue
        r = rp(t)
        imported.add(r)
        if r not in seen:
            seen[r] = t
            order.append(r)
            depth_of[r] = d + 1
            queue.append(r)

k1_total = 0
for r in order:
    with open(r, "rb") as f:
        k1_total += f.read().count(b"\n")
print("K1_DEF=%d" % k1_total)
print("K1_DEF_FILES=" + ",".join(disp(seen[r]) for r in order))
print("K1_DEF_MISSING=" + (",".join(missing) if missing else "none"))

# ---------- 対象ファイル（L2 用） ----------
books_dir = os.path.join(HOME, ".claude", "books")
book_files = sorted(glob.glob(os.path.join(books_dir, "*.md")))

# hook.py から CHAT_FORMAT と SECTION を読む
chat_format = None
section = None
chan_ok = False
if os.path.isfile(HOOK):
    cf = []
    sc = []
    for l in read_text(HOOK).split("\n"):
        if l.startswith("CHAT_FORMAT = "):
            cf.append(l)
        elif l.startswith("SECTION = "):
            sc.append(l)
    if len(cf) == 1 and len(sc) == 1:
        m1 = re.search(r'"(~/[^"]*)"', cf[0])
        m2 = re.search(r'"([^"]*)"', sc[0])
        if m1 and m2:
            chat_format = os.path.join(HOME, m1.group(1)[2:])
            section = m2.group(1)
            chan_ok = True

if chan_ok:
    n = 0
    cfr = rp(chat_format)
    for r in imported:
        if r == cfr and os.path.isfile(r):
            if any(l == section for l in read_text(r).split("\n")):
                n += 1
    L2_CHANNEL = str(n)
else:
    L2_CHANNEL = "unreadable"
print("L2_CHANNEL=" + L2_CHANNEL)

# 台帳
ledger = None
if os.path.isfile(LEDGER):
    try:
        rows = {}
        for line in read_text(LEDGER).split("\n"):
            s = line.strip()
            if not s.startswith("|"):
                continue
            c = [x.strip() for x in s.strip("|").split("|")]
            if len(c) < 4 or not re.match(r"^R-\d+$", c[0]):
                continue
            locs = [x.strip() for x in re.split(r"<br\s*/?>|; ", c[2]) if x.strip()]
            e = rows.setdefault(c[0], {"locs": [], "kinds": set(), "name": c[1]})
            e["locs"].extend(locs)
            e["kinds"].add(c[3])
        ledger = rows
    except OSError:
        ledger = None


def parse_loc(loc):
    """ファイル:見出し:行番号 → (実パス, 見出し)。"""
    if ":" not in loc:
        return None
    f, rest = loc.split(":", 1)
    m = re.match(r"^(.*):(\d+)$", rest)
    if m:
        rest = m.group(1)
    rest = re.sub(r"^#+\s*", "", rest.strip())
    f = f.strip()
    if f.startswith("~/"):
        f = os.path.join(HOME, f[2:])
    elif not os.path.isabs(f):
        f = os.path.join(REPO, f)
    return (rp(f), rest)


def parse_loc_line(loc):
    """ファイル:見出し:行番号 → (実パス, 見出し, 行番号 or None)。"""
    if ":" not in loc:
        return None
    f, rest = loc.split(":", 1)
    ln = None
    m = re.match(r"^(.*):(\d+)$", rest)
    if m:
        rest, ln = m.group(1), int(m.group(2))
    p = parse_loc(loc)
    return (p[0], p[1], ln) if p else None


# 対象ファイル
targets = []
tseen = set()
extra = list(book_files)
if chan_ok:
    extra.append(chat_format)
extra += rules_paths
for r in list(order) + [rp(x) for x in extra if os.path.isfile(x)]:
    if r not in tseen:
        tseen.add(r)
        targets.append(r)


def frontmatter_end(lines):
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return i + 1
    return 0


def headings_of(path):
    text = read_text(path)
    lines = text.split("\n")
    start = frontmatter_end(lines)
    out = []
    fence = False
    for i, line in enumerate(lines):
        if i < start:
            continue
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if line.startswith("## "):
            out.append(line[3:].strip())
        elif line.startswith("### "):
            out.append(line[4:].strip())
    return out


books_real = set(rp(b) for b in book_files)
TAG_RE = re.compile(r"\s*\[(R-\d+)\]\s*$")

# L2_DUP_ID
ids_in_books = {}
for b in book_files:
    for l in read_text(b).split("\n"):
        m = re.match(r"^#{1,6}\s+.*\[(R-\d+)\]\s*$", l)
        if m:
            ids_in_books.setdefault(m.group(1), set()).add(rp(b))
dup_id = sum(1 for v in ids_in_books.values() if len(v) >= 2)

# L2_DUP_LINE
imp_lines = {}
def norm_line(s):
    s = s.replace("　", " ")
    s = re.sub(r"^(?:[-*\s]|\d+\.)+", "", s)
    s = s.strip()
    s = s.rstrip("。")
    return s

line_files = {}
for r in targets:
    text = read_text(r)
    lines = text.split("\n")
    start = frontmatter_end(lines)
    at_lines = set(i for i, _ in imports_in(text))
    fence = False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence or i < start or i in at_lines:
            continue
        if line.startswith("#") or line.lstrip().startswith("- 本:"):
            continue
        n = norm_line(line)
        if len(n) >= 20:
            line_files.setdefault(n, set()).add(r)
dup_line = sum(1 for v in line_files.values() if len(v) >= 2)

# 台帳を使う3項目
if ledger is None:
    L2_DUP_LEDGER = L2_UNTAGGED = L3_LEDGER = L2_LINE_NG = "unreadable"
else:
    L2_DUP_LEDGER = str(sum(1 for e in ledger.values() if len(e["locs"]) >= 2))
    known = set()
    for e in ledger.values():
        for loc in e["locs"]:
            p = parse_loc(loc)
            if p:
                known.add(p)
    untagged = 0
    for r in targets:
        for h in headings_of(r):
            if r in books_real:
                h = TAG_RE.sub("", h)
            if (r, h) not in known:
                untagged += 1
    L2_UNTAGGED = str(untagged)
    L3_LEDGER = str(sum(1 for e in ledger.values() if "本" in e["kinds"]))

    # L2_LINE_NG: 台帳の行番号が、その行の見出しと合っているか
    HEAD_RE = re.compile(r"^(#{1,3})\s+(.*)$")
    head_cache = {}

    def heads_of_file(path):
        if path in head_cache:
            return head_cache[path]
        res = None
        if os.path.isfile(path):
            lines = read_text(path).split("\n")
            hs = {}
            fence = False
            for i, line in enumerate(lines):
                if line.lstrip().startswith("```"):
                    fence = not fence
                    continue
                if fence:
                    continue
                mm = HEAD_RE.match(line)
                if mm:
                    hs[i + 1] = (len(mm.group(1)), TAG_RE.sub("", mm.group(2)).strip())
            res = (len(lines), hs)
        head_cache[path] = res
        return res

    line_ng = 0
    for e in ledger.values():
        for loc in e["locs"]:
            pl = parse_loc_line(loc)
            if pl is None or pl[2] is None:
                line_ng += 1
                continue
            path, text, ln = pl
            info = heads_of_file(path)
            if info is None or ln < 1 or ln > info[0]:
                line_ng += 1
                continue
            hs = info[1]
            if ln in hs and hs[ln][1] == text:
                continue
            ok = False
            if e["name"].startswith("言い直し"):
                for hl, (k, ht) in hs.items():
                    if ht != text or hl >= ln:
                        continue
                    if not any(hl < x <= ln and hs[x][0] <= k for x in hs):
                        ok = True
                        break
            if not ok:
                line_ng += 1
    L2_LINE_NG = str(line_ng)

print("L2_DUP_LEDGER=" + L2_DUP_LEDGER)
print("L2_DUP_ID=%d" % dup_id)
print("L2_DUP_LINE=%d" % dup_line)
parts = [L2_CHANNEL, L2_DUP_LEDGER, str(dup_id), str(dup_line)]
if "unreadable" in parts:
    L2 = "unreadable"
else:
    L2 = str(sum(int(x) for x in parts))
print("L2=" + L2)
print("L2_UNTAGGED=" + L2_UNTAGGED)
print("L2_LINE_NG=" + L2_LINE_NG)

# ---------- L3 ----------
A = []
if os.path.isfile(home_claude):
    pat = re.compile(r"^- 本:([a-z0-9-]+)#(R-[0-9]{2,3}) .+ → (\S+)$")
    for l in read_text(home_claude).split("\n"):
        m = pat.match(l)
        if m:
            p = m.group(3)
            if p.startswith("~/"):
                p = os.path.join(HOME, p[2:])
            elif not os.path.isabs(p):
                p = os.path.join(os.path.dirname(home_claude), p)
            A.append((m.group(1), m.group(2), p))

B = []          # (book_id, R-nn)
book_ids = {}   # 実パス -> (book id, set(R-nn))
for b in book_files:
    text = read_text(b)
    lines = text.split("\n")
    bid = None
    if lines and lines[0].strip() == "---":
        for l in lines[1:]:
            if l.strip() == "---":
                break
            m = re.match(r"^book:\s*(\S+)\s*$", l)
            if m:
                bid = m.group(1)
    rs = set()
    for l in lines:
        m = re.match(r"^#{1,6}\s+.*\[(R-\d+)\]\s*$", l)
        if m:
            B.append((bid, m.group(1)))
            rs.add(m.group(1))
    book_ids[rp(b)] = (bid, rs)

a_ids = [x[1] for x in A]
b_ids = [x[1] for x in B]
bad = set()
bad |= set(a_ids) ^ set(b_ids)
if len(set(a_ids)) == len(set(b_ids)) and set(a_ids) == set(b_ids) and len(a_ids) != len(b_ids):
    for lst in (a_ids, b_ids):
        for x in set(lst):
            if lst.count(x) > 1:
                bad.add(x)
for bid, rid, path in A:
    bp = rp(path)
    if not os.path.isfile(path) or bp not in book_ids:
        bad.add(rid)
        continue
    fid, rs = book_ids[bp]
    if fid != bid:
        bad.add(rid)
    if rid not in rs:
        bad.add(rid)
if ledger is not None:
    led_books = set(k for k, e in ledger.items() if "本" in e["kinds"])
    bad |= led_books ^ set(b_ids)

print("L3_INDEX=%d" % len(A))
print("L3_BOOKS=%d" % len(B))
print("L3_LEDGER=" + L3_LEDGER)
if bad:
    print("L3_MATCH=no " + ",".join(sorted(bad)))
else:
    print("L3_MATCH=yes")

# ---------- BOOKS_IMPORTED ----------
nb = 0
for f in roots:
    for _, tok in imports_in(read_text(f)):
        if "books/" in tok:
            nb += 1
print("BOOKS_IMPORTED=%d" % nb)
PYEOF

python3 -I -c "$PY"
exit 0
