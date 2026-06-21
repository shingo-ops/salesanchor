#!/usr/bin/env python3
"""lead.channel_type を canonical channel_masters 値へ backfill する。

実施内容:
  - 全アクティブ tenant スキーマの channel_masters を確認し、whatsapp を補完
  - leads.channel_type を canonical 値へ正規化
    - whatsapp_personal / whatsapp_business → whatsapp
    - messenger / instagram / discord / phone / in_person は維持
    - それ以外の珍しい値は NULL 化（元値はレポートに保持）
  - dry-run / apply を切り替え可能（既定は dry-run）

危険変更:
  - 既存データを書き換えるため、PO の明示 GO 前提で運用する

実行方法:
  dry-run:
    python /app/scripts/migrate_20260621_030000_backfill_lead_channel_type.py
  apply:
    python /app/scripts/migrate_20260621_030000_backfill_lead_channel_type.py --apply
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.services.channel_masters import (  # noqa: E402
    ACTIVE_CHANNEL_PLATFORMS,
    DEFAULT_CHANNEL_MASTERS,
    normalize_channel_type_value,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPORT_PATH = Path(os.getenv("CHANNEL_TYPE_BACKFILL_REPORT_PATH", "/tmp/lead_channel_type_backfill_report.json"))


async def backfill_schema(conn, schema: str, tenant_id: int, *, dry_run: bool = True) -> dict[str, object]:
    """1 tenant スキーマの leads.channel_type と channel_masters を整える。"""
    counts: dict[str, object] = {
        "scanned": 0,
        "normalized": 0,
        "nulled": 0,
        "unchanged": 0,
        "channel_master_missing": 0,
        "rare_values": {},
        "changes": [],
    }

    table_check = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = :schema AND table_name = 'leads'"
        ),
        {"schema": schema},
    )
    if table_check.scalar_one_or_none() is None:
        logger.info("%s: leads table not found, skipped", schema)
        return counts

    channel_master_check = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = :schema AND table_name = 'channel_masters'"
        ),
        {"schema": schema},
    )
    if channel_master_check.scalar_one_or_none() is not None:
        existing = (
            await conn.execute(
                text(f"SELECT platform FROM {schema}.channel_masters")
            )
        ).scalars().all()
        missing = [row for row in DEFAULT_CHANNEL_MASTERS if row[0] not in set(existing)]
        counts["channel_master_missing"] = len(missing)
        if missing and not dry_run:
            for platform, display_name, connection_type in missing:
                await conn.execute(
                    text(
                        f"""
                        INSERT INTO {schema}.channel_masters
                            (tenant_id, platform, display_name, connection_type)
                        VALUES
                            (:tenant_id, :platform, :display_name, :connection_type)
                        ON CONFLICT (platform) DO NOTHING
                        """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "platform": platform,
                        "display_name": display_name,
                        "connection_type": connection_type,
                    },
                )
    else:
        logger.info("%s: channel_masters table not found, seed skipped", schema)

    channel_type_column_check = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = 'leads' AND column_name = 'channel_type'"
        ),
        {"schema": schema},
    )
    if channel_type_column_check.scalar_one_or_none() is None:
        logger.info("%s: leads.channel_type column not found, skipped", schema)
        return counts

    rows = (
        await conn.execute(
            text(f"SELECT id, channel_type FROM {schema}.leads WHERE channel_type IS NOT NULL")
        )
    ).mappings().all()

    rare_values: Counter[str] = Counter()
    changes: list[dict[str, object]] = []
    for row in rows:
        counts["scanned"] = int(counts["scanned"]) + 1
        raw = row["channel_type"]
        normalized = normalize_channel_type_value(raw)
        if normalized in ACTIVE_CHANNEL_PLATFORMS:
            if normalized == raw:
                counts["unchanged"] = int(counts["unchanged"]) + 1
                continue
            counts["normalized"] = int(counts["normalized"]) + 1
            changes.append({"lead_id": row["id"], "before": raw, "after": normalized})
            if not dry_run:
                await conn.execute(
                    text(f"UPDATE {schema}.leads SET channel_type = :channel_type WHERE id = :id"),
                    {"channel_type": normalized, "id": row["id"]},
                )
            continue

        rare_key = str(raw).strip() or "<empty>"
        rare_values[rare_key] += 1
        counts["nulled"] = int(counts["nulled"]) + 1
        changes.append({"lead_id": row["id"], "before": raw, "after": None})
        if not dry_run:
            await conn.execute(
                text(f"UPDATE {schema}.leads SET channel_type = NULL WHERE id = :id"),
                {"id": row["id"]},
            )

    counts["rare_values"] = dict(rare_values)
    counts["changes"] = changes
    return counts


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="実データを更新する")
    args = parser.parse_args()

    url = os.getenv("DATABASE_URL")
    if not url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    engine = create_async_engine(url, echo=False)

    dry_run = not args.apply
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "tenants": [],
        "summary": {
            "scanned": 0,
            "normalized": 0,
            "nulled": 0,
            "unchanged": 0,
            "channel_master_missing": 0,
        },
        "report_path": str(REPORT_PATH),
    }

    try:
        logger.info("=== lead.channel_type backfill 開始 (dry_run=%s) ===", dry_run)
        async with engine.connect() as conn:
            rows = await conn.execute(
                text(
                    "SELECT id, tenant_code FROM public.tenants "
                    "WHERE is_active = true ORDER BY id"
                )
            )
            tenants = [(row.id, row.tenant_code) for row in rows]
        logger.info("対象テナント: %d", len(tenants))

        for tid, tenant_code in tenants:
            schema = f"tenant_{tid:03d}"
            counts: dict[str, object] = {
                "scanned": 0,
                "normalized": 0,
                "nulled": 0,
                "unchanged": 0,
                "channel_master_missing": 0,
                "rare_values": {},
                "changes": [],
            }
            try:
                async with engine.begin() as conn:
                    counts = await backfill_schema(conn, schema, tid, dry_run=dry_run)
                report["tenants"].append({
                    "tenant_id": tid,
                    "tenant_code": tenant_code,
                    "schema": schema,
                    **counts,
                })
                for key in ("scanned", "normalized", "nulled", "unchanged", "channel_master_missing"):
                    report["summary"][key] += int(counts[key])  # type: ignore[index]
                logger.info(
                    "%s (tenant_code=%s): scanned=%s normalized=%s nulled=%s unchanged=%s missing_master=%s",
                    schema,
                    tenant_code,
                    counts["scanned"],
                    counts["normalized"],
                    counts["nulled"],
                    counts["unchanged"],
                    counts["channel_master_missing"],
                )
            except Exception as exc:
                logger.error("%s: FAILED — %s", schema, exc)
                raise

        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("backfill report written to %s", REPORT_PATH)
        logger.info("=== lead.channel_type backfill 完了 ===")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
