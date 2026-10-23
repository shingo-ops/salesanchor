#!/usr/bin/env python3
"""新規。手元の正本 ~/.claude/agent-tokens.json の danger_ops キーだけを danger_ops.json に書き出す。
（元: ~/.claude/scripts/agent-danger-hook.sh が読む同じ一覧）
他のキーは読まない・出さない（トークンを含みうるため）。手元で正本を直したら、このスクリプトを再実行する。
使い方: python3 sync_danger_ops.py [正本のパス]
"""
import json
import os
import sys

src = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.claude/agent-tokens.json")
dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "danger_ops.json")

with open(src, encoding="utf-8") as f:
    ops = json.load(f).get("danger_ops")
if not isinstance(ops, list) or not ops or not all(isinstance(x, str) for x in ops):
    print("danger_ops が見つからない／形が違うため中止します", file=sys.stderr)
    sys.exit(1)
with open(dst, "w", encoding="utf-8") as f:
    json.dump(ops, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"danger_ops {len(ops)} 件を書き出しました")
