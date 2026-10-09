"""型番の重なり判定を使い捨て PostgreSQL で確かめる（CI の PG 付きジョブで実行）。

SQL の is_active 絞り込みと、update_product_detail の配線は実 DB でしか確かめられない。
ローカルでは実行しない（PG を立てない方針）。
"""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.services import tcg_product_code_collision_svc as collisions
from app.services import tcg_product_detail_svc as details
from tests.test_tcg_product_detail_pg import (  # noqa: F401  (fixtures)
    _pid,
    detail_db,
    edit_pg,
    edit_values,
    pg,
    product_db,
    pytestmark,
)

_INSERT = (
    "INSERT INTO public.products "
    "(product_code,name,name_en,mark,category_class,is_active,required_output_value) "
    "VALUES (:code,:name,'',:mark,'Original',:active,'Keep this')"
)


async def _add(db, code, name, mark, active):
    await db.execute(
        text(_INSERT), {"code": code, "name": name, "mark": mark, "active": active}
    )


async def test_finds_only_active_products_with_equal_normalized_code(detail_db):  # noqa: F811
    db, _ = detail_db
    await _add(db, "COL-A", "Alpha box", "ST-01", True)
    await _add(db, "COL-B", "Beta box", "st01", True)
    await _add(db, "COL-C", "Gamma box", "ST01", False)
    await _add(db, "COL-D", "Delta box", "ST02", True)
    a = await _pid(db, "COL-A")
    b = await _pid(db, "COL-B")

    both = await collisions.find_code_collisions(
        db, product_code="", mark="ST 01", name="Self",
        search_keywords=[], exclude_keywords=[],
    )
    without_a = await collisions.find_code_collisions(
        db, product_code="", mark="ST 01", name="Self",
        search_keywords=[], exclude_keywords=[], exclude_product_id=a,
    )

    assert sorted(int(c["product_id"]) for c in both) == sorted([a, b])
    assert [int(c["product_id"]) for c in without_a] == [b]


@pytest.mark.asyncio
async def test_update_product_detail_returns_collisions_and_still_saves(edit_pg):  # noqa: F811
    connection, url = edit_pg
    with connection.cursor() as cur:
        cur.execute(
            "INSERT INTO public.products "
            "(product_code,name,category_class,mark,is_active,required_output_value) "
            "VALUES ('COL-OTHER','Other box','Keep category','ST01',true,'Keep output') RETURNING id"
        )
        other_id = cur.fetchone()[0]
    engine = create_async_engine(url)
    try:
        async with AsyncSession(engine) as db:
            pid = await _pid(db, "DETAIL")
            snapshot = await details.get_product_detail(db, pid)
            values = edit_values(snapshot)
            values["mark"] = "ST-01"
            result = await details.update_product_detail(
                db, pid, values, snapshot["revision"], "ci-reviewer"
            )
        assert result["product"]["mark"] == "ST-01"
        assert [c["product_id"] for c in result["code_collisions"]] == [str(other_id)]
        assert result["code_collisions"][0]["matched_field"] == "mark"
    finally:
        await engine.dispose()
