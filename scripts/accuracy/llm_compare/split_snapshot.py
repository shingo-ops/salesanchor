#!/usr/bin/env python3
"""fhd_snapshot.py convert の出力を score_v102.py の --snapshot-dir の形に分ける（design.md §5-3）。

入力: 先頭に tag・repeat・source_message の3列＋SNAP_COLS 14列の TSV（ヘッダ行つき）。
出力: OUT/<tag>/r<repeat>/<source_message>.tsv（先頭3列を落とした14列、ヘッダつき）。
  (tag, repeat) ごとに別フォルダ。バイト列は加工しない（行はそのまま、改行は \\n）。
  convert が1件も出さなかった投稿はファイルができない（score_v102.py が「写しの行が無い投稿」に数える）。
"""
import argparse
import os
import re
import sys

PREFIX = [b"tag", b"repeat", b"source_message"]
SAFE = re.compile(rb"^[A-Za-z0-9._-]+$")


def split(src, out_dir):
    data = open(src, "rb").read()
    lines = data.split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    if not lines:
        raise SystemExit("空のファイル")
    head = lines[0].split(b"\t")
    if head[:3] != PREFIX:
        raise SystemExit("先頭3列が tag,repeat,source_message ではない")
    header = b"\t".join(head[3:])
    groups = {}
    for ln in lines[1:]:
        if not ln:
            continue
        parts = ln.split(b"\t", 3)
        if len(parts) < 4:
            raise SystemExit("列が足りない行がある")
        tag, rep, sm, rest = parts
        for v in (tag, rep, sm):
            if not SAFE.match(v):
                raise SystemExit("フォルダ名・ファイル名に使えない値: %r" % v[:40])
        groups.setdefault((tag, rep, sm), []).append(rest)
    made = {}
    for (tag, rep, sm), rows in groups.items():
        d = os.path.join(out_dir, tag.decode(), "r" + rep.decode())
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, sm.decode() + ".tsv")
        if os.path.exists(path):
            raise SystemExit("既にある（上書きしない）: " + path)
        with open(path, "wb") as f:
            f.write(header + b"\n" + b"\n".join(rows) + b"\n")
        made.setdefault((tag.decode(), rep.decode()), 0)
        made[(tag.decode(), rep.decode())] += 1
    return made


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    made = split(a.src, a.out_dir)
    for (tag, rep), n in sorted(made.items()):
        print("%s\tr%s\t投稿=%d" % (tag, rep, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
