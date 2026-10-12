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
from typing import Literal, Mapping

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# --- resolve_backfill_category をインライン化 ---
# app.services.calendar_category_utils は Docker コンテナ外の CI 環境では
# sys.path が合わないため、依存を除去して自己完結スクリプトにする。
CalendarCategory = Literal["personal", "meeting", "purchase", "shipping", "billing", "release", "holiday"]

_BACKFILL_RULES: tuple[tuple[CalendarCategory, tuple[re.Pattern[str], ...]], ...] = (
    ("billing", (re.compile(r"\b請求\b"), re.compile(r"\b入金\b"), re.compile(r"請求"), re.compile(r"入金"), re.compile(r"billing", re.I), re.compile(r"invoice", re.I), re.compile(r"payment", re.I))),
    ("shipping", (re.compile(r"発送"), re.compile(r"集荷"), re.compile(r"出荷"), re.compile(r"shipping", re.I), re.compile(r"delivery", re.I), re.compile(r"pickup", re.I))),
    ("purchase", (re.compile(r"仕入"), re.compile(r"入荷"), re.compile(r"発注"), re.compile(r"purchase", re.I), re.compile(r"procure", re.I), re.compile(r"buy", re.I))),
)

def resolve_backfill_category(row: Mapping[str, object | None]) -> CalendarCategory | None:
    current = row.get("category")
    if isinstance(current, str) and current:
        return None
    if row.get("calendar_type") == "personal":
        return "personal"
    if row.get("source") != "app":
        return None
    text_val = "\n".join(str(row.get(f) or "") for f in ("title", "description", "location"))
    for category, patterns in _BACKFILL_RULES:
        if any(p.search(text_val) for p in patterns):
            return category
    return None
# --- インライン化ここまで ---

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
    # NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07):
    # 値の書き込みを外した。run_py が呼ぶ入口を、何もしない形にした。
    # 元の内容は git history で参照可能。
    print("ADR-1007 neutralized: migrate_20260620_080000_calendar_category_backfill.py no longer writes values")


if __name__ == "__main__":
    asyncio.run(main())
