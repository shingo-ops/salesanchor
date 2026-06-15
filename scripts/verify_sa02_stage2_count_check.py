#!/usr/bin/env python3
"""SA-02 段階2 件数突合検証スクリプト。

meta_messages と conversation_logs の件数を突合し、移行状態を報告する。

【実行方法】
  # 移行前（現状把握）
  docker compose exec backend python /app/scripts/verify_sa02_stage2_count_check.py

  # 移行後（突合確認）
  docker compose exec backend python /app/scripts/verify_sa02_stage2_count_check.py

  # 不一致があれば非0で終了（CI組み込み用）
  docker compose exec backend python /app/scripts/verify_sa02_stage2_count_check.py --strict

出力フォーマット（CSV形式）:
  tenant_code, meta_total, conv_from_meta, coverage_pct, gap
"""
from __future__ import annotations

import argparse
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


async def check_tenant(
    engine,
    tenant_id: int,
    tenant_code: str,
) -> dict:
    """1テナントの件数突合を実行。"""
    schema = f"tenant_{tenant_id:03d}"
    result = {
        "tenant_id": tenant_id,
        "tenant_code": tenant_code,
        "schema": schema,
        "meta_total": 0,
        "conv_total": 0,
        "conv_from_meta_mid": 0,   # message_id ありの移行分
        "conv_from_legacy": 0,     # meta_legacy: 合成キーの移行分
        "conv_from_meta_total": 0, # 上記合計
        "coverage_pct": 0.0,
        "gap": 0,
        "error": None,
    }

    try:
        async with engine.connect() as conn:
            # meta_messages 件数
            has_meta = await conn.execute(text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = :s AND table_name = 'meta_messages'"
            ), {"s": schema})
            if not has_meta.fetchone():
                result["error"] = "meta_messages なし"
                return result

            r = await conn.execute(text(
                f"SELECT COUNT(*) FROM {schema}.meta_messages"
            ))
            result["meta_total"] = r.scalar() or 0

            # conversation_logs 総件数
            has_conv = await conn.execute(text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = :s AND table_name = 'conversation_logs'"
            ), {"s": schema})
            if not has_conv.fetchone():
                result["error"] = "conversation_logs なし"
                return result

            r = await conn.execute(text(
                f"SELECT COUNT(*) FROM {schema}.conversation_logs WHERE deleted_at IS NULL"
            ))
            result["conv_total"] = r.scalar() or 0

            # 移行マーカーで正確に移行行を特定
            # analysis->>'_source' = 'sa02_stage2_migration' が移行スクリプトの識別子
            r = await conn.execute(text(
                f"SELECT COUNT(*) FROM {schema}.conversation_logs "
                f"WHERE analysis->>'_source' = 'sa02_stage2_migration'"
            ))
            result["conv_from_meta_total"] = r.scalar() or 0

            # 内訳: meta_legacy キーのもの（message_id なし行）
            r = await conn.execute(text(
                f"SELECT COUNT(*) FROM {schema}.conversation_logs "
                f"WHERE analysis->>'_source' = 'sa02_stage2_migration' "
                f"  AND external_message_id LIKE 'meta_legacy:%'"
            ))
            result["conv_from_legacy"] = r.scalar() or 0
            result["conv_from_meta_mid"] = result["conv_from_meta_total"] - result["conv_from_legacy"]

            if result["meta_total"] > 0:
                result["coverage_pct"] = round(
                    result["conv_from_meta_total"] / result["meta_total"] * 100, 1
                )
            result["gap"] = result["meta_total"] - result["conv_from_meta_total"]

    except Exception as e:
        result["error"] = str(e)

    return result


async def main(strict: bool, target_tenant_id: int | None) -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]

    engine = create_async_engine(url, echo=False)

    logger.info("=== SA-02 段階2 件数突合チェック ===")

    try:
        async with engine.connect() as conn:
            q = "SELECT id, tenant_code FROM public.tenants WHERE is_active = true"
            params: dict = {}
            if target_tenant_id:
                q += " AND id = :target_tenant_id"
                params["target_tenant_id"] = target_tenant_id
                logger.info("テナント指定: tenant_id=%d", target_tenant_id)
            q += " ORDER BY id"
            r = await conn.execute(text(q), params)
            tenants = [(row.id, row.tenant_code) for row in r]

        print("\n{:<20} {:>12} {:>12} {:>12} {:>10} {:>8}".format(
            "tenant_code", "meta_total", "conv_from_meta", "conv_total", "coverage%", "gap"
        ))
        print("-" * 80)

        total_meta = 0
        total_conv_from_meta = 0
        total_gap = 0
        has_gap = False

        for tid, tc in tenants:
            r = await check_tenant(engine, tid, tc)
            if r.get("error"):
                print(f"{tc:<20} ERROR: {r['error']}")
                continue

            total_meta += r["meta_total"]
            total_conv_from_meta += r["conv_from_meta_total"]
            total_gap += r["gap"]

            gap_marker = " ⚠️ " if r["gap"] > 0 else " ✅"
            print("{:<20} {:>12,} {:>12,} {:>12,} {:>9.1f}% {:>7,}{}".format(
                tc,
                r["meta_total"],
                r["conv_from_meta_total"],
                r["conv_total"],
                r["coverage_pct"],
                r["gap"],
                gap_marker,
            ))

            if r["gap"] > 0:
                has_gap = True

        print("-" * 80)
        coverage = round(total_conv_from_meta / total_meta * 100, 1) if total_meta > 0 else 0.0
        print("{:<20} {:>12,} {:>12,} {:>21} {:>7,}".format(
            "TOTAL", total_meta, total_conv_from_meta, f"{coverage:.1f}%", total_gap
        ))
        print()

        if has_gap:
            logger.warning("⚠️  未移行の gap があります（gap=%d）", total_gap)
            logger.warning("    移行スクリプト: scripts/migrate_sa02_stage2_meta_to_conv_logs.py")
            if strict:
                sys.exit(1)
        else:
            logger.info("✅ 全テナント: coverage 100%%（gap=0）")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SA-02 段階2 件数突合チェック")
    parser.add_argument("--strict", action="store_true", help="gap があれば非0で終了（CI用）")
    parser.add_argument("--tenant-id", type=int, help="特定テナントのみ確認（テスト用）")
    args = parser.parse_args()
    asyncio.run(main(strict=args.strict, target_tenant_id=args.tenant_id))
