#!/usr/bin/env python3
"""目次 docs/INDEX.md から手順書が届くかを数える検査（警告だけ。--strict で失敗にできる）。

使い方: python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root . [--strict]
辺の取り方は ~/CC報告ファイル-keep/agenda-nav-20261022/unreach/reach.py の variant any と同じ。
標準ライブラリだけで動く。
"""
import argparse
import posixpath
import re
import subprocess
import sys
from collections import deque

ENTRIES = [
    "CLAUDE.md", "AGENTS.md",
    "frontend/CLAUDE.md", "frontend/AGENTS.md",
    "backend/CLAUDE.md", "backend/AGENTS.md",
]
INDEX = "docs/INDEX.md"
WHEN_TABLES = ["docs/INDEX.md", "docs/specs/README.md"]
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
ANY = re.compile(r'[A-Za-z0-9_./~-]+\.md')
WHEN_NAME = "いつ読むか"
LIMIT_DEPTH = 3


def die(msg):
    print("ERROR " + msg)
    sys.exit(2)


def external(c):
    return bool(re.match(r'^[a-z]+:', c)) or c.startswith('#')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    root = a.root

    try:
        out = subprocess.run(["git", "-C", root, "ls-files", "-z"],
                             capture_output=True, check=True).stdout
    except Exception as e:  # noqa: BLE001
        die("git ls-files failed: %s" % e)
    files = [f for f in out.decode("utf-8", "replace").split("\0") if f]
    fset = set(files)

    def isdir(p):
        pre = p.rstrip("/") + "/"
        return any(f.startswith(pre) for f in fset)

    texts = {}

    def read(path):
        if path not in texts:
            try:
                with open(posixpath.join(root, path), encoding="utf-8", errors="replace") as fh:
                    texts[path] = fh.read()
            except OSError as e:
                die("cannot read %s: %s" % (path, e))
        return texts[path]

    if INDEX not in fset:
        die("no docs/INDEX.md")
        return

    def targets(src, text):
        base = posixpath.dirname(src)
        out = []
        folders = []
        cands = LINK.findall(text) + ANY.findall(text)
        for c in cands:
            if external(c):
                continue
            c = c.split('#')[0].split('?')[0]
            if not c:
                continue
            if c.startswith('/'):
                p = posixpath.normpath(c.lstrip('/'))
            else:
                p = posixpath.normpath(posixpath.join(base, c))
            if p in fset:
                out.append(p)
            alt = posixpath.normpath(c.lstrip("./"))
            if alt in fset:
                out.append(alt)
        if src == INDEX:
            for c in LINK.findall(text):
                if external(c):
                    continue
                c = c.split('#')[0].split('?')[0]
                if not c:
                    continue
                if c.startswith('/'):
                    p = posixpath.normpath(c.lstrip('/'))
                else:
                    p = posixpath.normpath(posixpath.join(base, c))
                if (c.endswith('/') or isdir(p)) and p not in fset and isdir(p):
                    folders.append(p)
        for fo in folders:
            pre = fo.rstrip("/") + "/"
            for f in files:
                if f.startswith(pre) and f.endswith(".md") and "/" not in f[len(pre):]:
                    out.append(f)
        return out

    depth = {}
    dq = deque()
    for e in ENTRIES:
        if e in fset:
            depth[e] = 0
            dq.append(e)
    depth[INDEX] = 1
    dq.append(INDEX)
    while dq:
        s = dq.popleft()
        if not s.endswith(".md"):
            continue
        for p in targets(s, read(s)):
            if p not in depth:
                depth[p] = depth[s] + 1
                dq.append(p)

    lines = []
    md = [f for f in files if f.endswith(".md")]
    scope = [f for f in md if f.startswith("docs/specs/") or f.startswith("docs/ai-agents/")]

    unreached = sorted(f for f in scope if f not in depth)
    for f in unreached:
        lines.append((f, "UNREACHED " + f))

    def terminal(f):
        if f.startswith("docs/ai-agents/"):
            return f.count("/") == 2
        if f.startswith("docs/specs/") and f.endswith("/README.md"):
            return f.count("/") == 3
        return False

    deep = 0
    max_depth = 0
    for f in sorted(f for f in scope if terminal(f) and f in depth):
        max_depth = max(max_depth, depth[f])
        if depth[f] > LIMIT_DEPTH:
            deep += 1
            lines.append((f, "DEEP %d %s" % (depth[f], f)))

    blank = 0
    no_when = 0
    for t in WHEN_TABLES:
        if t not in fset:
            continue
        col = None
        in_table = False
        found_when = False
        for i, line in enumerate(read(t).split("\n"), 1):
            s = line.strip()
            if not s.startswith("|"):
                in_table = False
                col = None if not in_table else col
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if WHEN_NAME in cells and not in_table:
                col = cells.index(WHEN_NAME)
                found_when = True
                in_table = True
                continue
            if col is None:
                continue
            if all(re.fullmatch(r':?-{2,}:?', c) for c in cells if c):
                continue
            if col >= len(cells) or cells[col] == "":
                blank += 1
                lines.append((t, "BLANK_WHEN %s:%d" % (t, i)))
        if t == INDEX or t == "docs/specs/README.md":
            if not found_when:
                no_when += 1
                lines.append((t, "NO_WHEN_COLUMN " + t))

    broken = 0
    check_files = sorted(set([INDEX] + [e for e in ENTRIES if e in fset] +
                             [f for f in scope]))
    for f in check_files:
        base = posixpath.dirname(f)
        for i, line in enumerate(read(f).split("\n"), 1):
            for c in LINK.findall(line):
                if external(c):
                    continue
                c0 = c.split('#')[0].split('?')[0]
                if not c0:
                    continue
                p = posixpath.normpath(c0.lstrip('/')) if c0.startswith('/') \
                    else posixpath.normpath(posixpath.join(base, c0))
                if p in fset or isdir(p):
                    continue
                broken += 1
                lines.append((f, "BROKEN_LINK %s:%d %s" % (f, i, c0)))

    lines.sort(key=lambda x: (x[1].split(" ")[0] != "UNREACHED", x[0], x[1]))
    for _, l in lines:
        print(l)
    warnings = len(unreached) + deep + blank + no_when + broken
    print("SUMMARY unreached=%d deep=%d blank_when=%d no_when_column=%d broken_link=%d warnings=%d"
          % (len(unreached), deep, blank, no_when, broken, warnings))
    print("MAX_DEPTH_TERMINAL %d" % max_depth)
    if a.strict and warnings >= 1:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
