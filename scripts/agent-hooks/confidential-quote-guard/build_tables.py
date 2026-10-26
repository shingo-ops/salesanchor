#!/usr/bin/env python3
"""除外表のうち「状態の言葉の写し」と「商品名の写し」を、手元の写しから作り直す。

使い方:
  python3 build_tables.py --conds <conds.json> --products <products.jsonl> [--out <社外秘フォルダ>]

  --conds     状態マスタの写し (JSON の配列。canonical / search_kw / aliases を使う)
  --products  共用商品マスタの写し (1 行 1 JSON。name / name_en / kw を使う。読み取り専用の道 ADR-1024 で取り出したもの)
  --out       出力先。省略時は ~/CC報告ファイル-keep/confid-guard

出力: status-words.txt, product-names.txt (1 行 1 語。先頭の # 行に作った日付)。
このスクリプトに語句・原文は入れない。出力は社外秘フォルダにだけ置き、repo に入れない。
標準出力は件数だけ。週の点検 (design.md 維持の仕組み) で 7 日より古ければ取り直す。
"""
import argparse
import datetime
import json
import os
import re

SPLIT = re.compile(r"[,、/\s|;]+")


def add(acc, v):
    if isinstance(v, str):
        for p in SPLIT.split(v):
            if p:
                acc.add(p)
    elif isinstance(v, list):
        for x in v:
            add(acc, x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conds", required=True)
    ap.add_argument("--products", required=True)
    ap.add_argument("--out", default="~/CC報告ファイル-keep/confid-guard")
    a = ap.parse_args()
    out = os.path.expanduser(a.out)
    os.makedirs(out, exist_ok=True)
    today = datetime.date.today().isoformat()

    status = set()
    with open(os.path.expanduser(a.conds), encoding="utf-8") as f:
        for r in json.load(f):
            for k in ("canonical", "search_kw", "aliases"):
                add(status, r.get(k))

    prod = set()
    with open(os.path.expanduser(a.products), encoding="utf-8") as f:
        for ln in f:
            if not ln.strip():
                continue
            r = json.loads(ln)
            for k in ("name", "name_en"):
                v = r.get(k)
                if isinstance(v, str) and v.strip():
                    prod.add(v.strip())
            add(prod, r.get("kw"))
            if isinstance(r.get("name"), str):
                add(prod, r["name"])  # 空白で区切った断片も除外に含める

    for name, words in (("status-words.txt", status), ("product-names.txt", prod)):
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write("# built: %s\n" % today)
            for w in sorted(words):
                f.write(w + "\n")
    print("status-words=%d product-names=%d built=%s" % (len(status), len(prod), today))


if __name__ == "__main__":
    main()
