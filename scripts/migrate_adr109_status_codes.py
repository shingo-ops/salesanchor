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
    # Non-standard value found in tenant_006 (2026-08-31 deploy block).
    # ADR-109 defines 7 immutable codes; 'disqualified' is absent.
    # goals.py excludes both 'out_of_scope' and 'disqualified' in the same NOT IN filter
    # (commit 98ba6555, 2026-07-26), so mapping to 'out_of_scope' is semantically correct
    # and has zero impact on aggregate counts.
    # See: docs/handoff/adr109-disqualified-cleanup/record.md
    ("disqualified", "out_of_scope"),
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
    # NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07):
    # 値の書き込みを外した。run_py が呼ぶ入口を、何もしない形にした。
    # 元の内容は git history で参照可能。
    print("ADR-1007 neutralized: migrate_adr109_status_codes.py no longer writes values")


if __name__ == "__main__":
    asyncio.run(main())
