#!/usr/bin/env python3
"""settings.json の autoMode.allow から、「private repo 前提の許可」1件だけを取り除く。

- 対象は、先頭80字が TARGET_PREFIX と完全に一致する要素。ちょうど1件でなければ何も変えず止まる。
  （0件 = 対象なし・終了コード0 / 2件以上 = 異常・終了コード1）
- 1件のときだけ、settings.json を settings.json.bak-<日時> に写してから取り除く。
- 取り除いた文の全文は <ログ置き場>/removed-allow-<日時>.txt に保存する（リポジトリの外）。
- 画面には全文を出さない。件数・sha256・台帳に追記する1行（先頭20語のみ）を表示する。

使い方: python3 po_remove_private_repo_rule.py <settings.json のパス> [ログ置き場（省略時 ~/.claude/logs）]
"""
import datetime
import hashlib
import json
import os
import shutil
import sys

TARGET_PREFIX = (
    "Recording production-derived records in this private repository (PO decision 202"
)
PREFIX_LEN = 80
HEAD_WORDS = 20
REASON = "repo は PUBLIC。critique 指摘 1（2026-10-13）。PO 決定 y"


def main():
    if len(sys.argv) not in (2, 3):
        print(
            "usage: po_remove_private_repo_rule.py <settings.json> [log_dir]",
            file=sys.stderr,
        )
        return 2
    path = sys.argv[1]
    log_dir = sys.argv[2] if len(sys.argv) == 3 else os.path.expanduser("~/.claude/logs")

    if len(TARGET_PREFIX) != PREFIX_LEN:
        print("ERROR: TARGET_PREFIX length is not %d; no change" % PREFIX_LEN, file=sys.stderr)
        return 1

    with open(path, encoding="utf-8") as f:
        settings = json.load(f)
    allow = settings.get("autoMode", {}).get("allow")
    if not isinstance(allow, list):
        print("ERROR: autoMode.allow is not a list; no change", file=sys.stderr)
        return 1

    hits = [
        i
        for i, item in enumerate(allow)
        if isinstance(item, str) and item[:PREFIX_LEN] == TARGET_PREFIX
    ]
    print("matches: %d (autoMode.allow has %d entries)" % (len(hits), len(allow)))
    if len(hits) == 0:
        print("対象なし: no change")
        return 0
    if len(hits) > 1:
        print("ERROR: matches %d (expected exactly 1); no change" % len(hits), file=sys.stderr)
        return 1

    index = hits[0]
    removed = allow[index]
    digest = hashlib.sha256(removed.encode("utf-8")).hexdigest()
    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    backup = "%s.bak-%s" % (path, stamp)
    shutil.copy2(path, backup)
    print("backup: %s" % backup)

    os.makedirs(log_dir, exist_ok=True)
    saved = os.path.join(log_dir, "removed-allow-%s.txt" % stamp)
    with open(saved, "w", encoding="utf-8") as f:
        f.write(removed)
        f.write("\n")
    print("saved removed text (outside repo): %s" % saved)

    new_allow = allow[:index] + allow[index + 1 :]
    settings["autoMode"]["allow"] = new_allow
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("removed index %d: autoMode.allow now has %d entries" % (index, len(new_allow)))
    print("removed sha256: %s" % digest)

    head20 = " ".join(removed.split()[:HEAD_WORDS])
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    change = "remove: sha256=%s 先頭20語「%s」（全文は repo 外 %s を参照）" % (
        digest,
        head20,
        saved,
    )
    row = "| %s | 結果 | PO | 適用（PO） | %s | %s | - | - | %s | - | - |" % (
        now,
        change,
        REASON,
        backup,
    )
    print("--- 台帳に追記する1行 ---")
    print(row)
    return 0


sys.exit(main())
