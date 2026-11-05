#!/usr/bin/env python3
"""合格の線（kgi.md の K1・K9・K12）の写しが正本とずれていないか見張る（標準ライブラリのみ）。

使い方: python3 -I scripts/ci/check_kgi_line_copies.py --root <リポジトリ> [--routines <routines.json>]
出力: BASE 行・COPY 行（写しごと）・SUMMARY 行。指示書の本文（promptText）は出さない。
終了コード: 0=すべて SAME / 1=DIFF か MISSING がある / 2=正本が読めない・引数が違う
設計: docs/handoff/doc-library-one-tree/line-copy-guard-design.md §3-1
"""
import argparse
import json
import os
import re
import sys
from decimal import Decimal, InvalidOperation

KGI = "docs/specs/doc-agenda-nav/kgi.md"
WEEKLY = "scripts/dev/doc-entry-weekly-check.sh"
REQ = "docs/handoff/doc-agenda-nav/library-requirements.md"
WEEKLY_TEST = "scripts/dev/test_doc_entry_weekly_check.sh"
ROUTINE_NAME = "入口の文書 週次点検"

NUM = r"(\d+(?:\.\d+)?)"
INT = r"(\d+)"

# 写しの一覧（ここ1か所だけ）。(名前, 種類, ファイル, 読み方, 期待する正本の名前, 倍率)
#   種類 "file": ファイルの全行に正規表現を当てる / "req": 要件の L1 行から取り消し線を除いて当てる
COPIES = [
    ("C1", "file", WEEKLY, r"^K1_LIMIT=" + INT + r"$", "K1", 1),
    ("C2", "file", WEEKLY, r"^K9_LIMIT_TOKENS=" + INT + r"$", "K9", 1000),
    ("C3", "file", WEEKLY, r"K9>" + NUM + r"k", "K9", 1),
    ("C4a", "req", REQ, r"K9 ≤\s*\*\*" + NUM + r"k\*\*", "K9", 1),
    ("C4b", "req", REQ, r"K1 ≤\s*\*\*" + INT + r"\*\*", "K1", 1),
    ("C5", "file", WEEKLY_TEST, r"K1>" + INT, "K1", 1),
]
# C6（--routines のときだけ）: 定期実行の指示書の中の K12 の写し
ROUTINE_RE = r"(\d+)/20 以上（docs/specs/doc-agenda-nav/kgi\.md の K12）"

# 正本の読み方: 行の頭、4つ目の欄（合格ライン）から最初に当たる数
BASE_READ = [
    ("K1", r"(\d+)行以下"),
    ("K9", r"(\d+(?:\.\d+)?)k 以下"),
    ("K12", r"(\d+)/20 以上"),
]


def read_lines(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().split("\n")
    except OSError:
        return None


def to_dec(s):
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def fmt(d):
    s = format(d.normalize(), "f")
    return s


def read_base(root):
    lines = read_lines(os.path.join(root, KGI))
    base = {}
    for name, pat in BASE_READ:
        val = None
        for line in lines or []:
            if line.startswith("| %s |" % name):
                cells = line.split("|")
                if len(cells) > 4:
                    m = re.search(pat, cells[4])
                    if m:
                        val = to_dec(m.group(1))
                break
        base[name] = val
    return base


def find_file(root, rel, kind, pat):
    """見つけた数の文字列の一覧。ファイルが読めなければ None。"""
    lines = read_lines(os.path.join(root, rel))
    if lines is None:
        return None
    out = []
    for line in lines:
        if kind == "req":
            if not line.startswith("| L1 "):
                continue
            line = re.sub(r"~~.*?~~", "", line)
        out.extend(re.findall(pat, line))
    return out


def find_routines(path):
    """指示書の中の K12 の写し。読めない・名前が無いときは None（本文は返さない）。"""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return None
    found = None
    for it in items:
        if isinstance(it, dict) and it.get("name") == ROUTINE_NAME:
            found = [] if found is None else found
            text = it.get("promptText")
            if isinstance(text, str):
                found.extend(re.findall(ROUTINE_RE, text))
    return found


def judge(name, expected, found_strs):
    if not found_strs:
        return "COPY %s expected=%s found=- MISSING" % (name, fmt(expected)), "missing"
    vals = [to_dec(x) for x in found_strs]
    shown = ",".join(fmt(v) if v is not None else x for v, x in zip(vals, found_strs))
    same = all(v is not None and v == expected for v in vals)
    return "COPY %s expected=%s found=%s %s" % (name, fmt(expected), shown, "SAME" if same else "DIFF"), \
        "same" if same else "diff"


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--routines")
    args = ap.parse_args(argv)

    base = read_base(args.root)
    unreadable = [n for n, _ in BASE_READ if base[n] is None]
    if unreadable:
        for n in unreadable:
            print("BASE %s unreadable" % n)
        return 2
    print("BASE K1=%s K9=%s K12=%s" % (fmt(base["K1"]), fmt(base["K9"]), fmt(base["K12"])))

    counts = {"same": 0, "diff": 0, "missing": 0}
    for name, kind, rel, pat, bname, mult in COPIES:
        found = find_file(args.root, rel, kind, pat)
        line, state = judge(name, base[bname] * mult, found)
        print(line)
        counts[state] += 1
    if args.routines is not None:
        line, state = judge("C6", base["K12"], find_routines(args.routines))
        print(line)
        counts[state] += 1
    print("SUMMARY same=%d diff=%d missing=%d" % (counts["same"], counts["diff"], counts["missing"]))
    return 0 if counts["diff"] == 0 and counts["missing"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
