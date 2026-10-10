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

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.services.country_codes import parse_country_code  # noqa: E402

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
    # NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07):
    # 値の書き込みを外した。run_py が呼ぶ入口を、何もしない形にした。
    # 元の内容は git history で参照可能。backfill_schema は試験が import するため、関数として残す。
    print("ADR-1007 neutralized: migrate_20260621_020000_backfill_lead_country.py no longer writes values")


if __name__ == "__main__":
    asyncio.run(main())
