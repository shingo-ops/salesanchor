#!/bin/bash
# install.sh — mac-test-guard を ~/.claude に導入する。PO が `!` で実行する。何度流しても同じ結果（冪等）。戻すときは rollback.sh。
# 設計: docs/handoff/mac-test-guard/design.md §9
# 手順: ①写す ②原本と diff ③写した先で試験 ④settings.json の写しを取り mac-vm-guard.py の直後に登録 ⑤JSON を確認して置換
set -eu

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
DEST="$CLAUDE_DIR/scripts/mac-test-guard"
SETTINGS="$CLAUDE_DIR/settings.json"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

# 1. 原本を写す (読み取り専用)
mkdir -p "$DEST"
[ -f "$DEST/guard.py" ] && chmod 755 "$DEST/guard.py"
cp "$SRC/guard.py" "$DEST/guard.py"
chmod 555 "$DEST/guard.py"

# 2. 原本と同じか
diff -q "$SRC/guard.py" "$DEST/guard.py" >/dev/null || { echo "INSTALL_FAILED: 写したものが原本と違います" >&2; exit 1; }

# 3. 写した先の guard.py で試験 (通らなければ settings.json に触らない)
if ! python3 "$SRC/test_guard.py" "$DEST/guard.py" >/dev/null; then
  echo "INSTALL_FAILED: 試験が通りません。登録していません" >&2
  exit 1
fi

# 4. settings.json に登録 (mac-vm-guard.py の直後。既にあれば足さない)
[ -f "$SETTINGS" ] || { echo "INSTALL_FAILED: settings.json がありません: $SETTINGS" >&2; exit 1; }
cp "$SETTINGS" "$SETTINGS.bak-mac-test-guard-$STAMP"
SETTINGS="$SETTINGS" DEST="$DEST" python3 - <<'PY'
import json, os
p = os.environ["SETTINGS"]
cmd = "python3 %s/guard.py" % os.environ["DEST"]
with open(p, encoding="utf-8") as f:
    d = json.load(f)
arr = d.setdefault("hooks", {}).setdefault("PreToolUse", [])
done = any(h.get("command") == cmd for e in arr for h in e.get("hooks", []))
if not done:
    new = {"type": "command", "command": cmd}
    placed = False
    for e in arr:
        if e.get("matcher") == "Bash":
            hs = e.setdefault("hooks", [])
            for i, h in enumerate(hs):
                if str(h.get("command", "")).endswith("mac-vm-guard.py"):
                    hs.insert(i + 1, new)
                    placed = True
                    break
        if placed:
            break
    if not placed:
        arr.append({"matcher": "Bash", "hooks": [new]})
tmp = p + ".tmp-mac-test-guard"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
    f.write("\n")
with open(tmp, encoding="utf-8") as f:
    json.load(f)  # JSON として読めるか確認
os.replace(tmp, p)
PY

echo "INSTALL_OK"
