#!/usr/bin/env python3
"""autoMode.allow の「SM- で始まる文」だけを足す・外す。順序: バックアップ → pending.json → 変更。

  add     --text T      足す（sm_check_entry.py に通してから）
  remove  --text T      外す（SM- の文に限る）
  recover               pending.json に書いた SM- の文1件だけを外し、pending.json を .done-<日時> に改名
  --clear-pending       pending.json を消す（台帳の結果行がマージされたあとにだけ使う）

settings.json 全体は戻さない。SM- でない文には触れない。
既定のパスは本物（~/.claude/）。引数で差し替えられる。標準ライブラリだけ。

使い方: python3 -I sm_apply.py <add|remove|recover|--clear-pending> [--text T] [--settings S]
         [--pending P] [--design D]
終了コード: 0=成功 / 1=拒否・失敗 / 2=使い方の誤り
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SETTINGS = os.path.expanduser("~/.claude/settings.json")
DEFAULT_PENDING = os.path.expanduser("~/.claude/logs/permission-maintenance-pending.json")
DEFAULT_DESIGN = os.path.join(HERE, os.pardir, "self-maintenance-design.md")
CHECK_SCRIPT = os.path.join(HERE, "sm_check_entry.py")
SM_PREFIX = "SM-"


def stamp():
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S")


def fail(message):
    print("REFUSED: %s" % message, file=sys.stderr)
    return 1


def load_settings(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_settings(path, settings):
    mode = os.stat(path).st_mode & 0o777
    tmp = path + ".tmp-sm"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def allow_list(settings):
    allow = settings.get("autoMode", {}).get("allow")
    if not isinstance(allow, list):
        raise ValueError("autoMode.allow が配列でない")
    return allow


def with_allow(settings, new_allow):
    return {**settings, "autoMode": {**settings["autoMode"], "allow": new_allow}}


def backup(path):
    dest = "%s.bak-%s" % (path, stamp())
    shutil.copy2(path, dest)
    with open(path, "rb") as a, open(dest, "rb") as b:
        if a.read() != b.read():
            raise OSError("バックアップが元と一致しない")
    return dest


def write_pending(path, action, text, backup_path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    payload = {"action": action, "statement": text,
               "statement_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
               "backup": backup_path,
               "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def run_check(text, args):
    cmd = [sys.executable, "-I", CHECK_SCRIPT, "--text", text, "--design", args.design,
           "--settings", args.settings]
    return subprocess.run(cmd, capture_output=True, text=True).returncode == 0


def do_change(args, action):
    text = (args.text or "").strip()
    if not text.startswith(SM_PREFIX):
        return fail("SM- で始まる文だけが対象")
    if os.path.exists(args.pending):
        return fail("pending.json が残っている。recover か --clear-pending が先")
    try:
        settings = load_settings(args.settings)
        allow = allow_list(settings)
    except (OSError, ValueError) as exc:
        return fail(str(exc))
    if action == "add":
        if text in allow:
            return fail("同じ文が既にある")
        if not run_check(text, args):
            return fail("sm_check_entry.py が不合格")
        new_allow = allow + [text]
    else:
        if text not in allow:
            return fail("外す対象が無い")
        idx = allow.index(text)
        new_allow = allow[:idx] + allow[idx + 1:]
    backup_path = backup(args.settings)
    write_pending(args.pending, action, text, backup_path)
    write_settings(args.settings, with_allow(settings, new_allow))
    print("%s: done. allow entries %d -> %d. backup=%s pending=%s"
          % (action, len(allow), len(new_allow), backup_path, args.pending))
    return 0


def do_recover(args):
    if not os.path.isfile(args.pending):
        return fail("pending.json が無い")
    try:
        with open(args.pending, encoding="utf-8") as f:
            text = json.load(f)["statement"]
        settings = load_settings(args.settings)
        allow = allow_list(settings)
    except (OSError, ValueError, KeyError) as exc:
        return fail(str(exc))
    if not isinstance(text, str) or not text.startswith(SM_PREFIX):
        return fail("pending.json の文が SM- で始まらない。何も変えない")
    if text in allow:
        idx = allow.index(text)
        write_settings(args.settings, with_allow(settings, allow[:idx] + allow[idx + 1:]))
        print("recover: removed 1 entry (allow %d -> %d)" % (len(allow), len(allow) - 1))
    else:
        print("recover: entry not present; nothing removed")
    done = "%s.done-%s" % (args.pending, stamp())
    os.replace(args.pending, done)
    print("pending renamed to %s" % done)
    return 0


def do_clear(args):
    if not os.path.isfile(args.pending):
        return fail("pending.json が無い")
    os.remove(args.pending)
    print("pending cleared: %s" % args.pending)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("command", nargs="?", choices=("add", "remove", "recover"))
    ap.add_argument("--clear-pending", action="store_true")
    ap.add_argument("--text")
    ap.add_argument("--settings", default=DEFAULT_SETTINGS)
    ap.add_argument("--pending", default=DEFAULT_PENDING)
    ap.add_argument("--design", default=DEFAULT_DESIGN)
    args = ap.parse_args(argv)
    if args.clear_pending:
        if args.command:
            ap.error("--clear-pending は単独で使う")
        return do_clear(args)
    if args.command in ("add", "remove"):
        return do_change(args, args.command)
    if args.command == "recover":
        return do_recover(args)
    ap.error("add / remove / recover / --clear-pending のどれかが要る")


if __name__ == "__main__":
    sys.exit(main())
