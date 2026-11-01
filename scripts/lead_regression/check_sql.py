#!/usr/bin/env python3
"""書き込みの SQL の機械の点検 K5①(a)（card-a-backend.md §5-3）。

次がすべて 0 件なら合格:
  - INSERT・UPDATE・DELETE の書き込み先で `<schema>.` で始まらないもの
  - FROM・JOIN で読む表のうち `<schema>.` でも `pg_temp.` でもないもの
  - `tenant_00` に続く 001 以外の数字、`public.`、`search_path`

読み取りだけの例外（read_allow）は名前で固定して渡す（消す SQL の public の読み取りなど）。
SQL は流さない。文字列として読むだけ。

    python3 scripts/lead_regression/check_sql.py <sql ファイル> [--schema tenant_001]
"""

from __future__ import annotations

import argparse
import re
import sys

_COMMENT = re.compile(r"--[^\n]*")
_STRING = re.compile(r"'(?:[^']|'')*'")
_WRITE = re.compile(r"\b(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+(?:ONLY\s+)?([A-Za-z_][\w.\"]*)", re.IGNORECASE)
_READ = re.compile(r"\b(?:FROM|JOIN)\s+(?:ONLY\s+)?([A-Za-z_][\w.\"]*)", re.IGNORECASE)
_OTHER_TENANT = re.compile(r"tenant_00(?!1\b)\d", re.IGNORECASE)


def _strip_comments(sql: str) -> str:
    return _COMMENT.sub("", sql)


def check_sql(sql: str, schema: str = "tenant_001", read_allow: tuple[str, ...] = ()) -> list[str]:
    """違反の一覧を返す（空なら合格）。"""
    violations: list[str] = []
    no_comments = _strip_comments(sql)
    # 文字列の中身（本文・メッセージ）は表の名前として読まない。ただしダラー引用の本体は読む。
    code = _STRING.sub("''", no_comments)

    for m in _WRITE.finditer(code):
        target = m.group(1).strip('"')
        if not target.startswith(f"{schema}."):
            violations.append(f"書き込み先が {schema}. で始まらない: {target}")

    for m in _READ.finditer(code):
        table = m.group(1).strip('"')
        if table.startswith(f"{schema}.") or table.startswith("pg_temp."):
            continue
        if table in read_allow:
            continue
        # SQL の関数・集合を返す式（FROM generate_series(...) など）は表ではない
        end = m.end()
        if code[end : end + 1] == "(":
            continue
        # EXTRACT(... FROM expr)・DELETE FROM の続きではない書き方（IS DISTINCT FROM 等）の取りこぼし避け
        violations.append(f"読む表が {schema}. でも pg_temp. でもない: {table}")

    scan = no_comments
    for allowed in read_allow:
        scan = scan.replace(allowed, "")
    if _OTHER_TENANT.search(scan):
        violations.append(f"{schema} 以外のテナントの名前がある")
    if re.search(r"\bpublic\.", scan, re.IGNORECASE):
        violations.append("public. がある")
    if re.search(r"search_path", scan, re.IGNORECASE):
        violations.append("search_path がある")
    return violations


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sql_file")
    ap.add_argument("--schema", default="tenant_001")
    ap.add_argument("--read-allow", action="append", default=[])
    args = ap.parse_args(argv)
    with open(args.sql_file, encoding="utf-8") as f:
        sql = f.read()
    found = check_sql(sql, args.schema, tuple(args.read_allow))
    for v in found:
        print(f"違反: {v}")
    print(f"violations={len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
