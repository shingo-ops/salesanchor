#!/bin/bash
# install.sh — confidential-quote-guard (ADR-1045) を ~/.claude に導入する。PO が `!` で実行する（ADR-1011:39）。
# 何度流しても同じ結果（冪等）。戻すときは rollback.sh。
# 設計: docs/handoff/confidential-quote-guard/design.md §3・§8・§9
# 手順: ①原本を写す ②写したものと原本が一字一句同じか diff ③原文の写しが無ければ本番から1回取る → 表が読めるか確認（読めなければ登録しない）
#       ④写した先の guard.py で試験 ⑤settings.json の PreToolUse:Bash に pr-body-guard.sh の前で登録
#       ⑥毎日1回の取り直し (LaunchAgent) を ~/Library/LaunchAgents に写して登録
set -eu

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
DEST="$CLAUDE_DIR/scripts/confidential-quote-guard"
SETTINGS="$CLAUDE_DIR/settings.json"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LABEL="jp.salesanchor.confidential-quote-guard-fetch"
LAUNCH_DIR="${LAUNCH_DIR:-$HOME/Library/LaunchAgents}"
GUARD_DIR="${CONFID_GUARD_DIR:-$HOME/CC報告ファイル-keep/confid-guard}"

# 1. 原本を写す (読み取り専用)
mkdir -p "$DEST"
[ -f "$DEST/guard.py" ] && chmod 755 "$DEST/guard.py"
cp "$SRC/guard.py" "$DEST/guard.py"
chmod 555 "$DEST/guard.py"
[ -f "$DEST/fetch_corpus.py" ] && chmod 755 "$DEST/fetch_corpus.py"
cp "$SRC/fetch_corpus.py" "$DEST/fetch_corpus.py"
chmod 555 "$DEST/fetch_corpus.py"

# 2. 写したものと原本が一字一句同じか (local-hooks-ssot の H3 の考え方)
diff -q "$SRC/guard.py" "$DEST/guard.py" >/dev/null || { echo "INSTALL_FAILED: 写したものが原本と違います" >&2; exit 1; }
diff -q "$SRC/fetch_corpus.py" "$DEST/fetch_corpus.py" >/dev/null || { echo "INSTALL_FAILED: 取り直しの写しが原本と違います" >&2; exit 1; }

# 2b. 原文の写し (本番から) が無い・古いときは、登録の前に1回取る (読み取りだけ。ADR-1024 の道)
if [ -z "$(find "$GUARD_DIR/source-messages.txt" -mtime -2 2>/dev/null)" ]; then
  python3 "$DEST/fetch_corpus.py" || { echo "INSTALL_FAILED: 原文の写しを本番から取れません。登録していません" >&2; exit 1; }
fi

# 3. 表が読めるか。読めないまま登録すると全部の git push が止まるので、登録の前に確かめる
if ! python3 "$DEST/guard.py" --check; then
  echo "INSTALL_FAILED: 表 (~/CC報告ファイル-keep/confid-guard) が読めません。登録していません" >&2
  exit 1
fi

# 4. 写した先の guard.py で試験を流す (本物の表・記録には触れない)
if ! python3 "$SRC/tests/test_guard.py" "$DEST/guard.py" >/dev/null || ! python3 "$SRC/tests/test_fetch.py" "$DEST/fetch_corpus.py" >/dev/null; then
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

# 6. 毎日1回の取り直し (LaunchAgent)。原本の plist の __HOME__ を置き換えて写し、登録し直す (何度流しても同じ)
mkdir -p "$LAUNCH_DIR" "$GUARD_DIR"
sed "s#__HOME__#$HOME#g" "$SRC/$LABEL.plist" > "$LAUNCH_DIR/$LABEL.plist"
plutil -lint "$LAUNCH_DIR/$LABEL.plist" >/dev/null || { echo "INSTALL_FAILED: plist が読めません" >&2; exit 1; }
if [ "${CONFID_SKIP_LAUNCHCTL:-0}" != "1" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$LAUNCH_DIR/$LABEL.plist"
fi

echo "INSTALL_OK"
