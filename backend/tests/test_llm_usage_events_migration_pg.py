"""
ADR-1004 A1: public.llm_usage_events CREATE TABLE の PG 統合テスト（表のみ、A2で分離したバックフィルは対象外）。

design.md §3-1 (CREATE TABLE) / §9 (2段階の出し方) の受入条件:
  - migration が冪等（2回流しても表構造が変わらない）
  - CHECK 制約（purpose / sdk）が存在する
  - extraction_attempt_id に FK があり、extraction_shadow_run_id には無い
    （CI の migration-test-run 差分実行ベースラインに public.extraction_shadow_runs が
    無いため。design.md §3-1 実装時変更 / ADR-1004 決定6）
  - 4本のインデックスが存在する

スキーマは本物の migration ファイル（.sql）を実行して作る（柱3-c: テストでの
本番テーブル定義コピー禁止 — scripts/check_test_schema_dup.py）。
test_tcg_extraction_record_pg.py と同じ `pg` フィクスチャ（実 PostgreSQL、
CI-only: GITHUB_ACTIONS=true + RLS_ADMIN_DATABASE_URL 必須）を使う。
public.extraction_attempts は `migrate()` が実行する
migrations/20260921_110000_pipeline_tables_public.sql で作成済み（FK 先として必要）。
"""
from __future__ import annotations

from tests.test_tcg_work_matching_integration import MIGRATIONS
from tests.test_tcg_work_matching_integration import pg as pg

_LEDGER_MIGRATION = "20260930_150000_create_llm_usage_events.sql"


def _apply_ledger_migration(connection) -> None:
    with connection.cursor() as cur:
        cur.execute((MIGRATIONS / _LEDGER_MIGRATION).read_text())


def test_table_created_idempotently(pg):
    connection, _, _ = pg
    _apply_ledger_migration(connection)  # 1回目
    _apply_ledger_migration(connection)  # 2回目（冪等であること）

    with connection.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='llm_usage_events'"
        )
        assert cur.fetchone()[0] == "llm_usage_events"


def test_check_constraints_exist(pg):
    connection, _, _ = pg
    _apply_ledger_migration(connection)

    with connection.cursor() as cur:
        cur.execute("""
            SELECT conname FROM pg_constraint c
            JOIN pg_class rel ON c.conrelid = rel.oid
            JOIN pg_namespace ns ON rel.relnamespace = ns.oid
            WHERE ns.nspname = 'public' AND rel.relname = 'llm_usage_events' AND c.contype = 'c'
        """)
        names = {row[0] for row in cur.fetchall()}
    assert "llm_usage_events_purpose_check" in names
    assert "llm_usage_events_sdk_check" in names


def test_extraction_shadow_run_id_has_no_fk(pg):
    """CI 対応: CI の差分実行ベースラインに extraction_shadow_runs が
    無いため FK を外した（design.md §3-1 実装時変更 / ADR-1004 決定6）。

    共有 pg fixture は tenant_901 用に FK を外すため（test_tcg_work_matching_integration.py
    migrate()）、ここでは本物の migration から作り直して本番と同じ制約を検証する
    （CI の使い捨て DB 内のみ）。
    """
    connection, _, _ = pg
    with connection.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS public.llm_usage_events")
    _apply_ledger_migration(connection)

    try:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
                WHERE tc.table_schema = 'public' AND tc.table_name = 'llm_usage_events'
                  AND tc.constraint_type = 'FOREIGN KEY'
                  AND kcu.column_name = 'extraction_shadow_run_id'
            """)
            assert cur.fetchone()[0] == 0

            cur.execute("""
                SELECT COUNT(*) FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
                WHERE tc.table_schema = 'public' AND tc.table_name = 'llm_usage_events'
                  AND tc.constraint_type = 'FOREIGN KEY'
                  AND kcu.column_name = 'extraction_attempt_id'
            """)
            assert cur.fetchone()[0] == 1
    finally:
        # テスト専用：共有 pg fixture は tenant_901 用に FK を外すため（test_tcg_work_matching_integration.py
        # migrate()）、ここで本物の migration から作り直した表を、同じ fixture を使う後続テスト向けに
        # 元の（FK なしの）状態へ戻す。
        with connection.cursor() as cur:
            cur.execute(
                "ALTER TABLE public.llm_usage_events "
                "DROP CONSTRAINT IF EXISTS llm_usage_events_extraction_attempt_id_fkey"
            )


def test_indexes_exist(pg):
    connection, _, _ = pg
    _apply_ledger_migration(connection)

    with connection.cursor() as cur:
        cur.execute("""
            SELECT indexname FROM pg_indexes
            WHERE schemaname='public' AND tablename='llm_usage_events'
        """)
        names = {row[0] for row in cur.fetchall()}
    for expected in (
        "ix_llm_usage_events_occurred_at",
        "ix_llm_usage_events_purpose_occurred_at",
        "ix_llm_usage_events_extraction_attempt_id",
        "ix_llm_usage_events_extraction_shadow_run_id",
    ):
        assert expected in names
