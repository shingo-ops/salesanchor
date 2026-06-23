"""GET /inventory/aggregated エンドポイントのテスト。

テスト種別:
  1. 純 Python 論理テスト (_pivot / _build_aggregation_offers) -- DB 不要
  2. PostgreSQL E2E テスト -- TEST_PG_URL 必須
     - 配線E2E: in_stock seed -> エンドポイントが best-pick 行を返す
     - 境界: supplier_name / reason / raw が応答に含まれない
     - タブ: ?category=pokemon で pokemon のみ絞り込み
"""
from __future__ import annotations

import os
import uuid

import pytest

TEST_PG_URL = os.getenv("TEST_PG_URL")

# ---------------------------------------------------------------------------
# 1. 純 Python 論理テスト (DB 不要)
# ---------------------------------------------------------------------------


def test_pivot_empty_results():
    from app.services.inventory_aggregated_service import _pivot

    tabs, rows = _pivot([], [])
    assert tabs == []
    assert rows == []


def test_pivot_single_result():
    from app.services.inventory_aggregated_service import _ProductMeta, _pivot
    from app.services.inventory_aggregation import AggregationResult

    product = _ProductMeta(product_id=1, name="テスト商品A", tcg_type="pokemon")
    result = AggregationResult(
        row_id=None,
        product_id=1,
        supplier_id=1,
        supplier_name="Supplier X",  # これは応答に出てはいけない
        series="テスト商品A",
        condition="Sealed box",
        quantity=10,
        unit_price=1000,
        status="In Stock",
        reason_category="lowest_price",
        reason="最安値のため採用",  # これも応答に出てはいけない
    )

    tabs, rows = _pivot([result], [product])

    assert tabs == ["pokemon"]
    assert len(rows) == 1
    row = rows[0]
    assert row["series"] == "テスト商品A"
    assert row["tcg_type"] == "pokemon"
    assert "Sealed box" in row["cells"]
    assert row["cells"]["Sealed box"] == {"price": 1000, "quantity": 10}
    # 応答形式に supplier_name / reason は含まれない
    assert "supplier_name" not in row
    assert "reason" not in row


def test_build_aggregation_offers_maps_series_from_product_name():
    from app.services.inventory_aggregated_service import (
        _ProductMeta,
        _build_aggregation_offers,
    )
    from app.services.inventory_search import OfferSummary

    product = _ProductMeta(product_id=42, name="ポケカ商品", tcg_type="pokemon")
    offer = OfferSummary(
        supplier_id=1,
        supplier_name="SupA",
        condition="Case",
        quantity=5,
        unit_price=10000,
        status="in_stock",
    )
    rows = _build_aggregation_offers([product], {42: [offer]})

    assert len(rows) == 1
    assert rows[0]["series"] == "ポケカ商品"
    assert rows[0]["condition"] == "Case"
    assert rows[0]["quantity"] == 5
    assert rows[0]["unit_price"] == 10000


# ---------------------------------------------------------------------------
# 2. PostgreSQL E2E テスト
# ---------------------------------------------------------------------------

pytestmark_pg = pytest.mark.skipif(
    not TEST_PG_URL,
    reason="実 PostgreSQL 環境が必要 (TEST_PG_URL 未設定)。",
)


def _split_sql(sql: str) -> list[str]:
    """$$ ブロックを保持しつつ ; 区切りで分割。"""
    statements: list[str] = []
    buf: list[str] = []
    in_dollar = False
    dollar_tag = ""
    i = 0
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


