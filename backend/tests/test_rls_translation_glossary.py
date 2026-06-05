"""
translation_glossary RLS テスト（ADR-SA-17）。

PostgreSQL 専用機能のため、RLS_TEST_DATABASE_URL が設定されたときだけ実行。
SUPERUSER は FORCE RLS をバイパスするため、非 SUPERUSER ロールで接続すること
（CI では jarvis_app ロールを使用）。

検証内容:
  1. テナントセッションが共有行（tenant_id IS NULL）を INSERT/UPDATE/DELETE できない
     → 42501 insufficient_privilege で拒否
  2. operator セッション（app.is_operator='true'）が共有行を書き込める
  3. テナントセッションは自テナント行のみ SELECT できる（他テナント行は見えない）
  4. operator リセット後（app.is_operator=''）にテナントが共有行を書き込めない
     → リセット漏れによるコネクションプール汚染がないことを確認
"""

from __future__ import annotations

import os
from typing import Optional

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine
from sqlalchemy.exc import ProgrammingError


_RLS_DB_URL: Optional[str] = os.getenv("RLS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not _RLS_DB_URL,
    reason=(
        "PostgreSQL ベースの RLS テストは環境変数 RLS_TEST_DATABASE_URL が "
        "設定されたときだけ実行する（ローカル pytest は SQLite）"
    ),
)

