#!/usr/bin/env python3
"""SA-02 段階2: meta_messages → conversation_logs 移行スクリプト。

【概要】
既存の `meta_messages` テーブル（Messenger/Instagram/Discord 受信履歴）を
`conversation_logs` テーブルに移行する。

【実行方法（本番はShingo GO後のみ）】
  # ドライランで件数だけ確認（DBは変更しない）
  docker compose exec backend python /app/scripts/migrate_sa02_stage2_meta_to_conv_logs.py --dry-run

  # 実際の移行（Shingo GO後のみ）
  docker compose exec backend python /app/scripts/migrate_sa02_stage2_meta_to_conv_logs.py

  # 特定テナントのみ（テスト用）
  docker compose exec backend python /app/scripts/migrate_sa02_stage2_meta_to_conv_logs.py --tenant-id 1

【冪等性】
  external_message_id（Meta mid）の UNIQUE 制約で保証。
  2回目以降は ON CONFLICT DO NOTHING で0行挿入。
  message_id がない古いレコードは合成キー meta_legacy:{id} を使用。

【ロールバック】
  docs/handoff/sa-02-stage2-migration/rollback.md を参照。

前提:
  - migration 20260604_090000_create_conversation_logs.sql 適用済み
  - migration 20260611_120000_add_conv_log_manual_columns.sql 適用済み
  - DATABASE_URL が postgresql:// または postgresql+asyncpg:// 形式
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

# channel_type 変換マッピング（meta_messages.platform → conversation_logs.channel_type）
PLATFORM_MAP: dict[str, str] = {
    "messenger": "meta_messenger",
    "instagram": "instagram",
    "discord": "discord",
    "whatsapp": "whatsapp",
    "telegram": "telegram",
    "email": "email",
}

# 1テナントあたりの INSERT バッチサイズ
BATCH_SIZE = 500


async def migrate_tenant(
    engine,
    tenant_id: int,
    tenant_code: str,
    dry_run: bool,
) -> dict[str, int]:
    """1テナントの meta_messages → conversation_logs 移行を実行。

    Returns:
        {"total": N, "inserted": N, "skipped": N, "errors": N}
    """
    schema = f"tenant_{tenant_id:03d}"
    stats = {"total": 0, "inserted": 0, "skipped": 0, "errors": 0}

    # テーブル存在確認
    async with engine.connect() as conn:
        exists = await conn.execute(text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = :s AND table_name = 'meta_messages'"
        ), {"s": schema})
        if not exists.fetchone():
            logger.info("  %s: meta_messages テーブルなし → スキップ", schema)
            return stats

        conv_exists = await conn.execute(text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = :s AND table_name = 'conversation_logs'"
        ), {"s": schema})
        if not conv_exists.fetchone():
            logger.warning("  %s: conversation_logs テーブルなし → スキップ", schema)
            return stats

        # 移行対象件数を取得
        r = await conn.execute(text(
            f"SELECT COUNT(*) FROM {schema}.meta_messages"
        ))
        stats["total"] = r.scalar()

    logger.info("  %s (tenant_code=%s): 対象 %d 件", schema, tenant_code, stats["total"])

    if stats["total"] == 0 or dry_run:
        if dry_run:
            logger.info("  [DRY-RUN] スキップ（実際の変更なし）")
        return stats

    # バッチ移行
    offset = 0
    while True:
        async with engine.begin() as conn:
            # set_tenant_context で RLS を通す
            await conn.execute(text(
                "SET LOCAL app.tenant_id = :tid"
            ), {"tid": tenant_id})

            rows = await conn.execute(text(f"""
                SELECT
                    mm.id,
                    mm.tenant_id,
                    mm.lead_id,
                    c.id AS company_id,
                    mm.platform,
                    mm.sender_id,
                    mm.sender_name,
                    mm.message_text,
                    mm.direction,
                    mm.raw_payload,
                    mm.created_at,
                    mm.message_id AS external_message_id,
                    mt.translated_text
                FROM {schema}.meta_messages mm
                LEFT JOIN {schema}.companies c ON c.lead_id = mm.lead_id
                LEFT JOIN {schema}.message_translations mt
                    ON mt.message_id = mm.message_id
                    AND mt.target_language = 'ja'
                ORDER BY mm.id
                LIMIT :limit OFFSET :offset
            """), {"limit": BATCH_SIZE, "offset": offset})

            batch = rows.fetchall()
            if not batch:
                break

            for row in batch:
                # 外部メッセージID: message_id があればそれ、なければ合成キー
                ext_id = row.external_message_id
                if not ext_id:
                    ext_id = f"meta_legacy:{row.id}"

                channel_type = PLATFORM_MAP.get(
                    (row.platform or "messenger").lower(),
                    row.platform or "meta_messenger"
                )

                try:
                    result = await conn.execute(text(f"""
                        INSERT INTO {schema}.conversation_logs (
                            tenant_id, lead_id, contact_id, company_id, deal_id,
                            channel_type, channel_identity, direction, sender,
                            content_text, original_language, external_message_id,
                            raw_payload, status, translated_text, analysis,
                            occurred_at, created_at,
                            is_manual, recorded_by_user_id, deleted_at
                        ) VALUES (
                            :tenant_id, :lead_id, NULL, :company_id, NULL,
                            :channel_type, :channel_identity, :direction, :sender,
                            :content_text, NULL, :external_message_id,
                            :raw_payload, 'sent', :translated_text, NULL,
                            :occurred_at, :created_at,
                            false, NULL, NULL
                        )
                        ON CONFLICT (external_message_id) DO NOTHING
                    """), {
                        "tenant_id": row.tenant_id,
                        "lead_id": row.lead_id,
                        "company_id": row.company_id,
                        "channel_type": channel_type,
                        "channel_identity": row.sender_id,
                        "direction": row.direction,
                        "sender": row.sender_name,
                        "content_text": row.message_text,
                        "external_message_id": ext_id,
                        "raw_payload": row.raw_payload,
                        "translated_text": row.translated_text,
                        "occurred_at": row.created_at,
                        "created_at": row.created_at,
                    })
                    if result.rowcount > 0:
                        stats["inserted"] += 1
                    else:
                        stats["skipped"] += 1
                except Exception as e:
                    logger.error("    行 id=%d 移行エラー: %s", row.id, e)
                    stats["errors"] += 1

        offset += BATCH_SIZE

    logger.info(
        "  %s: 挿入=%d / スキップ(重複)=%d / エラー=%d",
        schema, stats["inserted"], stats["skipped"], stats["errors"]
    )
    return stats


async def main(dry_run: bool, target_tenant_id: int | None) -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]

    engine = create_async_engine(url, echo=False)

    if dry_run:
        logger.info("=== [DRY-RUN] SA-02 段階2: meta_messages → conversation_logs ===")
    else:
        logger.info("=== SA-02 段階2: meta_messages → conversation_logs 移行開始 ===")

    try:
        async with engine.connect() as conn:
            q = "SELECT id, tenant_code FROM public.tenants WHERE is_active = true ORDER BY id"
            if target_tenant_id:
                q += f" AND id = {target_tenant_id}"
            r = await conn.execute(text(q))
            tenants = [(row.id, row.tenant_code) for row in r]

        logger.info("対象テナント: %d", len(tenants))

        total_stats = {"total": 0, "inserted": 0, "skipped": 0, "errors": 0}
        for tid, tc in tenants:
            stats = await migrate_tenant(engine, tid, tc, dry_run)
            for k in total_stats:
                total_stats[k] += stats[k]

        logger.info("=== 完了 ===")
        logger.info("  合計 meta_messages: %d", total_stats["total"])
        if not dry_run:
            logger.info("  挿入: %d", total_stats["inserted"])
            logger.info("  スキップ(重複): %d", total_stats["skipped"])
            logger.info("  エラー: %d", total_stats["errors"])
            if total_stats["errors"] > 0:
                logger.error("⚠️  エラーがあります。ロールバック手順を確認してください。")
                sys.exit(1)
        else:
            logger.info("  [DRY-RUN] 実際の変更は行われていません。")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SA-02 段階2: meta_messages → conv_logs 移行")
    parser.add_argument("--dry-run", action="store_true", help="件数確認のみ（DBを変更しない）")
    parser.add_argument("--tenant-id", type=int, help="特定テナントのみ移行（テスト用）")
    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run, target_tenant_id=args.tenant_id))
