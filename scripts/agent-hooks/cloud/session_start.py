#!/usr/bin/env python3
"""新規（SessionStart）。rules.md の中身を additionalContext として返す。K5。
R4c 便2: 決まりを渡す前に、今の場所の core.hooksPath を frontend/.husky にする（new-worktree.sh と同じ値）。
設定できなくても止めず、決まりの前に 1 行の知らせを足すだけ。"""
import json
import subprocess
import sys

HOOKS_PATH = "frontend/.husky"


def set_hooks_path():
    """成功なら None、失敗なら理由の短い文を返す。例外は外に出さない。"""
    try:
        p = subprocess.run(["git", "rev-parse", "--show-toplevel"], stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=10)
        top = p.stdout.strip()
        if p.returncode != 0 or not top:
            return "git リポジトリの場所を取れませんでした"
        q = subprocess.run(["git", "-C", top, "config", "core.hooksPath", HOOKS_PATH], stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=10)
        if q.returncode != 0:
            return "git config が失敗しました"
        return None
    except subprocess.TimeoutExpired:
        return "git がタイムアウトしました"
    except Exception:
        return "git を流せませんでした"


try:
    with open(sys.argv[1], encoding="utf-8") as f:
        text = f.read()
except Exception:  # 読めなければ何も渡さず通す
    sys.exit(0)
reason = set_hooks_path()
if reason:
    text = f"core.hooksPath を設定できませんでした（{reason}）。push の前に new-worktree.sh で作業場所を作ってください\n\n" + text
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}, ensure_ascii=False))