@pytest.fixture(scope="module")
async def pg_engine():
    from sqlalchemy.ext.asyncio import create_async_engine

    eng = create_async_engine(TEST_PG_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest.fixture
async def seed_aggregated_dataset(pg_engine):
    """配線E2E / タブテスト用 seed。"""
    from pathlib import Path

    from sqlalchemy import text

    tag = uuid.uuid4().hex[:8]

    # aggregation_rules を適用
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "20260620_010000_create_inventory_aggregation_rules.sql"
    )
    if migration_path.exists():
        sql = migration_path.read_text("utf-8")
        async with pg_engine.begin() as conn:
            for stmt in _split_sql(sql):
                stmt = stmt.strip()
                if stmt:
                    await conn.execute(text(stmt))

    async with pg_engine.begin() as conn:
        # suppliers
        sup_id = (
            await conn.execute(
                text(
                    "INSERT INTO public.suppliers (name, supplier_type, default_language) "
                    "VALUES (:n, 'corporate', 'ja') RETURNING id"
                ),
                {"n": f"agg_sup_{tag}"},
            )
        ).scalar_one()

        sup2_id = (
            await conn.execute(
                text(
                    "INSERT INTO public.suppliers (name, supplier_type, default_language) "
                    "VALUES (:n, 'corporate', 'ja') RETURNING id"
                ),
                {"n": f"agg_sup2_{tag}"},
            )
        ).scalar_one()

        # products: 2 pokemon + 1 yugioh
        poke1_id = (
            await conn.execute(
                text(
                    "INSERT INTO public.products (name, tcg_type, is_archived) "
                    "VALUES (:n, 'pokemon', false) RETURNING id"
                ),
                {"n": f"ポケカA_{tag}"},
            )
        ).scalar_one()
        poke2_id = (
            await conn.execute(
                text(
                    "INSERT INTO public.products (name, tcg_type, is_archived) "
                    "VALUES (:n, 'pokemon', false) RETURNING id"
                ),
                {"n": f"ポケカB_{tag}"},
            )
        ).scalar_one()
        yugi_id = (
            await conn.execute(
                text(
                    "INSERT INTO public.products (name, tcg_type, is_archived) "
                    "VALUES (:n, 'yugioh', false) RETURNING id"
                ),
                {"n": f"遊戯王C_{tag}"},
            )
        ).scalar_one()

        # poke1: Sealed box - 2 suppliers for best-pick test
        # sup: 1000 yen x 2 (cheapest but low stock)
        # sup2: 1100 yen x 50 (within tolerance -> stock_priority picks this)
        await conn.execute(
            text(
                "INSERT INTO public.inventory (supplier_id, product_id, condition, quantity, unit_price, status) "
                "VALUES (:s1, :p, 'Sealed box', 2, 1000, 'in_stock'), "
                "       (:s2, :p, 'Sealed box', 50, 1100, 'in_stock')"
            ),
            {"s1": sup_id, "s2": sup2_id, "p": poke1_id},
        )

        # poke2: Case
        await conn.execute(
            text(
                "INSERT INTO public.inventory (supplier_id, product_id, condition, quantity, unit_price, status) "
                "VALUES (:s, :p, 'Case', 5, 9000, 'in_stock')"
            ),
            {"s": sup_id, "p": poke2_id},
        )

        # yugioh: Sealed box
        await conn.execute(
            text(
                "INSERT INTO public.inventory (supplier_id, product_id, condition, quantity, unit_price, status) "
                "VALUES (:s, :p, 'Sealed box', 10, 500, 'in_stock')"
            ),
            {"s": sup_id, "p": yugi_id},
        )

    yield {
        "tag": tag,
        "sup_id": sup_id,
        "sup2_id": sup2_id,
        "poke1_id": poke1_id,
        "poke2_id": poke2_id,
        "yugi_id": yugi_id,
        "poke1_name": f"ポケカA_{tag}",
        "poke2_name": f"ポケカB_{tag}",
        "yugi_name": f"遊戯王C_{tag}",
    }

    # Cleanup
    async with pg_engine.begin() as conn:
        for pid in [poke1_id, poke2_id, yugi_id]:
            await conn.execute(
                text("DELETE FROM public.inventory WHERE product_id = :p"), {"p": pid}
            )
            await conn.execute(
                text("DELETE FROM public.products WHERE id = :p"), {"p": pid}
            )
        for sid in [sup_id, sup2_id]:
            await conn.execute(
                text("DELETE FROM public.suppliers WHERE id = :s"), {"s": sid}
            )


