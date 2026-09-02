"""
MIG-05 Task 1: ローカル TCG DB → 本番 DB 冪等投入スクリプト

使用方法:
  export TCG_DB_LOCAL_URL="postgresql+psycopg2://user:pass@localhost:5432/myapp_db"
  export TCG_DB_PROD_URL="postgresql+psycopg2://prod-user:pass@prod-host:5432/prod_db"
  cd backend
  python -m tcg_migration.scripts.ingest_to_prod [--dry-run] [--preview]

オプション:
  --dry-run   ソース行数のみ表示し、ターゲット DB に一切書き込まない
  --preview   投入前後の件数をターゲット DB で確認するのみ（書き込みなし）

冪等性:
  各テーブルの INSERT は ON CONFLICT (id) DO NOTHING で実行。
  同じスクリプトを複数回実行しても行が重複することはない。

注意:
  source_messages の superseded_by (自己参照FK) は 2-pass で処理:
    Pass 1: superseded_by = NULL で全行 INSERT
    Pass 2: UPDATE source_messages SET superseded_by = <元の値> WHERE ...

必要パッケージ: psycopg2-binary (requirements.txt に含まれる)
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any

import psycopg2
import psycopg2.extras

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# TCG解析システムは tenant_004 専用スキーマ。全ターゲット SQL はこの定数で修飾する
TCG_SCHEMA = "tenant_004"

# ---------------------------------------------------------------------------
# 投入テーブル順序（FK 依存順）
# ---------------------------------------------------------------------------
# source_messages は自己参照FK (superseded_by) があるため専用処理
TABLE_ORDER = [
    "tcg_suppliers",
    "supplier_channels",
    "tcg_products",
    # products_logistics: PARITY-02 A-7 で廃止（2列のみ・実データなし）
    "product_search_keywords",
    "product_exclude_keywords",
    "units",
    "unit_aliases",
    "conditions",
    "condition_aliases",
    # source_messages は専用処理 (_ingest_source_messages)
    "extraction_jobs",
    "extraction_items",
    "analysis_results",
    "unparsed_lines",
    "item_notes",
    "import_jobs",
    "audit_log",
]

# ON CONFLICT のターゲット列（デフォルト: id）
CONFLICT_KEY: dict[str, str] = {}

# ---------------------------------------------------------------------------
# 接続ヘルパー
# ---------------------------------------------------------------------------

def _parse_url(url: str) -> dict:
    """postgresql+psycopg2://user:pass@host:port/db → psycopg2 connect kwargs"""
    url = url.replace("postgresql+psycopg2://", "").replace("postgresql://", "")
    userinfo, hostinfo = url.split("@", 1)
    user, password = userinfo.split(":", 1) if ":" in userinfo else (userinfo, "")
    if "/" in hostinfo:
        hostport, dbname = hostinfo.rsplit("/", 1)
    else:
        hostport, dbname = hostinfo, ""
    if ":" in hostport:
        host, port_str = hostport.rsplit(":", 1)
        port = int(port_str)
    else:
        host, port = hostport, 5432
    return dict(host=host, port=port, user=user, password=password, dbname=dbname)


def _connect(url: str) -> psycopg2.extensions.connection:
    kwargs = _parse_url(url)
    return psycopg2.connect(**kwargs)


# ---------------------------------------------------------------------------
# カラム一覧取得
# ---------------------------------------------------------------------------

