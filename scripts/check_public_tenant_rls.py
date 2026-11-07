#!/usr/bin/env python3
"""public の表のうち tenant_id 列を持つのに RLS の無いものを見つける（ADR-1063 便5・K8）。

使い方（CI。接続先は PGHOST・PGUSER・PGPASSWORD の環境変数で渡す）:
  PYTHONPATH=backend python3 scripts/check_public_tenant_rls.py --db jarvis_report [--report-only]

結果:
  - 許可一覧（backend/app/ops/tenant_rls_allowlist.py）の理由が空の行がある → 終了コード 1
  - 許可一覧に無い表が見つかった → 終了コード 1（--report-only のときは名前を出して 0）
  - それ以外 → 0
"""

from __future__ import annotations

import argparse
import sys

import psycopg2

from app.ops.tenant_rls_allowlist import PUBLIC_TABLES_WITHOUT_RLS

FIND_SQL = """
SELECT c.relname
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attname = 'tenant_id' AND NOT a.attisdropped
WHERE n.nspname = 'public'
  AND c.relkind IN ('r', 'p')
  AND NOT c.relrowsecurity
ORDER BY c.relname
"""


def find_tables_without_rls(conn) -> list[str]:
    """public の tenant_id 付きで RLS の無い表の名前（名前順）。"""
    with conn.cursor() as cur:
        cur.execute(FIND_SQL)
        return [row[0] for row in cur.fetchall()]


def empty_reasons(allowlist: dict[str, str]) -> list[str]:
    """理由が空（空白だけを含む）の行の表名。"""
    return sorted(name for name, reason in allowlist.items() if not reason.strip())


def run(conn, allowlist: dict[str, str], report_only: bool) -> int:
    blank = empty_reasons(allowlist)
    if blank:
        for name in blank:
            print(f"❌ 許可一覧の理由が空です: {name}")
        return 1

    found = find_tables_without_rls(conn)
    unexpected = [name for name in found if name not in allowlist]
    allowed = [name for name in found if name in allowlist]
    stale = sorted(name for name in allowlist if name not in found)

    print(f"public の tenant_id 付きで RLS の無い表: {len(found)} 件（許可一覧にある {len(allowed)} 件・無い {len(unexpected)} 件）")
    for name in allowed:
        print(f"  許可一覧にある: {name}")
    for name in unexpected:
        print(f"  許可一覧に無い: {name}")
    for name in stale:
        print(f"  （参考）許可一覧にあるが見つからない: {name}")

    if unexpected and not report_only:
        print("❌ 会社の列があるのに RLS の無い表があります。RLS を付けるか、理由を書いて backend/app/ops/tenant_rls_allowlist.py に足してください。")
        return 1
    if unexpected:
        print("（--report-only のため落としません）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="点検する DB の名前")
    parser.add_argument("--report-only", action="store_true", help="見つけても落とさず名前だけ出す")
    args = parser.parse_args(argv)
    conn = psycopg2.connect(dbname=args.db)
    try:
        return run(conn, PUBLIC_TABLES_WITHOUT_RLS, args.report_only)
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
