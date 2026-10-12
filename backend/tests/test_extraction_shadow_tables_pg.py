"""
extraction_shadow_svc の PG 統合テスト（PR-B1 migration 前提）。

design.md PR-B1 はまだ本ブランチに存在しない（migration 未作成・GO待ち）。
そのため、このテストは
  1) TEST_PG_URL が未設定、または
  2) PR-B1 の migration ファイル（migrations/*_create_extraction_shadow_tables.sql）
     がまだ存在しない
のいずれかで skip する。PR-B1 がマージされた後にこのテストが自動的に
有効化される（テストファイル自体の変更は不要）。
"""
from __future__ import annotations

import glob
import os
from pathlib import Path

import pytest

TEST_PG_URL = os.getenv("TEST_PG_URL")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION_GLOB = str(_REPO_ROOT / "migrations" / "*_create_extraction_shadow_tables.sql")
_MIGRATION_MATCHES = sorted(glob.glob(_MIGRATION_GLOB))
_MIGRATION_FILE = _MIGRATION_MATCHES[0] if _MIGRATION_MATCHES else None

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not TEST_PG_URL,
        reason="実 PostgreSQL 環境が必要 (TEST_PG_URL 未設定)。",
    ),
    pytest.mark.skipif(
        _MIGRATION_FILE is None,
        reason=(
            "PR-B1 の migration ファイル "
            f"({_MIGRATION_GLOB}) がまだ存在しない（PR-B1 は別PR・GO待ち）。"
            "マージ後は本テストが自動的に有効化される。"
        ),
    ),
]


@pytest.fixture
async def engine():
    from sqlalchemy.ext.asyncio import create_async_engine
    eng = create_async_engine(TEST_PG_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest.fixture
async def shadow_tables(engine):
    """PR-B1 migration の SQL テキストを直接実行して2表を作る（テストセットアップ専用）。"""
    assert _MIGRATION_FILE is not None
    sql_text = Path(_MIGRATION_FILE).read_text(encoding="utf-8")
    async with engine.begin() as conn:
        from sqlalchemy import text as sa_text
        await conn.execute(sa_text(sql_text))
    yield
    async with engine.begin() as conn:
        from sqlalchemy import text as sa_text
        await conn.execute(sa_text("DROP TABLE IF EXISTS public.extraction_shadow_results"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS public.extraction_shadow_runs"))


async def test_shadow_tables_created_idempotently(engine, shadow_tables):
    """migration を2回流しても冪等（IF NOT EXISTS）であることを確認する。"""
    from sqlalchemy import text as sa_text

    sql_text = Path(_MIGRATION_FILE).read_text(encoding="utf-8")
    async with engine.begin() as conn:
        await conn.execute(sa_text(sql_text))  # 2回目

    async with engine.begin() as conn:
        result = await conn.execute(
            sa_text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name IN "
                "('extraction_shadow_runs', 'extraction_shadow_results')"
            )
        )
        tables = {row[0] for row in result.fetchall()}
    assert tables == {"extraction_shadow_runs", "extraction_shadow_results"}
