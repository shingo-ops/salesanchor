#!/usr/bin/env python3
"""settings.json の autoMode.allow の末尾に、自律保守の例外の文を1件足す。

- 文は実行のたびに設計書 §5-2 の引用ブロックから読む（スクリプトに直書きしない）。
- 同じ文が既にあれば何もしない（2回実行しても変わらない）。
- 既存の要素は保つ（順序もそのまま）。

使い方: python3 po_register_self_maintenance.py <settings.json> <バックアップのパス> <設計書のパス>
"""
import hashlib
import json
import sys

HEADING = "### 5-2."
QUOTE_START = "> Permission self-maintenance"


def read_statement(design_path):
    with open(design_path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    in_section = False
    found = []
    for line in lines:
        if line.startswith("### "):
            in_section = line.startswith(HEADING)
            continue
        if in_section and line.startswith(QUOTE_START):
            found.append(line[2:])
    if len(found) != 1:
        raise SystemExit("ERROR: 設計書 §5-2 に例外の文が %d 件ある（1件のはず）。変更しない。" % len(found))
    return found[0]


def main():
    if len(sys.argv) != 4:
        print("usage: po_register_self_maintenance.py <settings.json> <backup> <design.md>", file=sys.stderr)
        return 2
    path, backup, design = sys.argv[1], sys.argv[2], sys.argv[3]
    text = read_statement(design)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()

    with open(path, encoding="utf-8") as f:
        settings = json.load(f)
    allow = settings.setdefault("autoMode", {}).setdefault("allow", [])
    if not isinstance(allow, list):
        print("ERROR: autoMode.allow is not a list; no change", file=sys.stderr)
        return 1

    if text in allow:
        print("no change: 同じ文が既にある")
    else:
        allow.append(text)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("added: 例外の文を末尾に1件追加した")
    print("autoMode.allow entries: %d" % len(allow))
    print("statement sha256: %s" % digest)
    print("")
    print("台帳に追記する行（次の回の定期実行の手順1で permission-ledger.md に追記する）:")
    print(
        "| 日時=" + __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M") + " | 種別=結果 | source=PO | 結果=適用（PO） | 変更=add: %s "
        "| バックアップ=%s |" % (text, backup)
    )
    return 0


sys.exit(main())
