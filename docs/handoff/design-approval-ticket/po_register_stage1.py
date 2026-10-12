#!/usr/bin/env python3
"""settings.json の hooks.PermissionDenied に permission-denied-log.sh を1件足す（同じものが登録済みなら何もしない）。

使い方: python3 po_register_stage1.py <settings.json のパス>
"""
import json
import sys

ENTRY = {
    "matcher": "*",
    "hooks": [
        {
            "type": "command",
            "command": "bash /Users/tanizawashingo/.claude/scripts/permission-denied-log.sh",
        }
    ],
}


def main():
    if len(sys.argv) != 2:
        print("usage: po_register_stage1.py <settings.json>", file=sys.stderr)
        return 2
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        settings = json.load(f)

    hooks = settings.setdefault("hooks", {})
    entries = hooks.setdefault("PermissionDenied", [])
    if ENTRY in entries:
        print("already registered: hooks.PermissionDenied (no change)")
        return 0

    entries.append(ENTRY)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("registered: hooks.PermissionDenied now has %d entr%s" % (len(entries), "y" if len(entries) == 1 else "ies"))
    return 0


sys.exit(main())