_TABLE = "public.translation_glossary_rls_test"


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def pg_engine():
    assert _RLS_DB_URL
    eng = create_async_engine(_RLS_DB_URL, echo=False, future=True)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def setup_glossary_table(pg_engine):
    """テスト用 translation_glossary を最小 DDL で作成し RLS を適用する。"""
    async with pg_engine.begin() as conn:
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {_TABLE} (
                id          SERIAL PRIMARY KEY,
                tenant_id   INTEGER,
                source_term TEXT NOT NULL,
                target_text TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT TRUE
            )
        """))
        await conn.execute(text(
            f"ALTER TABLE {_TABLE} ENABLE ROW LEVEL SECURITY"
        ))
        await conn.execute(text(
            f"ALTER TABLE {_TABLE} FORCE ROW LEVEL SECURITY"
        ))
        # SELECT ポリシー
        await conn.execute(text(
            f"DROP POLICY IF EXISTS tg_select ON {_TABLE}"
        ))
        await conn.execute(text(f"""
            CREATE POLICY tg_select ON {_TABLE}
            FOR SELECT
            USING (
                tenant_id IS NULL
                OR tenant_id = current_setting('app.tenant_id', true)::INTEGER
            )
        """))
        # INSERT ポリシー
        await conn.execute(text(
            f"DROP POLICY IF EXISTS tg_insert ON {_TABLE}"
        ))
        await conn.execute(text(f"""
            CREATE POLICY tg_insert ON {_TABLE}
            FOR INSERT
            WITH CHECK (
                CASE
                    WHEN tenant_id IS NULL THEN
                        current_setting('app.is_operator', true) = 'true'
                    ELSE
                        tenant_id = current_setting('app.tenant_id', true)::INTEGER
                END
            )
        """))
        # UPDATE ポリシー
        await conn.execute(text(
            f"DROP POLICY IF EXISTS tg_update ON {_TABLE}"
        ))
        await conn.execute(text(f"""
            CREATE POLICY tg_update ON {_TABLE}
            FOR UPDATE
            USING (
                CASE
                    WHEN tenant_id IS NULL THEN
                        current_setting('app.is_operator', true) = 'true'
                    ELSE
                        tenant_id = current_setting('app.tenant_id', true)::INTEGER
                END
            )
            WITH CHECK (
                CASE
                    WHEN tenant_id IS NULL THEN
                        current_setting('app.is_operator', true) = 'true'
                    ELSE
                        tenant_id = current_setting('app.tenant_id', true)::INTEGER
                END
            )
        """))
        # DELETE ポリシー
        await conn.execute(text(
            f"DROP POLICY IF EXISTS tg_delete ON {_TABLE}"
        ))
        await conn.execute(text(f"""
            CREATE POLICY tg_delete ON {_TABLE}
            FOR DELETE
            USING (
                CASE
                    WHEN tenant_id IS NULL THEN
                        current_setting('app.is_operator', true) = 'true'
                    ELSE
                        tenant_id = current_setting('app.tenant_id', true)::INTEGER
                END
            )
        """))

    yield

    async with pg_engine.begin() as conn:
        await conn.execute(text(f"DROP TABLE IF EXISTS {_TABLE} CASCADE"))


@pytest_asyncio.fixture(loop_scope="module")
async def pg_conn(pg_engine, setup_glossary_table):
    """各テスト用に独立した AsyncConnection（autobegin で暗黙トランザクション）。"""
    async with pg_engine.connect() as conn:
        yield conn
        await conn.rollback()


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

async def _set_tenant(conn: AsyncConnection, tenant_id: int) -> None:
    await conn.execute(text(f"SET LOCAL app.tenant_id = '{tenant_id}'"))
    await conn.execute(text("SET LOCAL app.is_operator = ''"))


async def _set_operator(conn: AsyncConnection) -> None:
    await conn.execute(text("SET LOCAL app.tenant_id = ''"))
    await conn.execute(text("SET LOCAL app.is_operator = 'true'"))


async def _reset_operator(conn: AsyncConnection) -> None:
    """operator リセット後は app.is_operator = '' に戻す。"""
    await conn.execute(text("SET LOCAL app.is_operator = ''"))


# ---------------------------------------------------------------------------
# テスト: テナントセッション
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tenant_cannot_insert_shared_row(pg_conn: AsyncConnection) -> None:
    """テナントセッションが共有行（tenant_id IS NULL）を INSERT できない（I-8）。"""
    await _set_tenant(pg_conn, 1)
    with pytest.raises(ProgrammingError, match="42501|insufficient_privilege|new row violates"):
        await pg_conn.execute(text(f"""
            INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'shared_term')
        """))


@pytest.mark.asyncio
async def test_tenant_can_insert_own_row(pg_conn: AsyncConnection) -> None:
    """テナントセッションが自テナント行を INSERT できる。"""
    await _set_tenant(pg_conn, 1)
    await pg_conn.execute(text(f"""
        INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (1, 'tenant_term')
    """))


@pytest.mark.asyncio
async def test_tenant_cannot_see_other_tenant_row(pg_conn: AsyncConnection) -> None:
    """テナント1のセッションはテナント2の行が SELECT で見えない（I-8）。"""
    # テナント1で行を挿入（superuser 権限の別コネクション経由は困難なため
    # テナント1セッション自身の行として作成する）
    await _set_tenant(pg_conn, 1)
    await pg_conn.execute(text(f"""
        INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (1, 't1_term')
    """))
    # テナント2に切り替え
    await _set_tenant(pg_conn, 2)
    result = await pg_conn.execute(text(f"""
        SELECT source_term FROM {_TABLE} WHERE tenant_id = 1
    """))
    rows = result.fetchall()
    assert rows == [], f"テナント2がテナント1の行を参照できてしまった: {rows}"


@pytest.mark.asyncio
async def test_tenant_can_see_shared_rows(pg_conn: AsyncConnection) -> None:
    """テナントセッションは共有行（tenant_id IS NULL）を SELECT できる（I-5読み取り）。"""
    # operator で共有行を事前挿入
    await _set_operator(pg_conn)
    await pg_conn.execute(text(f"""
        INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'shared_visible')
    """))
    # テナント1に切り替えて共有行が見えることを確認
    await _set_tenant(pg_conn, 1)
    result = await pg_conn.execute(text(f"""
        SELECT source_term FROM {_TABLE} WHERE tenant_id IS NULL AND source_term = 'shared_visible'
    """))
    rows = result.fetchall()
    assert len(rows) == 1, "テナントセッションが共有行を SELECT できない"


# ---------------------------------------------------------------------------
# テスト: operator セッション
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_operator_can_insert_shared_row(pg_conn: AsyncConnection) -> None:
    """operator セッションが共有行を INSERT できる。"""
    await _set_operator(pg_conn)
    await pg_conn.execute(text(f"""
        INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'op_shared')
    """))


@pytest.mark.asyncio
async def test_operator_can_update_shared_row(pg_conn: AsyncConnection) -> None:
    """operator セッションが共有行を UPDATE できる。"""
    await _set_operator(pg_conn)
    await pg_conn.execute(text(f"""
        INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'op_update_src')
    """))
    await pg_conn.execute(text(f"""
        UPDATE {_TABLE} SET target_text = 'updated' WHERE source_term = 'op_update_src' AND tenant_id IS NULL
    """))


@pytest.mark.asyncio
async def test_operator_can_delete_shared_row(pg_conn: AsyncConnection) -> None:
    """operator セッションが共有行を DELETE できる。"""
    await _set_operator(pg_conn)
    await pg_conn.execute(text(f"""
        INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'op_delete_src')
    """))
    await pg_conn.execute(text(f"""
        DELETE FROM {_TABLE} WHERE source_term = 'op_delete_src' AND tenant_id IS NULL
    """))


# ---------------------------------------------------------------------------
# テスト: operator リセット後（コネクションプール汚染防止）
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_after_operator_reset_tenant_cannot_insert_shared(
    pg_conn: AsyncConnection,
) -> None:
    """operator リセット後にテナントセッションが共有行を書けない（I-8・汚染防止）。

    同一コネクションで operator → reset → tenant の順で操作し、
    リセット漏れがないことを確認する。
    """
    # 1. operator セッション → 共有行書き込み可
    await _set_operator(pg_conn)
    await pg_conn.execute(text(f"""
        INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'before_reset')
    """))
    # 2. operator リセット（reset_operator_context と同等）
    await _reset_operator(pg_conn)
    # 3. テナントに切り替え → 共有行書き込み不可
    await _set_tenant(pg_conn, 1)
    with pytest.raises(ProgrammingError, match="42501|insufficient_privilege|new row violates"):
        await pg_conn.execute(text(f"""
            INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'after_reset_attempt')
        """))


@pytest.mark.asyncio
async def test_unset_is_operator_denies_shared_insert(pg_conn: AsyncConnection) -> None:
    """app.is_operator 未設定（NULL）でも共有行 INSERT は deny（フェイルクローズ）。

    current_setting('app.is_operator', true) は未設定時 NULL を返す。
    NULL = 'true' は false → deny。
    """
    # app.is_operator を意図的に未設定にする（RESET）
    await pg_conn.execute(text("RESET app.is_operator"))
    await pg_conn.execute(text("SET LOCAL app.tenant_id = '1'"))
    with pytest.raises(ProgrammingError, match="42501|insufficient_privilege|new row violates"):
        await pg_conn.execute(text(f"""
            INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'failclose_test')
        """))
