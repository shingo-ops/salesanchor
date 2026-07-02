"""
GET /analytics/priority-prospects — PG/RLS 実走証明テスト。

rls_bootstrap で本番 migration 順のテナントスキーマを構築し、以下を実証する:
  - ease_pct = 該当軸 smoothed_rate 平均（欠軸除外）
  - null 金額は scope 内中央値で補完 + "monthly_forecast_unset" フラグ
  - rank_score = ease_pct × monthly_forecast（降順ソート）
  - low_sample フラグ（n < SHRINK_K=10 の軸に付与）
  - テナント分離（RLS ポリシーで他テナントリードは不可視）
  - scope=mine（assigned_to = current_user.id のみ）
  - converted_deal_id 基準 ＝ #2452 の集計を流用（Track B 不含）

実行条件:
  RLS_ADMIN_DATABASE_URL (or TEST_PG_URL) / RLS_TEST_DATABASE_URL が設定済みの場合のみ。
"""

from __future__ import annotations

import os
from contextlib import suppress

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import get_current_tenant, get_current_user
from app.database import get_db
from app.models import User
from app.routers import analytics as analytics_router
from tests.rls_bootstrap import (
    bootstrap_tenant_schema,
    tenant_schema_lock,
)

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
APP_PG_URL = os.getenv("RLS_TEST_DATABASE_URL")

_TENANT_ID = 7
_USER_ID = 777
_OTHER_USER_ID = 888
_SCHEMA = f"tenant_{_TENANT_ID:03d}"


def _build_user(user_id: int, tenant_id: int) -> User:
    u = User()
    u.id = user_id
    u.tenant_id = tenant_id
    u.username = "pp-rls-tester"
    u.email = "pp-rls-tester@example.com"
    u.role = "admin"
    u.is_active = True
    return u


