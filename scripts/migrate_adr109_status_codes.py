#!/usr/bin/env python3
"""ADR-109: status SSOT化 — 日本語ステータスを不変英字コードへ移行。

実施内容:
  全テナントスキーマの leads.status を1対1で変換する。
    - '新規'        → 'lead'
    - '商談中'      → 'negotiating'
    - '既存顧客'    → 'existing_customer'
    - '追客（短期）' → 'follow_up_short'
    - '追客（長期）' → 'follow_up_long'
    - '失注'        → 'lost'
    - '対象外'      → 'out_of_scope'

  また、public.leads テーブルの DEFAULT 値も 'lead' に変更する。

冪等:
  WHERE status = '...' 条件付きの UPDATE なので何度実行しても安全。

実行方法（VPS 側、docker compose exec 経由）:
  docker compose exec backend python /app/scripts/migrate_adr109_status_codes.py
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

# Mapping: old Japanese value -> new immutable code
STATUS_MAP = [
    ("新規", "lead"),
    ("商談中", "negotiating"),
    ("既存顧客", "existing_customer"),
    ("追客（短期）", "follow_up_short"),
    ("追客（長期）", "follow_up_long"),
    ("失注", "lost"),
    ("対象外", "out_of_scope"),
]


async def main() -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    engine = create_async_engine(url, echo=False)

    try:
        logger.info("=== ADR-109 Migration (status SSOT化) 開始 ===")

        async with engine.connect() as conn:
            r = await conn.execute(
                text("SELECT id, tenant_code FROM public.tenants WHERE is_active = true ORDER BY id")
            )
            tenants = [(row.id, row.tenant_code) for row in r]
        logger.info("対象テナント: %d", len(tenants))

        for tid, tc in tenants:
            schema = f"tenant_{tid:03d}"
            try:
                async with engine.begin() as conn:
                    counts = {}
                    for old_val, new_val in STATUS_MAP:
                        result = await conn.execute(
                            text(
                                f"UPDATE {schema}.leads SET status = :new_val, updated_at = NOW() "
                                f"WHERE status = :old_val"
                            ),
                            {"new_val": new_val, "old_val": old_val},
                        )
                        counts[f"{old_val}->{new_val}"] = result.rowcount

                    total = sum(counts.values())
                    logger.info(
                        "tenant %s (code=%s): %d rows updated — %s",
                        schema,
                        tc,
                        total,
                        ", ".join(f"{k}={v}" for k, v in counts.items() if v > 0) or "none",
                    )
            except Exception as e:
                logger.error("tenant %s 失敗: %s", schema, e)
                raise

        # ALTER DEFAULT on leads table (applies to all tenant schemas via inheritance or direct)
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE leads ALTER COLUMN status SET DEFAULT 'lead'"))
            logger.info("ALTER TABLE leads DEFAULT -> 'lead' 完了")

        # Verify: check for any remaining old values
        async with engine.connect() as conn:
            for tid, tc in tenants:
                schema = f"tenant_{tid:03d}"
                result = await conn.execute(
                    text(
                        f"SELECT COUNT(*) FROM {schema}.leads "
                        f"WHERE status IN ('新規', '商談中', '既存顧客', '追客（短期）', '追客（長期）', '失注', '対象外')"
                    )
                )
                remaining = result.scalar()
                if remaining and remaining > 0:
                    logger.warning(
                        "WARNING: %s still has %d rows with old status values!", schema, remaining
                    )
                else:
                    logger.info("tenant %s: 旧値残存ゼロ (検証OK)", schema)

        logger.info("=== ADR-109 Migration 完了 ===")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
