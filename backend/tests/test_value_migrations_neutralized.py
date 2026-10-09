"""値を書く migration の無効化（ADR-1007 決定2・PR-3a）の試験。

- 静的な試験（DB 不要）: 無効化した 18 本に、値を書く文が残っていない。
- PG の試験（RLS_ADMIN_DATABASE_URL か TEST_PG_URL があるとき）: migration を流しても、
  試験が変えた値が元に戻らない／消した行が再挿入されない。共有 DB の他の worker を乱さないよう、
  1 つの接続・1 つのトランザクションの中で確かめ、最後に必ず巻き戻す。
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"

# PR-3a で無効化した 18 本（step3_card.md の表。#4015 に依存する 4 本を含む）
NEUTRALIZED_FILES = [
    "20260620_010000_create_inventory_aggregation_rules.sql",
    "20260621_010000_create_countries_master.sql",
    "085_create_tcg_type_master.sql",
    "086_seed_additional_tcg_types.sql",
    "20260611_100000_create_channel_masters.sql",
    "20260611_010000_fix_owner_role_color.sql",
    "20260616_000000_fix_tcg_type_dedup.sql",
    "20260928_100000_delete_skip_condition_rules.sql",
    "20260924_040000_seed_knowledge_extraction_vocab.sql",
    "20260923_030000_promote_remaining_tcg_tables.sql",
    "20260927_120000_add_max_age_hours_setting.sql",
    "20260602_020000_add_products_tcg_type.sql",
    "20260603_000000_add_products_product_kind.sql",
    "20260604_020000_backfill_products_shipping_defaults.sql",
    "20260605_000000_add_products_display_order.sql",
    "20260916_130000_work_id_not_null.sql",
    "20260604_090000_create_link_templates.sql",
    "20260613_020000_funnel_close_reasons.sql",
]

_VALUE_WRITE_PATTERNS = [
    re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
    re.compile(r"\bUPDATE\s+[\w.%\"$]+\s+(?:AS\s+\w+\s+)?SET\b", re.IGNORECASE),
    re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
    re.compile(r"\bON\s+CONFLICT\b", re.IGNORECASE),
]


def _strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", " ", sql)


@pytest.mark.parametrize("filename", NEUTRALIZED_FILES)
def test_neutralized_migration_has_no_value_writes(filename):
    sql = (MIGRATIONS_DIR / filename).read_text("utf-8")

    assert "NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07)" in sql
    body = _strip_sql_comments(sql)
    for pattern in _VALUE_WRITE_PATTERNS:
        assert pattern.search(body) is None, f"{filename}: 値を書く文が残っている ({pattern.pattern})"


def test_channel_masters_selector_line_is_kept_byte_identical():
    # rls_bootstrap.py の正本のセレクタ（ちょうど 1 回）。変えると bootstrap_tenant_schema が落ちる
    sql = (MIGRATIONS_DIR / "20260611_100000_create_channel_masters.sql").read_text("utf-8")

    assert sql.count("\n        WHERE nspname ~ '^tenant_\\d+$'\n") == 1


async def _run_file_on_conn(conn, filename: str) -> None:
    from tests.rls_bootstrap import _apply_migration_on_conn

    await _apply_migration_on_conn(conn, filename)


@pytest.mark.skipif(not ADMIN_PG_URL, reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。")
@pytest.mark.asyncio
async def test_countries_migration_does_not_revert_values():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from tests.rls_bootstrap import bootstrap_public_countries

    engine = create_async_engine(ADMIN_PG_URL, echo=False)
    try:
        await bootstrap_public_countries(engine)
        async with engine.connect() as conn:
            trans = await conn.begin()
            try:
                await conn.exec_driver_sql("UPDATE public.countries SET dial_code = '+9999' WHERE code = 'JP'")
                await _run_file_on_conn(conn, "20260621_010000_create_countries_master.sql")
                dial_code = (
                    await conn.execute(text("SELECT dial_code FROM public.countries WHERE code = 'JP'"))
                ).scalar_one()
            finally:
                await trans.rollback()
        # 以前の migration は ON CONFLICT DO UPDATE で '+81' に戻していた
        assert dial_code == "+9999"
    finally:
        await engine.dispose()


@pytest.mark.skipif(not ADMIN_PG_URL, reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。")
@pytest.mark.asyncio
async def test_inventory_aggregation_rules_migration_does_not_revert_values():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from tests.rls_bootstrap import bootstrap_inventory_aggregation_rules

    engine = create_async_engine(ADMIN_PG_URL, echo=False)
    try:
        await bootstrap_inventory_aggregation_rules(engine)
        async with engine.connect() as conn:
            trans = await conn.begin()
            try:
                await conn.exec_driver_sql(
                    "UPDATE public.inventory_aggregation_rules SET price_tolerance = 1234 WHERE condition = 'Case'"
                )
                await _run_file_on_conn(conn, "20260620_010000_create_inventory_aggregation_rules.sql")
                tolerance = (
                    await conn.execute(
                        text("SELECT price_tolerance FROM public.inventory_aggregation_rules WHERE condition = 'Case'")
                    )
                ).scalar_one()
            finally:
                await trans.rollback()
        # 以前の migration は ON CONFLICT DO UPDATE で 1000 に戻していた
        assert tolerance == 1234
    finally:
        await engine.dispose()


@pytest.mark.skipif(not ADMIN_PG_URL, reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。")
@pytest.mark.asyncio
async def test_type_master_migrations_do_not_reinsert_deleted_rows():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from tests.rls_bootstrap import bootstrap_public_products

    engine = create_async_engine(ADMIN_PG_URL, echo=False)
    try:
        await bootstrap_public_products(engine)
        async with engine.connect() as conn:
            trans = await conn.begin()
            try:
                # 085 の seed 行（union_arena）と 086 の seed 行（xross_stars）を消してから、両方の migration を流す
                await conn.exec_driver_sql("DELETE FROM public.type_master WHERE code IN ('union_arena', 'xross_stars')")
                await _run_file_on_conn(conn, "085_create_tcg_type_master.sql")
                await _run_file_on_conn(conn, "086_seed_additional_tcg_types.sql")
                reinserted = (
                    await conn.execute(
                        text("SELECT count(*) FROM public.type_master WHERE code IN ('union_arena', 'xross_stars')")
                    )
                ).scalar_one()
                # 構造（表）は残っている
                table_exists = (
                    await conn.execute(text("SELECT to_regclass('public.type_master') IS NOT NULL"))
                ).scalar_one()
            finally:
                await trans.rollback()
        assert reinserted == 0
        assert table_exists is True
    finally:
        await engine.dispose()
