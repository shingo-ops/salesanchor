#!/bin/bash
# rollback.sh — install.sh で足した confidential-quote-guard (ADR-1045) の登録を外す。PO が `!` で実行する。
# settings.json の登録 1 つだけを外す（他の変更を巻き戻さないため .bak の丸ごと戻しはしない）。
# 毎日1回の取り直し (LaunchAgent) も外す。
# 表・原文の写し・商品名の写し・写したスクリプトは消さずに残す（登録が無ければ動かない）。
# 設計: docs/handoff/confidential-quote-guard/design.md §9
set -eu

CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
DEST="$CLAUDE_DIR/scripts/confidential-quote-guard"
SETTINGS="$CLAUDE_DIR/settings.json"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LABEL="jp.salesanchor.confidential-quote-guard-fetch"
LAUNCH_DIR="${LAUNCH_DIR:-$HOME/Library/LaunchAgents}"

# 毎日の取り直しを止めて外す (無ければ何もしない)
if [ "${CONFID_SKIP_LAUNCHCTL:-0}" != "1" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
fi
rm -f "$LAUNCH_DIR/$LABEL.plist"

if [ -f "$SETTINGS" ]; then
  cp "$SETTINGS" "$SETTINGS.bak-confidential-quote-guard-rollback-$STAMP"
  SETTINGS="$SETTINGS" DEST="$DEST" python3 - <<'PY'
import glob, json, os
p = os.environ["SETTINGS"]
target = "python3 %s/guard.py" % os.environ["DEST"]
# 導入前の姿 = いちばん古い install 時の .bak。無ければ空の項目は消さない
baks = sorted(glob.glob(p + ".bak-confidential-quote-guard-[0-9]*"))
orig = None
if baks:
    with open(baks[0], encoding="utf-8") as f:
        orig = json.load(f)
with open(p, encoding="utf-8") as f:
    d = json.load(f)
hooks = d.get("hooks", {})
for event in list(hooks):
    new = []
    for e in hooks[event]:
        kept = [h for h in e.get("hooks", []) if h.get("command") != target]
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
