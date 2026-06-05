import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 環境変数からDATABASE_URLを取得
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://myapp_user:password@postgres:5432/myapp_db")

# SA-18 Phase2: application_name でスモークテスト[7]判別
# asyncpg は application_name を connect() の直接引数として受け付けない。
# server_settings 経由で渡す必要がある（asyncpg 0.31.0 確認済み）。
_connect_args: dict = {
    "prepared_statement_cache_size": 0,  # ADR-065: コンテナ再起動後の InvalidCachedStatementError 防止
    "server_settings": {"application_name": "salesanchor_backend"},
}

# 非同期エンジンの作成（本番ではSQLログを無効化）
_engine_kwargs = {
    "echo": os.getenv("ENVIRONMENT", "development") != "production",
    "future": True,
}
# PostgreSQL使用時のみコネクションプール設定を追加（SQLiteはStaticPoolのため不要）
if DATABASE_URL.startswith("postgresql"):
    _engine_kwargs.update(
        pool_size=20,
        max_overflow=10,
        pool_recycle=3600,
        pool_pre_ping=True,
        pool_timeout=30,  # コネクションプール枯渇時の無限待機を防止（30秒で諦めて503を返す）
        connect_args=_connect_args,
    )
engine = create_async_engine(DATABASE_URL, **_engine_kwargs)

# 非同期セッションの作成
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# ベースクラス
Base = declarative_base()

# データベースセッションの依存性注入
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            # SQLエラー時は明示的にロールバックしてからコネクションを返却する。
            # ロールバックせずに close() すると INTRANS_INERROR 状態のままプールに
            # 返却され、次のリクエストで別の SQLAlchemyError が発生することがある。
            await session.rollback()
            raise


# ─── SA-18 Phase2: 管理者用（jarvis）engine ─────────────────────────
# DDL・クロステナント操作専用。ADMIN_DATABASE_URL 未設定時は DATABASE_URL にフォールバック。
ADMIN_DATABASE_URL: str = os.getenv("ADMIN_DATABASE_URL", DATABASE_URL)

_admin_connect_args: dict = {
    "prepared_statement_cache_size": 0,
    "server_settings": {"application_name": "salesanchor_admin_ops"},  # smoke[7] 判別用
}
_admin_engine_kwargs = {
    "echo": os.getenv("ENVIRONMENT", "development") != "production",
    "future": True,
}
if ADMIN_DATABASE_URL.startswith("postgresql"):
    _admin_engine_kwargs.update(
        pool_size=5,
        max_overflow=2,
        pool_recycle=1800,
        pool_pre_ping=True,
        connect_args=_admin_connect_args,
    )
admin_engine = create_async_engine(ADMIN_DATABASE_URL, **_admin_engine_kwargs)
AdminSessionLocal = sessionmaker(admin_engine, class_=AsyncSession, expire_on_commit=False)


async def get_admin_db() -> AsyncGenerator[AsyncSession, None]:
    """管理者専用セッション（DDL・クロステナント操作専用）。"""
    async with AdminSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
