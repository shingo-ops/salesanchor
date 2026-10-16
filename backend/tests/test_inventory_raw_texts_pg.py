# ruff: noqa: F811
"""在庫表スライドの原文タブ API（GET /inventory/raw-texts）の配信行判定を実 PostgreSQL で固定する試験（CI の使い捨て PostgreSQL 専用）。
原文・値はすべて架空。list_inventory_raw_texts の SQL（配信行 CTE + raw_ok）を実 PG で実行する。

B2: 配信行に入る ID だけ返る・入らない ID（48 時間より古い投稿）は返らない・入らない ID だけなら 404
B3: 返すキーは4つだけ
"""
from __future__ import annotations

import asyncio
import os

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.routers import inventory_offers as router
from tests.test_inventory_distribution_rows_pg import _add_job, _add_row, _item_id_of  # noqa: F401  fixture
from tests.test_inventory_distribution_rows_pg import ids as ids
from tests.test_line_analysis_v102_pg import v102 as v102  # noqa: F401  fixture
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

pytestmark = pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") != "true", reason="Disposable CI PostgreSQL service required")


def _call(pg_fixture, monkeypatch, item_ids: list[str]):
    async def _settings(_db):
        return {"max_age_hours": "48", "include_flag_single": "false"}

    monkeypatch.setattr(router, "load_distribution_settings", _settings)

    async def _run():
        engine = create_async_engine(pg_fixture[2])
        try:
            async with AsyncSession(engine) as db:
                return await router.list_inventory_raw_texts(extraction_item_ids=item_ids, db=db)
        finally:
            await engine.dispose()

    return asyncio.run(_run())


def _seed(pg_fixture, ids):
    fresh = [_add_row(pg_fixture, _add_job(pg_fixture, 1), ids.p1, ids.box, basis="R2:甲"),
             _add_row(pg_fixture, _add_job(pg_fixture, 2), ids.p1, ids.box, note="X", basis="R2:甲")]
    stale = _add_row(pg_fixture, _add_job(pg_fixture, 100), ids.p2, ids.case, basis="R2:甲", canonical="Case", unit="Case")
    return [_item_id_of(pg_fixture, r) for r in fresh], _item_id_of(pg_fixture, stale)


def test_b2_only_distribution_row_ids_are_returned(pg, ids, monkeypatch):
    fresh, stale = _seed(pg, ids)
    result = _call(pg, monkeypatch, [*fresh, stale])
    assert sorted(i.extraction_item_id for i in result.items) == sorted(fresh)
    assert stale not in [i.extraction_item_id for i in result.items]


def test_b2_ids_outside_the_distribution_rows_alone_give_404(pg, ids, monkeypatch):
    _fresh, stale = _seed(pg, ids)
    with pytest.raises(HTTPException) as caught:
        _call(pg, monkeypatch, [stale])
    assert caught.value.status_code == 404


def test_b3_each_item_has_exactly_four_keys(pg, ids, monkeypatch):
    fresh, _stale = _seed(pg, ids)
    result = _call(pg, monkeypatch, fresh)
    assert len(result.items) == 2
    for item in result.items:
        assert set(item.model_dump()) == {"extraction_item_id", "raw_text", "line_start", "line_end"}
        assert item.raw_text == "架空"