def _get_columns(cur: psycopg2.extensions.cursor, table: str) -> list[str]:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = %s AND table_schema = 'public'
        ORDER BY ordinal_position
        """,
        (table,),
    )
    return [row[0] for row in cur.fetchall()]


# ---------------------------------------------------------------------------
# 汎用テーブル投入
# ---------------------------------------------------------------------------

def _ingest_table(
    src_cur: psycopg2.extensions.cursor,
    tgt_conn: psycopg2.extensions.connection,
    table: str,
    dry_run: bool,
) -> tuple[int, int]:
    """
    Returns (source_count, inserted_count).
    inserted_count は ON CONFLICT DO NOTHING で実際に挿入された行数
    (dry_run=True の場合は常に 0)。
    """
    cols = _get_columns(src_cur, table)
    if not cols:
        log.warning("テーブル %s のカラムが見つかりません (スキップ)", table)
        return 0, 0

    src_cur.execute(f'SELECT {", ".join(cols)} FROM "{table}"')  # noqa: S608
    rows = src_cur.fetchall()
    source_count = len(rows)

    if dry_run or source_count == 0:
        return source_count, 0

    col_list = ", ".join(f'"{c}"' for c in cols)
    placeholders = ", ".join(["%s"] * len(cols))
    conflict_col = CONFLICT_KEY.get(table, "id")
    sql = (
        f'INSERT INTO {TCG_SCHEMA}."{table}" ({col_list}) VALUES ({placeholders}) '
        f"ON CONFLICT ({conflict_col}) DO NOTHING"
    )

    with tgt_conn.cursor() as tgt_cur:
        psycopg2.extras.execute_batch(tgt_cur, sql, rows, page_size=500)
        inserted = tgt_cur.rowcount  # psycopg2 may report -1 for batch; see note below
    tgt_conn.commit()

    # psycopg2 execute_batch の rowcount は最後のバッチのみ。
    # 実際の挿入数は commit 後にカウントで確認する。
    return source_count, inserted


def _count(cur: psycopg2.extensions.cursor, table: str, schema: str = "public") -> int:
    cur.execute(f'SELECT COUNT(*) FROM {schema}."{table}"')  # noqa: S608
    return cur.fetchone()[0]


# ---------------------------------------------------------------------------
# source_messages 専用 2-pass 投入
# ---------------------------------------------------------------------------

def _ingest_source_messages(
    src_cur: psycopg2.extensions.cursor,
    tgt_conn: psycopg2.extensions.connection,
    dry_run: bool,
) -> tuple[int, int]:
    """
    自己参照FK (superseded_by) を持つ source_messages の 2-pass 投入。

    Pass 1: superseded_by = NULL で INSERT ON CONFLICT DO NOTHING
    Pass 2: UPDATE source_messages SET superseded_by = <元の値>
            WHERE id = <id> AND superseded_by IS NULL AND <元の値> IS NOT NULL
    """
    cols = _get_columns(src_cur, "source_messages")
    src_cur.execute(f'SELECT {", ".join(cols)} FROM source_messages')  # noqa: S608
    rows = src_cur.fetchall()
    source_count = len(rows)

    if dry_run or source_count == 0:
        return source_count, 0

    # superseded_by の列インデックスを特定
    try:
        sb_idx = cols.index("superseded_by")
    except ValueError:
        sb_idx = None

    # Pass 1: superseded_by を NULL に置換してINSERT
    cols_no_sb = [c for c in cols if c != "superseded_by"]
    rows_pass1: list[tuple[Any, ...]] = []
    sb_updates: list[tuple[Any, Any]] = []  # (superseded_by, id)

    id_idx = cols.index("id")
    for row in rows:
        row_list = list(row)
        if sb_idx is not None and row_list[sb_idx] is not None:
            sb_updates.append((row_list[sb_idx], row_list[id_idx]))
        if sb_idx is not None:
            row_list[sb_idx] = None
        rows_pass1.append(tuple(v for i, v in enumerate(row_list) if cols[i] != "superseded_by"))

    col_list = ", ".join(f'"{c}"' for c in cols_no_sb)
    placeholders = ", ".join(["%s"] * len(cols_no_sb))
    sql_insert = (
        f"INSERT INTO {TCG_SCHEMA}.source_messages ({col_list}) VALUES ({placeholders}) "
        f"ON CONFLICT (id) DO NOTHING"
    )

    with tgt_conn.cursor() as tgt_cur:
        psycopg2.extras.execute_batch(tgt_cur, sql_insert, rows_pass1, page_size=500)
    tgt_conn.commit()
    log.info("source_messages: Pass 1 完了 (投入候補 %d 行)", source_count)

    # Pass 2: superseded_by を更新
    if sb_updates:
        sql_update = (
            f"UPDATE {TCG_SCHEMA}.source_messages SET superseded_by = %s "
            "WHERE id = %s AND superseded_by IS NULL"
        )
        with tgt_conn.cursor() as tgt_cur:
            psycopg2.extras.execute_batch(tgt_cur, sql_update, sb_updates, page_size=500)
        tgt_conn.commit()
        log.info("source_messages: Pass 2 完了 (superseded_by 更新 %d 行)", len(sb_updates))

    return source_count, source_count  # pass1 で全行投入を試みた


# ---------------------------------------------------------------------------
# 件数サマリー表示
# ---------------------------------------------------------------------------

SUMMARY_TABLES = [
    "tcg_suppliers",
    "supplier_channels",
    "tcg_products",
    "product_search_keywords",
    "product_exclude_keywords",
    "units",
    "unit_aliases",
    "conditions",
    "condition_aliases",
    "source_messages",
    "extraction_jobs",
    "extraction_items",
    "analysis_results",
    "import_jobs",
]


def _print_counts(label: str, cur: psycopg2.extensions.cursor, schema: str = "public") -> None:
    print(f"\n--- {label} ---")
    for t in SUMMARY_TABLES:
        try:
            n = _count(cur, t, schema=schema)
            print(f"  {t:<40} {n:>6}")
        except Exception as e:
            print(f"  {t:<40} ERROR: {e}")


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="TCG local DB → prod DB 冪等投入")
    parser.add_argument("--dry-run", action="store_true", help="ソース件数確認のみ。書き込みなし")
    parser.add_argument("--preview", action="store_true", help="現在のターゲット件数を表示して終了")
    args = parser.parse_args()

    local_url = os.environ.get(
        "TCG_DB_LOCAL_URL",
        os.environ.get("TCG_DB_URL", "postgresql+psycopg2://myapp_user:password@localhost:5432/myapp_db"),
    )
    prod_url = os.environ.get("TCG_DB_PROD_URL", "")

    if not prod_url and not args.dry_run and not args.preview:
        print(
            "[ERROR] TCG_DB_PROD_URL が未設定です。\n"
            "  export TCG_DB_PROD_URL='postgresql+psycopg2://user:pass@host/db'\n"
            "  または --dry-run でソース件数のみ確認できます。",
            file=sys.stderr,
        )
        sys.exit(1)

    log.info("ソース DB に接続中...")
    src_conn = _connect(local_url)
    src_cur = src_conn.cursor()

    if args.preview:
        if not prod_url:
            print("[ERROR] --preview には TCG_DB_PROD_URL が必要です", file=sys.stderr)
            sys.exit(1)
        tgt_conn = _connect(prod_url)
        with tgt_conn.cursor() as tgt_cur:
            _print_counts("ターゲット DB 現状", tgt_cur, schema=TCG_SCHEMA)
        tgt_conn.close()
        src_conn.close()
        return

    if args.dry_run:
        log.info("=== DRY RUN モード: ソース DB 件数のみ表示 ===")
        _print_counts("ソース DB 件数", src_cur)
        src_conn.close()
        return

    log.info("ターゲット DB (本番) に接続中...")
    tgt_conn = _connect(prod_url)

    # 投入前件数
    with tgt_conn.cursor() as tgt_cur:
        _print_counts("投入前 ターゲット DB", tgt_cur, schema=TCG_SCHEMA)

    results: dict[str, tuple[int, int]] = {}

    # source_messages を先に処理 (TABLE_ORDER には含まない)
    log.info("[source_messages] 投入開始 (2-pass)...")
    src_count, ins_count = _ingest_source_messages(src_cur, tgt_conn, dry_run=False)
    results["source_messages"] = (src_count, ins_count)
    log.info("[source_messages] ソース=%d 件", src_count)

    for table in TABLE_ORDER:
        log.info("[%s] 投入開始...", table)
        src_count, ins_count = _ingest_table(src_cur, tgt_conn, table, dry_run=False)
        results[table] = (src_count, ins_count)
        log.info("[%s] ソース=%d 件", table, src_count)

    # 投入後件数
    with tgt_conn.cursor() as tgt_cur:
        _print_counts("投入後 ターゲット DB", tgt_cur, schema=TCG_SCHEMA)

    print("\n=== 投入サマリー ===")
    print(f"  {'テーブル':<40} {'ソース':>8}")
    for t, (sc, _ic) in results.items():
        print(f"  {t:<40} {sc:>8}")

    tgt_conn.close()
    src_conn.close()
    log.info("完了")


if __name__ == "__main__":
    main()
