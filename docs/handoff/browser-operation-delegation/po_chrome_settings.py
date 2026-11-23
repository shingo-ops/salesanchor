#!/usr/bin/env python3
"""ADR-1085: settings.json に chrome-op-guard の登録2件（PreToolUse・PostToolUse）を足す／外す／確かめる。
既存の登録は変えない。コマンド文字列以外の値は表示しない。

使い方:
  python3 po_chrome_settings.py add    <settings.json のパス>
  python3 po_chrome_settings.py remove <settings.json のパス>
  python3 po_chrome_settings.py check  <settings.json のパス>   # 2件とも登録されていれば exit 0、でなければ exit 1
"""
import json
import os
import sys
import tempfile

MATCHER = "mcp__claude-in-chrome__.*"
GUARD = "chrome_op_guard.py"
RECORD = "chrome_op_record.py"
BASE = "$HOME/.claude/scripts/chrome-op-guard/"
WANT = (("PreToolUse", GUARD), ("PostToolUse", RECORD))


def command_for(script):
    return "python3 " + BASE + script


def is_ours(e, script):
    if not isinstance(e, dict) or e.get("matcher") != MATCHER:
        return False
    hs = e.get("hooks", [])
    return len(hs) == 1 and str(hs[0].get("command", "")).rstrip().endswith("/chrome-op-guard/" + script)


def save(path, settings):
    st = os.stat(path)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".settings.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.chmod(tmp, st.st_mode & 0o7777)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("add", "remove", "check"):
        print("usage: po_chrome_settings.py add|remove|check <settings.json>", file=sys.stderr)
        return 2
    mode, path = sys.argv[1], sys.argv[2]
    with open(path, encoding="utf-8") as f:
        settings = json.load(f)
    hooks = settings.setdefault("hooks", {}) if mode == "add" else settings.get("hooks", {})
    changed = False
    present = 0
    for event, script in WANT:
        entries = hooks.setdefault(event, []) if mode == "add" else hooks.get(event, [])
        ours = [e for e in entries if is_ours(e, script)]
        if mode == "check":
            present += 1 if ours else 0
        elif mode == "add":
            if ours:
                print("already registered: %s %s (no change)" % (event, MATCHER))
            else:
                entries.append({"matcher": MATCHER, "hooks": [{"type": "command", "command": command_for(script)}]})
                changed = True
                print("registered: %s %s (entries=%d)" % (event, MATCHER, len(entries)))
        else:
            if ours:
                hooks[event] = [e for e in entries if not is_ours(e, script)]
                changed = True
                print("removed: %s %s (entries=%d)" % (event, MATCHER, len(hooks[event])))
            else:
                print("not registered: %s (no change)" % event)
    if mode == "check":
        print("registered" if present == 2 else "not registered (%d/2)" % present)
        return 0 if present == 2 else 1
    if changed:
        save(path, settings)
    return 0


sys.exit(main())
