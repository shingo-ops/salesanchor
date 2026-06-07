#!/usr/bin/env python3
"""ADR-119: lead_channels バックフィル — leads.source / discord_user_id → lead_channels。

実施内容:
  全テナントスキーマの既存 leads.source を解析し、
  プラットフォーム別に lead_channels へ移植する。

  対象パターン:
    - source LIKE 'messenger:%'  → platform='messenger',  external_id=PSID
    - source LIKE 'instagram:%'  → platform='instagram',  external_id=IGSID
    - source LIKE 'discord:%'    → platform='discord',    external_id=Discord UID

  追加対象:
    - discord_user_id NOT NULL で上記 source がない leads
      → platform='discord', external_id=discord_user_id

冪等:
  INSERT ... ON CONFLICT (platform, external_id) DO NOTHING

実行方法（VPS 側、docker compose exec 経由）:
  docker compose exec backend python /app/scripts/migrate_adr119_lead_channels_backfill.py
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# プレフィックス → platform 名
PLATFORM_PREFIXES = [
    ("messenger:", "messenger"),
    ("instagram:", "instagram"),
    ("discord:", "discord"),
]


async def backfill_schema(conn, schema: str) -> dict[str, int]:
    """1テナントスキーマの lead_channels バックフィルを実行して件数を返す。"""
    counts: dict[str, int] = {p: 0 for _, p in PLATFORM_PREFIXES}
    counts["discord_uid"] = 0

    # lead_channels テーブルの存在確認（前の migration が通っているはず）
    tbl_check = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = :schema AND table_name = 'lead_channels'"
        ),
        {"schema": schema},
    )
    if not tbl_check.scalar():
        logger.warning("%s: lead_channels table not found, skipping", schema)
        return counts

    # 1) source プレフィックスから移植
    for prefix, platform in PLATFORM_PREFIXES:
        result = await conn.execute(
            text(
                f"""
                INSERT INTO {schema}.lead_channels (lead_id, platform, external_id, display_name)
                SELECT
                    id,
                    :platform,
                    SUBSTRING(source FROM :offset),
                    customer_name
                FROM {schema}.leads
                WHERE source LIKE :pattern
                ON CONFLICT (platform, external_id) DO NOTHING
                """
            ),
            {
                "platform": platform,
                "offset": len(prefix) + 1,  # SUBSTRING は 1-indexed
                "pattern": f"{prefix}%",
            },
        )
        counts[platform] += result.rowcount

    # 2) discord_user_id が残っている leads（source が 'discord:' で始まらないケース）
    discord_uid_result = await conn.execute(
        text(
            f"""
            INSERT INTO {schema}.lead_channels (lead_id, platform, external_id, display_name)
            SELECT
                id,
                'discord',
                discord_user_id,
                customer_name
            FROM {schema}.leads
            WHERE discord_user_id IS NOT NULL
              AND (source IS NULL OR source NOT LIKE 'discord:%')
            ON CONFLICT (platform, external_id) DO NOTHING
            """
        )
    )
    counts["discord_uid"] += discord_uid_result.rowcount

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
        logger.info("=== ADR-119 lead_channels backfill 開始 ===")

        async with engine.connect() as conn:
            r = await conn.execute(
                text(
                    "SELECT id, tenant_code FROM public.tenants "
                    "WHERE is_active = true ORDER BY id"
                )
            )
            tenants = [(row.id, row.tenant_code) for row in r]
        logger.info("対象テナント: %d", len(tenants))

        total_all: dict[str, int] = {}
        for tid, tc in tenants:
            schema = f"tenant_{tid:03d}"
            # スキーマ名を allowlist で検証（f-string 補間前の安全確認）
            if not re.fullmatch(r"tenant_\d{3}", schema):
                logger.error("Unexpected schema name: %s — skipping", schema)
                continue
            try:
                async with engine.begin() as conn:
                    counts = await backfill_schema(conn, schema)

                total = sum(counts.values())
                non_zero = {k: v for k, v in counts.items() if v > 0}
                logger.info(
                    "tenant %s (code=%s): %d rows inserted — %s",
                    schema, tc, total,
                    ", ".join(f"{k}={v}" for k, v in non_zero.items()) or "none",
                )
                for k, v in counts.items():
                    total_all[k] = total_all.get(k, 0) + v
            except Exception as exc:
                logger.error("tenant %s: FAILED — %s", schema, exc)
                raise

        logger.info(
            "=== 全テナント合計: %s ===",
            ", ".join(f"{k}={v}" for k, v in total_all.items()),
        )
        logger.info("=== ADR-119 lead_channels backfill 完了 ===")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
