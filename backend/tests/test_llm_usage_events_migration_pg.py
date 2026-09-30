"""
ADR-1004: public.llm_usage_events migration の PG 統合テスト。

design.md §3-1 (CREATE TABLE) / §3-4 (バックフィル) の受入条件:
  - migration が冪等（2回流しても行数・表構造が変わらない）
  - extraction_attempts の input_tokens/output_tokens/cost_usd を持つ行が
    backfilled=true で台帳に写る
  - 重複防止（WHERE NOT EXISTS）: 2回目のバックフィルで行が増えない

スキーマは本物の migration ファイル（.sql）を実行して作る（柱3-c: テストでの
本番テーブル定義コピー禁止 — scripts/check_test_schema_dup.py）。
test_tcg_extraction_record_pg.py と同じ `pg` フィクスチャ（実 PostgreSQL、
CI-only: GITHUB_ACTIONS=true + RLS_ADMIN_DATABASE_URL 必須）を使う。
public.extraction_attempts は `migrate()` が実行する
migrations/20260921_110000_pipeline_tables_public.sql で作成済み。
input_tokens/output_tokens/cost_usd 列は同フィクスチャに含まれないため、
本テストが migrations/20260927_130000_add_extraction_token_cost_columns.sql を
追加で実行する（これも本物のファイル読み込み、コピーではない）。
"""
from __future__ import annotations

from uuid import uuid4

from tests.test_tcg_work_matching_integration import MIGRATIONS
from tests.test_tcg_work_matching_integration import pg as pg

_TOKEN_COST_COLUMNS_MIGRATION = "20260927_130000_add_extraction_token_cost_columns.sql"
_LEDGER_MIGRATION = "20260930_130000_create_llm_usage_events.sql"


def _apply_token_cost_columns(connection) -> None:
    with connection.cursor() as cur:
        cur.execute((MIGRATIONS / _TOKEN_COST_COLUMNS_MIGRATION).read_text())


def _apply_ledger_migration(connection) -> None:
    with connection.cursor() as cur:
        cur.execute((MIGRATIONS / _LEDGER_MIGRATION).read_text())


def _insert_extraction_attempt(
    connection, *, input_tokens: int | None, output_tokens: int | None, cost_usd: float | None,
) -> str:
    """public.source_messages → public.extraction_jobs → public.extraction_attempts を1行ずつ作る。"""
    with connection.cursor() as cur:
        cur.execute(
            """INSERT INTO public.source_messages (raw_text, raw_sha256, is_active)
               VALUES (%s, %s, true) RETURNING id""",
            (f"raw-{uuid4().hex}", uuid4().hex),
        )
        source_message_id = cur.fetchone()[0]

        cur.execute(
            """INSERT INTO public.extraction_jobs (source_message_id, status)
               VALUES (%s, 'pending') RETURNING id""",
            (source_message_id,),
        )
        extraction_job_id = cur.fetchone()[0]

        attempt_id = str(uuid4())
        cur.execute(
            """INSERT INTO public.extraction_attempts
                   (id, extraction_job_id, source_message_id, input_sha256, input_bytes,
                    requested_model, prompt_version, input_tokens, output_tokens, cost_usd)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                attempt_id, extraction_job_id, source_message_id, uuid4().hex, 10,
                "gemini-3.1-flash-lite", "v1", input_tokens, output_tokens, cost_usd,
            ),
        )
        return attempt_id


def test_table_created_idempotently(pg):
    connection, _, _ = pg
    _apply_token_cost_columns(connection)

    _apply_ledger_migration(connection)  # 1回目
    _apply_ledger_migration(connection)  # 2回目（冪等であること）

    with connection.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='llm_usage_events'"
        )
        assert cur.fetchone()[0] == "llm_usage_events"


def test_extraction_shadow_run_id_has_no_fk(pg):
    """PR #3884 CI 対応: CI の差分実行ベースラインに extraction_shadow_runs が
    無いため FK を外した（design.md §3-1 実装時変更 / ADR-1004 決定6）。"""
    connection, _, _ = pg
    _apply_token_cost_columns(connection)
    _apply_ledger_migration(connection)

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

        # インデックスは維持されていること
        cur.execute("""
            SELECT COUNT(*) FROM pg_indexes
            WHERE schemaname='public' AND tablename='llm_usage_events'
              AND indexname='ix_llm_usage_events_extraction_shadow_run_id'
        """)
        assert cur.fetchone()[0] == 1


def test_backfill_copies_attempts_with_tokens_idempotently(pg):
    connection, _, _ = pg
    _apply_token_cost_columns(connection)

    attempt_with_tokens = _insert_extraction_attempt(
        connection, input_tokens=1000, output_tokens=200, cost_usd=0.000550,
    )
    _insert_extraction_attempt(connection, input_tokens=None, output_tokens=None, cost_usd=None)

    _apply_ledger_migration(connection)  # 1回目: backfill 実行

    with connection.cursor() as cur:
        cur.execute(
            "SELECT purpose, backfilled, prompt_tokens, candidates_tokens, cost_usd, extraction_attempt_id "
            "FROM public.llm_usage_events"
        )
        rows = cur.fetchall()
    assert len(rows) == 1
    purpose, backfilled, prompt_tokens, candidates_tokens, cost_usd, extraction_attempt_id = rows[0]
    assert purpose == "line_extraction"
    assert backfilled is True
    assert prompt_tokens == 1000
    assert candidates_tokens == 200
    assert str(extraction_attempt_id) == attempt_with_tokens

    _apply_ledger_migration(connection)  # 2回目: 冪等（重複しない）

    with connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM public.llm_usage_events")
        assert cur.fetchone()[0] == 1