@pytest.mark.skipif(
    not ADMIN_PG_URL or not APP_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL / RLS_TEST_DATABASE_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_priority_prospects_pg_rls_all_requirements():
    """
    本番 migration 順テナントスキーマで priority-prospects EP の全要件を実走検証。

    挿入データ:
      Lead-A: instagram/JP/physical_store/Hot/24h以内  uid=777  converted(1001) forecast=100
      Lead-B: instagram/JP/physical_store/Hot/24h以内  uid=777  NOT converted    forecast=300
      Lead-C: cold_call/US/NULL/Cold/3日超              uid=777  NOT converted    forecast=NULL
      Lead-D: messenger/CA/online/Warm/3日以内          uid=888  converted(2001)  forecast=9999  ← 別ユーザー

    期待する rank_score 順:
      Lead-B (ease=50% × 300=15000) > Lead-C (ease≈45.5% × 200≈9090) > Lead-A (ease=50% × 100=5000)
    """
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False)
    app_session_factory = sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)

    current_user = _build_user(_USER_ID, _TENANT_ID)

    async def _override_get_db():
        async with app_session_factory() as session:
            async with session.begin():
                await session.execute(text(f"SET search_path = {_SCHEMA}, public"))
                await session.execute(
                    text("SELECT set_config('app.tenant_id', :tid, true)"),
                    {"tid": str(_TENANT_ID)},
                )
                await session.execute(text("SELECT set_config('app.is_operator', '', true)"))
                yield session

    async def _override_get_current_user():
        return current_user

    async def _override_get_current_tenant():
        return _TENANT_ID

    test_app = FastAPI()
    test_app.include_router(analytics_router.router, prefix="/api/v1")
    test_app.dependency_overrides[get_db] = _override_get_db
    test_app.dependency_overrides[get_current_user] = _override_get_current_user
    test_app.dependency_overrides[get_current_tenant] = _override_get_current_tenant

    inserted_ids: list[int] = []
    origin_lead_ids: list[int] = []  # deals の出自 lead（クリーンアップ用・unpack 対象外）

    try:
        async with tenant_schema_lock(admin_engine, _TENANT_ID):
            # 1. 本番 migration 順でテナントスキーマを構築
            await bootstrap_tenant_schema(admin_engine, _TENANT_ID)

            # 2. leads.converted_deal_id FK 参照先となる deals を先に挿入
            #    （fk_leads_converted_deal: leads.converted_deal_id → deals.id）
            #    ben1a: deals.lead_id NOT NULL のため出自 lead を先に作成する
            async with admin_engine.begin() as conn:
                origin_result = await conn.execute(
                    text(f"""
                        INSERT INTO {_SCHEMA}.leads (tenant_id, customer_name)
                        VALUES (:tid, 'PP-DealOrigin-1001'),
                               (:tid, 'PP-DealOrigin-2001')
                        RETURNING id
                    """),
                    {"tid": _TENANT_ID},
                )
                origin_lead_ids.extend(int(r) for r in origin_result.scalars().all())

                await conn.execute(
                    text(f"""
                        INSERT INTO {_SCHEMA}.deals (id, tenant_id, title, lead_id)
                        VALUES (1001, :tid, 'PP-Deal-1001', :lid1),
                               (2001, :tid, 'PP-Deal-2001', :lid2)
                        ON CONFLICT (id) DO NOTHING
                    """),
                    {"tid": _TENANT_ID, "lid1": origin_lead_ids[0], "lid2": origin_lead_ids[1]},
                )

            # 3. リードを挿入（admin 権限で直接 INSERT）
            async with admin_engine.begin() as conn:
                result = await conn.execute(
                    text(f"""
                        INSERT INTO {_SCHEMA}.leads (
                            tenant_id, customer_name,
                            channel_type, country, sales_form, temperature, response_speed,
                            assigned_to, converted_deal_id, monthly_forecast
                        ) VALUES
                            (:tid, 'PP-Lead-A', 'instagram', 'JP', 'physical_store', 'Hot', '24h以内', :uid,       1001, 100),
                            (:tid, 'PP-Lead-B', 'instagram', 'JP', 'physical_store', 'Hot', '24h以内', :uid,       NULL, 300),
                            (:tid, 'PP-Lead-C', 'cold_call',  'US', NULL,             'Cold', '3日超',   :uid,      NULL, NULL),
                            (:tid, 'PP-Lead-D', 'messenger',  'CA', 'online',          'Warm', '3日以内', :other_uid, 2001, 9999)
                        RETURNING id
                    """),
                    {"tid": _TENANT_ID, "uid": _USER_ID, "other_uid": _OTHER_USER_ID},
                )
                inserted_ids.extend(int(r) for r in result.scalars().all())

            lead_a, lead_b, lead_c, lead_d = inserted_ids

            # 4. エンドポイントを呼び出し
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                res = await ac.get("/api/v1/analytics/priority-prospects?scope=mine")

            assert res.status_code == 200, res.text
            data = res.json()

            # ── 基本構造 ───────────────────────────────────────────────────────────
            assert data["scope"] == "mine"
            assert all(item["type"] == "priority_prospect" for item in data["items"])

            # ── scope=mine: uid=777 の 3 件のみ（Lead-D は除外）─────────────────
            returned_ids = {item["lead_id"] for item in data["items"]}
            assert len(data["items"]) == 3
            assert returned_ids == {lead_a, lead_b, lead_c}
            assert lead_d not in returned_ids, "他ユーザー Lead-D が scope=mine に漏れてはいけない"

            # ── rank_score 降順 ───────────────────────────────────────────────────
            ordered = data["items"]
            assert ordered == sorted(ordered, key=lambda x: (-x["rank_score"], x["lead_id"]))
            assert ordered[0]["lead_id"] == lead_b, (
                f"最高 rank は Lead-B(forecast=300) のはず。実際: {ordered[0]['lead_id']}"
            )

            # ── ease_pct = 該当軸 smoothed_rate 平均（欠軸除外）───────────────────
            for item in ordered:
                axes = item["axis_breakdown"]
                assert len(axes) > 0, f"lead_id={item['lead_id']}: axis_breakdown が空"
                expected_ease = sum(b["smoothed_rate"] for b in axes) / len(axes)
                assert item["ease_pct"] == pytest.approx(expected_ease * 100, abs=1e-4), (
                    f"lead_id={item['lead_id']}: ease_pct 計算ずれ"
                )

            # ── rank_score = ease_pct × monthly_forecast ─────────────────────────
            for item in ordered:
                assert item["rank_score"] == pytest.approx(
                    item["ease_pct"] * item["monthly_forecast"], abs=1e-2
                ), f"lead_id={item['lead_id']}: rank_score 計算ずれ"

            # ── Lead-C: null forecast → 中央値補完 + フラグ ───────────────────────
            item_c = next(x for x in ordered if x["lead_id"] == lead_c)
            # 中央値: [100, 300] → 200
            assert item_c["monthly_forecast"] == pytest.approx(200.0, abs=1e-4), (
                "Lead-C の monthly_forecast が中央値 200 に補完されていない"
            )
            assert "monthly_forecast_unset" in item_c["low_sample_flags"], (
                "Lead-C に monthly_forecast_unset フラグがない"
            )

            # ── Lead-C: sales_form=NULL → 欠軸（4 軸のみ） ───────────────────────
            assert len(item_c["axis_breakdown"]) == 4, (
                f"Lead-C は sales_form 欠軸なので 4 軸のはず: {item_c['axis_breakdown']}"
            )

            # ── low_sample フラグ（n < 10 の軸は全件で必ず存在） ─────────────────
            for item in ordered:
                assert any(f.endswith(":low_sample") for f in item["low_sample_flags"]), (
                    f"lead_id={item['lead_id']}: low_sample フラグがない (n < 10 の軸があるはず)"
                )

            # ── RLS テナント分離: tenant_007 セッションから他テナントリードは 0 件 ──
            foreign_schema = "tenant_998_pp_rls"
            foreign_inserted: list[int] = []
            try:
                async with admin_engine.begin() as conn:
                    await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {foreign_schema}"))
                    await conn.execute(text(f"""
                        CREATE TABLE IF NOT EXISTS {foreign_schema}.leads (
                            id SERIAL PRIMARY KEY,
                            tenant_id INTEGER NOT NULL DEFAULT 998,
                            customer_name VARCHAR(255) NOT NULL,
                            channel_type VARCHAR(30),
                            country VARCHAR(100),
                            sales_form VARCHAR(50),
                            temperature VARCHAR(20),
                            response_speed VARCHAR(20),
                            assigned_to INTEGER,
                            converted_deal_id INTEGER,
                            monthly_forecast NUMERIC(15, 2)
                        )
                    """))
                    await conn.execute(
                        text(f"ALTER TABLE {foreign_schema}.leads ENABLE ROW LEVEL SECURITY")
                    )
                    await conn.execute(
                        text(f"ALTER TABLE {foreign_schema}.leads FORCE ROW LEVEL SECURITY")
                    )
                    await conn.execute(
                        text(
                            f"DROP POLICY IF EXISTS tenant_isolation_leads ON {foreign_schema}.leads"
                        )
                    )
                    await conn.execute(text(f"""
                        CREATE POLICY tenant_isolation_leads ON {foreign_schema}.leads
                            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER)
                    """))
                    await conn.execute(
                        text(f"GRANT USAGE ON SCHEMA {foreign_schema} TO salesanchor_app")
                    )
                    await conn.execute(text(
                        f"GRANT SELECT, INSERT, UPDATE, DELETE "
                        f"ON ALL TABLES IN SCHEMA {foreign_schema} TO salesanchor_app"
                    ))
                    fr = await conn.execute(
                        text(f"""
                            INSERT INTO {foreign_schema}.leads (
                                tenant_id, customer_name,
                                channel_type, country, sales_form, temperature, response_speed,
                                assigned_to, converted_deal_id, monthly_forecast
                            ) VALUES (
                                998, 'Foreign-Lead',
                                'instagram', 'JP', 'physical_store', 'Hot', '24h以内',
                                :uid, NULL, 99999
                            )
                            RETURNING id
                        """),
                        {"uid": _USER_ID},
                    )
                    foreign_inserted.extend(int(r) for r in fr.scalars().all())

                # tenant_007 セッションで foreign_schema.leads を参照 → RLS により 0 件
                async with app_session_factory() as session:
                    async with session.begin():
                        await session.execute(
                            text(f"SET LOCAL search_path = {_SCHEMA}, public")
                        )
                        await session.execute(
                            text("SELECT set_config('app.tenant_id', :tid, true)"),
                            {"tid": str(_TENANT_ID)},
                        )
                        await session.execute(
                            text("SELECT set_config('app.is_operator', '', true)")
                        )
                        cnt = (
                            await session.execute(
                                text(f"SELECT COUNT(*) FROM {foreign_schema}.leads")
                            )
                        ).scalar_one()
                        assert cnt == 0, (
                            f"テナント 998 のリードが tenant_007 セッションから見えた (cnt={cnt}): "
                            "RLS テナント分離が機能していない"
                        )
            finally:
                with suppress(Exception):
                    async with admin_engine.begin() as conn:
                        for fid in foreign_inserted:
                            await conn.execute(
                                text(f"DELETE FROM {foreign_schema}.leads WHERE id = :id"),
                                {"id": fid},
                            )
                        await conn.execute(
                            text(f"DROP SCHEMA IF EXISTS {foreign_schema} CASCADE")
                        )

    finally:
        test_app.dependency_overrides.clear()
        with suppress(Exception):
            async with admin_engine.begin() as conn:
                for iid in inserted_ids + origin_lead_ids:
                    await conn.execute(
                        text(f"DELETE FROM {_SCHEMA}.leads WHERE id = :id"),
                        {"id": iid},
                    )
        await admin_engine.dispose()
        await app_engine.dispose()
