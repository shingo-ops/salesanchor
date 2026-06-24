"""GET /inventory?sort=release_date&order=desc のソート順テスト。

検収1（KPI4）の根拠:
  - release_date 降順 (新しい→古い) で返る
  - release_date=NULL の行が末尾 (NULLS LAST)

実 PostgreSQL 必須 (SQLite に public.inventory / public.products が存在しないため)。
CI は RLS_ADMIN_DATABASE_URL で通過（test_inventory_aggregated.py と同方針）。
"""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import patch

import pytest
import pytest_asyncio

_PG_URL = os.getenv("TEST_PG_URL") or os.getenv("RLS_ADMIN_DATABASE_URL")

pytestmark_pg = pytest.mark.skipif(
    not _PG_URL,
    reason="実 PostgreSQL 環境が必要 (TEST_PG_URL / RLS_ADMIN_DATABASE_URL 未設定)。",
)


def _split_sql(sql: str) -> list[str]:
    """$$ ブロックを保持しつつ ; 区切りで分割（test_inventory_aggregated.py と同一）。"""
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


@pytest_asyncio.fixture
async def seed_release_date_dataset():
    """release_date ソートテスト用 seed。

    products: 3行
      - prod_new:  release_date='2026-03-01' (新しい)
      - prod_old:  release_date='2025-01-15' (古い)
      - prod_null: release_date=NULL

    inventory: 各 product に 1 行 (status='in_stock', expires_at=NULL)
    """
    from pathlib import Path

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    eng = create_async_engine(_PG_URL, echo=False)

    # ── テーブル bootstrap (IF NOT EXISTS → 冪等) ──────────────────────────
    async with eng.begin() as conn:
        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS public.suppliers (
                    id              BIGSERIAL PRIMARY KEY,
                    name            TEXT NOT NULL,
                    supplier_type   TEXT NOT NULL DEFAULT 'corporate',
                    default_language TEXT NOT NULL DEFAULT 'ja',
                    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
        )
        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS public.products (
                    id              BIGSERIAL PRIMARY KEY,
                    tenant_id       INTEGER,
                    product_code    VARCHAR(50),
                    name            VARCHAR(255) NOT NULL,
                    name_en         VARCHAR(255),
                    description     TEXT,
                    unit_price      NUMERIC(15, 2),
                    unit_price_usd  NUMERIC(15, 2),
                    unit_price_eur  NUMERIC(15, 2),
                    stock_quantity  INTEGER NOT NULL DEFAULT 0,
                    jan_code        VARCHAR(20),
                    card_number     VARCHAR(50),
                    expansion_code  VARCHAR(20),
                    rarity          VARCHAR(20),
                    language        VARCHAR(10),
                    image_url       VARCHAR(500),
                    tcg_type        TEXT,
                    is_archived     BOOLEAN NOT NULL DEFAULT FALSE,
                    archived_at     TIMESTAMPTZ,
                    supplier_default_id INTEGER,
                    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
        )
        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS public.inventory (
                    id          BIGSERIAL PRIMARY KEY,
                    supplier_id BIGINT NOT NULL REFERENCES public.suppliers(id),
                    product_id  BIGINT NOT NULL REFERENCES public.products(id),
                    condition   TEXT NOT NULL,
                    quantity    INTEGER NOT NULL DEFAULT 0,
                    unit_price  INTEGER NOT NULL DEFAULT 0,
                    status      TEXT NOT NULL DEFAULT 'in_stock',
                    notes_ja    TEXT,
                    notes_en    TEXT,
                    offered_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    expires_at  TIMESTAMPTZ,
                    source      TEXT NOT NULL DEFAULT 'manual',
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (supplier_id, product_id, condition)
                )
            """)
        )

    # ── 必要な migration (冪等) ────────────────────────────────────────────
    migrations_root = Path(__file__).resolve().parents[2] / "migrations"
    for mig_file in [
        "082_extend_products_box_attributes.sql",     # p.release_date
        "084_add_unit_to_inventory.sql",               # i.unit
        "20260622_020000_add_inventory_raw_condition.sql",  # i.raw_condition
        "20260623_010000_add_inventory_axes_columns.sql",   # i.seal/search_cond/grade/damage
    ]:
        migration_path = migrations_root / mig_file
        if migration_path.exists():
            sql = migration_path.read_text("utf-8")
            async with eng.begin() as conn:
                for stmt in _split_sql(sql):
                    stmt = stmt.strip()
                    if stmt:
                        try:
                            await conn.execute(text(stmt))
                        except Exception:
                            pass  # 既存 INDEX 等の重複は無視

    tag = uuid.uuid4().hex[:8]

    async with eng.begin() as conn:
        sup_id = (
            await conn.execute(
                text("INSERT INTO public.suppliers (name) VALUES (:n) RETURNING id"),
                {"n": f"rdsort_sup_{tag}"},
            )
        ).scalar_one()

        # products: 新しい / 古い / NULL の 3種
        prod_new_id = (
            await conn.execute(
                text(
                    "INSERT INTO public.products (name, tcg_type, is_archived, release_date)"
                    " VALUES (:n, 'pokemon_booster_box', false, :rd) RETURNING id"
                ),
                {"n": f"prod_new_{tag}", "rd": date(2026, 3, 1)},
            )
        ).scalar_one()

        prod_old_id = (
            await conn.execute(
                text(
                    "INSERT INTO public.products (name, tcg_type, is_archived, release_date)"
                    " VALUES (:n, 'pokemon_booster_box', false, :rd) RETURNING id"
                ),
                {"n": f"prod_old_{tag}", "rd": date(2025, 1, 15)},
            )
        ).scalar_one()

        prod_null_id = (
            await conn.execute(
                text(
                    "INSERT INTO public.products (name, tcg_type, is_archived)"
                    " VALUES (:n, 'pokemon_booster_box', false) RETURNING id"
                ),
                {"n": f"prod_null_{tag}"},
            )
        ).scalar_one()

        # inventory: 各 product に 1 行 (status='in_stock', expires_at=NULL)
        for pid in [prod_new_id, prod_old_id, prod_null_id]:
            await conn.execute(
                text(
                    "INSERT INTO public.inventory"
                    " (supplier_id, product_id, condition, raw_condition, quantity, unit_price, status)"
                    " VALUES (:s, :p, 'Sealed box', 'Sealed box', 1, 1000, 'in_stock')"
                ),
                {"s": sup_id, "p": pid},
            )

    yield {
        "engine": eng,
        "tag": tag,
        "sup_id": sup_id,
        "prod_new_id": prod_new_id,
        "prod_old_id": prod_old_id,
        "prod_null_id": prod_null_id,
    }

    # ── Cleanup ────────────────────────────────────────────────────────────
    async with eng.begin() as conn:
        for pid in [prod_new_id, prod_old_id, prod_null_id]:
            await conn.execute(
                text("DELETE FROM public.inventory WHERE product_id = :p"), {"p": pid}
            )
            await conn.execute(
                text("DELETE FROM public.products WHERE id = :p"), {"p": pid}
            )
        await conn.execute(
            text("DELETE FROM public.suppliers WHERE id = :s"), {"s": sup_id}
        )
    await eng.dispose()


def _make_inventory_client(pg_engine):
    """GET /inventory 用の ASGI クライアント。

    - get_db: PG エンジンに差し替え
    - get_current_user / get_current_tenant: モック
    - load_user_permissions: products.view を返すモック
    """
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    from app.auth.dependencies import get_current_tenant, get_current_user
    from app.database import get_db
    from app.main import app
    from app.models import User

    async_session = sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session() as session:
            yield session

    mock_user = User(id=1, tenant_id=1, email="ci-test@test.com")

    async def mock_load_perms(*args, **kwargs):
        return frozenset({"products.view"})

    @asynccontextmanager
    async def _ctx():
        app.dependency_overrides = {}
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_tenant] = lambda: 1
        app.dependency_overrides[get_current_user] = lambda: mock_user
        with patch(
            "app.auth.dependencies.load_user_permissions",
            mock_load_perms,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                yield client
        app.dependency_overrides = {}

    return _ctx()


@pytestmark_pg
async def test_inventory_sort_by_release_date_desc(seed_release_date_dataset):
    """GET /inventory?sort=release_date&order=desc が release_date 降順・NULL末尾で返る。

    検収1 (KPI4):
      - release_date='2026-03-01' の行が先頭
      - release_date='2025-01-15' の行が2番目
      - release_date=NULL の行が末尾 (NULLS LAST)
    """
    data = seed_release_date_dataset
    tag = data["tag"]

    async with _make_inventory_client(data["engine"]) as client:
        resp = await client.get(
            "/api/v1/inventory",
            params={
                "sort": "release_date",
                "order": "desc",
                "per_page": 50,
                "q": tag,  # tag で絞り込み（他テストデータと混在しない）
            },
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()["items"]

    # 今回の seed 分だけを product_id で抽出
    seed_ids = {data["prod_new_id"], data["prod_old_id"], data["prod_null_id"]}
    seed_items = [it for it in items if it["product_id"] in seed_ids]

    assert len(seed_items) == 3, (
        f"seed 3行のうち {len(seed_items)} 行しか返らなかった。items={items}"
    )

    # release_date 降順・NULL末尾を確認
    dates = [it["release_date"] for it in seed_items]

    # 1位: 2026-03-01
    assert dates[0] == "2026-03-01", f"1位が {dates[0]} (expected 2026-03-01)"
    # 2位: 2025-01-15
    assert dates[1] == "2025-01-15", f"2位が {dates[1]} (expected 2025-01-15)"
    # 3位: NULL (NULLS LAST)
    assert dates[2] is None, f"3位が {dates[2]} (expected None)"
