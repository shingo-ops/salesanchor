"""ADR-119 バックフィルスクリプトの source ガードテスト (実 PostgreSQL)。

目的:
  1. OLD SQL パターン（source ガードなし）が leads.source 廃止済み DB で
     UndefinedColumnError を発生させることを証明する。
     → 新 CI 「廃止列前提検出」が地雷を検出できることのデモ（赤くなる証拠）

  2. NEW backfill_schema（has_source ガード付き）が同 DB で section 1 を
     スキップして正常完了することを証明する。
     → 今回の修正が機能することの証拠（緑になる証拠）

実行条件:
  RLS_ADMIN_DATABASE_URL または TEST_PG_URL が設定された実 PostgreSQL 環境が必要。
  CI では RLS_ADMIN_DATABASE_URL（jarvis:testpass@localhost:5432/jarvis_test_db）を使用。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# 実 Postgres URL が指定されていない場合はモジュール全体を skip
PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not PG_URL,
        reason=(
            "実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。"
            "SQLite では PostgreSQL UndefinedColumnError は再現できない。"
        ),
    ),
]

# リポジトリルートを sys.path に追加して scripts/ パッケージをインポートできるようにする
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.fixture
async def engine():
    """テスト用エンジン（function スコープ）。"""
    from sqlalchemy.ext.asyncio import create_async_engine

    eng = create_async_engine(PG_URL, echo=False)
    yield eng
    await eng.dispose()


async def _setup_source_less_schema(conn, schema: str) -> None:
    """leads.source が廃止済みのスキーマをセットアップする。

    ADR-138 §D1-3 クリーンスレート方針: source 列は存在しない。
    discord_user_id / customer_name は migration 003/091 相当で存在する。
    lead_channels は migration 119 相当で存在する。
    """
    from sqlalchemy import text

    await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))

    # leads: source 列なし（ADR-138 §D1-3 適用済み状態）
    await conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {schema}.leads (
            id              SERIAL PRIMARY KEY,
            tenant_id       INTEGER      NOT NULL DEFAULT 1,
            customer_name   VARCHAR(255),
            discord_user_id VARCHAR(64),
            created_at      TIMESTAMPTZ  DEFAULT NOW()
        )
    """))

    # lead_channels: ADR-119 で作成
    await conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {schema}.lead_channels (
            id           SERIAL PRIMARY KEY,
            lead_id      INTEGER      NOT NULL REFERENCES {schema}.leads(id),
            platform     VARCHAR(50)  NOT NULL,
            external_id  VARCHAR(255) NOT NULL,
            display_name VARCHAR(255),
            created_at   TIMESTAMPTZ  DEFAULT NOW(),
            UNIQUE (platform, external_id)
        )
    """))

    # テスト用リード（discord_user_id 付き）
    await conn.execute(text(f"""
        INSERT INTO {schema}.leads (customer_name, discord_user_id)
        VALUES ('テストリード', '123456789012345678')
    """))


async def _drop_schema(conn, schema: str) -> None:
    from sqlalchemy import text

    await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: OLD パターンが UndefinedColumnError を発生させることを証明
#         これが「新 CI は地雷を検出できる」ことのデモ（修正前 → 赤になる）
# ─────────────────────────────────────────────────────────────────────────────

async def test_old_sql_pattern_fails_without_source_column(engine):
    """OLD SQL パターン: source ガードなしで WHERE source LIKE を実行すると失敗する。

    これは「修正前の migrate_adr119_lead_channels_backfill.py がなぜ
    本番で step[119/145] を落としたか」の再現テスト。
    新 CI 廃止列前提検出がこのパターンを検知して赤くする根拠。
    """
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    schema = "test_adr119_old_pattern"

    async with engine.begin() as conn:
        await _setup_source_less_schema(conn, schema)

    try:
        with pytest.raises(DBAPIError) as exc_info:
            async with engine.begin() as conn:
                # ── OLD パターン: ガードなし（修正前の実装相当） ────────────────
                await conn.execute(text(f"""
                    INSERT INTO {schema}.lead_channels
                           (lead_id, platform, external_id, display_name)
                    SELECT id,
                           'messenger',
                           SUBSTRING(source FROM 11),
                           customer_name
                    FROM {schema}.leads
                    WHERE source LIKE 'messenger:%'
                    ON CONFLICT (platform, external_id) DO NOTHING
                """))

        # UndefinedColumnError: SQLSTATE 42703 であることを確認
        err_str = str(exc_info.value)
        assert (
            "42703" in err_str
            or "source" in err_str.lower()
            or "undefined" in err_str.lower()
        ), f"Expected UndefinedColumnError for 'source' column, got: {err_str}"

    finally:
        async with engine.begin() as conn:
            await _drop_schema(conn, schema)


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: NEW backfill_schema がスキップして正常完了することを証明
#         これが「今回の修正が機能する」証拠（修正後 → 緑になる）
# ─────────────────────────────────────────────────────────────────────────────

async def test_new_backfill_skips_section1_when_source_dropped(engine):
    """NEW backfill_schema: source 列なし DB で section 1 をスキップして正常完了する。

    ADR-138 §D1-3 廃止済み状態（本番相当）で冪等に完走することを確認する。
    section 2 (discord_user_id) は source 条件なしのパスで実行される。
    """
    from scripts.migrate_adr119_lead_channels_backfill import backfill_schema

    schema = "test_adr119_new_guard"

    async with engine.begin() as conn:
        await _setup_source_less_schema(conn, schema)

    try:
        async with engine.begin() as conn:
            counts = await backfill_schema(conn, schema)

        # section 1 (source-based) がスキップされた
        assert counts.get("messenger", 0) == 0, "messenger: section 1 should be skipped"
        assert counts.get("instagram", 0) == 0, "instagram: section 1 should be skipped"
        assert counts.get("discord", 0) == 0, "discord: section 1 should be skipped"

        # section 2 (discord_user_id): source なしパスで 1 件 insert
        assert counts.get("discord_uid", 0) == 1, (
            "discord_uid: 1 lead with discord_user_id should be inserted"
        )

    finally:
        async with engine.begin() as conn:
            await _drop_schema(conn, schema)


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: discord_user_id が lead_channels に正しく入ることを確認
# ─────────────────────────────────────────────────────────────────────────────

async def test_discord_uid_inserted_correctly_without_source(engine):
    """discord_user_id は source 廃止後も lead_channels に正しく挿入される。"""
    from sqlalchemy import text

    from scripts.migrate_adr119_lead_channels_backfill import backfill_schema

    schema = "test_adr119_discord_uid_check"

    async with engine.begin() as conn:
        await _setup_source_less_schema(conn, schema)

    try:
        async with engine.begin() as conn:
            await backfill_schema(conn, schema)

        async with engine.connect() as conn:
            result = await conn.execute(text(
                f"SELECT platform, external_id FROM {schema}.lead_channels"
            ))
            rows = list(result)

        assert len(rows) == 1
        assert rows[0].platform == "discord"
        assert rows[0].external_id == "123456789012345678"

    finally:
        async with engine.begin() as conn:
            await _drop_schema(conn, schema)


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: 冪等性確認 — 同じ backfill_schema を 2 回実行しても重複しない
# ─────────────────────────────────────────────────────────────────────────────

async def test_backfill_idempotent_on_second_run(engine):
    """backfill_schema の 2 回目実行は ON CONFLICT DO NOTHING で重複 insert しない。"""
    from sqlalchemy import text

    from scripts.migrate_adr119_lead_channels_backfill import backfill_schema

    schema = "test_adr119_idempotent"

    async with engine.begin() as conn:
        await _setup_source_less_schema(conn, schema)

    try:
        async with engine.begin() as conn:
            counts1 = await backfill_schema(conn, schema)

        async with engine.begin() as conn:
            counts2 = await backfill_schema(conn, schema)

        # 2 回目は discord_uid も 0（ON CONFLICT DO NOTHING）
        assert counts2.get("discord_uid", 0) == 0, (
            "2nd run should insert 0 rows (idempotent)"
        )

        async with engine.connect() as conn:
            result = await conn.execute(text(
                f"SELECT COUNT(*) FROM {schema}.lead_channels"
            ))
            total = result.scalar()

        assert total == 1, f"Expected 1 row total, got {total}"

    finally:
        async with engine.begin() as conn:
            await _drop_schema(conn, schema)
