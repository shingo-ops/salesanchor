"""
RLS 不変条件テスト（SA-19）。
salesanchor_app（NOSUPERUSER NOBYPASSRLS）で接続して以下を検証:
1. クロステナント遮断（tenant=A が tenant=B 行を SELECT できない）
2. 共有行は operator のみ書込可（is_operator='true' 以外は 42501）
3. フェイルクローズ（app.is_operator 未設定 → 拒否）
4. 汚染防止（operator リセット後 → tenant が共有行を書けない）

DDL（CREATE TABLE / ALTER TABLE / CREATE POLICY / GRANT）は管理者接続（admin_engine）で実行。
アサーション（SELECT / INSERT テスト）は salesanchor_app 接続（app_engine）で実行。
CI role = DML only の不変条件を守る。
"""
from __future__ import annotations

import os
from typing import Optional

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection
from sqlalchemy.exc import ProgrammingError

_APP_URL: Optional[str] = os.getenv("RLS_TEST_DATABASE_URL")
_ADMIN_URL: str = os.getenv(
    "RLS_ADMIN_DATABASE_URL",
    "postgresql+asyncpg://jarvis:testpass@localhost:5432/jarvis_test_db"
)
_TABLE = "public.translation_glossary_rls_test"

pytestmark = pytest.mark.skipif(
    not _APP_URL,
    reason="RLS_TEST_DATABASE_URL が未設定（PostgreSQL 専用テスト）"
)


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def admin_engine():
    """管理者接続（jarvis）— DDL / GRANT / 種データ投入専用。"""
    eng = create_async_engine(_ADMIN_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def app_engine():
    """アプリ接続（salesanchor_app）— アサーション専用。"""
    eng = create_async_engine(_APP_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def setup_test_table(admin_engine):
    """管理者で test テーブルを作成・RLS 設定（_TABLE は本番テーブルと別名）。"""
    async with admin_engine.begin() as conn:
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {_TABLE} (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER,
                source_term TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE
            )
        """))
        await conn.execute(text(f"ALTER TABLE {_TABLE} ENABLE ROW LEVEL SECURITY"))
        await conn.execute(text(f"ALTER TABLE {_TABLE} FORCE ROW LEVEL SECURITY"))
        # salesanchor_app に DML 付与（CREATE は付与しない）
        await conn.execute(text(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON {_TABLE} TO salesanchor_app"
        ))
        await conn.execute(text(
            f"GRANT USAGE, SELECT ON SEQUENCE {_TABLE}_id_seq TO salesanchor_app"
        ))
        # SELECT ポリシー
        await conn.execute(text(f"DROP POLICY IF EXISTS inv_select ON {_TABLE}"))
        await conn.execute(text(f"""
            CREATE POLICY inv_select ON {_TABLE} FOR SELECT USING (
                tenant_id IS NULL
                OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
            )
        """))
        # INSERT ポリシー
        await conn.execute(text(f"DROP POLICY IF EXISTS inv_insert ON {_TABLE}"))
        await conn.execute(text(f"""
            CREATE POLICY inv_insert ON {_TABLE} FOR INSERT WITH CHECK (
                CASE WHEN tenant_id IS NULL
                    THEN current_setting('app.is_operator', true) = 'true'
                    ELSE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
                END
            )
        """))
    yield
    async with admin_engine.begin() as conn:
        await conn.execute(text(f"DROP TABLE IF EXISTS {_TABLE} CASCADE"))


@pytest_asyncio.fixture(loop_scope="module")
async def app_conn(app_engine, setup_test_table):
    """salesanchor_app 接続 — アサーション専用。"""
    async with app_engine.connect() as conn:
        yield conn


@pytest_asyncio.fixture(loop_scope="module")
async def admin_conn(admin_engine, setup_test_table):
    """管理者接続 — 種データ投入専用。"""
    async with admin_engine.connect() as conn:
        yield conn


# --- テスト 1: クロステナント遮断 ---
@pytest.mark.asyncio(loop_scope="module")
async def test_cross_tenant_blocking(
    admin_conn: AsyncConnection, app_conn: AsyncConnection
) -> None:
    """tenant=1 の salesanchor_app セッションが tenant=2 の行を SELECT できない。"""
    # admin で tenant=2 行を挿入（RLS を気にせず直接挿入）
    async with admin_conn.begin():
        await admin_conn.execute(text(
            f"INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (2, 'tenant2_secret')"
        ))
    # salesanchor_app(tenant=1) から tenant=2 行が見えないことを確認
    async with app_conn.begin():
        await app_conn.execute(text("SET LOCAL app.tenant_id = '1'"))
        await app_conn.execute(text("SET LOCAL app.is_operator = ''"))
        result = await app_conn.execute(text(
            f"SELECT source_term FROM {_TABLE} WHERE tenant_id = 2"
        ))
        rows = result.fetchall()
        assert rows == [], (
            f"クロステナント遮断 FAIL: tenant=1 が tenant=2 行を参照できた: {rows}"
        )


# --- テスト 2: 共有行は operator のみ書込可 ---
@pytest.mark.asyncio(loop_scope="module")
async def test_shared_rows_operator_only(app_conn: AsyncConnection) -> None:
    """is_operator 未設定の salesanchor_app が共有行（tenant_id IS NULL）を INSERT できない。"""
    with pytest.raises(
        (ProgrammingError, Exception),
        match="42501|insufficient_privilege|new row violates",
    ):
        async with app_conn.begin():
            await app_conn.execute(text("SET LOCAL app.tenant_id = '1'"))
            await app_conn.execute(text("SET LOCAL app.is_operator = ''"))
            await app_conn.execute(text(
                f"INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'shared_forbidden')"
            ))


# --- テスト 3: フェイルクローズ ---
@pytest.mark.asyncio(loop_scope="module")
async def test_failclose_unset_is_operator(app_conn: AsyncConnection) -> None:
    """RESET app.is_operator 後（NULL 相当）に共有行 INSERT → 拒否（フェイルクローズ）。"""
    with pytest.raises(
        (ProgrammingError, Exception),
        match="42501|insufficient_privilege|new row violates",
    ):
        async with app_conn.begin():
            await app_conn.execute(text("RESET app.is_operator"))
            await app_conn.execute(text("SET LOCAL app.tenant_id = '1'"))
            await app_conn.execute(text(
                f"INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'failclose')"
            ))


# --- テスト 4: 汚染防止 ---
@pytest.mark.asyncio(loop_scope="module")
async def test_pool_pollution_prevention(app_conn: AsyncConnection) -> None:
    """operator として書込後、is_operator をリセットしてもテナントが共有行を書けない。"""
    # operator として書込成功
    async with app_conn.begin():
        await app_conn.execute(text("SET LOCAL app.is_operator = 'true'"))
        await app_conn.execute(text(
            f"INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'pollution_before')"
        ))
    # reset 後にテナントとして共有行書込 → 拒否
    with pytest.raises(
        (ProgrammingError, Exception),
        match="42501|insufficient_privilege|new row violates",
    ):
        async with app_conn.begin():
            await app_conn.execute(text("SET LOCAL app.is_operator = ''"))
            await app_conn.execute(text("SET LOCAL app.tenant_id = '1'"))
            await app_conn.execute(text(
                f"INSERT INTO {_TABLE} (tenant_id, source_term) VALUES (NULL, 'pollution_after')"
            ))
