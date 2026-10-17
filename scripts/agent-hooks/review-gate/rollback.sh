#!/bin/bash
# rollback.sh — install.sh で足した review-gate (ADR-1029) を外す。PO が `!` で実行する。
# settings.json の hooks 2 件と、~/.claude/agents/reviewer.md の印の節だけを外す
# （他の変更を巻き戻さないため .bak の丸ごと戻しはしない）。
# 設計: docs/handoff/review-gate-hook/design.md §5-5
set -eu

CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
DEST="$CLAUDE_DIR/scripts/review-gate"
SETTINGS="$CLAUDE_DIR/settings.json"
AGENT="$CLAUDE_DIR/agents/reviewer.md"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

if [ -f "$SETTINGS" ]; then
  cp "$SETTINGS" "$SETTINGS.bak-review-gate-rollback-$STAMP"
  SETTINGS="$SETTINGS" DEST="$DEST" python3 - <<'PY'
import glob, json, os
p = os.environ["SETTINGS"]
dest = os.environ["DEST"]
# 導入前の姿 = いちばん古い install 時の .bak。無ければ空の項目は消さない
baks = sorted(glob.glob(p + ".bak-review-gate-[0-9]*"))
orig = None
if baks:
    with open(baks[0], encoding="utf-8") as f:
        orig = json.load(f)
targets = {"python3 %s/gate.py" % dest, "python3 %s/record.py" % dest}
with open(p, encoding="utf-8") as f:
    d = json.load(f)
hooks = d.get("hooks", {})
for event in list(hooks):
    new = []
    for e in hooks[event]:
        kept = [h for h in e.get("hooks", []) if h.get("command") not in targets]
        if kept:
            e = dict(e)
            e["hooks"] = kept
            new.append(e)
        elif not e.get("hooks"):
            new.append(e)
    if new or orig is None or event in (orig.get("hooks") or {}):
        hooks[event] = new
    else:
        del hooks[event]
if not hooks and orig is not None and "hooks" not in orig:
    d.pop("hooks", None)
tmp = p + ".tmp-review-gate"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
    f.write("\n")
with open(tmp, encoding="utf-8") as f:
    json.load(f)
os.replace(tmp, p)
PY
fi

if [ -f "$AGENT" ] && grep -qF '<!-- review-gate:ADR-1029 -->' "$AGENT"; then
  cp "$AGENT" "$AGENT.bak-review-gate-rollback-$STAMP"
  AGENT="$AGENT" python3 - <<'PY'
import os, re
p = os.environ["AGENT"]
s = open(p, encoding="utf-8").read()
s = re.sub(r"\n?<!-- review-gate:ADR-1029 -->\n.*?<!-- /review-gate:ADR-1029 -->\n?", "", s, flags=re.S)
open(p, "w", encoding="utf-8").write(s)
PY
fi

echo "ROLLBACK_OK"