@pytest.mark.asyncio
@pytestmark_pg
async def test_aggregated_endpoint_returns_best_pick_rows(
    seed_aggregated_dataset, pg_engine
):
    """配線E2E: エンドポイントが集計後の best-pick 行を返す。"""
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.auth.dependencies import (
        get_current_tenant,
        get_current_user,
        load_user_permissions,
    )
    from app.database import get_db
    from app.main import app
    from app.models import User

    data = seed_aggregated_dataset

    engine = create_async_engine(TEST_PG_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session() as session:
            yield session

    mock_user = User(id=1, tenant_id=1, email="test@test.com")
    mock_perms = frozenset({"products.view"})

    app.dependency_overrides = {}
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant] = lambda: 1
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[load_user_permissions] = lambda: mock_perms

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/inventory/aggregated")
            assert resp.status_code == 200, resp.text
            data_resp = resp.json()

            assert "tabs" in data_resp
            assert "rows" in data_resp

            # tabs must contain pokemon and yugioh
            tabs = data_resp["tabs"]
            assert "pokemon" in tabs
            assert "yugioh" in tabs

            # Find poke1 row
            poke1_rows = [
                r for r in data_resp["rows"] if r["series"] == data["poke1_name"]
            ]
            assert poke1_rows, f"Expected row for {data['poke1_name']}"
            poke1_row = poke1_rows[0]

            assert "Sealed box" in poke1_row["cells"]
            cell = poke1_row["cells"]["Sealed box"]
            # Either best-pick (stock_priority: sup2 with 50 qty at 1100) or cheapest
            assert cell["price"] is not None
            assert cell["quantity"] is not None

            # Boundary: no supplier_name, no reason in response
            assert "supplier_name" not in poke1_row
            assert "reason" not in poke1_row
            assert "reason_category" not in poke1_row
            assert "raw" not in poke1_row

    finally:
        app.dependency_overrides = {}
        await engine.dispose()


@pytest.mark.asyncio
@pytestmark_pg
async def test_aggregated_endpoint_category_filter(
    seed_aggregated_dataset, pg_engine
):
    """タブ: ?category=pokemon で pokemon のみ絞り込み。"""
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.auth.dependencies import (
        get_current_tenant,
        get_current_user,
        load_user_permissions,
    )
    from app.database import get_db
    from app.main import app
    from app.models import User

    data = seed_aggregated_dataset

    engine = create_async_engine(TEST_PG_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session() as session:
            yield session

    mock_user = User(id=1, tenant_id=1, email="test@test.com")
    mock_perms = frozenset({"products.view"})

    app.dependency_overrides = {}
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant] = lambda: 1
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[load_user_permissions] = lambda: mock_perms

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/inventory/aggregated?category=pokemon")
            assert resp.status_code == 200, resp.text
            data_resp = resp.json()

            rows = data_resp["rows"]
            assert all(r["tcg_type"] == "pokemon" for r in rows), (
                f"category=pokemon でも pokemon 以外の行がある: {rows}"
            )

            yugi_rows = [r for r in rows if r["series"] == data["yugi_name"]]
            assert not yugi_rows, "pokemon フィルタで yugioh 商品が返ってきた"

    finally:
        app.dependency_overrides = {}
        await engine.dispose()


@pytest.mark.asyncio
@pytestmark_pg
async def test_aggregated_boundary_no_internal_fields(
    seed_aggregated_dataset, pg_engine
):
    """境界: supplier_name / reason / raw が JSON 応答の全階層に存在しない。"""
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.auth.dependencies import (
        get_current_tenant,
        get_current_user,
        load_user_permissions,
    )
    from app.database import get_db
    from app.main import app
    from app.models import User

    engine = create_async_engine(TEST_PG_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session() as session:
            yield session

    mock_user = User(id=1, tenant_id=1, email="test@test.com")
    mock_perms = frozenset({"products.view"})

    app.dependency_overrides = {}
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant] = lambda: 1
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[load_user_permissions] = lambda: mock_perms

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/inventory/aggregated")
            assert resp.status_code == 200

            raw_json = resp.text
            forbidden_keys = ["supplier_name", "reason", "reason_category", "raw"]
            for key in forbidden_keys:
                assert f'"{key}"' not in raw_json, (
                    f'境界違反: "{key}" が JSON 応答に含まれています'
                )

    finally:
        app.dependency_overrides = {}
        await engine.dispose()
