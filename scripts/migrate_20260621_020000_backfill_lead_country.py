#!/usr/bin/env python3
"""lead.country を ISO alpha-2 に backfill する。

実施内容:
  - 全アクティブ tenant スキーマの leads.country を走査
  - parse_country_code() で ISO 3166-1 alpha-2 に正規化
  - 解決不能値は NULL にし、元値の件数を JSON レポートに残す

危険変更:
  - 既存データを書き換えるため、PO の明示 GO 前提で運用する

実行方法:
  docker compose exec backend python /app/scripts/migrate_20260621_020000_backfill_lead_country.py
"""

from __future__ import annotations

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

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.services.country_codes import parse_country_code

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPORT_PATH = Path(os.getenv("COUNTRY_BACKFILL_REPORT_PATH", "/tmp/lead_country_backfill_report.json"))


async def backfill_schema(conn, schema: str) -> dict[str, int | dict[str, int]]:
    """1 tenant スキーマの leads.country を正規化する。"""
    counts: dict[str, int | dict[str, int]] = {
        "scanned": 0,
        "normalized": 0,
        "nulled": 0,
        "unchanged": 0,
        "unresolved": {},
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

    column_check = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = 'leads' AND column_name = 'country'"
        ),
        {"schema": schema},
    )
    if column_check.scalar_one_or_none() is None:
        logger.info("%s: leads.country column not found, skipped", schema)
        return counts

    rows = (
        await conn.execute(
            text(f"SELECT id, country FROM {schema}.leads WHERE country IS NOT NULL")
        )
    ).mappings().all()

    unresolved: Counter[str] = Counter()
    for row in rows:
        counts["scanned"] = int(counts["scanned"]) + 1
        raw = row["country"]
        parsed = parse_country_code(raw)
        if parsed == raw:
            counts["unchanged"] = int(counts["unchanged"]) + 1
            continue
        if parsed is None:
            unresolved[str(raw).strip() or "<empty>"] += 1
            counts["nulled"] = int(counts["nulled"]) + 1
        else:
            counts["normalized"] = int(counts["normalized"]) + 1
        await conn.execute(
            text(f"UPDATE {schema}.leads SET country = :country WHERE id = :id"),
            {"country": parsed, "id": row["id"]},
        )

    counts["unresolved"] = dict(unresolved)
    return counts


async def main() -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    engine = create_async_engine(url, echo=False)

    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "tenants": [],
        "summary": {
            "scanned": 0,
            "normalized": 0,
            "nulled": 0,
            "unchanged": 0,
        },
        "report_path": str(REPORT_PATH),
    }

    try:
        logger.info("=== lead.country backfill 開始 ===")
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
            counts = {"scanned": 0, "normalized": 0, "nulled": 0, "unchanged": 0, "unresolved": {}}
            try:
                async with engine.begin() as conn:
                    counts = await backfill_schema(conn, schema)
                report["tenants"].append({
                    "tenant_id": tid,
                    "tenant_code": tenant_code,
                    "schema": schema,
                    **counts,
                })
                for key in ("scanned", "normalized", "nulled", "unchanged"):
                    report["summary"][key] += int(counts[key])  # type: ignore[index]
                unresolved = counts.get("unresolved", {})
                unresolved_text = ", ".join(f"{k}={v}" for k, v in unresolved.items()) if unresolved else "none"
                logger.info(
                    "%s (tenant_code=%s): scanned=%s normalized=%s nulled=%s unchanged=%s unresolved=%s",
                    schema,
                    tenant_code,
                    counts["scanned"],
                    counts["normalized"],
                    counts["nulled"],
                    counts["unchanged"],
                    unresolved_text,
                )
            except Exception as exc:
                logger.error("%s: FAILED — %s", schema, exc)
                raise

        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("backfill report written to %s", REPORT_PATH)
        logger.info("=== lead.country backfill 完了 ===")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
