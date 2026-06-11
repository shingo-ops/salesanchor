#!/usr/bin/env python3
"""ADR-128 用マイグレーションランナー。

実施内容:
  全テナントスキーマの order_shipping_details テーブルに
  Ship API / Pickup API 用カラムを additive 追加する。

冪等:
  ADD COLUMN IF NOT EXISTS で何度実行しても副作用なし。

実行方法（VPS 側）:
  docker compose exec backend python /app/scripts/migrate_adr128_extend_order_shipping.py

前提:
  - migration 048（order_shipping_details テーブル本体）が全テナントに適用済み
  - DATABASE_URL が postgresql:// または postgresql+asyncpg:// 形式
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = BASE_DIR / "migrations"


async def _exec(conn, sql: str) -> None:
    for stmt in sql.split(";"):
        stmt = stmt.strip()
        if stmt:
            await conn.exec_driver_sql(stmt)


async def main() -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    engine = create_async_engine(url, echo=False)

    try:
        logger.info("=== ADR-128 Migration (extend order_shipping_details) 開始 ===")

        async with engine.connect() as conn:
            r = await conn.execute(
                text(
                    "SELECT id, tenant_code FROM public.tenants "
                    "WHERE is_active = true ORDER BY id"
                )
            )
            tenants = [(row.id, row.tenant_code) for row in r]
        logger.info("対象テナント: %d", len(tenants))

        tmpl = (MIGRATIONS_DIR / "20260611_100000_extend_order_shipping_for_ship_api.sql").read_text("utf-8")
        for tid, tc in tenants:
            schema = f"tenant_{tid:03d}"
            try:
                async with engine.begin() as conn:
                    await _exec(
                        conn,
                        tmpl.replace("{schema}", schema)
                            .replace("{tenant_id}", str(tid)),
                    )
                logger.info(
                    "✓ %s (tenant_code=%s) order_shipping_details 拡張完了",
                    schema,
                    tc,
                )
            except Exception as e:
                logger.error("✗ %s 失敗: %s", schema, e)
                raise

        logger.info("=== ADR-128 Migration 完了 ===")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
