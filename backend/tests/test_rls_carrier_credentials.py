"""
public.tenant_carrier_credentials の RLS（Row Level Security）テスト。

ADR-124 D1: RLS ポリシー `tenant_isolation_carrier_credentials` が
別テナントのキャリア認証情報を隠蔽することを検証する。

PostgreSQL 専用テスト。ローカル pytest（SQLite）では自動的に skip する。
CI で RLS_TEST_DATABASE_URL を設定したときのみ実行される。

検証内容:
1. テナント A の context でテナント B の行が SELECT で見えない（cross-tenant 遮断）
2. 同じ tenant_id を SET LOCAL app.tenant_id すれば自テナントの行が見える
3. app.tenant_id 未設定（空文字列）でも INTEGER キャストエラーが発生しない
   （NULLIF ポリシーの動作確認）

CI 実行例:
    RLS_TEST_DATABASE_URL=postgresql+asyncpg://salesanchor_app:apppass@localhost/jarvis_test_db \\
    RLS_ADMIN_DATABASE_URL=postgresql+asyncpg://jarvis:testpass@localhost/jarvis_test_db \\
        pytest backend/tests/test_rls_carrier_credentials.py -v

変更履歴:
    2026-06-09: ADR-124 Phase A 初版
"""

from __future__ import annotations

import os
from typing import Optional

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine


_RLS_DB_URL: Optional[str] = os.getenv("RLS_TEST_DATABASE_URL")
_ADMIN_URL: str = os.getenv(
    "RLS_ADMIN_DATABASE_URL",
    "postgresql+asyncpg://jarvis:testpass@localhost:5432/jarvis_test_db",
)

_TABLE = "public.carrier_credentials_rls_test"

