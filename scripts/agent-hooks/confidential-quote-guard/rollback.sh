#!/bin/bash
# rollback.sh — install.sh で足した confidential-quote-guard (ADR-1045) の登録を外す。PO が `!` で実行する。
# settings.json の登録 1 つだけを外す（他の変更を巻き戻さないため .bak の丸ごと戻しはしない）。
# 表 2 つ・商品名の写し・写したスクリプトは消さずに残す（登録が無ければ動かない）。
# 設計: docs/handoff/confidential-quote-guard/design.md §9
set -eu

CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
DEST="$CLAUDE_DIR/scripts/confidential-quote-guard"
SETTINGS="$CLAUDE_DIR/settings.json"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

if [ -f "$SETTINGS" ]; then
  cp "$SETTINGS" "$SETTINGS.bak-confidential-quote-guard-rollback-$STAMP"
  SETTINGS="$SETTINGS" DEST="$DEST" python3 - <<'PY'
import json, os
p = os.environ["SETTINGS"]
target = "python3 %s/guard.py" % os.environ["DEST"]
with open(p, encoding="utf-8") as f:
    d = json.load(f)
arr = d.get("hooks", {}).get("PreToolUse", [])
new = []
for e in arr:
    hs = e.get("hooks", [])
    kept = [h for h in hs if h.get("command") != target]
    if kept:
        e = dict(e)
        e["hooks"] = kept
        new.append(e)
    elif not hs:
        new.append(e)
if "hooks" in d and "PreToolUse" in d["hooks"]:
    d["hooks"]["PreToolUse"] = new
tmp = p + ".tmp-confidential-quote-guard"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
    f.write("\n")
with open(tmp, encoding="utf-8") as f:
    json.load(f)
os.replace(tmp, p)
PY
fi

echo "ROLLBACK_OK"
