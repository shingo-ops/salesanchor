"""
MIG-05 Task 1: 本番 DB 検収スクリプト

投入後の本番 DB に対して、MIG-02/04 の検収条件をすべて確認する。

使用方法:
  export TCG_DB_PROD_URL="postgresql+psycopg2://user:pass@prod-host:5432/prod_db"
  cd backend
  python -m tcg_migration.scripts.verify_acceptance

終了コード:
  0 = 全チェック PASS
  1 = 1件以上 FAIL
"""
from __future__ import annotations

import os
import sys

import psycopg2

# ---------------------------------------------------------------------------
# 接続
# ---------------------------------------------------------------------------

def _connect(url: str) -> psycopg2.extensions.connection:
    url = url.replace("postgresql+psycopg2://", "").replace("postgresql://", "")
    userinfo, hostinfo = url.split("@", 1)
    user, password = userinfo.split(":", 1) if ":" in userinfo else (userinfo, "")
    hostport, dbname = hostinfo.rsplit("/", 1) if "/" in hostinfo else (hostinfo, "")
    host, port = hostport.rsplit(":", 1) if ":" in hostport else (hostport, "5432")
    return psycopg2.connect(host=host, port=int(port), user=user, password=password, dbname=dbname)


# ---------------------------------------------------------------------------
# 検収チェック定義
# ---------------------------------------------------------------------------

def _count(cur: psycopg2.extensions.cursor, sql: str, params: tuple = ()) -> int:
    cur.execute(sql, params)
    return cur.fetchone()[0]


CHECKS = [
    # (ラベル, SQL, 期待値)
    (
        "tcg_suppliers = 45",
        "SELECT COUNT(*) FROM tcg_suppliers",
        45,
    ),
    (
        "extraction_items = 1626",
        "SELECT COUNT(*) FROM extraction_items",
        1626,
    ),
    (
        "tcg_products = 267",
        "SELECT COUNT(*) FROM tcg_products",
        267,
    ),
    (
        "product_exclude_keywords = 123",
        "SELECT COUNT(*) FROM product_exclude_keywords",
        123,
    ),
    (
        "analysis_results = 1626",
        "SELECT COUNT(*) FROM analysis_results",
        1626,
    ),
    (
        "needs_review = 1394",
        "SELECT COUNT(*) FROM analysis_results WHERE needs_review",
        1394,
    ),
    (
        "pid_unresolved = 344",
        "SELECT COUNT(*) FROM analysis_results WHERE NOT pid_resolved",
        344,
    ),
    (
        "unit_unresolved = 528",
        "SELECT COUNT(*) FROM analysis_results WHERE NOT unit_resolved",
        528,
    ),
    (
        "engine_version = compat-v1 (全行)",
        "SELECT COUNT(*) FROM analysis_results WHERE engine_version != 'compat-v1'",
        0,
    ),
    (
        "SP0023 analysis_results = 198",
        """
        SELECT COUNT(*) FROM analysis_results ar
        JOIN extraction_items ei ON ei.id = ar.extraction_item_id
        JOIN extraction_jobs  ej ON ej.id = ei.extraction_job_id
        JOIN source_messages  sm ON sm.id = ej.source_message_id
        JOIN supplier_channels sc ON sc.id = sm.supplier_channel_id
        JOIN tcg_suppliers s ON s.id = sc.supplier_id
        WHERE s.code = 'SP0023'
        """,
        198,
    ),
    (
        "SP0057 extraction_items = 0",
        """
        SELECT COUNT(*) FROM extraction_items ei
        JOIN extraction_jobs ej ON ej.id = ei.extraction_job_id
        JOIN source_messages sm ON sm.id = ej.source_message_id
        JOIN supplier_channels sc ON sc.id = sm.supplier_channel_id
        JOIN tcg_suppliers s ON s.id = sc.supplier_id
        WHERE s.code = 'SP0057'
        """,
        0,
    ),
    (
        "SP0004 extraction_items = 91",
        """
        SELECT COUNT(*) FROM extraction_items ei
        JOIN extraction_jobs ej ON ej.id = ei.extraction_job_id
        JOIN source_messages sm ON sm.id = ej.source_message_id
        JOIN supplier_channels sc ON sc.id = sm.supplier_channel_id
        JOIN tcg_suppliers s ON s.id = sc.supplier_id
        WHERE s.code = 'SP0004'
        """,
        91,
    ),
    (
        "SP0011 extraction_items = 14",
        """
        SELECT COUNT(*) FROM extraction_items ei
        JOIN extraction_jobs ej ON ej.id = ei.extraction_job_id
        JOIN source_messages sm ON sm.id = ej.source_message_id
        JOIN supplier_channels sc ON sc.id = sm.supplier_channel_id
        JOIN tcg_suppliers s ON s.id = sc.supplier_id
        WHERE s.code = 'SP0011'
        """,
        14,
    ),
    # import_jobs スキーマ確認
    (
        "import_jobs テーブル存在",
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'import_jobs'",
        1,
    ),
    (
        "extraction_jobs.prompt_version カラム存在",
        """
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name = 'extraction_jobs' AND column_name = 'prompt_version'
        """,
        1,
    ),
]

# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def main() -> None:
    prod_url = os.environ.get("TCG_DB_PROD_URL", "")
    if not prod_url:
        print(
            "[ERROR] TCG_DB_PROD_URL が未設定です。\n"
            "  export TCG_DB_PROD_URL='postgresql+psycopg2://user:pass@host/db'",
            file=sys.stderr,
        )
        sys.exit(1)

    conn = _connect(prod_url)
    cur = conn.cursor()

    passed = 0
    failed = 0

    print(f"\n{'検収チェック':<50} {'期待':>8} {'実測':>8} {'結果'}")
    print("-" * 80)

    for label, sql, expected in CHECKS:
        actual = _count(cur, sql)
        ok = actual == expected
        mark = "PASS" if ok else "FAIL"
        print(f"  {label:<48} {expected:>8} {actual:>8}  {mark}")
        if ok:
            passed += 1
        else:
            failed += 1

    print("-" * 80)
    print(f"\n結果: {passed} PASS / {failed} FAIL")

    cur.close()
    conn.close()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
