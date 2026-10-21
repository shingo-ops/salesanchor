#!/usr/bin/env python3
"""ADR-1033: hooks.PreToolUse に matcher "MultiEdit|NotebookEdit"（worktree-only-guard.sh だけ）の登録を1件足す／外す。
既存の登録は変えない。値（コマンド文字列以外）は表示しない。

使い方:
  python3 po_settings_matcher.py add    <settings.json のパス>
  python3 po_settings_matcher.py remove <settings.json のパス>
  python3 po_settings_matcher.py check  <settings.json のパス>   # 登録されていれば exit 0、無ければ exit 1
"""
import json
import os
import sys
import tempfile

MATCHER = "MultiEdit|NotebookEdit"
GUARD = "worktree-only-guard.sh"


def find_guard_command(entries):
    """既存の登録から worktree-only-guard.sh のコマンド文字列の書き方を写す。無ければ bash 付きの標準形。"""
    for e in entries:
        for h in e.get("hooks", []):
            c = h.get("command", "")
            if isinstance(c, str) and c.rstrip().endswith(GUARD):
                return c
    return "bash " + os.path.join(os.path.expanduser("~"), ".claude", "scripts", GUARD)


def is_ours(e):
    if e.get("matcher") != MATCHER:
        return False
    hs = e.get("hooks", [])
    return len(hs) == 1 and str(hs[0].get("command", "")).rstrip().endswith(GUARD)


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
        print("usage: po_settings_matcher.py add|remove|check <settings.json>", file=sys.stderr)
        return 2
    mode, path = sys.argv[1], sys.argv[2]
    with open(path, encoding="utf-8") as f:
        settings = json.load(f)
    hooks = settings.setdefault("hooks", {})
    entries = hooks.setdefault("PreToolUse", [])
    ours = [e for e in entries if is_ours(e)]

    if mode == "check":
        print("registered" if ours else "not registered")
        return 0 if ours else 1
    if mode == "add":
        if ours:
            print("already registered: PreToolUse %s (no change)" % MATCHER)
            return 0
        entry = {"matcher": MATCHER, "hooks": [{"type": "command", "command": find_guard_command(entries)}]}
        entries.append(entry)
        save(path, settings)
        print("registered: PreToolUse %s (entries=%d)" % (MATCHER, len(entries)))
        return 0
    # remove
    if not ours:
        print("not registered (no change)")
        return 0
    hooks["PreToolUse"] = [e for e in entries if not is_ours(e)]
    save(path, settings)
    print("removed: PreToolUse %s (entries=%d)" % (MATCHER, len(hooks["PreToolUse"])))
    return 0


sys.exit(main())
