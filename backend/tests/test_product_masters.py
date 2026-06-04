"""各種マスタ (public.product_attribute_masters) ルーター/スキーマ 単体テスト。

スキーマ検証は DB 不要で常時実行。CRUD round-trip は実 PostgreSQL 必須。
"""
from __future__ import annotations

import os

import pytest

from app.schemas.product_masters import (
    VALID_ATTRIBUTES,
    ProductAttributeMasterCreate,
    ProductAttributeMasterUpdate,
)


# ── スキーマ検証（DB 不要） ──────────────────────────────────────────────
def test_create_schema_accepts_valid_attribute():
    m = ProductAttributeMasterCreate(attribute="rarity", label_ja="SR")
    assert m.attribute == "rarity"
    assert m.label_ja == "SR"
    assert m.sort_order == 100
    assert m.is_active is True


def test_create_schema_rejects_unknown_attribute():
    with pytest.raises(ValueError):
        ProductAttributeMasterCreate(attribute="bogus", label_ja="X")


def test_valid_attributes_cover_eight_masters():
    # TCGシリーズは tcg_type_master 側で管理するため 8 区分。
    assert VALID_ATTRIBUTES == {
        "product_kind",
        "set_type",
        "rarity",
        "language",
        "unit",
        "hs_code",
        "item",
        "material",
    }


def test_update_schema_partial():
    u = ProductAttributeMasterUpdate(label_en="Super Rare")
    data = u.model_dump(exclude_unset=True)
    assert data == {"label_en": "Super Rare"}


# ── CRUD round-trip（実 PostgreSQL 必須） ────────────────────────────────
TEST_PG_URL = os.getenv("TEST_PG_URL")

pg = pytest.mark.skipif(
    not TEST_PG_URL,
    reason="実 PostgreSQL 環境が必要 (TEST_PG_URL 未設定)。",
)


@pytest.fixture
async def engine():
    from sqlalchemy.ext.asyncio import create_async_engine
    eng = create_async_engine(TEST_PG_URL, echo=False)
    yield eng
    await eng.dispose()


@pg
@pytest.mark.asyncio
async def test_product_attribute_masters_crud_round_trip(engine):
    from sqlalchemy import text
    async with engine.connect() as conn:
        exists = (await conn.execute(text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='product_attribute_masters'"
        ))).scalar_one_or_none()
    if not exists:
        pytest.skip("public.product_attribute_masters 未作成 (migration 20260604_170000 が必要)")

    label = "TEST_RARITY_ZZZ"
    async with engine.begin() as conn:
        await conn.execute(text(
            "DELETE FROM public.product_attribute_masters "
            "WHERE attribute='rarity' AND label_ja = :l"
        ), {"l": label})

    async with engine.begin() as conn:
        new_id = (await conn.execute(text("""
            INSERT INTO public.product_attribute_masters
                (attribute, label_ja, label_en, sort_order)
            VALUES ('rarity', :l, 'Test', 999)
            RETURNING id
        """), {"l": label})).scalar_one()

        await conn.execute(text(
            "UPDATE public.product_attribute_masters SET label_en='Updated' WHERE id = :id"
        ), {"id": new_id})
        got = (await conn.execute(text(
            "SELECT label_en FROM public.product_attribute_masters WHERE id = :id"
        ), {"id": new_id})).scalar_one()
        assert got == "Updated"

        await conn.execute(text(
            "DELETE FROM public.product_attribute_masters WHERE id = :id"
        ), {"id": new_id})
