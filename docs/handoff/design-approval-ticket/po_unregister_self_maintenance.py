#!/usr/bin/env python3
"""settings.json の autoMode.allow から、自律保守の例外の文（設計書 §5-2）と完全一致する1件を外す。

- `SM-` で始まる文は残す。
- 一致する文がなければ何もしない。

使い方: python3 po_unregister_self_maintenance.py <settings.json> <設計書のパス>
"""
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
    if len(sys.argv) != 3:
        print("usage: po_unregister_self_maintenance.py <settings.json> <design.md>", file=sys.stderr)
        return 2
    path, design = sys.argv[1], sys.argv[2]
    text = read_statement(design)

    with open(path, encoding="utf-8") as f:
        settings = json.load(f)
    allow = settings.get("autoMode", {}).get("allow")
    if not isinstance(allow, list):
        print("ERROR: autoMode.allow is not a list; no change", file=sys.stderr)
        return 1

    if text not in allow:
        print("no change: 例外の文は登録されていない")
    else:
        idx = allow.index(text)
        settings["autoMode"]["allow"] = allow[:idx] + allow[idx + 1:]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("removed: 例外の文を1件取り除いた")
    after = settings["autoMode"]["allow"]
    kept = sum(1 for e in after if isinstance(e, str) and e.startswith("SM-"))
    print("autoMode.allow entries: %d (SM- で始まる文は %d 件残す)" % (len(after), kept))
    return 0


sys.exit(main())
