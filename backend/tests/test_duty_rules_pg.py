"""関税の額の決まりの読み書きを本物の PostgreSQL で確かめる（invoice-create-portfolio 便B・K18）。

- 送料の会社の大文字・空白の違いは同じ会社として重なりになる。空は NULL で、NULL どうしも重なりになる。
- 直すときに自分の行とは重ならない。ほかの行と重なれば重なりになる。使わない決まりは重なりを調べない。
- 国の表に無い国は断る。無い決まりは見つからない。消すと中身の行も消える。
- 試験の中で入れた行は最後に戻す。ゲートは CI が設定する RLS_ADMIN_DATABASE_URL（前例 test_tenant_duty_rules_pg.py）。
"""
from __future__ import annotations

import datetime
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.schemas.duty_rules import DutyRuleIn
from app.services import duty_rules as svc
from tests.rls_bootstrap import (
    bootstrap_public_countries,
    bootstrap_tenant_schema,
    public_bootstrap_lock,
    tenant_schema_lock,
)

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

# 試験・移行のどこにも無い 964 を使う（962 は便Aの関税の表、963 は発行元の表の試験が使用）
_TENANT_ID = 964
_SCHEMA = f"tenant_{_TENANT_ID:03d}"


def _body(**overrides) -> DutyRuleIn:
    data = {
        "destination_country_code": "US",
        "carrier": "fedex",
        "label": "US DDP FedEx",
        "effective_from": "2026-01-01",
        "effective_to": None,
        "source_url": "https://www.fedex.com/en-us/billing/duty-tax.html",
        "components": [
            {"label": "Duty", "base": "subtotal", "rate_pct": "15"},
            {"label": "DDP fee", "base": "subtotal_shipping", "rate_pct": "2.5",
             "min_amount": "10", "max_amount": "100", "amount_currency": "USD"},
        ],
    }
    data.update(overrides)
    return DutyRuleIn.model_validate(data)


async def _expect_overlap(db: AsyncSession, coro) -> list[int]:
    sp = await db.begin_nested()
    with pytest.raises(svc.DutyRuleOverlap) as exc_info:
        await coro
    await sp.rollback()
    return exc_info.value.rule_ids


async def _check_service(db: AsyncSession) -> None:
    tid = _TENANT_ID
    first = await svc.create_duty_rule(db, tid, _body(carrier=" FedEx "))
    assert first["carrier"] == "fedex"
    assert first["destination_country_code"] == "US"
    assert [c["sort_order"] for c in first["components"]] == [0, 1]
    assert first["components"][1]["min_amount"] == "10.00"
    assert first["components"][1]["amount_currency"] == "USD"

    # 大文字・空白の違いは同じ会社（K18）
    assert await _expect_overlap(db, svc.create_duty_rule(db, tid, _body(carrier="FEDEX "))) == [first["id"]]

    # 直す: 自分の行とは重ならない（200 相当）。中身の行は置き換わる
    before, after = await svc.update_duty_rule(
        db, tid, first["id"],
        _body(effective_to="2026-12-31", components=[{"label": "Duty", "base": "subtotal", "rate_pct": "12"}]),
    )
    assert before["effective_to"] is None
    assert after["effective_to"] == datetime.date(2026, 12, 31)
    assert [c["rate_pct"] for c in after["components"]] == ["12.0000"]

    # 期間が重ならなければ足せる
    later = await svc.create_duty_rule(
        db, tid, _body(effective_from="2027-01-01", effective_to="2027-12-31", label="US DDP FedEx 2027"),
    )
    # 2026-06-01 から終わりの無い決まりは first とも later とも重なる
    assert await _expect_overlap(db, svc.create_duty_rule(db, tid, _body(effective_from="2026-06-01"))) == [
        first["id"], later["id"],
    ]
    # 直す: ほかの行と重なれば重なり（409 相当）
    assert await _expect_overlap(
        db, svc.update_duty_rule(db, tid, later["id"], _body(effective_from="2026-06-01", effective_to="2027-12-31")),
    ) == [first["id"]]

    # 空の送料の会社は NULL。NULL どうしも重なり（K18）。fedex の行とは別
    any_carrier = await svc.create_duty_rule(db, tid, _body(carrier="   ", label="US DDP any"))
    assert any_carrier["carrier"] is None
    assert await _expect_overlap(db, svc.create_duty_rule(db, tid, _body(carrier=None))) == [any_carrier["id"]]

    # 使わない決まりは重なりを調べない
    inactive = await svc.create_duty_rule(db, tid, _body(is_active=False, label="draft"))
    assert inactive["is_active"] is False

    # 国の表に無い国は断る
    sp = await db.begin_nested()
    with pytest.raises(svc.DutyCountryInvalid):
        await svc.create_duty_rule(db, tid, _body(destination_country_code="ZZ"))
    await sp.rollback()

    # 一覧は国・送料の会社（NULL が先）・始まりの日の順
    rows = await svc.list_duty_rules(db, tid)
    # fedex の 2026-01-01 始まりは first と inactive の2件で、id の小さい first が先
    assert [r["id"] for r in rows] == [any_carrier["id"], first["id"], inactive["id"], later["id"]]

    # 消す: 中身の行も消える。無い決まりは見つからない
    removed = await svc.delete_duty_rule(db, tid, later["id"])
    assert removed["id"] == later["id"]
    left = (
        await db.execute(
            text(f"SELECT count(*) FROM {_SCHEMA}.tenant_duty_rule_components WHERE rule_id = :id"),
            {"id": later["id"]},
        )
    ).scalar_one()
    assert left == 0
    with pytest.raises(svc.DutyRuleNotFound):
        await svc.get_duty_rule(db, tid, later["id"])
    with pytest.raises(svc.DutyRuleNotFound):
        await svc.delete_duty_rule(db, tid, later["id"])


@pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_duty_rule_service_on_postgres():
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    try:
        await bootstrap_public_countries(admin_engine)
        async with tenant_schema_lock(admin_engine, _TENANT_ID):
            try:
                assert await bootstrap_tenant_schema(admin_engine, _TENANT_ID) == _SCHEMA
                async with AsyncSession(admin_engine, expire_on_commit=False) as db:
                    try:
                        await _check_service(db)
                    finally:
                        await db.rollback()
            finally:
                async with public_bootstrap_lock(admin_engine):
                    async with admin_engine.begin() as conn:
                        await conn.execute(text(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE"))
    finally:
        await admin_engine.dispose()
