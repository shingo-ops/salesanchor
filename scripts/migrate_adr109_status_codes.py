#!/usr/bin/env python3
"""ADR-109: status SSOT化 — 日本語・旧英語ステータスを不変英字コードへ移行。

実施内容:
  全テナントスキーマの leads.status を1対1で変換する。

  日本語 → 新コード:
    - '新規'        → 'lead'
    - '商談中'      → 'negotiating'
    - '既存顧客'    → 'existing_customer'
    - '追客（短期）' → 'follow_up_short'
    - '追客（長期）' → 'follow_up_long'
    - '失注'        → 'lost'
    - '対象外'      → 'out_of_scope'

  旧英語 → 新コード（ADR-109 以前の非標準値、tenant_006 で確認済み）:
    - 'new'         → 'lead'             （新規リード）
    - 'in_progress' → 'negotiating'      （商談進行中）
    - 'converted'   → 'existing_customer'（成約済み既存顧客）

  また、各テナントスキーマの leads テーブルの DEFAULT 値も 'lead' に変更する。

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

# Mapping: old value -> new immutable code
# Japanese values (original migration targets)
STATUS_MAP = [
    ("新規", "lead"),
    ("商談中", "negotiating"),
    ("既存顧客", "existing_customer"),
    ("追客（短期）", "follow_up_short"),
    ("追客（長期）", "follow_up_long"),
    ("失注", "lost"),
    ("対象外", "out_of_scope"),
    # Legacy English values (pre-ADR-109 non-standard codes, confirmed in tenant_006)
    ("new", "lead"),
    ("in_progress", "negotiating"),
    ("converted", "existing_customer"),
]

# The 7 valid ADR-109 codes — used for comprehensive post-migration verification
VALID_STATUS_CODES = frozenset([
    "lead",
    "negotiating",
    "existing_customer",
    "follow_up_short",
    "follow_up_long",
    "lost",
    "out_of_scope",
])

# All values recognised by this migration (old + new).
# Any value outside this set is "unexpected" and must abort the migration.
_ALL_KNOWN_VALS = VALID_STATUS_CODES | frozenset(old for old, _ in STATUS_MAP)


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

        # ── 事前検証: 想定外の status 値があれば UPDATE なしで中断 ──────────────
        logger.info("=== [Pre-check] 想定外ステータス値の確認 ===")
        unknown_found = False
        for tid, tc in tenants:
            schema = f"tenant_{tid:03d}"
            async with engine.connect() as pre_conn:
                # status 列の存在チェック
                col_check = await pre_conn.execute(
                    text("""
                        SELECT COUNT(*) FROM information_schema.columns
                        WHERE table_schema = :schema AND table_name = 'leads'
                        AND column_name = 'status'
                    """),
                    {"schema": schema},
                )
                if not col_check.scalar():
                    continue
                # 全 status の distinct 値を取得
                rows = await pre_conn.execute(
                    text(f"SELECT DISTINCT status FROM {schema}.leads WHERE status IS NOT NULL")
                )
                for (val,) in rows:
                    if val not in _ALL_KNOWN_VALS:
                        logger.error(
                            "[Pre-check] %s: 想定外の status 値 '%s' を検出。"
                            "マッピングを定義せずに移行することはできません。",
                            schema, val,
                        )
                        unknown_found = True
        if unknown_found:
            logger.error("=== 事前検証失敗: 想定外値が存在するため migration を中断します ===")
            sys.exit(1)
        logger.info("=== [Pre-check] 全テナント OK — migration を開始します ===")

        for tid, tc in tenants:
            schema = f"tenant_{tid:03d}"
            try:
                # 冪等性ガード: status 列が存在しない場合はスキップ
                async with engine.connect() as check_conn:
                    col_check = await check_conn.execute(
                        text("""
                            SELECT COUNT(*) FROM information_schema.columns
                            WHERE table_schema = :schema AND table_name = 'leads'
                            AND column_name = 'status'
                        """),
                        {"schema": schema},
                    )
                    if not col_check.scalar():
                        logger.warning("tenant %s: leads.status column not found, skipping", schema)
                        continue
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

        # ALTER DEFAULT on each tenant schema's leads table
        for tid, tc in tenants:
            schema = f"tenant_{tid:03d}"
            try:
                async with engine.connect() as check_conn:
                    col_check = await check_conn.execute(
                        text("""
                            SELECT COUNT(*) FROM information_schema.columns
                            WHERE table_schema = :schema AND table_name = 'leads'
                            AND column_name = 'status'
                        """),
                        {"schema": schema},
                    )
                    if not col_check.scalar():
                        logger.info("tenant %s: no status column, skipping ALTER DEFAULT", schema)
                        continue
                async with engine.begin() as conn:
                    await conn.execute(
                        text(f"ALTER TABLE IF EXISTS {schema}.leads ALTER COLUMN status SET DEFAULT 'lead'")
                    )
                    logger.info("ALTER TABLE %s.leads DEFAULT -> 'lead' 完了", schema)
            except Exception as e:
                logger.error("tenant %s DEFAULT 変更失敗: %s", schema, e)
                raise

        # Verify: comprehensive check — any value outside the 7 valid ADR-109 codes must be 0
        valid_codes_sql = ", ".join(f"'{c}'" for c in sorted(VALID_STATUS_CODES))
        all_ok = True
        async with engine.connect() as conn:
            for tid, tc in tenants:
                schema = f"tenant_{tid:03d}"
                col_check = await conn.execute(
                    text("""
                        SELECT COUNT(*) FROM information_schema.columns
                        WHERE table_schema = :schema AND table_name = 'leads'
                        AND column_name = 'status'
                    """),
                    {"schema": schema},
                )
                if not col_check.scalar():
                    logger.info("tenant %s: no status column, skipping verification", schema)
                    continue
                result = await conn.execute(
                    text(
                        f"SELECT status, COUNT(*) AS cnt FROM {schema}.leads "
                        f"WHERE status IS NOT NULL AND status NOT IN ({valid_codes_sql}) "
                        f"GROUP BY status ORDER BY status"
                    )
                )
                invalid_rows = result.fetchall()
                if invalid_rows:
                    all_ok = False
                    for row in invalid_rows:
                        logger.warning(
                            "WARNING: %s still has %d rows with invalid status='%s'!",
                            schema, row.cnt, row.status,
                        )
                else:
                    logger.info("tenant %s: 全行が正規コード (検証OK)", schema)
        if not all_ok:
            logger.error("=== 検証失敗: 正規コード外の値が残存しています ===")
            sys.exit(1)

        logger.info("=== ADR-109 Migration 完了 ===")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
