#!/bin/bash
# rollback.sh — install.sh で足した mac-test-guard の登録を外す。PO が `!` で実行する。
# settings.json の登録 1 つだけを外す。写した guard.py は消さずに残す（登録が無ければ動かない）。
# 設計: docs/handoff/mac-test-guard/design.md §11
set -eu

CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
DEST="$CLAUDE_DIR/scripts/mac-test-guard"
SETTINGS="$CLAUDE_DIR/settings.json"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

if [ -f "$SETTINGS" ]; then
  cp "$SETTINGS" "$SETTINGS.bak-mac-test-guard-rollback-$STAMP"
  SETTINGS="$SETTINGS" DEST="$DEST" python3 - <<'PY'
import json, os
p = os.environ["SETTINGS"]
target = "python3 %s/guard.py" % os.environ["DEST"]
with open(p, encoding="utf-8") as f:
    d = json.load(f)
for event, entries in (d.get("hooks") or {}).items():
    for e in entries:
        if "hooks" in e:
            e["hooks"] = [h for h in e["hooks"] if h.get("command") != target]
tmp = p + ".tmp-mac-test-guard"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
    f.write("\n")
with open(tmp, encoding="utf-8") as f:
    json.load(f)
os.replace(tmp, p)
PY
fi

echo "ROLLBACK_OK"
