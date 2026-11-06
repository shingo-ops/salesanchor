# ruff: noqa: F811
"""シフト API（backend/app/routers/shifts.py）の日付・時刻の受け渡しを実 PostgreSQL で固定する試験（CI の使い捨て PostgreSQL 専用）。

本番の GET /api/v1/shifts?date_from&date_to が 500 だった（asyncpg が DATE 列の引数に str を受け付けない）。
SQLite の試験（test_shifts.py）は日付・時刻の列が TEXT なので見えない。ここでは shifts 表を
migrations/011_add_phase5_tenant_tables.sql の「シフト管理」の区間をそのまま読み込んで作る（表の定義を書き写さない）。

P1: 期間で読むと 200 相当の結果が返り、期間の外の行は入らない・応答の JSON の形
P2: 登録すると DATE・TIME の列に入り、応答は date・time の形
"""
from __future__ import annotations

import asyncio
import os
from datetime import date, time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.auth.dependencies import set_tenant_context
from app.routers import shifts as router
from tests.test_tcg_work_matching_integration import SCHEMA
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

pytestmark = pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") != "true", reason="Disposable CI PostgreSQL service required")

REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE5_PATH = REPO_ROOT / "migrations" / "011_add_phase5_tenant_tables.sql"
TENANT_ID = int(SCHEMA.rsplit("_", 1)[-1])
_SHIFTS_BANNER = "-- === シフト管理 ===\n"
_SHIFTS_END_BANNER = "-- === ERP連携ログ ===\n"


def _shifts_table_sql() -> str:
    text_all = PHASE5_PATH.read_text(encoding="utf-8")
    start = text_all.index(_SHIFTS_BANNER)
    end = text_all.index(_SHIFTS_END_BANNER, start)
    return text_all[start:end].replace("{schema}", SCHEMA).replace("{tenant_id}", str(TENANT_ID))


def _create_shifts(connection) -> None:
    with connection.cursor() as cur:
        cur.execute(_shifts_table_sql())
        cur.execute(
            f"INSERT INTO {SCHEMA}.shifts (tenant_id, user_id, shift_date, start_time, end_time) VALUES "
            f"({TENANT_ID}, 1, '2026-11-02', '09:00', '18:00'), ({TENANT_ID}, 1, '2026-12-01', '10:00', '19:00')"
        )


def _insert_public_user(connection, *, user_id: int, tenant_id: int) -> None:
    """担当者の会社照合（ensure_user_in_tenant）が読む public.users の本物の行を入れる。"""
    with connection.cursor() as cur:
        cur.execute(
            "INSERT INTO public.users (id, tenant_id) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
            (user_id, tenant_id),
        )


def _run(pg_fixture, call):
    async def _go():
        engine = create_async_engine(pg_fixture[2])
        try:
            async with AsyncSession(engine) as db:
                await set_tenant_context(db, TENANT_ID)
                return await call(db)
        finally:
            await engine.dispose()

    return asyncio.run(_go())


def test_p1_list_by_period_uses_date_parameters(pg):
    _create_shifts(pg[0])

    async def call(db):
        return await router.list_shifts(
            user_id=None, date_from=date(2026, 11, 1), date_to=date(2026, 11, 7),
            db=db, tenant_id=TENANT_ID, current_user=SimpleNamespace(id=1),
        )

    result = _run(pg, call)
    assert [r.shift_date for r in result] == [date(2026, 11, 2)]
    dumped = result[0].model_dump(mode="json")
    assert dumped["shift_date"] == "2026-11-02"
    assert dumped["start_time"] == "09:00"
    assert dumped["end_time"] == "18:00"
    assert dumped["created_at"] is not None


def test_p2_create_writes_date_and_time_columns(pg, monkeypatch):
    _create_shifts(pg[0])

    async def _no_audit(**_kwargs):
        return None

    monkeypatch.setattr(router, "record_audit_log", _no_audit)
    _insert_public_user(pg[0], user_id=2, tenant_id=TENANT_ID)
    data = router.ShiftCreate(user_id=2, shift_date="2026-11-03", start_time="09:00", end_time="18:00")

    async def call(db):
        return await router.create_shift(data=data, db=db, tenant_id=TENANT_ID, current_user=SimpleNamespace(id=1))

    created = _run(pg, call)
    assert created.shift_date == date(2026, 11, 3)
    assert created.start_time == time(9, 0)
    assert created.end_time == time(18, 0)


def test_p3_create_rejects_user_of_other_tenant(pg, monkeypatch):
    """他社の人（会社 999）の番号では 422。行は増えない（ADR-1008）。"""
    _create_shifts(pg[0])

    async def _no_audit(**_kwargs):
        return None

    monkeypatch.setattr(router, "record_audit_log", _no_audit)
    _insert_public_user(pg[0], user_id=3, tenant_id=999)
    data = router.ShiftCreate(user_id=3, shift_date="2026-11-04", start_time="09:00", end_time="18:00")

    async def call(db):
        return await router.create_shift(data=data, db=db, tenant_id=TENANT_ID, current_user=SimpleNamespace(id=1))

    with pytest.raises(HTTPException) as exc:
        _run(pg, call)
    assert exc.value.status_code == 422
    with pg[0].cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.shifts")
        assert cur.fetchone()[0] == 2