pytestmark = pytest.mark.skipif(
    not _RLS_DB_URL,
    reason=(
        "PostgreSQL ベースの RLS テストは環境変数 RLS_TEST_DATABASE_URL が "
        "設定されたときだけ実行する（ローカル pytest は SQLite）"
    ),
)


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def admin_engine():
    """管理者接続（jarvis）— DDL / GRANT / 種データ投入専用。"""
    eng = create_async_engine(_ADMIN_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def app_engine():
    """アプリ接続（salesanchor_app: NOSUPERUSER NOBYPASSRLS）— アサーション専用。"""
    assert _RLS_DB_URL
    eng = create_async_engine(_RLS_DB_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def setup_test_table(admin_engine):
    """
    本番テーブルとは別のテスト専用テーブルを作成し、RLS ポリシーを設定する。

    本番 tenant_carrier_credentials と同じポリシー:
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER)

    DDL は管理者接続（admin_engine: SUPERUSER）で実行。
    DML アサーションは salesanchor_app（app_engine: NOBYPASSRLS）で実行。
    """
    async with admin_engine.begin() as conn:
        # テスト用テーブル作成（本番テーブルの最小構成）
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {_TABLE} (
                id        SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                carrier   TEXT    NOT NULL,
                env       TEXT    NOT NULL DEFAULT 'sandbox'
            )
        """))
        await conn.execute(text(f"ALTER TABLE {_TABLE} ENABLE ROW LEVEL SECURITY"))
        # FORCE: テーブル所有者にも RLS 適用（SUPERUSER は依然バイパス）
        await conn.execute(text(f"ALTER TABLE {_TABLE} FORCE ROW LEVEL SECURITY"))
        # salesanchor_app に DML 付与（DDL は付与しない）
        await conn.execute(text(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON {_TABLE} TO salesanchor_app"
        ))
        await conn.execute(text(
            f"GRANT USAGE, SELECT ON SEQUENCE {_TABLE}_id_seq TO salesanchor_app"
        ))
        # RLS ポリシー設定（本番と同型）
        await conn.execute(text(
            f"DROP POLICY IF EXISTS tenant_isolation_carrier_credentials ON {_TABLE}"
        ))
        await conn.execute(text(f"""
            CREATE POLICY tenant_isolation_carrier_credentials ON {_TABLE}
                USING (
                    tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
                )
        """))

    yield

    # cleanup
    async with admin_engine.begin() as conn:
        await conn.execute(text(f"DROP TABLE IF EXISTS {_TABLE} CASCADE"))


@pytest_asyncio.fixture(loop_scope="module")
async def admin_conn(admin_engine, setup_test_table):
    """管理者接続（種データ投入専用）。"""
    async with admin_engine.connect() as conn:
        yield conn


@pytest_asyncio.fixture(loop_scope="module")
async def app_conn(app_engine, setup_test_table):
    """salesanchor_app 接続（アサーション専用）。"""
    async with app_engine.connect() as conn:
        yield conn


# ---------------------------------------------------------------------------
# テスト 1: クロステナント遮断
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="module")
async def test_cross_tenant_blocking(
    admin_conn: AsyncConnection,
    app_conn: AsyncConnection,
) -> None:
    """テナント 1 の context でテナント 2 のキャリア認証情報が SELECT できない。"""
    # 管理者（SUPERUSER = RLS バイパス）でテナント 2 のデータを投入
    async with admin_conn.begin():
        await admin_conn.execute(text(
            f"INSERT INTO {_TABLE} (tenant_id, carrier, env) VALUES (2, 'fedex', 'sandbox')"
        ))

    # salesanchor_app(tenant=1) から tenant=2 行が見えないことを確認
    async with app_conn.begin():
        await app_conn.execute(text("SET LOCAL app.tenant_id = '1'"))
        result = await app_conn.execute(text(
            f"SELECT carrier FROM {_TABLE} WHERE tenant_id = 2"
        ))
        rows = result.fetchall()
        assert rows == [], (
            f"クロステナント遮断 FAIL: tenant=1 が tenant=2 のキャリア情報を参照できた: {rows}"
        )


# ---------------------------------------------------------------------------
# テスト 2: 自テナントは見える
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="module")
async def test_own_tenant_visible(
    admin_conn: AsyncConnection,
    app_conn: AsyncConnection,
) -> None:
    """app.tenant_id を正しく設定すると自テナントの行が見える。"""
    # 管理者でテナント 10 のデータを投入
    async with admin_conn.begin():
        await admin_conn.execute(text(
            f"INSERT INTO {_TABLE} (tenant_id, carrier, env) VALUES (10, 'fedex', 'production')"
        ))

    async with app_conn.begin():
        await app_conn.execute(text("SET LOCAL app.tenant_id = '10'"))
        result = await app_conn.execute(text(
            f"SELECT carrier, env FROM {_TABLE} WHERE tenant_id = 10"
        ))
        rows = result.fetchall()
        assert len(rows) == 1, f"自テナントの行が見えない: {rows}"
        assert rows[0][0] == "fedex"
        assert rows[0][1] == "production"


# ---------------------------------------------------------------------------
# テスト 3: app.tenant_id 未設定で NULLIF がキャストエラーを防ぐ
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="module")
async def test_nullif_prevents_cast_error_on_unset(
    admin_conn: AsyncConnection,
    app_conn: AsyncConnection,
) -> None:
    """RESET app.tenant_id 後（空文字相当）に SELECT してもキャストエラーが発生しない。
    NULLIF が空文字 → NULL に変換し、tenant_id = NULL は常に FALSE となるため行は返らない。
    """
    async with admin_conn.begin():
        await admin_conn.execute(text(
            f"INSERT INTO {_TABLE} (tenant_id, carrier, env) VALUES (20, 'dhl', 'sandbox')"
        ))

    # app.tenant_id を RESET（空文字列 or NULL 相当）
    # キャストエラーではなく空結果が返ることを確認
    async with app_conn.begin():
        await app_conn.execute(text("RESET app.tenant_id"))
        # エラーが出なければ NULLIF が正しく動作している
        result = await app_conn.execute(text(
            f"SELECT carrier FROM {_TABLE}"
        ))
        rows = result.fetchall()
        # 空文字 → NULL → tenant_id = NULL は常に FALSE → 行は返らない
        assert rows == [], (
            f"app.tenant_id 未設定でも行が見えてしまう（RLS が機能していない可能性）: {rows}"
        )
