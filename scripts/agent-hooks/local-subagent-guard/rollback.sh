#!/bin/bash
# rollback.sh — install.sh で足した local-subagent-guard (ADR-1045) を外す。PO が `!` で実行する。
# settings.json の足した 1 項目（command が一致するもの）と写しだけを外す。log は消さない（K-c の記録のため）。
# 設計: docs/handoff/local-subagent-guard/design.md §5-5
set -eu

CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
DEST="$CLAUDE_DIR/scripts/local-subagent-guard"
SETTINGS="$CLAUDE_DIR/settings.json"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

if [ -f "$SETTINGS" ]; then
  cp "$SETTINGS" "$SETTINGS.bak-local-subagent-guard-rollback-$STAMP"
  SETTINGS="$SETTINGS" DEST="$DEST" python3 - <<'PY'
import json, os
p = os.environ["SETTINGS"]
target = "python3 -I %s/guard.py" % os.environ["DEST"]
with open(p, encoding="utf-8") as f:
    d = json.load(f)
hooks = d.get("hooks", {})
arr = hooks.get("PreToolUse")
if arr is not None:
    new = []
    for e in arr:
        kept = [h for h in e.get("hooks", []) if h.get("command") != target]
        if kept:
            e = dict(e)
            e["hooks"] = kept
            new.append(e)
        elif not e.get("hooks"):
            new.append(e)
    hooks["PreToolUse"] = new
tmp = p + ".tmp-local-subagent-guard"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
    f.write("\n")
with open(tmp, encoding="utf-8") as f:
    json.load(f)
os.replace(tmp, p)
PY
fi

if [ -d "$DEST" ]; then
  chmod -R u+w "$DEST"
  rm -rf "$DEST"
fi

echo "ROLLBACK_OK"
