#!/usr/bin/env python3
"""足す文が設計書 §5-2 (3) を満たすか判定する（読み取りだけ）。

禁止の文字列・全称の語は、実行のたびに設計書 §5-2 の引用ブロックから抜き出す
（このファイルには写さない）。1つでも抜き出せなければ、全部不合格に倒す。

使い方:
  python3 -I sm_check_entry.py (--text T | --file F | 標準入力) [--design D] [--settings S]
終了コード: 0=合格 / 1=不合格 / 2=使い方の誤り
"""
import argparse
import json
import os
import re
import sys

DEFAULT_DESIGN = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, "self-maintenance-design.md")
DEFAULT_SETTINGS = os.path.expanduser("~/.claude/settings.json")

SECTION_HEADING = "### 5-2."
QUOTE_START = "> Permission self-maintenance"
PREFIX_RE = re.compile(r"^SM-\d{4}-\d{2}-\d{2}-\d+:")
MAX_WORDS = 120
FORBIDDEN_MARK = "contains none of these strings:"
UNIVERSAL_MARK = "universal wording ("
HOST_RE = re.compile(
    r"\b\d{1,3}(?:\.\d{1,3}){3}\b|\b[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")


def read_quote(design_path):
    with open(design_path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    in_section, found = False, []
    for line in lines:
        if line.startswith("### "):
            in_section = line.startswith(SECTION_HEADING)
            continue
        if in_section and line.startswith(QUOTE_START):
            found.append(line[2:])
    if len(found) != 1:
        raise ValueError("設計書 §5-2 に例外の文が %d 件ある（1件のはず）" % len(found))
    return found[0]


def backticked(segment):
    return re.findall(r"`([^`]+)`", segment)


def extract_lists(quote):
    start = quote.find(FORBIDDEN_MARK)
    end = quote.find("; uses no universal wording")
    if start < 0 or end < start:
        raise ValueError("禁止の文字列の一覧を §5-2 から抜き出せない")
    forbidden = backticked(quote[start + len(FORBIDDEN_MARK):end])
    ustart = quote.find(UNIVERSAL_MARK)
    uend = quote.find(")", ustart) if ustart >= 0 else -1
    if ustart < 0 or uend < 0:
        raise ValueError("全称の語の一覧を §5-2 から抜き出せない")
    universal = backticked(quote[ustart + len(UNIVERSAL_MARK):uend])
    if not forbidden or not universal:
        raise ValueError("一覧が空")
    return forbidden, universal


def environment_hosts(settings_path):
    """autoMode.environment の文に出てくるホストのアドレス（IP・ドメイン）。"""
    with open(settings_path, encoding="utf-8") as f:
        settings = json.load(f)
    env = settings.get("autoMode", {}).get("environment", [])
    if not isinstance(env, list):
        raise ValueError("autoMode.environment が配列でない")
    hosts = set()
    for item in env:
        if isinstance(item, str):
            hosts.update(HOST_RE.findall(item))
    return sorted(hosts)


def check(text, forbidden, universal, hosts):
    lowered = text.lower()
    results = []

    def add(name, ok, detail=""):
        results.append({"check": name, "ok": ok, "detail": detail})

    add("prefix", bool(PREFIX_RE.match(text)), "先頭が SM-YYYY-MM-DD-N: の形")
    words = len(text.split())
    add("max_words", words <= MAX_WORDS, "%d 語（上限 %d）" % (words, MAX_WORDS))
    hit = [s for s in forbidden if s.lower() in lowered]
    add("forbidden_strings", not hit, "当たった: %s" % ", ".join(hit) if hit else "当たりなし")
    hit_u = [w for w in universal if re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(w.lower()), lowered)]
    add("universal_words", not hit_u, "当たった: %s" % ", ".join(hit_u) if hit_u else "当たりなし")
    hit_h = [h for h in hosts if h.lower() in lowered]
    add("environment_hosts", not hit_h, "ホスト %d 件を照合" % len(hosts) + (("、当たりあり: %d 件" % len(hit_h)) if hit_h else ""))
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--text")
    src.add_argument("--file")
    ap.add_argument("--design", default=DEFAULT_DESIGN)
    ap.add_argument("--settings", default=DEFAULT_SETTINGS)
    args = ap.parse_args(argv)

    if args.text is not None:
        text = args.text
    elif args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()
    text = text.strip()

    try:
        forbidden, universal = extract_lists(read_quote(args.design))
        hosts = environment_hosts(args.settings)
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    results = check(text, forbidden, universal, hosts)
    ok = all(r["ok"] for r in results)
    print(json.dumps({"ok": ok, "words": len(text.split()), "checks": results}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
