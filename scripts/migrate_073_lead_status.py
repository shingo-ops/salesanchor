#!/usr/bin/env python3
"""Migration 073: LeadStatus 整理 — 受信箱タブを商談進捗ベースに変更。

実施内容:
  全テナントスキーマの leads.status を新しい値に移行する。
    - '案件化' → '商談中'
    - 'AI対応中' / 'コンタクト中' / '提案中' → '新規'
    - '保留' → '追客（短期）'

冪等:
  WHERE status = '...' 条件付きの UPDATE なので何度実行しても安全。

実行方法（VPS 側、docker compose exec 経由）:
  docker compose exec -e TENANT_CODE=highlife-jpn backend \\
      python /app/scripts/migrate_073_lead_status.py
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


async def main() -> None:
    # NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07):
    # 値の書き込みを外した。run_py が呼ぶ入口を、何もしない形にした。
    # 元の内容は git history で参照可能。
    print("ADR-1007 neutralized: migrate_073_lead_status.py no longer writes values")


if __name__ == "__main__":
    asyncio.run(main())
