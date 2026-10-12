"""design.md PR-D の PG 統合テスト。実 PostgreSQL 必須（TEST_PG_URL 未設定なら skip）。

- add_exclude_keyword（tcg_product_master_svc）: 成功・重複・商品なし・空ワード
- tcg_shadow_review_svc の各クエリが実 DB に対して例外なく実行できること（SQL構文の検証）
"""
from __future__ import annotations

import os
import uuid

import pytest

TEST_PG_URL = os.getenv("TEST_PG_URL")

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not TEST_PG_URL,
        reason="実 PostgreSQL 環境が必要 (TEST_PG_URL 未設定)。",
    ),
]


@pytest.fixture
async def engine():
    from sqlalchemy.ext.asyncio import create_async_engine
    eng = create_async_engine(TEST_PG_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest.fixture
async def test_product(engine):
    """使い捨ての products 行を1件作り、テスト後に削除する。"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession

    code = f"TESTPRD{uuid.uuid4().hex[:8]}"
    async with AsyncSession(engine) as db:
        work_row = (
            await db.execute(text("SELECT id FROM public.type_master WHERE is_active = TRUE LIMIT 1"))
        ).fetchone()
        if work_row is None:
            pytest.skip("public.type_master に有効な行がありません")
        work_id = work_row[0]
        row = (
            await db.execute(
                text(
                    """
                    INSERT INTO public.products (product_code, name, category_class, is_active, work_id)
                    VALUES (:code, :name, 'Box', TRUE, :work_id)
                    RETURNING id
                    """
                ),
                {"code": code, "name": f"テスト商品{code}", "work_id": work_id},
            )
        ).fetchone()
        pid = row[0]
        await db.commit()
    yield pid
    async with AsyncSession(engine) as db:
        await db.execute(text("DELETE FROM public.product_exclude_keywords WHERE product_id = :pid"), {"pid": pid})
        await db.execute(text("DELETE FROM public.products WHERE id = :pid"), {"pid": pid})
        await db.commit()


async def test_add_exclude_keyword_ok_then_duplicate(engine, test_product):
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.tcg_product_master_svc import add_exclude_keyword

    async with AsyncSession(engine) as db:
        result = await add_exclude_keyword(db, product_id=test_product, new_keyword="シュリ無")
    assert result == {"ok": True}

    async with AsyncSession(engine) as db:
        dup = await add_exclude_keyword(db, product_id=test_product, new_keyword="シュリ無")
    assert dup == {"ok": False, "code": "KEYWORD_ALREADY_EXISTS"}


async def test_add_exclude_keyword_product_not_found(engine):
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.tcg_product_master_svc import add_exclude_keyword

    async with AsyncSession(engine) as db:
        with pytest.raises(ValueError, match="EXCLUDE_KEYWORD_PRODUCT_NOT_FOUND"):
            await add_exclude_keyword(db, product_id=-1, new_keyword="x")


async def test_add_exclude_keyword_empty(engine, test_product):
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.tcg_product_master_svc import add_exclude_keyword

    async with AsyncSession(engine) as db:
        with pytest.raises(ValueError, match="EXCLUDE_KEYWORD_EMPTY"):
            await add_exclude_keyword(db, product_id=test_product, new_keyword="   ")


async def test_fetch_shadow_results_query_executes(engine):
    """extraction_shadow_results が0件でも SQL 構文エラーなく空配列を返す。"""
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.tcg_shadow_review_svc import fetch_shadow_results

    async with AsyncSession(engine) as db:
        result = await fetch_shadow_results(db, offset=0, limit=5)
    assert "items" in result
    assert "total" in result


async def test_fetch_bottlenecks_query_executes(engine):
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.tcg_shadow_review_svc import fetch_bottlenecks

    async with AsyncSession(engine) as db:
        result = await fetch_bottlenecks(db, days=7)
    assert result["days"] == 7
    assert "by_supplier" in result
    assert "by_item" in result
