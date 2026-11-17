#!/usr/bin/env python3
"""流し終えた手順の書き換え・削除を止める（段5 5-3・K5-10。設計 §5-7「書き換えを止める CI の決まり」）。

比べる起点:
  TIP = PR の宛先の枝の最新（台本の中で取り直す。--tip で渡したときはそれを使う。試験用）。
  MB  = git merge-base TIP head（出来事に入った古い値から MB を出さない）。
  「比べる元」の本体として読む物（記録の対象・記録の外の一覧）は MB から取る。
  凍らせるファイルだけは MB と TIP の両方の「記録の対象」を合わせる（遅れた枝が、MB の後に
  登録されたファイルを書き換えても通さないため）。
  限界: CI が流れた後に main で登録された物は、その PR の CI を流し直すまで拾わない。

凍らせるファイル: 記録の対象のファイル（本体の ^run_(sql|py) の行から記録の外を除いた物）と、
  そのうち run_py の台本が読む SQL（P13 の決まり。scripts/lib/migration_record.sh の mr_py_sql_names と同じ結果）。

記録の外の一覧: 各本体の配列 MIGRATION_OUTSIDE_RECORD。本体にこの配列が無いとき
  （5-3 自身の PR と、5-3 より前に分かれた枝の PR）は、§5-4b の2本を記録の外として使う（OUTSIDE_DEFAULT。ここ1か所）。

止める物:
  (i)   凍らせるファイルの変更・削除・名前の変更（MB と head の差の M・D・R）。
        scripts/migration-guard/rewrite-allowlist.tsv にあるファイルは通す（例外の道）。
  (ii)  MB の記録の対象が head の記録の対象に無い（登録の行を消した・記録の外に移した）。
  (iii) head の本体の記録の外の一覧が、ビューを外す2本と一致しない。head に配列が無いときは、
        MB にも無いときだけ §5-4b の2本を使い (iii) は見ない。MB に有って head に無いなら赤。
  一覧のファイルが凍らせるファイルに無ければ失敗（登録から消えた行を一覧に残さない）。

使い方（リポジトリの中で）:
  python3 scripts/check_migration_freeze.py --head <sha> --base-ref main
  python3 scripts/check_migration_freeze.py --head <sha> --tip <sha>      # 試験用
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

BODY = "scripts/run_all_migrations.sh"
ALLOWLIST = "scripts/migration-guard/rewrite-allowlist.tsv"

# §5-4b の2本。本体に配列が無いときの記録の外（この扱いの書き場所はここ1か所）。
OUTSIDE_DEFAULT = (
    "migrations/20261024_100200_drop_ai_cloud_views.sql",
    "migrations/20261017_125900_drop_ai_ro_views.sql",
)

_REG_RE = re.compile(r"^run_(sql|py)[ \t]+(\S+)(.*)$")
_ARRAY_RE = re.compile(r"^MIGRATION_OUTSIDE_RECORD=\(([^)]*)\)", re.M)
_SQL_RE = re.compile(r"[A-Za-z0-9_./\-]*[A-Za-z0-9_\-]\.sql")


def git(args: list[str], check: bool = True) -> str | None:
    p = subprocess.run(["git", *args], capture_output=True)
    if p.returncode != 0:
        if check:
            sys.stderr.write(p.stderr.decode("utf-8", "replace"))
            raise SystemExit(f"git {' '.join(args)} failed")
        return None
    return p.stdout.decode("utf-8", "replace")


def show(rev: str, path: str) -> str | None:
    return git(["show", f"{rev}:{path}"], check=False)


def parse_body(text: str) -> tuple[list[tuple[str, str]], list[str] | None]:
    """本体の登録（種類・ファイル）の一覧と、記録の外の配列（無ければ None）。"""
    reg = []
    for line in text.splitlines():
        m = _REG_RE.match(line)
        if m:
            reg.append((m.group(1), m.group(2)))
    m = _ARRAY_RE.search(text)
    outside = m.group(1).split() if m else None
    return reg, outside


def targets_of(rev: str) -> tuple[list[tuple[str, str]], list[str] | None, set[str]]:
    """rev の記録の対象（種類・ファイル）・記録の外の配列（無ければ None）・凍らせる SQL（台本が読む物）。"""
    text = show(rev, BODY)
    if text is None:
        return [], None, set()
    reg, outside = parse_body(text)
    outs = set(outside if outside is not None else OUTSIDE_DEFAULT)
    tg = [(k, f) for k, f in reg if f not in outs]
    migs = {os.path.basename(x) for x in (git(["ls-tree", "-r", "--name-only", rev, "migrations/"], check=False) or "").split()}
    sqls: set[str] = set()
    for kind, f in tg:
        if kind != "py":
            continue
        body = show(rev, f)
        if body is None:
            continue
        for hit in _SQL_RE.findall(body):
            base = os.path.basename(hit)
            if base in migs:
                sqls.add(f"migrations/{base}")
    return tg, outside, sqls


def read_allowlist(rev: str) -> dict[str, str]:
    text = show(rev, ALLOWLIST)
    out: dict[str, str] = {}
    for line in (text or "").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cols = line.split("\t")
        out[cols[0].strip()] = cols[2].strip() if len(cols) > 2 else ""
    return out


def check(head: str, tip: str) -> list[str]:
    mb = (git(["merge-base", tip, head]) or "").strip()
    if not mb:
        raise SystemExit("merge-base が取れません")
    mb_tg, mb_outside, mb_sqls = targets_of(mb)
    tip_tg, _tip_outside, tip_sqls = targets_of(tip)
    head_tg, head_outside, _head_sqls = targets_of(head)

    frozen = {f for _, f in mb_tg} | {f for _, f in tip_tg} | mb_sqls | tip_sqls
    allow = read_allowlist(head)
    errors: list[str] = []

    # (i) 凍らせるファイルの変更・削除・名前の変更
    diff = git(["diff", "--name-status", "-M", mb, head]) or ""
    for line in diff.splitlines():
        cols = line.split("\t")
        status = cols[0][0]
        if status in ("M", "D"):
            paths = [cols[1]]
        elif status == "R":
            paths = [cols[1]]  # 名前を変える前のファイルが凍っていれば赤
        else:
            continue
        for p in paths:
            if p in frozen and p not in allow:
                errors.append(f"(i) 流し終えた手順を書き換え・削除・改名した: {p}（{status}）")

    # 一覧のファイルが凍らせるファイルに無ければ失敗
    for f in sorted(allow):
        if f not in frozen:
            errors.append(f"rewrite-allowlist.tsv の {f} は凍らせるファイル（登録の対象）に無い。行を消す")

    # (ii) MB の記録の対象が head に無い
    head_files = {f for _, f in head_tg}
    for _, f in mb_tg:
        if f not in head_files:
            errors.append(f"(ii) 記録の対象の登録の行を消した（または記録の外へ移した）: {f}")

    # (iii) 記録の外の一覧
    if head_outside is None:
        if mb_outside is not None:
            errors.append("(iii) MIGRATION_OUTSIDE_RECORD の配列を消した")
    elif sorted(head_outside) != sorted(OUTSIDE_DEFAULT):
        errors.append(
            "(iii) 記録の外の一覧がビューを外す2本と一致しない（設計 §5-4b）: "
            + " ".join(head_outside)
        )
    return errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--head", required=True, help="PR の head の commit")
    ap.add_argument("--base-ref", default="main", help="PR の宛先の枝の名前（TIP を取り直す）")
    ap.add_argument("--tip", default=None, help="TIP を直接渡す（試験用。CI では渡さない）")
    args = ap.parse_args(argv)

    tip = args.tip
    if tip is None:
        git(["fetch", "--no-tags", "origin", args.base_ref])
        tip = (git(["rev-parse", "FETCH_HEAD"]) or "").strip()
    errors = check(args.head, tip)
    if errors:
        print("❌ MIGRATION FREEZE FAILED（設計 §5-7）")
        for e in errors:
            print(f"  - {e}")
        print("直したいときは新しい手順を足す。本番で記録される前に失敗した手順だけは scripts/migration-guard/rewrite-allowlist.tsv に入れる。")
        return 1
    print("✅ 流し終えた手順の書き換え・削除なし、記録の外の一覧は2本のまま")
    return 0


if __name__ == "__main__":
    sys.exit(main())
