#!/bin/bash
# install.sh — confidential-quote-guard (ADR-1045) を ~/.claude に導入する。PO が `!` で実行する（ADR-1011:39）。
# 何度流しても同じ結果（冪等）。戻すときは rollback.sh。
# 設計: docs/handoff/confidential-quote-guard/design.md §3・§8・§9
# 手順: ①原本を写す ②写したものと原本が一字一句同じか diff ③表が読めるか確認（読めなければ登録しない）
#       ④写した先の guard.py で試験 ⑤settings.json の PreToolUse:Bash に pr-body-guard.sh の前で登録
set -eu

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
DEST="$CLAUDE_DIR/scripts/confidential-quote-guard"
SETTINGS="$CLAUDE_DIR/settings.json"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

# 1. 原本を写す (読み取り専用)
mkdir -p "$DEST"
[ -f "$DEST/guard.py" ] && chmod 755 "$DEST/guard.py"
cp "$SRC/guard.py" "$DEST/guard.py"
chmod 555 "$DEST/guard.py"

# 2. 写したものと原本が一字一句同じか (local-hooks-ssot の H3 の考え方)
diff -q "$SRC/guard.py" "$DEST/guard.py" >/dev/null || { echo "INSTALL_FAILED: 写したものが原本と違います" >&2; exit 1; }

# 3. 表が読めるか。読めないまま登録すると全部の git push が止まるので、登録の前に確かめる
if ! python3 "$DEST/guard.py" --check; then
  echo "INSTALL_FAILED: 表 (~/CC報告ファイル-keep/confid-guard) が読めません。登録していません" >&2
  exit 1
fi

# 4. 写した先の guard.py で試験を流す (本物の表・記録には触れない)
if ! python3 "$SRC/tests/test_guard.py" "$DEST/guard.py" >/dev/null; then
  echo "INSTALL_FAILED: 試験が通りません。登録していません" >&2
  exit 1
fi

# 5. settings.json の PreToolUse:Bash に登録 (pr-body-guard.sh の前。既にあれば足さない)
[ -f "$SETTINGS" ] || { echo "settings.json がありません: $SETTINGS" >&2; exit 1; }
cp "$SETTINGS" "$SETTINGS.bak-confidential-quote-guard-$STAMP"
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
            hs = e.get("hooks", [])
            for i, h in enumerate(hs):
                if str(h.get("command", "")).endswith("pr-body-guard.sh"):
                    hs.insert(i, new)
                    placed = True
                    break
        if placed:
            break
    if not placed:
        arr.append({"matcher": "Bash", "hooks": [new]})
tmp = p + ".tmp-confidential-quote-guard"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
    f.write("\n")
with open(tmp, encoding="utf-8") as f:
    json.load(f)  # JSON として読めるか確認
os.replace(tmp, p)
PY

echo "INSTALL_OK"
