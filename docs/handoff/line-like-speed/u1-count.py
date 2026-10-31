#!/usr/bin/env python3
"""recon §4 U1 の数え直し（設計の根拠を誰でも再現できるようにする・読むだけ）。

使い方: リポジトリの根で `python3 docs/handoff/line-like-speed/u1-count.py`
対象: frontend/src/pages の *Page.tsx（*.test.tsx を除く）。結果は 1 行 1 画面で標準出力へ。
"""
import pathlib
import re
import sys

ROOT = pathlib.Path("frontend/src/pages")
EARLY = re.compile(r"if\s*\(\s*!?\w*[Ll]oading\w*[^)]*\)\s*(\{\s*)?return\b")
TERN = re.compile(r"\{\s*\w*[Ll]oading\w*\s*\?")
GET = re.compile(r"\bapi\.get\b")
INDICATOR = re.compile(r"LoadingBlock|Spinner|Skeleton|loading-indicator|common\.loading")
# EARLY に当たるが中身を消す形ではない行（審査 1 回目で 1 本ずつ確かめた）
NOT_CLEARING = {
    "schedule/ScheduleSettingsPage.tsx": {52},       # useEffect の中の return
    "super-admin/ViewerTemplatesPage.tsx": {72},     # useEffect の中の return
    "super-admin/SupplierExtractionRulesPage.tsx": {456},  # 権限確認中の return null
}


def lines(pattern, text):
    return [i for i, line in enumerate(text.splitlines(), 1) if pattern.search(line)]


def main():
    files = sorted(p for p in ROOT.rglob("*Page.tsx") if not p.name.endswith(".test.tsx"))
    counts = {}
    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        text = p.read_text(encoding="utf-8")
        early = [n for n in lines(EARLY, text) if n not in NOT_CLEARING.get(rel, set())]
        tern = lines(TERN, text)
        get = lines(GET, text)
        ind = lines(INDICATOR, text)
        if early or tern:
            kind = "A_clear"  # 読み込み中は中身を消して印だけ出す
        elif not get:
            kind = "N_nofetch_in_file"  # このファイルでは取得しない（子の部品か hook で取る）
        elif ind:
            kind = "X_other_indicator"
        else:
            kind = "C_noindicator"
        counts[kind] = counts.get(kind, 0) + 1
        print(f"{rel}\t{kind}\tearly:{','.join(map(str, early))}\ttern:{','.join(map(str, tern))}\tget:{','.join(map(str, get))}")
    print(f"# total {len(files)} " + " ".join(f"{k}={v}" for k, v in sorted(counts.items())), file=sys.stderr)


if __name__ == "__main__":
    main()
