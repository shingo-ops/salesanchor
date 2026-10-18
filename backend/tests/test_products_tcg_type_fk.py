from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from tests.rls_bootstrap import ensure_product_packagings, public_bootstrap_lock, seed_type_master

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
APP_PG_URL = os.getenv("RLS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not ADMIN_PG_URL or not APP_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL / TEST_PG_URL 未設定)。",
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATIONS_DIR = _REPO_ROOT / "migrations"
_PG_BOOTSTRAP_MIGRATIONS = [
    "056_add_suppliers_type_and_promote_public.sql",
    "062_create_inventory_movements_and_budget.sql",
    "082_extend_products_box_attributes.sql",       # products.category 追加（020000 の backfill に必須）
    "085_create_tcg_type_master.sql",
    "086_seed_additional_tcg_types.sql",
    "20260602_000000_add_products_central_columns.sql",
    "20260602_020000_add_products_tcg_type.sql",
    "20260602_030000_add_products_unit.sql",
    "20260602_170000_add_products_master_label_columns.sql",
    "20260603_000000_add_products_product_kind.sql",
    "20260603_040000_add_products_set_type.sql",        # products.set_type 追加
    "20260605_000000_add_products_display_order.sql",   # products.display_order 追加
    "20260616_000000_fix_tcg_type_dedup.sql",
    "20260623_060000_add_products_tcg_type_fk.sql",
    "20260921_060000_create_product_kinds.sql",
    "20260921_070000_rename_tcg_type_master_to_type_master.sql",
    "20261016_190000_create_product_blank_confirmations.sql",  # ADR-1020 便4a: 共用の行の PATCH が印の表を読む
]


def _split_sql_preserving_do_blocks(sql: str) -> list[str]:
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    in_dollar = False
    dollar_tag = ""
    while i < len(sql):
        if sql[i] == "$":
            j = i + 1
            while j < len(sql) and (sql[j].isalnum() or sql[j] == "_"):
                j += 1
            if j < len(sql) and sql[j] == "$":
                tag = sql[i : j + 1]
                if not in_dollar:
                    in_dollar = True
                    dollar_tag = tag
                    buf.append(tag)
                    i = j + 1
                    continue
                if tag == dollar_tag:
                    in_dollar = False
                    dollar_tag = ""
                    buf.append(tag)
                    i = j + 1
                    continue
        if sql[i] == ";" and not in_dollar:
            statements.append("".join(buf))
            buf = []
        else:
            buf.append(sql[i])
        i += 1
    if buf:
        statements.append("".join(buf))
    return statements


async def _apply_migration(admin_engine, filename: str) -> None:
    sql = (_MIGRATIONS_DIR / filename).read_text("utf-8")
    async with admin_engine.begin() as conn:
        for stmt in _split_sql_preserving_do_blocks(sql):
            stmt = stmt.strip()
            if stmt:
                await conn.exec_driver_sql(stmt)


async def _bootstrap_public_products(admin_engine) -> None:
    async with public_bootstrap_lock(admin_engine):
        for filename in _PG_BOOTSTRAP_MIGRATIONS:
            await _apply_migration(admin_engine, filename)
        # type_master の行は migration ではなく試験側で入れる（ADR-1007 段2）
        async with admin_engine.begin() as conn:
            await seed_type_master(conn)

        async with admin_engine.connect() as conn:
            fk_exists = await conn.scalar(
                text("""
                    SELECT 1
                    FROM pg_constraint c
                    JOIN pg_class rel ON rel.oid = c.conrelid
                    JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                    WHERE nsp.nspname = 'public'
                      AND rel.relname = 'products'
                      AND c.conname = 'fk_products_tcg_type'
                """)
            )
        assert fk_exists == 1, "FK migration が public.products に適用されていません"
    # 荷姿の表（ADR-1028 便3）。public_bootstrap_lock の外で、一度だけ確定させる
    await ensure_product_packagings(admin_engine)


@pytest.mark.asyncio
async def test_products_tcg_type_fk_enforcement():
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    created_ids: list[int] = []

    try:
        await _bootstrap_public_products(admin_engine)

        async with admin_engine.begin() as conn:
            null_row = await conn.execute(
                text(
                    "INSERT INTO public.products (name, stock_quantity, tcg_type) "
                    "VALUES (:name, :stock_quantity, NULL) RETURNING id, tcg_type"
                ),
                {"name": "PG FK Enforcement NULL", "stock_quantity": 0},
            )
            inserted_null = null_row.mappings().first()
            assert inserted_null is not None
            assert inserted_null["tcg_type"] is None
            created_ids.append(inserted_null["id"])

        async with admin_engine.begin() as conn:
            with pytest.raises(IntegrityError):
                await conn.execute(
                    text(
                        "INSERT INTO public.products (name, stock_quantity, tcg_type) "
                        "VALUES (:name, :stock_quantity, :tcg_type)"
                    ),
                    {
                        "name": "PG FK Enforcement NG",
                        "stock_quantity": 0,
                        "tcg_type": "unknown_type",
                    },
                )

        async with admin_engine.begin() as conn:
            ok_row = await conn.execute(
                text(
                    "INSERT INTO public.products (name, stock_quantity, tcg_type) "
                    "VALUES (:name, :stock_quantity, :tcg_type) RETURNING id, tcg_type"
                ),
                {
                    "name": "PG FK Enforcement OK",
                    "stock_quantity": 0,
                    "tcg_type": "gundam",
                },
            )
            inserted = ok_row.mappings().first()
            assert inserted is not None
            assert inserted["tcg_type"] == "gundam"
            created_ids.append(inserted["id"])
    finally:
        async with admin_engine.begin() as conn:
            for product_id in created_ids:
                await conn.execute(
                    text("DELETE FROM public.products WHERE id = :id"),
                    {"id": product_id},
                )
        await admin_engine.dispose()
