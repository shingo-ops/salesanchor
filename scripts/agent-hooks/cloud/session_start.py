#!/usr/bin/env python3
"""新規（SessionStart）。rules.md の中身を additionalContext として返す。K5。"""
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as f:
        text = f.read()
except Exception:  # 読めなければ何も渡さず通す
    sys.exit(0)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}, ensure_ascii=False))
