"""
ADR-1004: public.llm_usage_events migration の PG 統合テスト。

design.md §3-1 (CREATE TABLE) / §3-4 (バックフィル) の受入条件:
  - migration が冪等（2回流しても行数・表構造が変わらない）
  - extraction_attempts の input_tokens/output_tokens/cost_usd を持つ行が
    backfilled=true で台帳に写る
  - 重複防止（WHERE NOT EXISTS）: 2回目のバックフィルで行が増えない

test_extraction_shadow_tables_pg.py と同じ TEST_PG_URL ゲート方式（実 PostgreSQL
必須、未設定なら skip）。FK 先の extraction_attempts / extraction_shadow_runs は
本テスト専用の最小スタブを作る（実スキーマ全体は provision しない）。
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

TEST_PG_URL = os.getenv("TEST_PG_URL")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION_FILE = _REPO_ROOT / "migrations" / "20260930_130000_create_llm_usage_events.sql"

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not TEST_PG_URL, reason="実 PostgreSQL 環境が必要 (TEST_PG_URL 未設定)。"),
    pytest.mark.skipif(
        not _MIGRATION_FILE.exists(),
        reason=f"migration ファイルが見つからない: {_MIGRATION_FILE}",
    ),
]


@pytest.fixture
async def engine():
    from sqlalchemy.ext.asyncio import create_async_engine
    eng = create_async_engine(TEST_PG_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest.fixture
async def stub_tables(engine):
    """FK 先の最小スタブ（id + backfill クエリが読む列のみ）。"""
    from sqlalchemy import text as sa_text
    async with engine.begin() as conn:
        await conn.execute(sa_text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        await conn.execute(sa_text("""
            CREATE TABLE IF NOT EXISTS public.extraction_attempts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                requested_model TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                cost_usd NUMERIC(10,6),
                started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                response_received_at TIMESTAMPTZ,
                finished_at TIMESTAMPTZ
            )
        """))
        await conn.execute(sa_text("""
            CREATE TABLE IF NOT EXISTS public.extraction_shadow_runs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid()
            )
        """))
    yield
    async with engine.begin() as conn:
        await conn.execute(sa_text("DROP TABLE IF EXISTS public.llm_usage_events"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS public.extraction_attempts CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS public.extraction_shadow_runs CASCADE"))


async def test_table_created_idempotently(engine, stub_tables):
    from sqlalchemy import text as sa_text
    sql_text = _MIGRATION_FILE.read_text(encoding="utf-8")

    async with engine.begin() as conn:
        await conn.execute(sa_text(sql_text))  # 1回目
    async with engine.begin() as conn:
        await conn.execute(sa_text(sql_text))  # 2回目（冪等であること）

    async with engine.begin() as conn:
        result = await conn.execute(sa_text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='llm_usage_events'"
        ))
        assert result.scalar_one() == "llm_usage_events"


async def test_backfill_copies_attempts_with_tokens_idempotently(engine, stub_tables):
    from sqlalchemy import text as sa_text
    sql_text = _MIGRATION_FILE.read_text(encoding="utf-8")

    async with engine.begin() as conn:
        # 台帳へ写すべき行（token あり）と写さない行（全部 NULL）
        await conn.execute(sa_text("""
            INSERT INTO public.extraction_attempts (requested_model, input_tokens, output_tokens, cost_usd)
            VALUES ('gemini-3.1-flash-lite', 1000, 200, 0.000550)
        """))
        await conn.execute(sa_text("""
            INSERT INTO public.extraction_attempts (requested_model, input_tokens, output_tokens, cost_usd)
            VALUES ('gemini-3.1-flash-lite', NULL, NULL, NULL)
        """))

    async with engine.begin() as conn:
        await conn.execute(sa_text(sql_text))  # 1回目: backfill 実行

    async with engine.begin() as conn:
        rows = (await conn.execute(sa_text(
            "SELECT purpose, backfilled, prompt_tokens, candidates_tokens, cost_usd "
            "FROM public.llm_usage_events"
        ))).fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert row[0] == "line_extraction"
    assert row[1] is True
    assert row[2] == 1000
    assert row[3] == 200

    async with engine.begin() as conn:
        await conn.execute(sa_text(sql_text))  # 2回目: 冪等（重複しない）

    async with engine.begin() as conn:
        count = (await conn.execute(sa_text("SELECT COUNT(*) FROM public.llm_usage_events"))).scalar_one()
    assert count == 1
