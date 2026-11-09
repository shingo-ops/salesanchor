#!/usr/bin/env python3
"""settings.json の autoMode.allow に PDL-1 の例外の文を足す／外す（ADR-1034 §4-6）。

- 文は実行のたびに design.md §4-6 の引用ブロック（> PDL-1: で始まる1行）から読む（直書きしない）。
- 足すのは末尾に1件。同じ文が既にあれば何もしない。外すのは PDL-1 の文だけ（他の要素は触らない）。
- 最後に item_hash（consent-audit.py の item_sha8）を `HASH=` の行で出す。

使い方: python3 po_delegation_edit.py register|unregister <settings.json> <design.md> <consent-audit.py> [<見出し> <ラベル>]
見出しとラベルを省くと `### 4-6.` と `PDL-1`（ADR-1034）。HKI-1 は `### 6-1.` `HKI-1`（ADR-1072）。
"""
import importlib.util
import json
import os
import re
import sys

HEADING = "### 4-6."


def read_statement(design_path, heading=HEADING, label="PDL-1"):
    in_section, found = False, []
    with open(design_path, encoding="utf-8") as f:
        for line in f.read().split("\n"):
            if line.startswith("### "):
                in_section = line.startswith(heading)
                continue
            if in_section and line.startswith("> %s:" % label):
                found.append(line[2:])
    if len(found) != 1:
        raise SystemExit("ERROR: design.md %s に %s の文が %d 件ある（1件のはず）。変更しない。" % (heading[4:], label, len(found)))
    return found[0]


def main():
    if len(sys.argv) not in (5, 7) or sys.argv[1] not in ("register", "unregister"):
        print("usage: po_delegation_edit.py register|unregister <settings.json> <design.md> <consent-audit.py> [<見出し> <ラベル>]", file=sys.stderr)
        return 2
    mode, path, design, audit_path = sys.argv[1:5]
    heading, label = (sys.argv[5], sys.argv[6]) if len(sys.argv) == 7 else (HEADING, "PDL-1")
    if not re.fullmatch(r"### [0-9]+(-[0-9]+)*\.", heading) or not re.fullmatch(r"[A-Z]{2,5}-[0-9]{1,3}", label):
        print("ERROR: 見出し・ラベルの形が違う。変更しない。", file=sys.stderr)
        return 2
    text = read_statement(design, heading, label)
    spec = importlib.util.spec_from_file_location("consent_audit", audit_path)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    with open(path, encoding="utf-8") as f:
        settings = json.load(f)
    allow = settings.setdefault("autoMode", {}).setdefault("allow", [])
    if not isinstance(allow, list):
        print("ERROR: autoMode.allow is not a list; no change", file=sys.stderr)
        return 1
    changed = False
    if mode == "register":
        if text in allow:
            print("no change: 同じ文が既にある")
        else:
            allow.append(text)
            changed = True
            print("added: %s を末尾に1件追加した" % label)
    else:
        if text not in allow:
            print("no change: %s は無い" % label)
        else:
            allow[:] = [x for x in allow if x != text]
            changed = True
            print("removed: %s だけを外した" % label)
    if changed:
        tmp = path + ".potmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
            f.write("\n")
        try:
            os.chmod(tmp, os.stat(path).st_mode & 0o777)
        except OSError:
            pass
        os.replace(tmp, path)
    # 読み直し
    with open(path, encoding="utf-8") as f:
        again = json.load(f)
    present = text in again.get("autoMode", {}).get("allow", [])
    if present != (mode == "register"):
        print("ERROR: 読み直しで期待と違う。控えから戻してください。", file=sys.stderr)
        return 1
    print("autoMode.allow entries: %d" % len(again["autoMode"]["allow"]))
    print("CHANGED=%s" % ("yes" if changed else "no"))
    print("HASH=%s" % audit.item_sha8(text))
    return 0


sys.exit(main())
