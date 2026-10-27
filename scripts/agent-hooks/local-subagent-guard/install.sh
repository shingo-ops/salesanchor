#!/bin/bash
# install.sh — local-subagent-guard (ADR-1046) を ~/.claude に導入する。PO が `!` で実行する（ADR-1011:39）。
# 何度流しても同じ結果（冪等）。戻すときは rollback.sh。
# 設計: docs/handoff/local-subagent-guard/design.md §5-5
set -eu

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLOUD="$SRC/../cloud"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
DEST="$CLAUDE_DIR/scripts/local-subagent-guard"
SETTINGS="$CLAUDE_DIR/settings.json"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
MATCHER='Write|Edit|MultiEdit|NotebookEdit|EnterWorktree|ExitWorktree|Bash|Monitor'

[ -f "$SETTINGS" ] || { echo "settings.json がありません: $SETTINGS" >&2; exit 1; }
[ -f "$CLOUD/guard_pre_tool.py" ] || { echo "見つかりません: $CLOUD/guard_pre_tool.py" >&2; exit 1; }

# 1. 台本を写す (読み取り専用)
mkdir -p "$DEST"
for f in "$SRC/guard.py" "$CLOUD/guard_pre_tool.py"; do
  n="$(basename "$f")"
  [ -f "$DEST/$n" ] && chmod 755 "$DEST/$n"
  cp "$f" "$DEST/$n"
  chmod 555 "$DEST/$n"
done

# 2. 写した元の commit と sha256
{
  echo "commit: $(git -C "$SRC" rev-parse HEAD)"
  echo "installed: $STAMP"
  for n in guard.py guard_pre_tool.py; do
    if command -v sha256sum >/dev/null 2>&1; then (cd "$DEST" && sha256sum "$n"); else (cd "$DEST" && shasum -a 256 "$n"); fi
  done
} > "$DEST/installed-from.txt"

# 3. settings.json の PreToolUse に 1 項目を足す (同じ command があれば足さない)
cp "$SETTINGS" "$SETTINGS.bak-local-subagent-guard-$STAMP"
SETTINGS="$SETTINGS" DEST="$DEST" MATCHER="$MATCHER" python3 - <<'PY'
import json, os
p = os.environ["SETTINGS"]
command = "python3 -I %s/guard.py" % os.environ["DEST"]
with open(p, encoding="utf-8") as f:
    d = json.load(f)
arr = d.setdefault("hooks", {}).setdefault("PreToolUse", [])
if not any(h.get("command") == command for e in arr for h in e.get("hooks", [])):
    arr.append({"matcher": os.environ["MATCHER"], "hooks": [{"type": "command", "command": command}]})
tmp = p + ".tmp-local-subagent-guard"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
    f.write("\n")
with open(tmp, encoding="utf-8") as f:
    json.load(f)  # JSON として読めるか確認
os.replace(tmp, p)
PY

echo "INSTALL_OK"
