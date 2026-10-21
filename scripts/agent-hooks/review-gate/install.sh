#!/bin/bash
# install.sh — review-gate (ADR-1029) を ~/.claude に導入する。PO が `!` で実行する（ADR-1011:39）。
# 何度流しても同じ結果（冪等）。戻すときは rollback.sh。
# 設計: docs/handoff/review-gate-hook/design.md §5-5
set -eu

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
DEST="$CLAUDE_DIR/scripts/review-gate"
SETTINGS="$CLAUDE_DIR/settings.json"
AGENT="$CLAUDE_DIR/agents/reviewer.md"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
MARK='<!-- review-gate:ADR-1029 -->'

# 1. 台本を写す (読み取り専用)
mkdir -p "$DEST"
for f in record.py gate.py; do
  [ -f "$DEST/$f" ] && chmod 755 "$DEST/$f"
  cp "$SRC/$f" "$DEST/$f"
  chmod 555 "$DEST/$f"
done

# 2. 記録の置き場
mkdir -p "$CLAUDE_DIR/review-gate/records"
chmod 700 "$CLAUDE_DIR/review-gate" "$CLAUDE_DIR/review-gate/records"

# 3-4. settings.json に hooks を 2 件足す (既にあれば足さない)
[ -f "$SETTINGS" ] || { echo "settings.json がありません: $SETTINGS" >&2; exit 1; }
cp "$SETTINGS" "$SETTINGS.bak-review-gate-$STAMP"
SETTINGS="$SETTINGS" DEST="$DEST" python3 - <<'PY'
import json, os
p = os.environ["SETTINGS"]
dest = os.environ["DEST"]
with open(p, encoding="utf-8") as f:
    d = json.load(f)
hooks = d.setdefault("hooks", {})

def add(event, matcher, command):
    arr = hooks.setdefault(event, [])
    for e in arr:
        for h in e.get("hooks", []):
            if h.get("command") == command:
                return
    arr.append({"matcher": matcher, "hooks": [{"type": "command", "command": command}]})

add("PreToolUse", "Bash|Write|Edit|MultiEdit|NotebookEdit|Agent", "python3 %s/gate.py" % dest)
add("PostToolUse", "SubagentHandback", "python3 %s/record.py" % dest)
tmp = p + ".tmp-review-gate"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
    f.write("\n")
with open(tmp, encoding="utf-8") as f:
    json.load(f)  # JSON として読めるか確認
os.replace(tmp, p)
PY

# 5. ~/.claude/agents/reviewer.md の末尾に決まりを足す (印があれば足さない)
if [ -f "$AGENT" ]; then
  if ! grep -qF "$MARK" "$AGENT"; then
    cp "$AGENT" "$AGENT.bak-review-gate-$STAMP"
    {
      printf '\n%s\n' "$MARK"
      cat "$SRC/reviewer-verdict-rule.md"
      printf '%s\n' "<!-- /review-gate:ADR-1029 -->"
    } >> "$AGENT"
  fi
else
  mkdir -p "$(dirname "$AGENT")"
  {
    printf '%s\n' "$MARK"
    cat "$SRC/reviewer-verdict-rule.md"
    printf '%s\n' "<!-- /review-gate:ADR-1029 -->"
  } > "$AGENT"
fi

# 6. 写した先の台本で試験を流す
if REVIEW_GATE_SKIP_ROUNDTRIP=1 bash "$SRC/test_review_gate.sh" "$DEST"; then
  echo "INSTALL_OK"
else
  echo "INSTALL_FAILED: 試験が通りません。rollback.sh で外してください" >&2
  exit 1
fi
