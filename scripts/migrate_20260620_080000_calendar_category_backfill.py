#!/usr/bin/env python3
"""Migration 080: calendar_events.category の保守的 backfill。

実施内容:
  - category IS NULL の既存行のみを対象にする
  - calendar_type='personal' は personal で確定
  - source='app' かつ明確なキーワード一致がある行のみ
    shipping / billing / purchase を補完する
  - release / holiday / meeting / 判別不能は NULL のまま据え置く
  - 明示 category がある行は絶対に上書きしない

冪等:
  - WHERE category IS NULL のみ更新
  - 既に埋まっている行は再実行しても変更しない

実行方法（VPS 側、docker compose exec 経由）:
  docker compose exec backend python /app/scripts/migrate_20260620_080000_calendar_category_backfill.py
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.services.calendar_category_utils import resolve_backfill_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def backfill_schema(conn, schema: str) -> dict[str, int]:
    """1テナントスキーマの category backfill を実行して件数を返す。"""
    counts: dict[str, int] = {
        "personal": 0,
        "billing": 0,
        "shipping": 0,
        "purchase": 0,
        "skipped": 0,
    }

    table_check = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = :schema AND table_name = 'calendar_events'"
        ),
        {"schema": schema},
    )
    if table_check.scalar() is None:
        logger.warning("%s: calendar_events table not found, skipping", schema)
        return counts

    rows = await conn.execute(
        text(
            f"""
            SELECT id, category, calendar_type, source, title, description, location
            FROM {schema}.calendar_events
            WHERE category IS NULL
            ORDER BY id
            """
        )
    )

    for row in rows.fetchall():
        row_map = {
            "id": row.id,
            "category": row.category,
            "calendar_type": row.calendar_type,
            "source": row.source,
            "title": row.title,
            "description": row.description,
            "location": row.location,
        }
        category = resolve_backfill_category(row_map)
        if category is None:
            counts["skipped"] += 1
            continue

        result = await conn.execute(
            text(
                f"""
                UPDATE {schema}.calendar_events
                SET category = :category,
                    updated_at = NOW()
                WHERE id = :id
                  AND category IS NULL
                """
            ),
            {"id": row.id, "category": category},
        )
        if result.rowcount:
            counts[category] = counts.get(category, 0) + result.rowcount

    return counts


async def main() -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    engine = create_async_engine(url, echo=False)

    try:
        logger.info("=== Migration 080 (calendar category backfill) 開始 ===")

        async with engine.connect() as conn:
            r = await conn.execute(
                text("SELECT id, tenant_code FROM public.tenants WHERE is_active = true ORDER BY id")
            )
            tenants = [(row.id, row.tenant_code) for row in r]
        logger.info("対象テナント: %d", len(tenants))

        total_all: dict[str, int] = {"personal": 0, "billing": 0, "shipping": 0, "purchase": 0, "skipped": 0}
        for tid, tc in tenants:
            schema = f"tenant_{tid:03d}"
            if not re.fullmatch(r"tenant_\d{3}", schema):
                logger.error("Unexpected schema name: %s — skipping", schema)
                continue
            try:
                async with engine.begin() as conn:
                    counts = await backfill_schema(conn, schema)

                total = sum(counts.values())
                non_zero = {k: v for k, v in counts.items() if v > 0}
                logger.info(
                    "✓ %s (tenant_code=%s): %d rows inspected — %s",
                    schema,
                    tc,
                    total,
                    ", ".join(f"{k}={v}" for k, v in non_zero.items()) or "none",
                )
                for k, v in counts.items():
                    total_all[k] = total_all.get(k, 0) + v
            except Exception as exc:
                logger.error("✗ %s 失敗: %s", schema, exc)
                raise

        logger.info(
            "=== 全テナント合計: %s ===",
            ", ".join(f"{k}={v}" for k, v in total_all.items()),
        )
        logger.info("=== Migration 080 完了 ===")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
