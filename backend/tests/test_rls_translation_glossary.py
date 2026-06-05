"""
translation_glossary RLS テスト（ADR-SA-17）。

PostgreSQL 専用機能のため、RLS_TEST_DATABASE_URL が設定されたときだけ実行。
SUPERUSER は FORCE RLS をバイパスするため、非 SUPERUSER ロールで接続すること
（CI では jarvis_app ロールを使用）。

検証内容:
  1. テナントセッションが共有行（tenant_id IS NULL）を INSERT できない → 42501
  2. operator セッション（app.is_operator='true'）が共有行を書き込める
  3. テナントセッションは自テナント行のみ SELECT できる（他テナント行は見えない）
  4. operator リセット後（app.is_operator=''）にテナントが共有行を書けない
     → コネクションプール汚染防止
  5. app.is_operator 未設定（RESET 後の NULL）でも deny（フェイルクローズ）
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
# ADR-SA-17 Fix: DDL は superuser (jarvis) で実行し jarvis_app に DML GRANT する。
# これにより本番の権限モデル（アプリユーザーは DML のみ）を再現する。
_ADMIN_DB_URL: Optional[str] = os.getenv("ADMIN_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not _RLS_DB_URL,
    reason=(
        "PostgreSQL ベースの RLS テストは環境変数 RLS_TEST_DATABASE_URL が "
        "設定されたときだけ実行する（ローカル pytest は SQLite）"
    ),
)

_TABLE = "public.translation_glossary_rls_test"
_APP_ROLE = "jarvis_app"


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def pg_engine():
    assert _RLS_DB_URL
    eng = create_async_engine(_RLS_DB_URL, echo=False, future=True)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def admin_engine():
    """DDL 専用エンジン（superuser）。本番と同じ権限モデルを再現するために使用。"""
    url = _ADMIN_DB_URL or _RLS_DB_URL
    assert url
    eng = create_async_engine(url, echo=False, future=True)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def setup_glossary_table(admin_engine):
    """テスト用テーブルを最小 DDL で作成し RLS ポリシーを適用する。

    DDL は admin_engine (superuser) で実行し、アプリユーザー (jarvis_app) に
    DML 権限を GRANT する。FORCE RLS により jarvis_app (非 superuser) は
    ポリシーを通る。
    """
    async with admin_engine.begin() as conn:
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
        await conn.execute(text(f"DROP POLICY IF EXISTS tg_select ON {_TABLE}"))
        await conn.execute(text(f"""
            CREATE POLICY tg_select ON {_TABLE} FOR SELECT
            USING (
                tenant_id IS NULL
                OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
            )
        """))
        # INSERT ポリシー
        await conn.execute(text(f"DROP POLICY IF EXISTS tg_insert ON {_TABLE}"))
        await conn.execute(text(f"""
            CREATE POLICY tg_insert ON {_TABLE} FOR INSERT
            WITH CHECK (
                CASE
                    WHEN tenant_id IS NULL THEN
                        current_setting('app.is_operator', true) = 'true'
                    ELSE
                        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
                END
            )
        """))
        # UPDATE ポリシー
        await conn.execute(text(f"DROP POLICY IF EXISTS tg_update ON {_TABLE}"))
        await conn.execute(text(f"""
            CREATE POLICY tg_update ON {_TABLE} FOR UPDATE
            USING (
                CASE
                    WHEN tenant_id IS NULL THEN
                        current_setting('app.is_operator', true) = 'true'
                    ELSE
                        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
                END
            )
            WITH CHECK (
                CASE
                    WHEN tenant_id IS NULL THEN
                        current_setting('app.is_operator', true) = 'true'
                    ELSE
                        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
                END
            )
        """))
        # DELETE ポリシー
        await conn.execute(text(f"DROP POLICY IF EXISTS tg_delete ON {_TABLE}"))
        await conn.execute(text(f"""
            CREATE POLICY tg_delete ON {_TABLE} FOR DELETE
            USING (
                CASE
                    WHEN tenant_id IS NULL THEN
                        current_setting('app.is_operator', true) = 'true'
                    ELSE
                        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
                END
            )
        """))
        # Fix item-8: superuser がテーブルを作成するため、アプリユーザーに DML を GRANT。
        # GRANT ALL ON SCHEMA public は USAGE+CREATE のみで table-level DML は含まない。
        await conn.execute(text(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON {_TABLE} TO {_APP_ROLE}"
        ))
        await conn.execute(text(
            f"GRANT USAGE, SELECT ON SEQUENCE {_TABLE}_id_seq TO {_APP_ROLE}"
        ))

    yield

    async with admin_engine.begin() as conn:
        await conn.execute(text(f"DROP TABLE IF EXISTS {_TABLE} CASCADE"))


@pytest_asyncio.fixture(loop_scope="module")
async def pg_conn(pg_engine, setup_glossary_table):  # noqa: F811
    """各テストごとに共有 AsyncConnection（jarvis_app で接続）。テストは begin() ブロックで隔離する。"""
    async with pg_engine.connect() as conn:
        yield conn


# ---------------------------------------------------------------------------
# テスト: テナントセッション
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="module")
async def test_tenant_cannot_insert_shared_row(pg_conn: AsyncConnection) -> None:
    """テナントセッションが共有行（tenant_id IS NULL）を INSERT できない（I-8）。"""
    with pytest.raises((ProgrammingError, Exception), match="42501|insufficient_privilege|new row violates"):
        async with pg_conn.begin():
            await pg_conn.execute(text("SET LOCAL app.tenant_id = '1'"))
            await pg_conn.execute(text("SET LOCAL app.is_operator = ''"))
            await pg_conn.execute(text(
                f"INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'shared_forbidden')"
            ))


@pytest.mark.asyncio(loop_scope="module")
async def test_tenant_can_insert_own_row(pg_conn: AsyncConnection) -> None:
    """テナントセッションが自テナント行を INSERT できる。"""
    async with pg_conn.begin():
        await pg_conn.execute(text("SET LOCAL app.tenant_id = '1'"))
        await pg_conn.execute(text("SET LOCAL app.is_operator = ''"))
        await pg_conn.execute(text(
            f"INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (1, 'tenant_own_row')"
        ))


@pytest.mark.asyncio(loop_scope="module")
async def test_tenant_cannot_see_other_tenant_row(pg_conn: AsyncConnection) -> None:
    """テナント1のセッションはテナント2の行が SELECT で見えない（I-8）。"""
    # テナント2の行をテナント2セッションで挿入
    async with pg_conn.begin():
        await pg_conn.execute(text("SET LOCAL app.tenant_id = '2'"))
        await pg_conn.execute(text("SET LOCAL app.is_operator = ''"))
        await pg_conn.execute(text(
            f"INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (2, 't2_secret')"
        ))
    # テナント1に切り替えてテナント2の行が見えないことを確認
    async with pg_conn.begin():
        await pg_conn.execute(text("SET LOCAL app.tenant_id = '1'"))
        await pg_conn.execute(text("SET LOCAL app.is_operator = ''"))
        result = await pg_conn.execute(text(
            f"SELECT source_term FROM {_TABLE} WHERE tenant_id = 2"
        ))
        rows = result.fetchall()
        assert rows == [], f"テナント1がテナント2の行を参照できてしまった: {rows}"


@pytest.mark.asyncio(loop_scope="module")
async def test_tenant_can_see_shared_rows(pg_conn: AsyncConnection) -> None:
    """テナントセッションは共有行（tenant_id IS NULL）を SELECT できる（I-5読み取り）。"""
    # operator で共有行を挿入
    async with pg_conn.begin():
        await pg_conn.execute(text("SET LOCAL app.is_operator = 'true'"))
        await pg_conn.execute(text(
            f"INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'shared_visible')"
        ))
    # テナント1に切り替えて共有行が見えることを確認
    async with pg_conn.begin():
        await pg_conn.execute(text("SET LOCAL app.tenant_id = '1'"))
        await pg_conn.execute(text("SET LOCAL app.is_operator = ''"))
        result = await pg_conn.execute(text(
            f"SELECT source_term FROM {_TABLE} WHERE tenant_id IS NULL AND source_term = 'shared_visible'"
        ))
        rows = result.fetchall()
        assert len(rows) == 1, "テナントセッションが共有行を SELECT できない"


# ---------------------------------------------------------------------------
# テスト: operator セッション
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="module")
async def test_operator_can_insert_shared_row(pg_conn: AsyncConnection) -> None:
    """operator セッションが共有行を INSERT できる。"""
    async with pg_conn.begin():
        await pg_conn.execute(text("SET LOCAL app.is_operator = 'true'"))
        await pg_conn.execute(text(
            f"INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'op_insert')"
        ))


@pytest.mark.asyncio(loop_scope="module")
async def test_operator_can_update_shared_row(pg_conn: AsyncConnection) -> None:
    """operator セッションが共有行を UPDATE できる。"""
    async with pg_conn.begin():
        await pg_conn.execute(text("SET LOCAL app.is_operator = 'true'"))
        await pg_conn.execute(text(
            f"INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'op_before_update')"
        ))
    async with pg_conn.begin():
        await pg_conn.execute(text("SET LOCAL app.is_operator = 'true'"))
        await pg_conn.execute(text(
            f"UPDATE {_TABLE} SET target_text = 'updated' "
            f"WHERE source_term = 'op_before_update' AND tenant_id IS NULL"
        ))


@pytest.mark.asyncio(loop_scope="module")
async def test_operator_can_delete_shared_row(pg_conn: AsyncConnection) -> None:
    """operator セッションが共有行を DELETE できる。"""
    async with pg_conn.begin():
        await pg_conn.execute(text("SET LOCAL app.is_operator = 'true'"))
        await pg_conn.execute(text(
            f"INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'op_before_delete')"
        ))
    async with pg_conn.begin():
        await pg_conn.execute(text("SET LOCAL app.is_operator = 'true'"))
        await pg_conn.execute(text(
            f"DELETE FROM {_TABLE} WHERE source_term = 'op_before_delete' AND tenant_id IS NULL"
        ))


# ---------------------------------------------------------------------------
# テスト: operator リセット後（コネクションプール汚染防止）
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="module")
async def test_after_operator_reset_tenant_cannot_insert_shared(
    pg_conn: AsyncConnection,
) -> None:
    """operator リセット後にテナントが共有行を書けない（コネクションプール汚染防止）。

    同一コネクションで operator → reset → tenant の順で確認する。
    reset_operator_context() 相当の処理後に app.is_operator = '' になることを保証。
    """
    # 1. operator セッション → 共有行書き込み可
    async with pg_conn.begin():
        await pg_conn.execute(text("SET LOCAL app.is_operator = 'true'"))
        await pg_conn.execute(text(
            f"INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'before_reset')"
        ))
    # 2. operator リセット後にテナントとして共有行書き込み → 拒否
    with pytest.raises((ProgrammingError, Exception), match="42501|insufficient_privilege|new row violates"):
        async with pg_conn.begin():
            # reset_operator_context() に相当: app.is_operator = ''
            await pg_conn.execute(text("SET LOCAL app.is_operator = ''"))
            await pg_conn.execute(text("SET LOCAL app.tenant_id = '1'"))
            await pg_conn.execute(text(
                f"INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'after_reset_attempt')"
            ))


@pytest.mark.asyncio(loop_scope="module")
async def test_unset_is_operator_denies_shared_insert(pg_conn: AsyncConnection) -> None:
    """app.is_operator 未設定（RESET 後の NULL）でも共有行 INSERT は deny（フェイルクローズ）。

    current_setting('app.is_operator', true) は未設定時 NULL を返す。
    NULL = 'true' は false → deny。
    """
    with pytest.raises((ProgrammingError, Exception), match="42501|insufficient_privilege|new row violates"):
        async with pg_conn.begin():
            await pg_conn.execute(text("RESET app.is_operator"))
            await pg_conn.execute(text("SET LOCAL app.tenant_id = '1'"))
            await pg_conn.execute(text(
                f"INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'failclose')"
            ))
